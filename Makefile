# Makefile for Non Real Assistant

.PHONY: help build up down logs dev prod clean

help:
	@echo "Non Real Assistant - Docker Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make dev          - Start development (SQLite, without nginx)"
	@echo "  make prod         - Start production (SQLite + nginx)"
	@echo "  make prod-pg      - Start production with PostgreSQL"
	@echo "  make prod-mysql   - Start production with MariaDB"
	@echo ""
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs"
	@echo "  make clean        - Remove containers and images"
	@echo "  make shell        - Open shell in web container"
	@echo "  make migrate      - Run database migrations"

# ===== Development =====
dev:
	docker-compose -f docker-compose.dev.yml up --build

dev-d:
	docker-compose -f docker-compose.dev.yml up --build -d

down-dev:
	docker-compose -f docker-compose.dev.yml down

# ===== Production with SQLite (default) =====
prod:
	docker-compose up --build -d

# ===== Production with PostgreSQL =====
prod-pg:
	docker-compose --profile postgres up --build -d

down-pg:
	docker-compose --profile postgres down

# ===== Production with MariaDB =====
prod-mysql:
	docker-compose --profile mariadb up --build -d

down-mysql:
	docker-compose --profile mariadb down

# ===== Basic Commands =====
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

# ===== Logs =====
logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f web

logs-bot:
	docker-compose logs -f bot

logs-nginx:
	docker-compose logs -f nginx

logs-db:
	docker-compose logs -f postgres mariadb 2>/dev/null || true

# ===== Utilities =====
shell:
	docker-compose exec web /bin/bash

shell-dev:
	docker-compose -f docker-compose.dev.yml exec web /bin/bash

# ===== Database =====
migrate:
	docker-compose exec web python -m migrations.migrate

migrate-dev:
	docker-compose -f docker-compose.dev.yml exec web python -m migrations.migrate

# PostgreSQL shell
psql:
	docker-compose exec postgres psql -U $${POSTGRES_USER:-nra_user} -d $${POSTGRES_DB:-non_real_assistant}

# MariaDB shell
mysql:
	docker-compose exec mariadb mysql -u $${MYSQL_USER:-nra_user} -p$${MYSQL_PASSWORD:-nra_password} $${MYSQL_DATABASE:-non_real_assistant}

# ===== User Management =====
create-user:
	@read -p "Phone: " phone; \
	read -p "Telegram ID: " telegram_id; \
	docker-compose exec web python create_user.py create --phone $$phone --telegram_id $$telegram_id

create-admin:
	@read -p "Phone: " phone; \
	read -p "Telegram ID: " telegram_id; \
	docker-compose exec web python create_user.py create --phone $$phone --telegram_id $$telegram_id --is_admin

# ===== Cleanup =====
clean:
	docker-compose down -v --rmi local
	docker-compose --profile postgres down -v --rmi local 2>/dev/null || true
	docker-compose --profile mariadb down -v --rmi local 2>/dev/null || true

# ===== Restart =====
restart:
	docker-compose restart

restart-web:
	docker-compose restart web

restart-bot:
	docker-compose restart bot
