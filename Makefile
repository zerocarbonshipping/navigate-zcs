# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

ENV_NAME := nav

# A local .venv wins over the conda env: the conda env carries one editable
# install pointing at one checkout, so a second git worktree would otherwise
# import the primary checkout's source. Without a local .venv, use conda if the
# env exists, else the .venv path anyway.
ifneq ($(wildcard $(CURDIR)/.venv/bin/python),)
  RUN := env PATH="$(CURDIR)/.venv/bin:$(PATH)"
else ifeq ($(shell conda env list 2>/dev/null | grep -q "^$(ENV_NAME)[[:space:]]" && echo 1),1)
  RUN := conda run -n $(ENV_NAME)
else
  RUN := env PATH="$(CURDIR)/.venv/bin:$(PATH)"
endif

.PHONY: lint test-unit test-e2e test-all test-examples help setup conda-setup pip-setup docs docs-clean

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

conda-setup:  ## Create conda env with Python 3.13 and install package in editable mode
	@if ! command -v conda >/dev/null 2>&1; then \
		echo "Error: conda is not installed or not on PATH."; \
		exit 1; \
	fi
	@if conda env list | grep -q "^$(ENV_NAME)[[:space:]]"; then \
		echo "Updating existing '$(ENV_NAME)' environment..."; \
	else \
		echo "Creating '$(ENV_NAME)' environment..."; \
		conda create -n $(ENV_NAME) -c conda-forge python=3.13 pip -y; \
	fi
	@conda run -n $(ENV_NAME) pip install -e ".[dev]" --quiet

pip-setup:  ## Create venv and install package with dev dependencies (no conda required). Preferred in web.
	@if [ ! -d .venv ]; then \
		echo "Creating virtual environment..."; \
		python3.13 -m venv .venv; \
	fi
	@.venv/bin/pip install -q -e ".[dev]"

lint:  ## Run ruff, mypy, and REUSE checks
	$(RUN) ruff check navigate tests
	$(RUN) ruff format --check navigate tests
	$(RUN) mypy navigate
	$(RUN) reuse lint

test-unit:  ## Unit + contract tests
	$(RUN) pytest tests/unit/ -v --tb=short

# --maxfail=0 overrides the -x in pyproject addopts: one failing combination
# must not mask the others behind it.
test-e2e:  ## End-to-end deck tests (attribute coverage + input combinations)
	$(RUN) pytest tests/end_to_end/ -v --tb=short --maxfail=0

test-all:  ## Full test suite (pytest suites + examples)
	$(MAKE) test-unit
	$(MAKE) test-e2e
	$(MAKE) test-examples

test-examples:  ## Run simulations/examples
	$(RUN) navigate simulations/examples/example_1/example_1.nav -d ./assumptions -s
	$(RUN) navigate simulations/examples/example_2/example_2.nav -d ./assumptions -s
	$(RUN) navigate simulations/examples/example_3/example_3.nav -d ./assumptions -s

docs:  ## Stage content and build the documentation site (needs docs/requirements.txt installed)
	$(RUN) $(MAKE) -C docs html

docs-clean:  ## Remove the documentation build output
	$(MAKE) -C docs clean
