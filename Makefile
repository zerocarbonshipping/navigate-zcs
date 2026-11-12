# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

ENV_NAME := nav

# bash for its `time`, which ends a lint or a deck run with its wall time; the
# pytest suites print their own
SHELL := bash
export TIMEFORMAT := wall time %1Rs

# The tools run from a local .venv, else from the conda env if it exists, else
# from whatever is on PATH. The conda env carries one editable install pointing
# at one checkout, so in any other checkout it imports someone else's source:
# every target that imports navigate depends on own-environment, which refuses
# that.
ifneq ($(wildcard $(CURDIR)/.venv/bin/python),)
  RUN := env PATH="$(CURDIR)/.venv/bin:$$PATH"
else ifeq ($(shell conda env list 2>/dev/null | grep -q "^$(ENV_NAME)[[:space:]]" && echo 1),1)
  RUN := conda run -n $(ENV_NAME)
endif

# The navigate command and the test helpers both prefer this variable to the
# checkout's own folder, so a caller's export would make every run read another
# checkout's assumptions.
export ASSUMPTIONS_DATA_DIR := $(CURDIR)/assumptions

# The interpreter every workload runs through, so that it imports the navigate
# own-environment probes; -P keeps the current directory off sys.path, as the
# installed pytest and navigate commands do.
PYTHON := python -P

# Prints the folder navigate imports from, nothing if it does not import.
NAVIGATE_PATH := $(PYTHON) -c 'import navigate; print(navigate.__path__[0])' 2>/dev/null

.PHONY: help conda-setup pip-setup lint fix check own-environment test-unit \
	test-e2e test-examples test-all compare-results docs docs-clean clean

help:  ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# The env carries one editable install, so setting it up here would take it
# from the checkout it runs now. A fresh env, or one that runs no checkout or
# this one, may be set up.
conda-setup:  ## Create conda env with Python 3.13 and install package in editable mode
	@if ! command -v conda >/dev/null 2>&1; then \
		echo "Error: conda is not installed or not on PATH."; \
		exit 1; \
	fi
	@where=$$(conda run -n $(ENV_NAME) $(NAVIGATE_PATH)); \
	case "$$where" in \
		"" | "$(CURDIR)/navigate" | */site-packages/navigate) ;; \
		*) echo "Error: the conda env '$(ENV_NAME)' runs the checkout at '$${where%/navigate}'."; \
		   echo "Run 'make pip-setup' for an environment of this checkout's own, or remove the env first to move it here: conda env remove -n $(ENV_NAME)"; \
		   exit 1 ;; \
	esac
	@if conda env list | grep -q "^$(ENV_NAME)[[:space:]]"; then \
		echo "Updating existing '$(ENV_NAME)' environment..."; \
	else \
		echo "Creating '$(ENV_NAME)' environment..."; \
		conda create -n $(ENV_NAME) -c conda-forge python=3.13 pip -y; \
	fi
	@conda run -n $(ENV_NAME) pip install -e ".[dev]" --quiet

# A .venv made on Windows keeps its executables in Scripts/, not bin/, so
# nothing here can run it.
pip-setup:  ## Create this checkout's own .venv with an editable install and the dev extras (no conda)
	@if [ -d .venv/Scripts ]; then \
		echo "Error: .venv is a Windows-layout environment (Scripts/, no bin/), which make cannot use."; \
		echo "Delete it and rerun if nothing on Windows uses it; else run 'make conda-setup', or 'make pip-setup' in a git worktree."; \
		exit 1; \
	fi
	@[ -d .venv ] || python3.13 -m venv .venv
	@.venv/bin/pip install -q -e ".[dev]"

lint:  ## Run ruff, mypy, and REUSE checks
	@time { \
		$(RUN) ruff check navigate tests && \
		$(RUN) ruff format --check navigate tests && \
		$(RUN) mypy navigate && \
		$(RUN) reuse lint; \
	}

fix:  ## Apply ruff's fixes and formatting to navigate/ (tests/ are left to their owners)
	$(RUN) ruff check --fix navigate
	$(RUN) ruff format navigate

check: lint test-unit  ## Lint and unit suite: the check before a pull request

# This checkout's source passes, and so does an installed copy, as in CI's test
# job.
own-environment:
	@where=$$($(RUN) $(NAVIGATE_PATH)); \
	case "$$where" in \
		"$(CURDIR)/navigate" | */site-packages/navigate) ;; \
		*) echo "Error: navigate imports from '$${where:-nowhere}', not from this checkout."; \
		   echo "Run 'make pip-setup' to create this checkout's own environment."; \
		   exit 1 ;; \
	esac

test-unit: own-environment  ## Unit + contract tests
	$(RUN) $(PYTHON) -m pytest tests/unit/

# --maxfail=0 overrides the -x in pyproject addopts: one failing combination
# must not mask the others behind it.
test-e2e: own-environment  ## End-to-end deck tests (attribute coverage + input combinations)
	$(RUN) $(PYTHON) -m pytest tests/end_to_end/ --maxfail=0

# A run's console output shows only when the run fails.
test-examples: own-environment  ## Run simulations/examples
	@time ( \
		for n in 1 2 3; do \
			echo "example_$$n"; \
			deck=simulations/examples/example_$$n/example_$$n.nav; \
			out=$$($(RUN) $(PYTHON) -m navigate $$deck -d ./assumptions) \
				|| { echo "$$out"; exit 1; }; \
		done \
	)

test-all: test-unit test-e2e test-examples  ## Full test suite (pytest suites + examples)

# The base ref, by default the newest dev after a fetch, is checked out into a
# worktree and installed into its own venv, so neither side imports the other's
# source; each side runs its own decks against its own assumptions
# (tests/compare_results.py). CI runs the same comparison on pull requests
# labelled maintenance (.github/workflows/compare-results.yml). The head side
# runs on the interpreter own-environment probes, without -P: the script needs
# its own folder, tests/, on sys.path, and the checkout root is never on it.
BASE ?= origin/dev
COMPARE_DIR := $(CURDIR)/.compare

compare-results: own-environment  ## Compare deck results with another ref: make compare-results BASE=<ref> (default origin/dev)
	git fetch -q origin
	rm -rf $(COMPARE_DIR) && git worktree prune
	git worktree add --detach $(COMPARE_DIR)/base $(BASE)
	$(RUN) python -m venv $(COMPARE_DIR)/env
	$(COMPARE_DIR)/env/bin/pip install -q $(COMPARE_DIR)/base
	$(COMPARE_DIR)/env/bin/python $(COMPARE_DIR)/base/tests/compare_results.py snapshot \
		--assumptions $(COMPARE_DIR)/base/assumptions --out $(COMPARE_DIR)/snapshots/base
	$(RUN) python tests/compare_results.py snapshot --out $(COMPARE_DIR)/snapshots/head
	$(RUN) python tests/compare_results.py diff \
		$(COMPARE_DIR)/snapshots/base $(COMPARE_DIR)/snapshots/head; \
		status=$$?; git worktree remove --force $(COMPARE_DIR)/base; exit $$status

docs:  ## Stage content and build the documentation site (needs docs/requirements.txt installed)
	$(RUN) $(MAKE) -C docs html

docs-clean:  ## Remove the documentation build output
	$(MAKE) -C docs clean

# git clean -X removes only gitignored files, so tracked files and decks stay.
# simulations/debug/ ignores one's own decks too, so there only the run output
# goes: plots*/ folders, logs, reports and pickles.
clean:  ## Remove build output, test and lint caches, and simulation run output
	rm -rf build dist *.egg-info .eggs .pytest_cache .mypy_cache .ruff_cache \
		.coverage .coverage.* htmlcov .hypothesis $(COMPARE_DIR)
	git worktree prune
	git clean -fdX -- navigate/ tests/ docs/_build/ simulations/ \
		':!simulations/debug/'
	[ ! -d simulations/debug ] || find simulations/debug -mindepth 1 \
		\( -type d -name 'plots*' -prune -exec rm -rf {} + \) -o \
		\( -type f \( -name '*.log' -o -name '*.xlsx' -o -name '*.pkl' \
		-o -name '*.png' \) -delete \)
