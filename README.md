# Beyond Citation Entailment

[![validate](https://github.com/sergiofigueras/causal-evidence-audit/actions/workflows/validate.yml/badge.svg)](https://github.com/sergiofigueras/causal-evidence-audit/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This repository contains the LaTeX manuscript and complete reproducibility artifact for the 32-item Causal Evidence Audit pilot.

- Public source-code repository: <https://github.com/sergiofigueras/causal-evidence-audit>
- Immutable release: <https://github.com/sergiofigueras/causal-evidence-audit/releases/tag/v0.1.0>

## TL;DR

**Research question:** If a RAG system gives the correct answer and cites passages that support it, does that show that those passages determined the answer?

**Short answer:** Not necessarily. A single observed response shows that the answer is compatible with its cited sources, but cannot show whether the system actually relied on them. It might use parametric memory, a shortcut, or a prior draft and attach a suitable citation afterward. The paper proposes the *Causal Evidence Audit* (CEA): ask the same question with the original evidence, with a minimal change to a decisive fact that changes the correct answer, and with an indispensable source removed. To pass, the system must answer correctly in both complete evidence worlds, abstain when the remaining evidence is insufficient, and cite the complete proof chain.

**How this differs from existing tests:** Current approaches cover parts of this problem: [Ragas](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/) measures answer faithfulness to retrieved context; [ContextCite](https://proceedings.neurips.cc/paper_files/paper/2024/hash/adbea136219b64db96a9941e4249a857-Abstract-Conference.html) and [RAGONITE](https://arxiv.org/abs/2412.10571) use context removal for attribution; and [SURE-RAG](https://arxiv.org/abs/2605.03534) evaluates evidence sufficiency and selective abstention with counterfactual swaps. Among the approaches surveyed in the paper, none makes correct answers in both minimally different, answer-changing evidence worlds, abstention after removing indispensable evidence, and complete oracle proof citations a single per-item pass condition. CEA's contribution is this joint protocol, rather than any one test in isolation.

**Pilot result:** Across 32 fictional items, two models, and two prompting regimes, the single-world pass rate for correct answers with complete proof citations ranged from 59.4% to 78.1%; the coverage-based joint causal score ranged from 0% to 31.3%. The gap exposes failures that a single-world check can miss, especially answering when an essential proof element is absent. This is a behavioral pilot with evidence supplied to the models: it does not test retrieval or establish how a model works internally.

## CEA-Extended (dataset schema v2): proposed protocol

The paper now specifies an extension for cases where a single changed fact and a single gold proof could give misleading results. A schema-v2 case includes the baseline, at least two independent answer-changing edits, an answer-preserving perturbation, an ablation that removes every valid proof, an ablation that leaves an alternative proof intact, and a condition with an explicit conflict-resolution policy.

For each answerable world, annotators record **all admissible minimal proof sets**. Coverage accepts citations containing any one complete proof; the strict score accepts citations equal to any one proof. A removal requires abstention only after an independent oracle confirms that no alternative proof survives. Conflicting sources follow a policy fixed before evaluation; an unresolved conflict calls for abstention. A separate retrieval audit reruns indexing and retrieval on edited corpus snapshots and distinguishes missing corpus evidence, retrieval misses, and synthesis errors. Held-out templates, domains, proof shapes, and source styles test generalization.

This is a **prospective protocol**, with one deterministic construction fixture and executable validation assertions. It has no new model scores. The original paper pilot, its 32 items, all 384 raw generations, and published metrics remain unchanged. Passing a finite black-box audit is evidence for the tested worlds, not proof that a system always relies on evidence; the manuscript gives a formal counterexample.

The schema-v2 runner's per-case Wilson intervals describe item-level variation only. Correlated templates and domains need a separate grouped analysis before making population-level claims.

## Contents

- `main.tex` — complete paper source.
- `references.bib` — BibTeX bibliography with direct source URLs.
- `main.pdf` — compiled verification copy.
- `reproducibility/causal_audit_core.py` — standard-library benchmark, parser, scorer, and metric implementation.
- `reproducibility/run_causal_grounding_pilot.py` — local MLX inference runner and provenance-manifest writer.
- `reproducibility/benchmark.json` — exact 32-item paired-world benchmark used in the paper.
- `reproducibility/qwen3-4b_responses.jsonl` — 192 raw Qwen generations.
- `reproducibility/llama3.2-3b_responses.jsonl` — 192 raw Llama generations.
- `reproducibility/summary.json` — combined machine-readable metrics and Wilson intervals.
- `reproducibility/run_manifest.json` — runtime, model revision, decoder, source, and artifact hashes.
- `reproducibility/validate_artifacts.py` — deep integrity validation and reproduction comparison.
- `reproducibility/validate_manuscript.py` — citation and publication-metadata checks.
- `reproducibility/extended_fixture.json` — deterministic schema-v2 worked case; not a model-response artifact.
- `reproducibility/validate_extended_fixture.py` — structural and logical assertions for the worked case.
- `requirements.in` — direct runtime dependencies.
- `requirements.txt` — fully resolved, hash-locked Python environment.
- `Makefile` — setup, compilation, validation, reproduction, and comparison commands.
- `CITATION.cff` — citation metadata for the manuscript and artifact.

## Validate the committed artifact

Validation uses only the Python standard library. It regenerates the benchmark, reparses all 384 raw outputs, recomputes every stored score and summary, verifies source and artifact checksums, checks the manuscript's citation keys and publication links, and validates the independent schema-v2 construction fixture.

```bash
make validate
```

## Build the paper

```bash
tectonic main.tex
```

The source also works with a conventional LaTeX/BibTeX toolchain supporting the packages declared in `main.tex`.

## Reproduce the pilot

The hash-locked experiment environment requires an Apple Silicon Mac, Python 3.12 or newer, and approximately 4 GB for model weights. On this Mac, `/usr/bin/python3` is too old; the example below selects the current Homebrew Python explicitly.

```bash
PYTHON=/opt/homebrew/bin/python3 make setup
make reproduce-and-validate
```

`make setup` rebuilds `.venv` so an older local interpreter cannot leak into the locked environment. `make reproduce` creates the same per-model file layout as the committed artifact. `make validate-reproduced` deeply validates the new run. `make compare` requires an identical benchmark and identical aggregate metrics, then reports any raw-text or parsed-field differences instead of assuming byte-level determinism.

The two complete prompt regimes and immutable model revisions are recorded in `reproducibility/causal_audit_core.py`. Generation uses greedy decoding at temperature zero. Greedy decoding removes sampling randomness but does not guarantee byte-identical output across changes in kernels, runtimes, chat templates, or hardware.

## Recorded release environment

- Date: 2026-09-12
- macOS 26.5.2
- Apple M4 Pro, 14 CPU cores, 48 GB unified memory
- Python 3.14.6
- MLX-LM 0.31.3
- MLX 0.32.2
- Transformers 5.17.0
- NumPy 2.5.3
- `mlx-community/Qwen3-4B-4bit`, revision `4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25`
- `mlx-community/Llama-3.2-3B-Instruct-4bit`, revision `7f0dc925e0d0afb0322d96f9255cfddf2ba5636e`

The hash-locked dependency set had no known vulnerabilities in a `pip-audit` check performed on 2026-09-12. This is a dated observation, not a guarantee about future disclosures; Dependabot is configured for ongoing monitoring.

## License

The repository is released under the [MIT License](LICENSE). Third-party model weights are not redistributed and remain subject to their own licenses.
