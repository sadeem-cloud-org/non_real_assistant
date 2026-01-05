# Makefile for Non Real Assistant

.PHONY: help build up down logs dev prod clean

help:
	@echo "Non Real Assistant - Docker Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make dev      - Start development environment (without nginx)"
	@echo "  make prod     - Start production environment (with nginx)"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - Show logs"
	@echo "  make logs-web - Show web app logs"
	@echo "  make logs-bot - Show bot logs"
	@echo "  make clean    - Remove containers and images"
	@echo "  make shell    - Open shell in web container"

# Development (without nginx)
dev:
	docker-compose -f docker-compose.dev.yml up --build

dev-d:
	docker-compose -f docker-compose.dev.yml up --build -d

# Production (with nginx)
prod:
	docker-compose up --build -d

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

down-dev:
	docker-compose -f docker-compose.dev.yml down

# Logs
logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

logs-bot:
	docker-compose logs -f bot

logs-nginx:
	docker-compose logs -f nginx

# Utilities
shell:
	docker-compose exec web /bin/bash

shell-dev:
	docker-compose -f docker-compose.dev.yml exec web /bin/bash

# Database migration
migrate:
	docker-compose exec web python -m migrations.migrate

migrate-dev:
	docker-compose -f docker-compose.dev.yml exec web python -m migrations.migrate

# Create user
create-user:
	@read -p "Phone: " phone; \
	read -p "Telegram ID: " telegram_id; \
	docker-compose exec web python create_user.py create --phone $$phone --telegram_id $$telegram_id

# Clean up
clean:
	docker-compose down -v --rmi local
	docker-compose -f docker-compose.dev.yml down -v --rmi local

# Restart services
restart:
	docker-compose restart

restart-web:
	docker-compose restart web

restart-bot:
	docker-compose restart bot
