# Beyond Citation Entailment

This bundle contains the LaTeX manuscript and the complete reproducibility artifact for the 32-item pilot.

Public source-code repository: <https://github.com/sergiofigueras/causal-evidence-audit>

## Contents

- `main.tex` — complete paper source.
- `references.bib` — BibTeX bibliography with direct arXiv URLs.
- `main.pdf` — compiled verification copy.
- `reproducibility/run_causal_grounding_pilot.py` — benchmark generator, local inference runner, parser, and scorer.
- `reproducibility/benchmark.json` — the exact 32-item paired-world benchmark used in the paper.
- `reproducibility/qwen3-4b_responses.jsonl` — 192 raw Qwen generations.
- `reproducibility/llama3.2-3b_responses.jsonl` — 192 raw Llama generations.
- `reproducibility/summary.json` — combined machine-readable metrics and Wilson intervals.
- `reproducibility/validate_artifacts.py` — standard-library integrity checks for the committed artifacts.
- `requirements.txt` — pinned Python environment used by the pilot.
- `Makefile` — convenience commands for setup, compilation, validation, and reproduction.
- `CITATION.cff` — local citation metadata for the manuscript and artifact.

## Build the paper

From this directory, run:

```bash
tectonic main.tex
```

The source also works with a conventional LaTeX/BibTeX toolchain supporting the packages declared in `main.tex`.

## Reproduce the pilot

The experiment requires an Apple Silicon Mac and downloads approximately 4 GB of model weights.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make reproduce
```

Run `make validate` to check the committed benchmark, raw generations, summaries, and Python syntax without downloading model weights. The two complete prompt regimes are the `REGIMES` constants in `reproducibility/run_causal_grounding_pilot.py`. Model repository IDs and immutable revisions are recorded in its `MODELS` constant and passed directly to MLX-LM.

Greedy decoding is deterministic for a fixed software and model snapshot, but changes in kernels, chat templates, or repository revisions can still alter exact outputs.

## Recorded environment

- Date: 2026-09-11
- macOS 26.5.2
- Apple M4 Pro, 14 CPU cores, 48 GB unified memory
- Python 3.9.6
- MLX-LM 0.29.1
- MLX 0.29.3
- Transformers 4.57.6
- NumPy 2.0.2
- `mlx-community/Qwen3-4B-4bit`, revision `4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25`
- `mlx-community/Llama-3.2-3B-Instruct-4bit`, revision `7f0dc925e0d0afb0322d96f9255cfddf2ba5636e`
