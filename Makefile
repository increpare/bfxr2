.DEFAULT_GOAL := build
.PHONY: build serve

build:
	@node compile.js

serve:
	@node tools/serve.js
