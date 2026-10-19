NODE ?= node
ifeq ($(OS),Windows_NT)
NPM := npm.cmd
else
NPM ?= npm
endif
.DEFAULT_GOAL := help

.PHONY: help all build desktop serve distro install test

help:
	@echo "make / make help   Show commands"
	@echo "make desktop       Build all desktop apps for this platform; print launch paths"
	@echo "make serve         Prepare web assets and serve on a free port; print LAN links"
	@echo "make distro        Build host archives; assemble other hosts via GUI95_DIST_INPUT"
	@echo "make install       Build and install for the current user"
	@echo "make test          Run tests"

all: desktop

build: node_modules/.package-lock.json
	$(NODE) compile.js

desktop: node_modules/.package-lock.json
	$(NODE) scripts/gui95-icons.mjs
	$(NODE) desktop/package.js
	$(NODE) scripts/gui95-app.mjs pack
	$(NODE) scripts/gui95-app.mjs paths

serve:
	$(NODE) insert_templates.js
	$(NODE) tools/serve.js

distro: desktop
	$(NODE) scripts/gui95-distro.mjs

install: desktop
	$(NODE) scripts/gui95-app.mjs install

test: node_modules/.package-lock.json
	$(NPM) test

node_modules/.package-lock.json: package.json package-lock.json
	$(NPM) ci
