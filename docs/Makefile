# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Minimal makefile for the Navigate Sphinx documentation.
#
# `make html` builds the site into _build/html. All content lives in this
# directory, so a plain sphinx-build is all that is required.

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help html clean

help:
	@echo "make html    build HTML into $(BUILDDIR)/html"
	@echo "make clean   remove the build output"

html:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)

clean:
	rm -rf "$(BUILDDIR)"
