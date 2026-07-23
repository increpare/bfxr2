# Inverse model + common tooling shortcuts.
# Run from tools/:  make help

.PHONY: rebuild_inverse_model train_inverse_model \
	run_inverse_model one_shot_inverse_model \
	render_bfxr_targets eval_inverse_model eval_inverse_model_bfxr \
	eval_inverse_model_all native help

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
EVAL_OUT     ?= $(RUN)/eval_targets
BFXR_PRESETS ?= targets_from_bfxr/Bfxr
BFXR_WAV_DIR ?= $(RUN)/bfxr_rendered
EVAL_BFXR_OUT ?= $(RUN)/eval_bfxr
RENDER       ?= bfxr_native/build/bfxr_render
RENDER_SEED  ?= 1234

help:
	@echo "Inverse model:"
	@echo "  make rebuild_inverse_model      # gen $(N) shards + train → $(CKPT)"
	@echo "  make train_inverse_model        # train only (reuse $(DATA))"
	@echo "  make run_inverse_model          # seeded match on one TARGET"
	@echo "  make one_shot_inverse_model     # raw model guess, no search"
	@echo "  make render_bfxr_targets        # .bfxr presets → wavs ($(BFXR_WAV_DIR))"
	@echo "  make eval_inverse_model_bfxr    # in-domain: Bfxr presets (render+eval)"
	@echo "  make eval_inverse_model         # all wavs in targets/"
	@echo "  make eval_inverse_model_all     # bfxr presets + targets/"
	@echo ""
	@echo "Overrides: N= EPOCHS= TARGET= OUT= BUDGET= EVAL_BUDGET= CKPT="

native:
	$(MAKE) -C bfxr_native

rebuild_inverse_model: native
	uv run python -m invert.dataset --out $(DATA) --n $(N) --seed $(SEED)
	uv run python -m invert.train --data $(DATA) --out $(RUN) --version 1 --epochs $(EPOCHS)

train_inverse_model:
	uv run python -m invert.train --data $(DATA) --out $(RUN) --version 1 --epochs $(EPOCHS)

run_inverse_model:
	uv sync --extra report --group dev
	uv run python -m match.match $(TARGET) -o $(OUT) \
		--seed-model $(CKPT) --budget $(BUDGET) --html-report

one_shot_inverse_model:
	uv run python -m match.match $(TARGET) -o $(OUT)_os \
		--seed-model $(CKPT) --one-shot

# Fresh deterministic renders from the shipped Bfxr preset .bfxr files.
render_bfxr_targets: native
	@test -x $(RENDER) || (echo "missing $(RENDER); run make native" >&2; exit 1)
	mkdir -p $(BFXR_WAV_DIR)
	@for f in $(BFXR_PRESETS)/*.bfxr; do \
		base=$$(basename "$$f" .bfxr); \
		echo "render $$base"; \
		$(RENDER) --in "$$f" --out "$(BFXR_WAV_DIR)/$$base.wav" --seed $(RENDER_SEED); \
	done
	@echo "wrote wavs in $(BFXR_WAV_DIR)/"

# In-domain: can the seeder recover sounds that actually came from bfxr?
eval_inverse_model_bfxr: render_bfxr_targets
	uv run python -m invert.eval_targets \
		--targets $(BFXR_WAV_DIR) \
		--ckpt $(CKPT) --budget $(EVAL_BUDGET) -o $(EVAL_BFXR_OUT)
	@echo "open $(EVAL_BFXR_OUT)/results.md"

# Real-world game SFX in targets/
eval_inverse_model:
	uv run python -m invert.eval_targets \
		--targets targets \
		--ckpt $(CKPT) --budget $(EVAL_BUDGET) -o $(EVAL_OUT)
	@echo "open $(EVAL_OUT)/results.md"

eval_inverse_model_all: eval_inverse_model_bfxr eval_inverse_model
