# Research notes for the next acoustic training objective

Read on 2026-10-04 while the v2 rendered benchmark runs. These findings motivate
future experiments; v2 does not implement these papers' systems.

[Learning to Solve Inverse Problems for Perceptual Sound Matching](https://arxiv.org/html/2311.14213v2)
(Han, Lostanlen and Lagrange, 2024 revision) develops a local quadratic loss from
the synthesis-to-auditory-feature Jacobian. It precomputes the metric and tests
nonstationary AM/FM and membrane sounds with joint time–frequency scattering.
The paper discusses weaknesses of plain parameter error and multiscale spectral
loss for changing pitch, inharmonicity and motion.

Application inference: replace fixed semantic slider weights with measured
acoustic sensitivity, including interactions between controls. Our shipped DSP
is not differentiable; finite differences or a separately validated forward
surrogate would be an adaptation, not the paper's exact method. A local metric
also requires checking its useful radius. A new objective must retain explicit
pitch evidence and be tested on gestures and real recordings, not just tones.

[Sound2Synth](https://www.ijcai.org/proceedings/2022/0682.pdf)
(Chen et al., 2022) combines several audio representations for FM parameter
estimation; its designed convolution uses constant-Q information. It works with
a fixed input note in the formulation and evaluates Dexed.

Application inference: test pitch-aware temporal encoders and modality-specific
branches instead of assuming a larger flat shared MLP is sufficient. Our SFX
vary in duration, pitch motion and noise, so musical timbre results do not
establish general game-sound reproduction. Keep all-engine native/mutated
coverage and separately test unseen families and human preferences.

[Universal audio synthesizer control with normalizing flows](https://arxiv.org/abs/1907.00971)
(Esling et al., 2019) connects parameter inference, macro controls and preset
exploration in one model. This is relevant to the user's interest in running a
reproduction model in reverse to explore new presets.

Application inference: represent multiple valid control solutions rather than
averaging them into one mediocre patch. Generate several posterior candidates,
render them with actual DSP and select by human-aligned similarity. This is a
new model experiment, not a capability of v2's sigmoid regression head.

[Simi-SFX](https://arxiv.org/abs/2412.18710)
(Liu and Jin, 2024) uses pretrained audio representations and continuous
similarity conditioning, with footstep and impact datasets. Its authors'
[project description](https://reinliu.github.io/Simi-SFX/) uses distance to
class embedding distributions.

Application inference: a semantic representation might complement gesture and
pitch features for evocative categories and creative interpolation. It should
not replace pitch or event-order checks: embedding closeness and general model
quality do not establish faithful reproduction of our short clips. Evaluate it
with retained heard-only preferences and new blind choices before promotion.

The existing original Bfxr pipeline already includes a learned differentiable
forward surrogate and real-reference finetuning (`invert/surrogate.py` and
`invert/finetune_real.py`). V2's data/head/loss ablation supplies a better raw
starting point; a multisynth forward model and real-audio finetuning should be a
separate measured stage, with surrogate exploitation checked through actual DSP.
