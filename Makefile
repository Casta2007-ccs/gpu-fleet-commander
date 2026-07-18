.PHONY: help init start stop restart create-db install test lint format clean run

# Help command to show available tasks
help:
	@echo "======================================================================"
	@echo "⚡ GPU Fleet Commander Development Runner ⚡"
	@echo "======================================================================"
	@echo "Available commands:"
	@echo "  init         - Initialize local PostgreSQL cluster files"
	@echo "  start        - Start database and caching services in background"
	@echo "  stop         - Stop background databases"
	@echo "  restart      - Restart all local background databases"
	@echo "  create-db    - Create the local development PostgreSQL database"
	@echo "  install      - Install Python dependencies via uv"
	@echo "  test         - Run unit tests with pytest"
	@echo "  lint         - Check code style and type annotations (ruff & mypy)"
	@echo "  format       - Auto-format code using ruff formatter"
	@echo "  run          - Run the FastAPI development server"
	@echo "  clean        - Remove temporary pycache and build artifacts"
	@echo "======================================================================"

# Install Python packages using uv
install:
	uv pip install -r requirements.txt

# Database lifecycle management (Nix/Flox compatible)
init:
	initdb -D .flox/cache/pgdata --no-locale --encoding=UTF8

start:
	pg_ctl -D .flox/cache/pgdata -l .flox/cache/postgres.log start

stop:
	pg_ctl -D .flox/cache/pgdata stop

restart: stop start

create-db:
	createdb -h localhost -p 5432 -U postgres gpu_fleet

# Testing tasks
test:
	python -m pytest tests/unit/

# Quality assurance (Ruff)
lint:
	ruff check src/ cmd/ tests/
	mypy src/ cmd/

format:
	ruff format src/ cmd/ tests/

# Running local dev server
run:
	uvicorn cmd.api.main:app --reload --host 0.0.0.0 --port 8000

# Cleaning temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache
