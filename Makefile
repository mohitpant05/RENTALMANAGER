.PHONY: up down build logs test migrate shell psql redis-cli

up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

down-clean:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

test:
	docker compose exec backend pytest -v

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

shell:
	docker compose exec backend bash

psql:
	docker compose exec postgres psql -U $${POSTGRES_USER:-rentmanager} -d $${POSTGRES_DB:-rentmanager}

redis-cli:
	docker compose exec redis redis-cli

status:
	docker compose ps
