# -----------------------------
# Config (override via CLI/env)
# -----------------------------
IMAGE_NAME ?= omerdagan/budget-manager-api
TAG        ?=                          # may be auto-derived from HEAD
CONTEXT    ?= .                        # docker build context

# Compose location (where docker-compose.yml and .env live)
COMPOSE_DIR     ?= .
ENV_FILE        ?= $(COMPOSE_DIR)/.env
DOCKER_CONTEXT  ?=                     # e.g., prod (created via `docker context create ...`)

# Tools
COMPOSE_CMD := docker $(if $(DOCKER_CONTEXT),--context $(DOCKER_CONTEXT),) compose

# -----------------------------
# Helper: command runner
# -----------------------------
RUN = $(if $(DRY_RUN),@echo,)

# -----------------------------
# Auto-derive TAG from HEAD if not provided
# -----------------------------
ifeq ($(strip $(TAG)),)
  ifneq ($(SKIP_GIT_CHECKS),1)
    TAG := $(shell git describe --exact-match --tags HEAD 2>/dev/null || git tag --points-at HEAD | head -n1)
  endif
endif

# -----------------------------
# Require TAG present (after auto-derive)
# -----------------------------
define REQUIRE_TAG
	@if [ -z "$(TAG)" ]; then \
		echo "ERROR: TAG is required (or must be derivable from HEAD)."; \
		echo "Usage: make <target> TAG=1.3"; \
		echo "Or:    git tag -a 1.3 -m 'release 1.3' && git push origin 1.3"; \
		echo "Or bypass: SKIP_GIT_CHECKS=1 make <target> (uses dev-<sha> fallback)"; \
		exit 1; \
	fi
endef

# -----------------------------
# Require git tag exists & HEAD at tag (unless SKIP_GIT_CHECKS=1)
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
# Require .env IMAGE_TAG == TAG (unless SKIP_ENV_TAG_CHECK=1)
# -----------------------------
define REQUIRE_ENV_TAG_MATCH
	@if [ "$(SKIP_ENV_TAG_CHECK)" = "1" ]; then \
		echo "⚠️  Skipping .env tag check (SKIP_ENV_TAG_CHECK=1)"; \
	else \
		if [ ! -f "$(ENV_FILE)" ]; then \
			echo "ERROR: Env file not found: $(ENV_FILE)"; \
			echo "Create it with: echo 'IMAGE_TAG=$(TAG)' > $(ENV_FILE)"; \
			exit 1; \
		fi; \
		ENV_TAG=$$(grep -E '^IMAGE_TAG=' "$(ENV_FILE)" | head -n1 | sed 's/#.*//' | cut -d= -f2- | tr -d '[:space:]'); \
		if [ -z "$$ENV_TAG" ]; then \
			echo "ERROR: IMAGE_TAG is missing/empty in $(ENV_FILE)"; \
			echo "Add: IMAGE_TAG=$(TAG)"; \
			exit 1; \
		fi; \
		if [ "$$ENV_TAG" != "$(TAG)" ]; then \
			echo "ERROR: .env IMAGE_TAG ('$$ENV_TAG') does not match TAG ('$(TAG)')"; \
			echo "Fix by updating $(ENV_FILE): IMAGE_TAG=$(TAG)"; \
			echo "Or bypass with SKIP_ENV_TAG_CHECK=1"; \
			exit 1; \
		fi; \
	fi
endef

# -----------------------------
# Build / Push / Release
# -----------------------------

.PHONY: docker-build
docker-build:
	$(REQUIRE_TAG)
	$(REQUIRE_GIT_TAG_AND_HEAD)
	$(REQUIRE_ENV_TAG_MATCH)
	$(RUN) docker build \
	  -t $(IMAGE_NAME):$(TAG) \
	  -t $(IMAGE_NAME):latest \
	  $(CONTEXT)

.PHONY: docker-push
docker-push:
	$(REQUIRE_TAG)
	$(REQUIRE_GIT_TAG_AND_HEAD)
	$(REQUIRE_ENV_TAG_MATCH)
	$(RUN) docker push $(IMAGE_NAME):$(TAG)
	$(RUN) docker push $(IMAGE_NAME):latest

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
	$(RUN) cd $(COMPOSE_DIR) && \
	  $(COMPOSE_CMD) pull && \
	  $(COMPOSE_CMD) up -d && \
	  docker $(if $(DOCKER_CONTEXT),--context $(DOCKER_CONTEXT),) image prune -f
	@echo "✅ Deploy complete"

# -----------------------------
# Utilities
# -----------------------------

.PHONY: status
status:
	$(RUN) cd $(COMPOSE_DIR) && $(COMPOSE_CMD) ps

.PHONY: logs
logs:
	$(RUN) cd $(COMPOSE_DIR) && $(COMPOSE_CMD) logs -f budget-api

.PHONY: restart
restart:
	$(RUN) cd $(COMPOSE_DIR) && $(COMPOSE_CMD) restart budget-api

