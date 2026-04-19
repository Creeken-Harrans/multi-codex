PYTHON ?= /home/Creeken/miniconda3/envs/pytorch/bin/python

.PHONY: install test smoke lint

install:
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest

smoke:
	$(PYTHON) -m codex_hive.cli doctor

lint:
	$(PYTHON) -m compileall codex_hive
