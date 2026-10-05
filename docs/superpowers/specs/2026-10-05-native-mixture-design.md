# Multiple complete patches on expanded Transfxr coverage

The current expanded expert has one numeric head. Its four proposals vary
categorical choices, while ambiguous continuous controls are averaged. Test
whether four complete explanations help after expanding native training coverage.
The earlier four-mode experiment used the small original corpus; it does not
answer this question. This is a hypothesis, not an announced model improvement.

Alternatives considered: codec augmentation addresses a numerical failure that
the human called a tie; cross-engine fitted labels need verified fitting first.
Use the existing multiple-solution architecture with expanded data now, keeping
input features and actual-render ranking unchanged to isolate this limitation.

Both arms start from the frozen expanded checkpoint. One retains one head;
the other copies it to four, retaining head zero exactly and adding seeded small
weight perturbations to the other heads to break symmetry. Encoder is copied
exactly. Equal 4,000 updates, learning rate 1e-4, batch 128 with half native and
half structured, same minibatches and normalization. Train existing mixture
acoustic loss, including routing balance, and select minimum original balanced
validation mixture loss including step zero. Report native, structured, new
native validation and per-mode responsibility to expose collapse.

Do not compare differently shaped training losses as audible-quality evidence.
Actual DSP is decisive: four proposals per arm, with the existing expanded-four
as baseline. Evaluate all 90 frozen transfer development targets and 32 further
new-validation control groups excluding previous selection/evaluation targets.
Report pool diversity, pitch/gesture and distance, failures and retained PCM.
These remain shared-preset-family controls, not family-independent generalization.

Listening gate: no silent or missing selected output; numerical benefit on
fresh native or external targets; inspect regressions and keep exact baselines.
If useful candidates exist, select six including positive, disagreement and
coverage cases; immediate absolute-likeness questions are required. No automatic
promotion or removal of older experts. No repeat rating of identical pairs.

User has authorized autonomous experiments; execute design and review inline.
