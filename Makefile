.PHONY: help dev build test clean logs down setup

help:
	@echo "LogWatch - Makefile Commands"
	@echo ""
	@echo "  make dev          - Start all services in development mode"
	@echo "  make build        - Build Docker images"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-frontend- Run frontend tests"
	@echo "  make logs         - Show logs from all services"
	@echo "  make down         - Stop all services"
	@echo "  make clean        - Remove all containers, volumes, and build artifacts"
	@echo "  make setup        - Initial setup (indices, sample data)"
	@echo "  make ingest       - Ingest sample logs"
	@echo "  make watch        - Start file watcher"
	@echo "  make scale        - Scale backend workers"

dev:
	@echo "Starting LogWatch development environment..."
	docker compose up -d
	@echo "Services starting..."
	@echo "  - OpenSearch: http://localhost:9200"
	@echo "  - Backend API: http://localhost:8000"
	@echo "  - Frontend UI: http://localhost:3000"
	@echo ""
	@echo "Run 'make setup' to initialize indices and generate sample logs"
	@echo "Run 'make logs' to view service logs"

build:
	@echo "Building Docker images..."
	docker compose build

test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	docker compose exec backend pytest -v --cov=app

test-frontend:
	@echo "Running frontend tests..."
	docker compose exec frontend npm test

logs:
	docker compose logs -f

down:
	@echo "Stopping all services..."
	docker compose down

clean:
	@echo "Cleaning up..."
	docker compose down -v
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf backend/htmlcov
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf logs_in/*
	@echo "Clean complete"

setup:
	@echo "Setting up OpenSearch indices..."
	sleep 10  # Wait for OpenSearch to be ready
	docker compose exec backend python scripts/setup_opensearch.py
	@echo "Generating sample logs..."
	docker compose exec backend python scripts/generate_logs.py --output /logs_in --count 10000
	@echo "Setup complete!"

ingest:
	@echo "Ingesting existing log files..."
	docker compose exec backend python -m app.cli.ingest --directory /logs_in

watch:
	@echo "Starting file watcher..."
	docker compose exec backend python -m app.cli.watch --directory /logs_in

scale:
	@echo "Scaling backend to 3 workers..."
	docker compose up -d --scale backend=3

install-local:
	@echo "Installing dependencies locally (macOS)..."
	brew install python@3.11 node@20 docker
	cd backend && python3.11 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install
	@echo "Local installation complete!"
