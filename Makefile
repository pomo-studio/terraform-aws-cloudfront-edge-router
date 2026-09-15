.PHONY: test test-router fmt validate

test: test-router
	terraform init -backend=false
	terraform test

test-router:
	node --test tests/*.test.mjs

fmt:
	terraform fmt -recursive

validate:
	terraform init -backend=false
	terraform validate
