.PHONY: help
help: ## Run this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)


.PHONY: run
run: ## Build and run the project
	docker run --rm -it -p 8081:8081 $$(docker build -q .) 


dev: ## Run as dev, mapping the local folder to your machine
	docker run --rm -it -p 8081:8081 $$(docker build -q .) 