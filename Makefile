.PHONY: help setup dev clean test lint format

help:
	@echo "DubWizard - Available commands:"
	@echo "  make setup    - Install all dependencies"
	@echo "  make dev      - Start all services in development mode"
	@echo "  make test     - Run all tests"
	@echo "  make lint     - Run linters"
	@echo "  make format   - Format code"
	@echo "  make clean    - Clean build artifacts and temp files"

setup:
	@echo "Setting up shared package..."
	pip install -e packages/shared
	@echo "Setting up backend..."
	cd apps/api && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt && pip install -e ../../packages/shared
	@echo "Setting up frontend..."
	cd apps/web && npm install
	@echo "Setting up worker..."
	cd worker && pip install -r requirements.txt && pip install -e ../packages/shared
	@echo "Setup complete! Copy .env.example to .env and configure your API keys."

dev:
	@echo "Starting all services..."
	@echo "Run these in separate terminals:"
	@echo "  Terminal 1: cd apps/api && source venv/bin/activate && uvicorn app.main:app --reload --port 8000"
	@echo "  Terminal 2: source apps/api/venv/bin/activate && export PYTHONPATH=$PYTHONPATH:. && python -m worker.worker"
	@echo "  Terminal 3: cd apps/web && npm run dev"

test:
	@echo "Running backend tests..."
	cd apps/api && source venv/bin/activate && pytest
	@echo "Running frontend tests..."
	cd apps/web && npm test

lint:
	@echo "Linting backend..."
	cd apps/api && source venv/bin/activate && flake8 app/
	@echo "Linting frontend..."
	cd apps/web && npm run lint

format:
	@echo "Formatting backend..."
	cd apps/api && source venv/bin/activate && black app/
	@echo "Formatting frontend..."
	cd apps/web && npm run format

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	rm -f dubwizard.db
	rm -rf tmp/
	@echo "Clean complete!"
