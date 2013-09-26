all: test flakes
	@echo "Default target is to test. You need to specify other targets explicitly."

.PHONY: stop
stop:
	./pushmanager stop

.PHONY: start
start:
	./pushmanager start


.PHONY: restart
restart:
	./pushmanager restart


.PHONY: flakes
flakes:
	pyflakes . | grep -v tornado

.PHONY: test
test:
	testify -v --summary tests

.PHONY: coverage
coverage:
	@coverage erase
	coverage run `which testify` --verbose --exclude-suite disabled tests
	coverage report
	coverage html
	coverage xml

.PHONY: tests
tests: test ;
