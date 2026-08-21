# Local CI. This project never spends CI minutes on a hosted runner; see docs/local-ci.md.
UV ?= uv
VENV := .venv
BIN := $(VENV)/bin

.DEFAULT_GOAL := help

.PHONY: help setup fmt lint test build check ci hooks clean

help: ## List available targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-8s %s\n", $$1, $$2}'

setup: ## Create the virtualenv and install skillforge with its dev tools
	$(UV) venv
	$(UV) pip install -e .
	$(UV) pip install pytest ruff

fmt: ## Format and autofix
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

lint: ## Static checks on the code and on the skills this repo ships
	$(BIN)/ruff format --check .
	$(BIN)/ruff check .
	$(BIN)/skillforge lint --strict

test: ## Run the test suite
	$(BIN)/python -m pytest

build: ## Re-render this repo's own skills
	$(BIN)/skillforge build

check: ## Fail if committed output is stale
	$(BIN)/skillforge check

ci: lint test check ## Everything that must pass before a commit lands

hooks: ## Install the git hooks that run `make ci`
	$(BIN)/skillforge install-hooks

clean: ## Remove build and cache artifacts
	rm -rf $(VENV) .pytest_cache .ruff_cache .skillforge/cache
