# ---- Config ----
SRC := src
TESTS := tests

.PHONY: setup sync test test-cov cov-html lint format check typecheck

setup: ## cria venv e instala deps
	uv venv
	uv pip install -e .[dev]

sync: ## sincroniza dependencias
	uv pip sync pyproject.toml

test: ## roda testes
	uv run pytest -vv

test-cov: ## roda testes com relatorio de cobertura
	uv run pytest --cov --cov-report=term-missing --no-cov-on-fail

cov-html: ## gera relatorio de cobertura em htmlcov/
	uv run pytest --cov --cov-report=html --no-cov-on-fail

lint: ## checa lint e tipos (ruff + basedpyright)
	uv run ruff check $(SRC) $(TESTS)
	uv run basedpyright

format: ## formata codigo
	uv run ruff format $(SRC) $(TESTS)

check: lint test ## roda tudo
