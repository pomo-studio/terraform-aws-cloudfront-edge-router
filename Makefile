.PHONY: test fmt validate

test:
	terraform init -backend=false
	terraform test

fmt:
	terraform fmt -recursive

validate:
	terraform init -backend=false
	terraform validate
