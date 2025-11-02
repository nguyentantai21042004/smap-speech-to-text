.PHONY: help install dev-install run-api run-queue run-scheduler docker-build docker-up docker-down docker-logs clean test format lint

help:
	@echo "Available commands:"
	@echo "  make install            - Install production dependencies"
	@echo "  make dev-install        - Install development dependencies"
	@echo "  make run-api            - Run API service locally (original)"
	@echo "  make run-api-refactored - Run API service locally (refactored)"
	@echo "  make run-consumer       - Run Consumer service locally (refactored)"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start all services with Docker Compose"
	@echo "  make docker-down        - Stop all services"
	@echo "  make docker-logs        - View Docker logs"
	@echo "  make clean              - Clean up generated files"
	@echo "  make test               - Run tests"
	@echo "  make format             - Format code with black"
	@echo "  make lint               - Lint code with flake8"

install:
	pip install -r requirements.txt

dev-install: install
	pip install pytest pytest-asyncio black flake8 mypy

run-api:
	PYTHONPATH=. myenv/bin/python cmd/api/main.py

run-api-refactored:
	PYTHONPATH=. myenv/bin/python cmd/api/main.py

run-consumer:
	PYTHONPATH=. myenv/bin/python cmd/consumer/main.py


docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

docker-clean:
	docker-compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

test:
	pytest -v

format:
	black core/ repositories/ services/ cmd/

lint:
	flake8 core/ repositories/ services/ cmd/ --max-line-length=100

# Scale queue consumers
scale-queue:
	docker-compose up -d --scale queue=3

# View specific service logs
logs-api:
	docker-compose logs -f api

logs-queue:
	docker-compose logs -f queue

logs-mongodb:
	docker-compose logs -f mongodb

logs-rabbitmq:
	docker-compose logs -f rabbitmq

