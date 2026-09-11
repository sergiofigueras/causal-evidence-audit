#!/usr/bin/env python3
"""Run a deterministic pilot of paired evidence interventions on local MLX LMs.

The benchmark uses fictional entities so that answers must be derived from the
provided documents.  Each item has two minimally different evidence worlds and
an ablation in which the decisive evidence is removed.
"""

import argparse
import json
import math
import re
import time
from pathlib import Path

import numpy as np
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler


MODELS = {
    "qwen3-4b": {
        "repo": "mlx-community/Qwen3-4B-4bit",
        "revision": "4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25",
    },
    "llama3.2-3b": {
        "repo": "mlx-community/Llama-3.2-3B-Instruct-4bit",
        "revision": "7f0dc925e0d0afb0322d96f9255cfddf2ba5636e",
    },
}

REGIMES = {
    "baseline": (
        "Answer the question using only the numbered sources. If the sources do "
        "not determine the answer, answer INSUFFICIENT. Return exactly one JSON "
        "object with keys answer and citations. citations must be a list of source "
        "IDs such as [\"D1\"]. Do not add prose."
    ),
    "evidence_contract": (
        "Use only the numbered sources. Internally identify the smallest complete "
        "proof chain for the answer. Answer only when every necessary link is "
        "explicitly supported; otherwise answer INSUFFICIENT. Treat the current "
        "sources as authoritative even when their entities are unfamiliar. Return "
        "exactly one JSON object with keys answer and citations. citations must list "
        "every source in the proof chain and no irrelevant source. Do not add prose."
    ),
}


def build_items(n_per_family=8):
    colors = [
        ("Avenite", "Borelite"), ("Ceryx", "Dovran"),
        ("Elnor", "Fasmin"), ("Galdite", "Hesper"),
        ("Ilyron", "Jaspar"), ("Kelmite", "Lunex"),
        ("Mavrin", "Norell"), ("Orphite", "Praxen"),
    ]
    places = [
        ("Aldermere", "Bramblecross"), ("Cindervale", "Duskhaven"),
        ("Emberfall", "Frostmere"), ("Glimmerbay", "Highfen"),
        ("Ivydell", "Juniper Reach"), ("Kestrel Point", "Larkspur"),
        ("Moonridge", "Northbarrow"), ("Oakstrand", "Pinewatch"),
    ]
    agents = ["Vela", "Rook", "Sable", "Tern", "Wren", "Yarrow", "Zephyr", "Kite"]
    items = []

    for i in range(n_per_family):
        a, b = colors[i]
        reactor = f"Reactor-{17 + i}"
        common = {
            "D2": f"{reactor} was commissioned during audit cycle {40 + i}.",
            "D3": f"A preliminary trial evaluated both {a} and {b} without authorizing either.",
            "D4": "Authorization is defined by the current registry, not by preliminary trials.",
        }
        worlds = []
        for answer in (a, b):
            docs = {"D1": f"The current registry states that the authorized coolant for {reactor} is {answer}."}
            docs.update(common)
            worlds.append(docs)
        items.append({
            "id": f"direct-{i+1:02d}",
            "family": "direct",
            "question": f"Which coolant is currently authorized for {reactor}?",
            "answers": [a, b],
            "worlds": worlds,
            "gold_citations": [["D1"], ["D1"]],
            "ablate": ["D1"],
        })

    for i in range(n_per_family):
        depot_a, depot_b = places[i]
        cipher_a, cipher_b = colors[(i + 3) % len(colors)]
        courier = agents[i]
        base = {
            "D2": f"Every parcel routed through {depot_a} uses the {cipher_a} cipher.",
            "D3": f"Every parcel routed through {depot_b} uses the {cipher_b} cipher.",
            "D4": f"Courier {courier} carries sealed research parcels.",
            "D5": f"The {cipher_a} and {cipher_b} ciphers are incompatible.",
        }
        worlds = []
        for depot in (depot_a, depot_b):
            docs = {"D1": f"The dispatch ledger routes courier {courier} through {depot}."}
            docs.update(base)
            worlds.append(docs)
        items.append({
            "id": f"twohop-{i+1:02d}",
            "family": "two-hop",
            "question": f"Which cipher is used for courier {courier}'s parcel?",
            "answers": [cipher_a, cipher_b],
            "worlds": worlds,
            "gold_citations": [["D1", "D2"], ["D1", "D3"]],
            "ablate": ["D1"],
        })

    for i in range(n_per_family):
        station_a, station_b = places[i]
        low = 31 + 3 * i
        mid = low + 7
        high = mid + 9
        worlds = [
            {
                "D1": f"The verified output of {station_a} is {high} teracycles.",
                "D2": f"The verified output of {station_b} is {mid} teracycles.",
                "D3": "The station with the larger verified output ranks first.",
                "D4": f"An obsolete estimate placed {station_b} at {low} teracycles.",
            },
            {
                "D1": f"The verified output of {station_a} is {low} teracycles.",
                "D2": f"The verified output of {station_b} is {mid} teracycles.",
                "D3": "The station with the larger verified output ranks first.",
                "D4": f"An obsolete estimate placed {station_b} at {high} teracycles.",
            },
        ]
        items.append({
            "id": f"compare-{i+1:02d}",
            "family": "comparison",
            "question": "Which station ranks first by verified output?",
            "answers": [station_a, station_b],
            "worlds": worlds,
            "gold_citations": [["D1", "D2", "D3"], ["D1", "D2", "D3"]],
            "ablate": ["D1"],
        })

    for i in range(n_per_family):
        protocol_a, protocol_b = colors[(i + 5) % len(colors)]
        site = places[(i + 2) % len(places)][0]
        threshold = 50 + i
        worlds = []
        for index in (threshold + 6, threshold - 6):
            worlds.append({
                "D1": (
                    f"Policy K-{i+1} requires protocol {protocol_a} when the stability index "
                    f"is above {threshold}; otherwise it requires protocol {protocol_b}."
                ),
                "D2": f"The current stability index at {site} is {index}.",
                "D3": f"Both {protocol_a} and {protocol_b} remain available at {site}.",
                "D4": "Availability does not determine which protocol policy requires.",
            })
        items.append({
            "id": f"conditional-{i+1:02d}",
            "family": "conditional",
            "question": f"Which protocol does Policy K-{i+1} currently require at {site}?",
            "answers": [protocol_a, protocol_b],
            "worlds": worlds,
            "gold_citations": [["D1", "D2"], ["D1", "D2"]],
            "ablate": ["D2"],
        })

    return items


def render_user_prompt(item, docs):
    lines = [f"[{key}] {value}" for key, value in docs.items()]
    return "SOURCES\n" + "\n".join(lines) + "\n\nQUESTION\n" + item["question"]


def parse_response(text):
    candidates = re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL)
    obj = None
    for candidate in reversed(candidates):
        try:
            obj = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(obj, dict):
        upper = text.upper()
        answer = "INSUFFICIENT" if "INSUFFICIENT" in upper else text.strip()
        return answer, [], False
    answer = str(obj.get("answer", "")).strip()
    citations = obj.get("citations", [])
    if not isinstance(citations, list):
        return answer, [], False
    schema_valid = (
        "answer" in obj
        and "citations" in obj
        and all(isinstance(c, str) and re.fullmatch(r"D\d+", c.strip().upper()) for c in citations)
    )
    citations = [str(c).strip().upper() for c in citations if re.fullmatch(r"D\d+", str(c).strip().upper())]
    return answer, sorted(set(citations)), schema_valid


def canonical_answer(answer):
    return re.sub(r"[^a-z0-9]+", "", answer.lower())


def is_abstention(answer):
    key = canonical_answer(answer)
    markers = (
        "insufficient", "notspecified", "notprovided", "cannotdetermine",
        "cannotbedetermined", "unabletodetermine", "indeterminate",
    )
    return any(marker in key for marker in markers)


def answer_matches(answer, expected, alternatives):
    if canonical_answer(expected) == canonical_answer("INSUFFICIENT"):
        return is_abstention(answer)
    answer_key = canonical_answer(answer)
    expected_key = canonical_answer(expected)
    if expected_key not in answer_key:
        return False
    other_keys = [canonical_answer(value) for value in alternatives if canonical_answer(value) != expected_key]
    return not any(other and other in answer_key for other in other_keys)


def apply_chat_template(tokenizer, model_name, system, user):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    if "qwen" in model_name.lower():
        kwargs["enable_thinking"] = False
    return tokenizer.apply_chat_template(messages, **kwargs)


def wilson(successes, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [center - half, center + half]


def summarize(rows, items):
    by_item = {item["id"]: item for item in items}
    groups = {}
    for row in rows:
        groups.setdefault((row["model"], row["regime"]), {})[(row["item_id"], row["condition"])] = row
    summaries = []
    for (model, regime), group in groups.items():
        indicators = {
            "world0_accuracy": [], "world1_accuracy": [], "paired_responsiveness": [],
            "ablation_abstention": [], "observational_support": [],
            "coverage_causal_evidence_score": [], "causal_evidence_score": [],
            "format_validity": [],
        }
        family_indicators = {}
        for item_id, item in by_item.items():
            w0 = group[(item_id, "world0")]
            w1 = group[(item_id, "world1")]
            ab = group[(item_id, "ablated")]
            c0 = w0["correct"] and w0["citation_complete"]
            c1 = w1["correct"] and w1["citation_complete"]
            paired = w0["correct"] and w1["correct"] and canonical_answer(w0["answer"]) != canonical_answer(w1["answer"])
            coverage_ces = paired and ab["abstained"] and w0["citation_complete"] and w1["citation_complete"]
            ces = paired and ab["abstained"] and w0["citation_exact"] and w1["citation_exact"]
            vals = {
                "world0_accuracy": w0["correct"],
                "world1_accuracy": w1["correct"],
                "paired_responsiveness": paired,
                "ablation_abstention": ab["abstained"],
                "observational_support": c0,
                "coverage_causal_evidence_score": coverage_ces,
                "causal_evidence_score": ces,
                "format_validity": w0["format_valid"] and w1["format_valid"] and ab["format_valid"],
            }
            for key, value in vals.items():
                indicators[key].append(int(value))
            family_indicators.setdefault(item["family"], []).append(int(ces))

        metric_block = {}
        for key, values in indicators.items():
            successes = int(sum(values))
            metric_block[key] = {
                "rate": successes / len(values),
                "count": successes,
                "n": len(values),
                "wilson95": wilson(successes, len(values)),
            }
        summaries.append({
            "model": model,
            "regime": regime,
            "metrics": metric_block,
            "causal_evidence_score_by_family": {
                key: sum(vals) / len(vals) for key, vals in family_indicators.items()
            },
        })
    return summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--n-per-family", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=Path("work/pilot_results"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    items = build_items(args.n_per_family)
    (args.output_dir / "benchmark.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
    rows = []
    sampler = make_sampler(temp=0.0)

    for model_key in args.models:
        model_spec = MODELS[model_key]
        repo = model_spec["repo"]
        revision = model_spec["revision"]
        print(f"Loading {model_key} ({repo}@{revision})", flush=True)
        model, tokenizer = load(repo, revision=revision)
        for regime, system in REGIMES.items():
            started = time.time()
            for index, item in enumerate(items, start=1):
                conditions = [
                    ("world0", item["worlds"][0], item["answers"][0], item["gold_citations"][0]),
                    ("world1", item["worlds"][1], item["answers"][1], item["gold_citations"][1]),
                ]
                ablated_docs = {k: v for k, v in item["worlds"][0].items() if k not in item["ablate"]}
                conditions.append(("ablated", ablated_docs, "INSUFFICIENT", []))
                for condition, docs, expected, gold_citations in conditions:
                    user = render_user_prompt(item, docs)
                    prompt = apply_chat_template(tokenizer, model_key, system, user)
                    output = generate(model, tokenizer, prompt=prompt, max_tokens=96, sampler=sampler, verbose=False)
                    answer, citations, format_valid = parse_response(output)
                    valid_docs = set(docs)
                    row = {
                        "model": model_key,
                        "regime": regime,
                        "item_id": item["id"],
                        "family": item["family"],
                        "condition": condition,
                        "expected": expected,
                        "answer": answer,
                        "citations": citations,
                        "gold_citations": gold_citations,
                        "correct": answer_matches(answer, expected, item["answers"]),
                        "abstained": is_abstention(answer),
                        "citation_complete": set(gold_citations).issubset(set(citations)),
                        "citation_exact": set(gold_citations) == set(citations),
                        "citation_valid": set(citations).issubset(valid_docs),
                        "format_valid": format_valid,
                        "raw": output,
                    }
                    rows.append(row)
                if index % 4 == 0:
                    print(f"  {regime}: {index}/{len(items)} items ({time.time()-started:.1f}s)", flush=True)
        del model, tokenizer

    summaries = summarize(rows, items)
    (args.output_dir / "responses.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    (args.output_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2), flush=True)


if __name__ == "__main__":
    main()
