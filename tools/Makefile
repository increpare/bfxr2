# Inverse model + common tooling shortcuts.
# Run from tools/:  make rebuild_inverse_model

.PHONY: rebuild_inverse_model train_inverse_model \
	run_inverse_model one_shot_inverse_model eval_inverse_model \
	native help

N            ?= 300000
SEED         ?= 0
EPOCHS       ?= 30
DATA         ?= invert/data/v1
RUN          ?= invert/runs/v1
CKPT         ?= $(RUN)/best.pt
TARGET       ?= targets/mega_man_ii_hurt.wav
OUT          ?= out
BUDGET       ?= 5000
EVAL_BUDGET  ?= 2000
EVAL_OUT     ?= $(RUN)/eval

help:
	@echo "Inverse model:"
	@echo "  make rebuild_inverse_model   # gen $(N) shards + train → $(CKPT)"
	@echo "  make train_inverse_model     # train only (reuse existing $(DATA))"
	@echo "  make run_inverse_model       # seeded match on TARGET"
	@echo "  make one_shot_inverse_model  # raw model guess, no search"
	@echo "  make eval_inverse_model      # current vs seeded vs one-shot table"
	@echo ""
	@echo "Overrides: N= SEED= EPOCHS= TARGET= OUT= BUDGET= CKPT="

native:
	$(MAKE) -C bfxr_native

# Full rebuild: dataset + train (wipes DATA shards via gen_data clear).
rebuild_inverse_model: native
	uv run python -m invert.dataset --out $(DATA) --n $(N) --seed $(SEED)
	uv run python -m invert.train --data $(DATA) --out $(RUN) --version 1 --epochs $(EPOCHS)

train_inverse_model:
	uv run python -m invert.train --data $(DATA) --out $(RUN) --version 1 --epochs $(EPOCHS)

run_inverse_model:
	uv run python -m match.match $(TARGET) -o $(OUT) \
		--seed-model $(CKPT) --budget $(BUDGET) --html-report

one_shot_inverse_model:
	uv run python -m match.match $(TARGET) -o $(OUT)_os \
		--seed-model $(CKPT) --one-shot

eval_inverse_model:
	uv run python -m invert.eval_targets \
		--ckpt $(CKPT) --budget $(EVAL_BUDGET) -o $(EVAL_OUT)
