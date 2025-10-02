.PHONY: dev lint type test

dev:
pip install -e .[dev]

lint:
ruff check .

type:
mypy .

test:
pytest
