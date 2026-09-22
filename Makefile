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

.PHONY: lint test-unit test-attribute test-guardrails test-regression regen-regression test-all test-tutorials test-examples help setup conda-setup pip-setup docs docs-clean

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

test-attribute:  ## Attribute coverage tests
	$(RUN) pytest tests/attribute/ -s -v --tb=short

# --maxfail=0 overrides the -x in pyproject addopts: guardrail failures are
# domain findings, and one must not mask the assertions behind it.
test-guardrails:  ## Behavior guardrail tests
	$(RUN) pytest tests/guardrails/ -v --tb=short --maxfail=0

# --maxfail=0 as for guardrails: a failed activation guard must not mask the
# golden diff behind it.
test-regression:  ## Golden-baseline regression tests
	$(RUN) pytest tests/regression/ -v --tb=short --maxfail=0

# The one sanctioned way to update baselines (tests/regression/README.md);
# -s so the per-file regeneration summary prints.
regen-regression:  ## Regenerate golden baselines, then review the git diff
	$(RUN) pytest tests/regression/ -v --tb=short --maxfail=0 -s --regen-baselines

test-all:  ## Full test suite (all pytest suites + tutorials + examples)
	$(MAKE) test-unit
	$(MAKE) test-attribute
	$(MAKE) test-guardrails
	$(MAKE) test-regression
	$(MAKE) test-tutorials
	$(MAKE) test-examples

test-tutorials:  ## Run tutorial example solutions
	$(RUN) navigate tutorials/tutorial_1/example_solution/tutorial_1.nav -d ./assumptions -s
	$(RUN) navigate tutorials/tutorial_2/example_solution/tutorial_2.nav -d ./assumptions -s
	$(RUN) navigate tutorials/tutorial_3/example_solution/tutorial_3_scenarios/baseline/baseline.nav -d ./assumptions -s
	$(RUN) navigate tutorials/tutorial_3/example_solution/tutorial_3_scenarios/scenario_100/scenario_100.nav -d ./assumptions -s
	$(RUN) navigate tutorials/tutorial_3/example_solution/tutorial_3_scenarios/scenario_170/scenario_170.nav -d ./assumptions -s

test-examples:  ## Run simulations/examples
	$(RUN) navigate simulations/examples/example_1/example_1.nav -d ./assumptions -s
	$(RUN) navigate simulations/examples/example_2/example_2.nav -d ./assumptions -s
	$(RUN) navigate simulations/examples/example_3/example_3.nav -d ./assumptions -s

docs:  ## Stage content and build the documentation site (needs docs/requirements.txt installed)
	$(MAKE) -C docs html

docs-clean:  ## Remove the documentation build output
	$(MAKE) -C docs clean
