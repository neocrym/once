help:
	@echo "'make lint' for linting"

lint:
	isort --atomic --apply --recursive once tests
	black .
	pylint once tests
	mypy once tests

test:
	python3 -m unittest

.PHONY: help lint test