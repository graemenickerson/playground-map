.PHONY: dev frontend

dev:
	.venv/bin/flask --app backend.app run --debug --port 5001

frontend:
	npm --prefix frontend run dev
