# Check rendered finite-difference directions before further audio training

The forward surrogate passes a value-prediction check but previously produced harmful optimization directions. More data may help it, but first distinguish surrogate error from a poor local audio objective. This is a private mechanistic diagnostic, not a new model or listening gate.

Compare the retained surrogate-gradient steps with directions estimated by central finite differences of actual DSP descriptor loss. Use the first four native and first four structured cases in the frozen local-gradient-v1 report, without choosing on outcomes. Keep their exact initial candidates, categorical controls, seeds, targets and feature normalization. For each continuous unit control, render +/- .001 (clipped at bounds), use the actual canonical unit displacement as denominator, and save every render plus loss. No categorical/seed gradients are estimated.

Apply the resulting normalized full direction at .001 and .005, plus reversed .005 as a negative control. No line search, candidate selection or target-control substitution. Compare actual loss, MatchObjective and pitch diagnostics to before and the retained surrogate steps. Report cosine agreement and sign agreement for coordinates with nonzero finite-difference derivative. Finite differences are scale-dependent estimates, particularly near trimming, voicing and categorical boundaries; do not call them exact gradients or perceptual ground truth.

Alternatives: train a bigger forward network immediately (cannot distinguish objective failure); rewrite DSP in a differentiable framework (large parity burden); first measure local directions through existing exact DSP (chosen). If actual finite-difference descent also damages pitch, prioritize objective/constraints before gradient imitation. If rendered directions work but the surrogate disagrees, investigate directional supervision with larger coverage. Either result remains development evidence and does not unlock inverse fine-tuning automatically.

Autonomous implementation authorized by the ongoing user goal. Do not change the running real-reference refinement or the pending human comparison.
