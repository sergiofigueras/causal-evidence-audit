#!/usr/bin/env python3
"""Run the greedy-decoded Causal Evidence Audit pilot on local MLX models."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

from causal_audit_core import (
    CONDITIONS,
    MAX_ITEMS_PER_FAMILY,
    MODELS,
    REGIMES,
    build_items,
    condition_spec,
    render_user_prompt,
    score_generation,
    summarize,
)


PACKAGE_DISTRIBUTIONS = (
    "mlx",
    "mlx-lm",
    "numpy",
    "huggingface-hub",
    "transformers",
    "tokenizers",
    "safetensors",
    "sentencepiece",
    "protobuf",
)


def bounded_family_count(value):
    count = int(value)
    if not 1 <= count <= MAX_ITEMS_PER_FAMILY:
        raise argparse.ArgumentTypeError(
            f"must be between 1 and {MAX_ITEMS_PER_FAMILY}"
        )
    return count


def apply_chat_template(tokenizer, model_name, system, user):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    if "qwen" in model_name.lower():
        kwargs["enable_thinking"] = False
    return tokenizer.apply_chat_template(messages, **kwargs)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installed_versions():
    versions = {}
    for distribution in PACKAGE_DISTRIBUTIONS:
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def write_manifest(output_dir, rows, n_per_family, model_keys):
    script_dir = Path(__file__).resolve().parent
    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": [str(value) for value in sys.argv],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": installed_versions(),
        "models": {key: MODELS[key] for key in model_keys},
        "regimes": list(REGIMES),
        "conditions": list(CONDITIONS),
        "n_per_family": n_per_family,
        "generation_count": len(rows),
        "decoder": {
            "strategy": "greedy",
            "temperature": 0.0,
            "max_tokens": 96,
        },
        "source_sha256": {
            "causal_audit_core.py": sha256_file(
                script_dir / "causal_audit_core.py"
            ),
            "run_causal_grounding_pilot.py": sha256_file(
                Path(__file__).resolve()
            ),
        },
        "artifact_sha256": {},
    }
    artifact_names = [
        "benchmark.json",
        *(f"{model}_responses.jsonl" for model in model_keys),
        "summary.json",
    ]
    manifest["artifact_sha256"] = {
        name: sha256_file(output_dir / name) for name in artifact_names
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models", nargs="+", choices=sorted(MODELS), default=list(MODELS)
    )
    parser.add_argument(
        "--n-per-family", type=bounded_family_count,
        default=MAX_ITEMS_PER_FAMILY,
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("work/pilot_results")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    items = build_items(args.n_per_family)
    (args.output_dir / "benchmark.json").write_text(
        json.dumps(items, indent=2) + "\n", encoding="utf-8"
    )
    rows = []
    sampler = make_sampler(temp=0.0)

    for model_key in args.models:
        model_spec = MODELS[model_key]
        print(
            f"Loading {model_key} ({model_spec['repo']}@{model_spec['revision']})",
            flush=True,
        )
        model, tokenizer = load(
            model_spec["repo"], revision=model_spec["revision"]
        )
        for regime, system in REGIMES.items():
            started = time.time()
            for index, item in enumerate(items, start=1):
                for condition in CONDITIONS:
                    docs, _, _ = condition_spec(item, condition)
                    user = render_user_prompt(item, docs)
                    prompt = apply_chat_template(
                        tokenizer, model_key, system, user
                    )
                    output = generate(
                        model,
                        tokenizer,
                        prompt=prompt,
                        max_tokens=96,
                        sampler=sampler,
                        verbose=False,
                    )
                    rows.append(
                        score_generation(
                            model_key, regime, item, condition, output
                        )
                    )
                if index % 4 == 0:
                    print(
                        f"  {regime}: {index}/{len(items)} items "
                        f"({time.time()-started:.1f}s)",
                        flush=True,
                    )
        del model, tokenizer

    for model_key in args.models:
        model_rows = [row for row in rows if row["model"] == model_key]
        (args.output_dir / f"{model_key}_responses.jsonl").write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in model_rows
            ),
            encoding="utf-8",
        )
    summary = summarize(rows, items)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    stale_combined = args.output_dir / "responses.jsonl"
    if stale_combined.exists():
        stale_combined.unlink()
    write_manifest(args.output_dir, rows, args.n_per_family, args.models)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
