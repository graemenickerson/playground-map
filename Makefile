.PHONY: dev

dev:
	.venv/bin/flask --app backend.app run --debug --port 5001
