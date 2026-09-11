PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: setup paper reproduce validate

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

paper:
	tectonic main.tex

reproduce:
	HF_HUB_DISABLE_XET=1 $(PY) reproducibility/run_causal_grounding_pilot.py \
		--models qwen3-4b llama3.2-3b \
		--n-per-family 8 \
		--output-dir reproduced_results

validate:
	$(PYTHON) -m py_compile reproducibility/run_causal_grounding_pilot.py
	$(PYTHON) reproducibility/validate_artifacts.py
