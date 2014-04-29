all: test flakes
	@echo "Default target is to test. You need to specify other targets explicitly."

.PHONY: flakes
flakes:
	tox

.PHONY: test
test:
	tox

.PHONY: coverage
coverage:
	tox -e cover
	coverage html
	coverage xml

.PHONY: tests
tests: test ;

.PHONY: clean
clean:
	rm -rf .coverage
	rm -rf .tox
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
