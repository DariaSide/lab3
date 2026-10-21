PYTHON ?= .venv/bin/python
CSV ?= /Users/side/Downloads/it_vacancies_2024.csv

.PHONY: setup up down prepare upload mapreduce duckdb verify profile analyze all test

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

prepare:
	$(PYTHON) -m src.prepare --input "$(CSV)"

upload:
	$(PYTHON) -m src.storage upload

mapreduce:
	$(PYTHON) -m src.mapreduce_job

duckdb:
	$(PYTHON) -m src.duckdb_job

verify:
	$(PYTHON) -m src.verify

profile:
	$(PYTHON) -m src.profile_runs --runs 3

analyze:
	$(PYTHON) -m src.analysis

all: prepare upload profile analyze

test:
	$(PYTHON) -m unittest discover -s tests -v
