export PROJECTNAME=$(shell basename "$(PWD)")
PY=./venv/bin/python3

.SILENT: ;               # no need for @

setup: clean ## Re-initiates virtualenv
	rm -rf venv
	python3 -m venv venv

deps: ## Install dependencies
	$(PY) -m pip install --upgrade -r requirements-dev.txt
	$(PY) -m pip install --upgrade pip

check: ## Manually run all precommit hooks
	./venv/bin/pre-commit install
	./venv/bin/pre-commit run --all-files

check-tool: ## Manually run a single pre-commit hook
	./venv/bin/pre-commit run $(TOOL) --all-files

clean: ## Clean package
	find . -type d -name '__pycache__' | xargs rm -rf
	rm -rf build dist

run: ## Runs the application
	./venv/bin/python3 main.py

package: clean check ## Run installer
	./venv/bin/pyinstaller main.spec

install-macosx: package ## Installs application in users Application folder
	./scripts/install-macosx.sh AnnotateIt.app

context: clean ## Build context file from application sources
	llm-context-builder.py --extensions .py --ignored_dirs build dist generated venv .venv .idea .aider.tags.cache.v3 --print_contents --temp_file

.PHONY: help
.DEFAULT_GOAL := help

help: Makefile
	echo
	echo " Choose a command run in "$(PROJECTNAME)":"
	echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo
