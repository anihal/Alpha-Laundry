# Makefile for Alpha Laundry Management System API

.PHONY: help install dev prod init-db seed-db reset-db clean test

# Default target
help:
	@echo "Alpha Laundry Management System - Python API"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server with auto-reload"
	@echo "  make prod       - Run production server"
	@echo "  make init-db    - Initialize database tables"
	@echo "  make seed-db    - Seed database with sample data"
	@echo "  make reset-db   - Reset database (WARNING: deletes all data)"
	@echo "  make clean      - Clean Python cache files"
	@echo "  make test       - Run tests (not implemented yet)"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Run development server
dev:
	@echo "🚀 Starting development server..."
	python run.py run --reload

# Run production server
prod:
	@echo "🚀 Starting production server..."
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Initialize database
init-db:
	@echo "🔧 Initializing database..."
	python run.py init-db

# Seed database
seed-db:
	@echo "🌱 Seeding database..."
	python run.py seed-db

# Reset database
reset-db:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		python -c "from api.database import reset_database; reset_database()"; \
		python run.py seed-db; \
	fi

# Clean Python cache
clean:
	@echo "🧹 Cleaning Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache cleaned"

# Run tests (placeholder)
test:
	@echo "🧪 Running tests..."
	@echo "⚠️  Tests not implemented yet"
