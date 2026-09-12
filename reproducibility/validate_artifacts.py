#!/usr/bin/env python3
"""Deeply validate Causal Evidence Audit artifacts using the standard library."""

import argparse
import hashlib
import json
from pathlib import Path

from causal_audit_core import (
    CONDITIONS,
    MODELS,
    REGIMES,
    build_items,
    score_generation,
    summarize,
)


HERE = Path(__file__).resolve().parent


class ValidationError(ValueError):
    """Raised when a committed or reproduced artifact is inconsistent."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def load_json(path):
    require(path.is_file(), f"missing file: {path}")
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_jsonl(path):
    require(path.is_file(), f"missing file: {path}")
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(root, manifest):
    require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    model_specs = manifest.get("models")
    require(isinstance(model_specs, dict) and model_specs, "manifest has no models")
    require(set(model_specs).issubset(MODELS), "manifest has an unknown model")
    for model, specification in model_specs.items():
        require(
            specification == MODELS[model],
            f"model repository or revision mismatch for {model}",
        )
    require(manifest.get("regimes") == list(REGIMES), "regime manifest mismatch")
    require(
        manifest.get("conditions") == list(CONDITIONS),
        "condition manifest mismatch",
    )
    require(
        manifest.get("decoder")
        == {"strategy": "greedy", "temperature": 0.0, "max_tokens": 96},
        "decoder manifest mismatch",
    )

    expected_artifacts = {
        "benchmark.json",
        *(f"{model}_responses.jsonl" for model in model_specs),
        "summary.json",
    }
    artifact_hashes = manifest.get("artifact_sha256")
    require(
        isinstance(artifact_hashes, dict)
        and set(artifact_hashes) == expected_artifacts,
        "manifest artifact checksum set mismatch",
    )
    for name, expected_hash in artifact_hashes.items():
        path = root / name
        require(path.is_file(), f"manifest artifact is missing: {path}")
        require(
            sha256_file(path) == expected_hash,
            f"artifact checksum mismatch: {path}",
        )
    source_hashes = manifest.get("source_sha256")
    require(
        isinstance(source_hashes, dict)
        and set(source_hashes)
        == {"causal_audit_core.py", "run_causal_grounding_pilot.py"},
        "manifest source checksum set mismatch",
    )
    for name, expected_hash in source_hashes.items():
        path = HERE / name
        require(path.is_file(), f"manifest source is missing: {path}")
        require(
            sha256_file(path) == expected_hash,
            f"source checksum mismatch: {path}",
        )
    return list(model_specs)


def validate_artifact_directory(root):
    root = root.resolve()
    manifest = load_json(root / "run_manifest.json")
    models = validate_manifest(root, manifest)
    n_per_family = manifest.get("n_per_family")
    require(isinstance(n_per_family, int), "manifest n_per_family must be an integer")

    benchmark = load_json(root / "benchmark.json")
    generated_benchmark = build_items(n_per_family)
    require(
        benchmark == generated_benchmark,
        "benchmark.json does not match the benchmark generator",
    )
    item_by_id = {item["id"]: item for item in benchmark}
    require(
        len(item_by_id) == len(benchmark),
        "benchmark item IDs must be unique",
    )

    rows = []
    for model in models:
        model_rows = load_jsonl(root / f"{model}_responses.jsonl")
        expected_count = len(benchmark) * len(REGIMES) * len(CONDITIONS)
        require(
            len(model_rows) == expected_count,
            f"{model} must contain {expected_count} generations",
        )
        observed = {
            (row.get("item_id"), row.get("regime"), row.get("condition"))
            for row in model_rows
        }
        expected = {
            (item_id, regime, condition)
            for item_id in item_by_id
            for regime in REGIMES
            for condition in CONDITIONS
        }
        require(observed == expected, f"{model} has missing or duplicate conditions")

        for row in model_rows:
            item = item_by_id[row["item_id"]]
            recomputed = score_generation(
                model,
                row["regime"],
                item,
                row["condition"],
                row["raw"],
            )
            require(
                row == recomputed,
                f"stored row differs from recomputed row: "
                f"{model}/{row['regime']}/{row['item_id']}/{row['condition']}",
            )
        rows.extend(model_rows)

    expected_generation_count = len(rows)
    require(
        manifest.get("generation_count") == expected_generation_count,
        "manifest generation count mismatch",
    )
    committed_summary = load_json(root / "summary.json")
    recomputed_summary = summarize(rows, benchmark)
    require(
        committed_summary == recomputed_summary,
        "summary.json differs from metrics recomputed from raw generations",
    )
    print(
        f"Validated {len(benchmark)} benchmark items, "
        f"{len(rows)} raw generations, every stored score, all checksums, "
        f"and {len(committed_summary)} recomputed model/regime summaries in {root}."
    )
    return {
        "benchmark": benchmark,
        "rows": rows,
        "summary": committed_summary,
    }


def compare_artifacts(reference, candidate):
    require(
        reference["benchmark"] == candidate["benchmark"],
        "candidate benchmark differs from the reference benchmark",
    )
    require(
        reference["summary"] == candidate["summary"],
        "candidate metrics differ from the reference metrics",
    )
    key = lambda row: (
        row["model"], row["regime"], row["item_id"], row["condition"]
    )
    reference_rows = {key(row): row for row in reference["rows"]}
    candidate_rows = {key(row): row for row in candidate["rows"]}
    require(
        set(reference_rows) == set(candidate_rows),
        "candidate generation keys differ from the reference",
    )
    raw_differences = sum(
        reference_rows[row_key]["raw"] != candidate_rows[row_key]["raw"]
        for row_key in reference_rows
    )
    scored_differences = sum(
        any(
            reference_rows[row_key][field] != candidate_rows[row_key][field]
            for field in reference_rows[row_key]
            if field != "raw"
        )
        for row_key in reference_rows
    )
    print(
        "Candidate reproduces the reference benchmark and all aggregate metrics; "
        f"raw text differs in {raw_differences}/{len(reference_rows)} rows and "
        f"parsed/scored fields differ in {scored_differences}/{len(reference_rows)} rows."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, default=HERE)
    parser.add_argument("--reference-dir", type=Path)
    args = parser.parse_args()
    candidate = validate_artifact_directory(args.artifact_dir)
    if args.reference_dir:
        reference = validate_artifact_directory(args.reference_dir)
        compare_artifacts(reference, candidate)


if __name__ == "__main__":
    main()
