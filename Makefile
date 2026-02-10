.PHONY: dev test test-unit test-integration test-e2e lint fmt docker assess-local clean fixture

# Set up development environment
dev:
	python -m venv .venv
	.venv/bin/pip install -e "./agent[dev]"
	@echo "Development environment ready. Activate with: source .venv/bin/activate"

# Generate the DuckDB fixture database
fixture:
	.venv/bin/python tests/fixtures/create_fixture.py

# Run all tests
test: fixture
	.venv/bin/pytest tests/ -v --tb=short

# Run only unit tests (no DB, no filesystem beyond tmp_path)
test-unit:
	.venv/bin/pytest tests/unit/ -v --tb=short

# Run integration tests (requires DuckDB fixture)
test-integration: fixture
	.venv/bin/pytest tests/integration/ -v --tb=short

# Run end-to-end tests (full CLI pipeline)
test-e2e: fixture
	.venv/bin/pytest tests/e2e/ -v --tb=short

# Run tests with coverage
test-cov: fixture
	.venv/bin/pytest tests/ -v --cov=agent --cov-report=term-missing --tb=short

# Lint
lint:
	.venv/bin/ruff check agent/
	.venv/bin/ruff format --check agent/

# Format
fmt:
	.venv/bin/ruff format agent/

# Build Docker image
docker:
	docker build -t aird/agent:latest .

# Run assessment against local DuckDB fixture
assess-local: fixture
	.venv/bin/python -m agent.cli assess --connection "duckdb://tests/fixtures/sample.duckdb" --output markdown --schema analytics --no-save

# Dry-run assessment against local fixture
assess-preview: fixture
	.venv/bin/python -m agent.cli assess --connection "duckdb://tests/fixtures/sample.duckdb" --schema analytics --dry-run --no-save

# Clean build artifacts
clean:
	rm -rf .venv dist build *.egg-info __pycache__
	rm -f tests/fixtures/sample.duckdb
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
