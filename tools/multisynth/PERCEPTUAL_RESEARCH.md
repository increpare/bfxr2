# Perceptual similarity research, 2026-10-03

The task is reference-conditioned recreation of short game effects, judged by
movement, texture and evocative character. Useful/fun is a separate label.
The following are research leads, not claims that a published metric solves
this task. The active big-v4 experiment was frozen before this additional
literature pass; none of these new proposals silently changes its objective.

## Evidence and implications

| Primary source | Finding relevant to this task | Proposed experiment and limit |
| --- | --- | --- |
| [Gygi, Kidd & Watson (2007), Similarity and categorization of environmental sounds](https://link.springer.com/article/10.3758/BF03193921) | Similarity judgments for 50 environmental sounds clustered harmonic, discrete-impact and continuous sounds. Harmonicity, silence and modulation depth helped predict perceptual dimensions; source associations also mattered. | Add explicit gap structure and modulation-depth features. Compare continuous, impact and tonal subsets diagnostically. Abstract was accessible; the full paper was paywalled. Categories must not become hard filename-based routing rules. |
| [McDermott & Simoncelli (2011), Sound Texture Perception via Statistics of the Auditory Periphery](https://mcdermottlab.mit.edu/bib2php/papers/McDermott_Simoncelli_2011_sound_texture_synthesis.pdf) | Auditory-channel and modulation statistics, including cross-channel correlations, produced recognizable textures where channel power/sparsity alone was insufficient. The work explicitly distinguishes stationary textures from individual events and ordered sequences. | Compare compressed subband-envelope modulation power and correlations for rattles, crackles and sustained noise. Keep a separate ordered event representation for impacts and gestures; global statistics can erase their order. |
| [Grey (1977), Multidimensional perceptual scaling of musical timbres](https://sites.music.columbia.edu/cmc/courses/g6610/fall2019/week3/Grey_1977_Multidimensional_perceptual_scaling_of_musical_timbres.pdf) | In 16 instrument tones, perceptual dimensions related to spectral distribution, harmonic-transient synchrony/spectral fluctuation, and attack energy. | Measure early attack separately at shorter windows and compare how frequency bands enter/decay. Small instrument-tone study, not direct evidence for arbitrary SFX. |
| [Andén, Lostanlen & Mallat (2019), Joint Time–Frequency Scattering](https://arxiv.org/abs/1807.08869) | A structured representation captures joint spectrotemporal modulation beyond a plain averaged spectrum. | Benchmark JTFS as a fixed feature extractor, retaining absolute duration and event cues. Its invariances are hypotheses to test against game-effect ratings, not automatic benefits. |
| [Manocha et al. (2021), CDPAM](https://arxiv.org/abs/2102.05109) | Contrastive pretraining and human triplet judgments improve a learned perceptual audio metric, with demonstrations in speech tasks. | Transfer the evaluation/training idea: reference A, candidate B, candidate C and human preference. Benchmark pretrained CDPAM before adopting it; speech-distortion similarity need not match stylized recreation. |
| [Tian et al. (2025), Assessing the Alignment of Audio Representations with Timbre Similarity Ratings](https://arxiv.org/html/2507.07764v1) | Across 21 instrument-timbre datasets, intermediate style statistics improved alignment; CLAP Huang-style features led their comparison, MFCC remained competitive, and CDPAM transferred poorly. | Compare CLAP intermediate mean/std features, plain embedding and MFCC on identical held-out reference groups. The dataset is instrument timbre, not game SFX. Pitch and timing cannot simply be declared irrelevant here. |
| [Tailleur et al. (2024), Correlation of Fréchet Audio Distance With Human Perception of Environmental Audio Is Embedding Dependant](https://arxiv.org/html/2403.17508v1) | On DCASE Foley systems, embedding choice strongly affected correlation with human quality/category-fit judgments; PANNs Wavegram-Logmel performed best in their comparison. | Include environmental-audio PANNs as a candidate encoder. FAD is a distribution comparison, so this does not validate single-reference cosine distance or justify using FAD to rank individual presets. |

## Concrete next benchmark

1. Freeze the v4 feedback before inspecting any new feature's test performance.
   Keep exact-reference grouping across sessions; additionally group related
   source takes when metadata permits. Fit scales and weights inside folds.
2. Test four additions separately: short-window attack synchrony; ordered onset
   and gap structure; subband modulation power/correlation; pretrained style
   features. Compare against auditory-v1 and v4 on the same pairs. Include
   ablations, ties and per-reference performance, not only an overall average.
3. Create diagnostic transformations: gain/leading silence, small onset shifts,
   modest duration changes, reversed sweeps, reordered/repeated events, and
   different random texture seeds. Human validation is required before declaring
   an augmentation similarity-preserving. Reversing a rise or adding a bounce
   can fundamentally change a game cue.
4. Only promote a metric after new listening comparisons of optimized outputs.
   Correct ranking of existing finalists is necessary but insufficient: search
   can exploit a distance's blind spots. Use shared candidate pools and preserve
   an original-distance competitor, as big-v4 already does.

The main hypothesis is **conditional timing tolerance**: ignore incidental
microtiming within a texture while preserving salient attacks, repetitions and
pitch/energy direction. This is an engineering inference from the sources and
the user's feedback, not a result established by any one paper. Begin with a
small explicit feature benchmark before training a complex gating network on
the limited retained judgments.
