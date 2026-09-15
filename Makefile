.PHONY: test test-router test-sync fmt validate

test: test-router test-sync
	terraform init -backend=false
	terraform test

test-router:
	node --test tests/*.test.mjs

test-sync:
	python3 -m unittest discover -s tests -p 'test_*.py'

fmt:
	terraform fmt -recursive

validate:
	terraform init -backend=false
	terraform validate
