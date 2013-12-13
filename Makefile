.PHONY: test tests coverage clean

all: test clean

test:
	tox

coverage:
	@coverage erase
	coverage run `which testify` --verbose --exclude-suite disabled pushmanager.tests
	coverage report
	coverage html
	coverage xml


clean:
	rm -rf .tox dist
