#!/usr/bin/env python3
"""Validate the checked-in Causal Evidence Audit reproduction artifacts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODELS = {"qwen3-4b", "llama3.2-3b"}
REGIMES = {"baseline", "evidence_contract"}
CONDITIONS = {"world0", "world1", "ablated"}


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    benchmark = load_json(ROOT / "benchmark.json")
    assert len(benchmark) == 32, "benchmark must contain 32 items"
    item_ids = {item["id"] for item in benchmark}
    assert len(item_ids) == 32, "benchmark item IDs must be unique"

    rows = []
    for model in sorted(MODELS):
        model_rows = load_jsonl(ROOT / f"{model}_responses.jsonl")
        assert len(model_rows) == 192, f"{model} must contain 192 generations"
        rows.extend(model_rows)

        observed = {
            (row["item_id"], row["regime"], row["condition"])
            for row in model_rows
        }
        expected = {
            (item_id, regime, condition)
            for item_id in item_ids
            for regime in REGIMES
            for condition in CONDITIONS
        }
        assert observed == expected, f"{model} has missing or duplicate conditions"
        assert {row["model"] for row in model_rows} == {model}

    summaries = load_json(ROOT / "summary.json")
    observed_summaries = {(row["model"], row["regime"]) for row in summaries}
    expected_summaries = {(model, regime) for model in MODELS for regime in REGIMES}
    assert observed_summaries == expected_summaries, "summary configurations are incomplete"

    print(
        "Validated 32 benchmark items, 384 raw generations, "
        "and four model/regime summaries."
    )


if __name__ == "__main__":
    main()
