.PHONY: dev test lint docker assess-local clean

# Set up development environment
dev:
	python -m venv .venv
	.venv/bin/pip install -e "./agent[dev]"
	@echo "Development environment ready. Activate with: source .venv/bin/activate"

# Run tests
test:
	.venv/bin/pytest tests/ -v

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

# Run assessment against local test fixture
assess-local:
	.venv/bin/python -m agent.cli assess --connection "sqlite:///tests/fixtures/sample.db" --output stdout

# Clean build artifacts
clean:
	rm -rf .venv dist build *.egg-info __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
