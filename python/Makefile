# -----------------------------
# Config (override via CLI/env)
# -----------------------------
IMAGE_NAME ?= omerdagan/budget-manager-api
TAG        ?=                          # required for build/push/release
CONTEXT    ?= .                        # docker build context

# Compose location (where docker-compose.yml and .env live)
COMPOSE_DIR     ?= .
DOCKER_CONTEXT  ?=                     # e.g., prod (created via `docker context create ...`)

# Tools
COMPOSE_CMD := docker $(if $(DOCKER_CONTEXT),--context $(DOCKER_CONTEXT),) compose

# -----------------------------
# Helper: require TAG
# -----------------------------
define REQUIRE_TAG
	@if [ -z "$(TAG)" ]; then \
		echo "ERROR: TAG is required. Usage: make <target> TAG=1.3"; \
		exit 1; \
	fi
endef

# -----------------------------
# Helper: require git tag & HEAD at tag (unless SKIP_GIT_CHECKS=1)
# -----------------------------
define REQUIRE_GIT_TAG_AND_HEAD
	@if [ "$(SKIP_GIT_CHECKS)" = "1" ]; then \
		echo "⚠️  Skipping git tag checks (SKIP_GIT_CHECKS=1)"; \
	else \
		if ! git rev-parse --git-dir >/dev/null 2>&1; then \
			echo "ERROR: Not a git repository (no .git)."; exit 1; \
		fi; \
		if ! git rev-parse -q --verify "refs/tags/$(TAG)" >/dev/null; then \
			echo "ERROR: Git tag '$(TAG)' does not exist."; \
			echo "Hint: git tag -a $(TAG) -m \"release $(TAG)\" && git push origin $(TAG)"; \
			exit 1; \
		fi; \
		HEAD_TAGS=$$(git tag --points-at HEAD); \
		echo "$$HEAD_TAGS" | tr ' ' '\n' | grep -qx "$(TAG)" || { \
			echo "ERROR: HEAD is not at tag '$(TAG)'."; \
			echo "Current HEAD tags: $$HEAD_TAGS"; \
			echo "Hints:"; \
			echo "  - git checkout $(TAG)   # move HEAD to the tagged commit"; \
			echo "  - or retag the desired commit: git tag -f $(TAG) <commit>"; \
			exit 1; \
		}; \
	fi
endef

# -----------------------------
# Build / Push / Release
# -----------------------------

.PHONY: docker-build
docker-build:
	$(REQUIRE_TAG)
	$(REQUIRE_GIT_TAG_AND_HEAD)
	docker build \
	  -t $(IMAGE_NAME):$(TAG) \
	  -t $(IMAGE_NAME):latest \
	  $(CONTEXT)

.PHONY: docker-push
docker-push:
	$(REQUIRE_TAG)
	$(REQUIRE_GIT_TAG_AND_HEAD)
	docker push $(IMAGE_NAME):$(TAG)
	docker push $(IMAGE_NAME):latest

# Convenience: build + push
.PHONY: release
release: docker-build docker-push
	@echo "✅ Released $(IMAGE_NAME):$(TAG) and latest"

# -----------------------------
# Deploy (Compose)
# -----------------------------
# Expects docker-compose.yml and .env to be in $(COMPOSE_DIR)
# .env should set IMAGE_TAG used by docker-compose.yml

.PHONY: deploy
deploy:
	@echo "🚀 Deploying compose stack in $(COMPOSE_DIR) $(if $(DOCKER_CONTEXT),(context=$(DOCKER_CONTEXT)),)"
	cd $(COMPOSE_DIR) && \
	  $(COMPOSE_CMD) pull && \
	  $(COMPOSE_CMD) up -d && \
	  docker $(if $(DOCKER_CONTEXT),--context $(DOCKER_CONTEXT),) image prune -f
	@echo "✅ Deploy complete"

# -----------------------------
# Utilities
# -----------------------------

.PHONY: status
status:
	cd $(COMPOSE_DIR) && $(COMPOSE_CMD) ps

.PHONY: logs
logs:
	cd $(COMPOSE_DIR) && $(COMPOSE_CMD) logs -f budget-api

.PHONY: restart
restart:
	cd $(COMPOSE_DIR) && $(COMPOSE_CMD) restart budget-api

