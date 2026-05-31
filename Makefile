# Bradesco BBI AI Challenge — standard commands
# Usage: make <target>

PYTHON ?= python3
VENV   ?= .venv
PY      = $(VENV)/bin/python
PIP     = $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help venv install demo demo-case1 demo-case2 test validate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

venv: ## Create the virtual environment
	$(PYTHON) -m venv $(VENV)

install: venv ## Install dependencies into the venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

demo: ## Run both cases end-to-end (mock mode if no OPENAI_API_KEY)
	$(PY) demo.py

demo-case1: ## Run only Case 1 (earnings call)
	$(PY) demo.py --case 1

demo-case2: ## Run only Case 2 (macro scenario)
	$(PY) demo.py --case 2

test: ## Run the automated test suite
	$(PY) -m pytest -q

validate: install test demo ## Full validation: install, test, then demo
	@echo "Validation complete."

clean: ## Remove caches and the venv
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
