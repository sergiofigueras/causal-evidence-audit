PYTHON ?= python3
VENV ?= .venv
ARTIFACT_DIR ?= reproducibility
REPRODUCED_DIR ?= reproduced_results
PY := $(VENV)/bin/python

.PHONY: setup paper paper-pt-br reproduce validate validate-reproduced compare reproduce-and-validate

setup:
	$(PYTHON) -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12 or newer is required"'
	$(PYTHON) -m venv --clear $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install --require-hashes -r requirements.txt

paper:
	tectonic main.tex

paper-pt-br:
	tectonic main_pt_br.tex

reproduce:
	HF_HUB_DISABLE_XET=1 $(PY) reproducibility/run_causal_grounding_pilot.py \
		--models qwen3-4b llama3.2-3b \
		--n-per-family 8 \
		--output-dir $(REPRODUCED_DIR)

validate:
	$(PYTHON) -m py_compile reproducibility/causal_audit_core.py
	$(PYTHON) -m py_compile reproducibility/run_causal_grounding_pilot.py
	$(PYTHON) -m py_compile reproducibility/validate_artifacts.py
	$(PYTHON) -m py_compile reproducibility/validate_manuscript.py
	$(PYTHON) -m py_compile reproducibility/validate_extended_fixture.py
	$(PYTHON) reproducibility/validate_artifacts.py --artifact-dir $(ARTIFACT_DIR)
	$(PYTHON) reproducibility/validate_manuscript.py
	$(PYTHON) reproducibility/validate_extended_fixture.py

validate-reproduced:
	$(PYTHON) reproducibility/validate_artifacts.py --artifact-dir $(REPRODUCED_DIR)

compare:
	$(PYTHON) reproducibility/validate_artifacts.py \
		--artifact-dir $(REPRODUCED_DIR) \
		--reference-dir $(ARTIFACT_DIR)

reproduce-and-validate: reproduce validate-reproduced compare
