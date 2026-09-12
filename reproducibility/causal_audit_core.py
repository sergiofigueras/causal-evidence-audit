"""Standard-library benchmark construction, parsing, scoring, and summaries."""

import json
import math
import re


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

CONDITIONS = ("world0", "world1", "ablated")
MAX_ITEMS_PER_FAMILY = 8


def build_items(n_per_family=MAX_ITEMS_PER_FAMILY):
    if not 1 <= n_per_family <= MAX_ITEMS_PER_FAMILY:
        raise ValueError(
            f"n_per_family must be between 1 and {MAX_ITEMS_PER_FAMILY}, "
            f"got {n_per_family}"
        )

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
    try:
        obj = json.loads(text.strip())
    except json.JSONDecodeError:
        obj = None
    if not isinstance(obj, dict):
        upper = text.upper()
        answer = "INSUFFICIENT" if "INSUFFICIENT" in upper else text.strip()
        return answer, [], False

    answer_value = obj.get("answer", "")
    answer = str(answer_value).strip()
    citations = obj.get("citations", [])
    if not isinstance(citations, list):
        return answer, [], False

    citation_pattern = re.compile(r"D\d+")
    schema_valid = (
        set(obj) == {"answer", "citations"}
        and isinstance(answer_value, str)
        and all(
            isinstance(citation, str)
            and citation_pattern.fullmatch(citation.strip().upper())
            for citation in citations
        )
    )
    normalized_citations = sorted({
        str(citation).strip().upper()
        for citation in citations
        if citation_pattern.fullmatch(str(citation).strip().upper())
    })
    return answer, normalized_citations, schema_valid


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
    other_keys = [
        canonical_answer(value)
        for value in alternatives
        if canonical_answer(value) != expected_key
    ]
    return not any(other and other in answer_key for other in other_keys)


def condition_spec(item, condition):
    if condition == "world0":
        return item["worlds"][0], item["answers"][0], item["gold_citations"][0]
    if condition == "world1":
        return item["worlds"][1], item["answers"][1], item["gold_citations"][1]
    if condition == "ablated":
        docs = {
            key: value
            for key, value in item["worlds"][0].items()
            if key not in item["ablate"]
        }
        return docs, "INSUFFICIENT", []
    raise ValueError(f"unknown condition: {condition}")


def score_generation(model, regime, item, condition, output):
    docs, expected, gold_citations = condition_spec(item, condition)
    answer, citations, format_valid = parse_response(output)
    return {
        "model": model,
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
        "citation_complete": set(gold_citations).issubset(citations),
        "citation_exact": set(gold_citations) == set(citations),
        "citation_valid": set(citations).issubset(docs),
        "format_valid": format_valid,
        "raw": output,
    }


def wilson(successes, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    proportion = successes / n
    denominator = 1 + z * z / n
    center = (proportion + z * z / (2 * n)) / denominator
    half = z * math.sqrt(
        proportion * (1 - proportion) / n + z * z / (4 * n * n)
    ) / denominator
    return [center - half, center + half]


def summarize(rows, items):
    by_item = {item["id"]: item for item in items}
    groups = {}
    for row in rows:
        groups.setdefault((row["model"], row["regime"]), {})[
            (row["item_id"], row["condition"])
        ] = row

    summaries = []
    for model, regime in (
        (model, regime)
        for model in MODELS
        for regime in REGIMES
        if (model, regime) in groups
    ):
        group = groups[(model, regime)]
        indicators = {
            "world0_accuracy": [], "world1_accuracy": [],
            "paired_responsiveness": [], "ablation_abstention": [],
            "ablation_citation_validity": [], "observational_support": [],
            "coverage_causal_evidence_score": [], "causal_evidence_score": [],
            "format_validity": [],
        }
        family_indicators = {}
        for item_id, item in by_item.items():
            world0 = group[(item_id, "world0")]
            world1 = group[(item_id, "world1")]
            ablated = group[(item_id, "ablated")]
            paired = (
                world0["correct"]
                and world1["correct"]
                and canonical_answer(world0["answer"])
                != canonical_answer(world1["answer"])
            )
            coverage_score = (
                paired
                and ablated["abstained"]
                and ablated["citation_valid"]
                and world0["citation_complete"]
                and world1["citation_complete"]
            )
            strict_score = (
                coverage_score
                and not ablated["citations"]
                and world0["citation_exact"]
                and world1["citation_exact"]
            )
            values = {
                "world0_accuracy": world0["correct"],
                "world1_accuracy": world1["correct"],
                "paired_responsiveness": paired,
                "ablation_abstention": ablated["abstained"],
                "ablation_citation_validity": ablated["citation_valid"],
                "observational_support": world0["correct"] and world0["citation_complete"],
                "coverage_causal_evidence_score": coverage_score,
                "causal_evidence_score": strict_score,
                "format_validity": (
                    world0["format_valid"]
                    and world1["format_valid"]
                    and ablated["format_valid"]
                ),
            }
            for key, value in values.items():
                indicators[key].append(int(value))
            family_indicators.setdefault(item["family"], []).append(int(strict_score))

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
                key: sum(values) / len(values)
                for key, values in family_indicators.items()
            },
        })
    return summaries
