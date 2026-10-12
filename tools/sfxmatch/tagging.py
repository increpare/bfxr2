"""How well do pretrained audio models agree with the hand-tagged corpus?

    uv run --with transformers python -m sfxmatch.tagging
    uv run --with transformers --with msclap --with panns-inference python -m sfxmatch.tagging --models all

Two tests. Zero-shot: a text-audio model picks the tag whose description is
nearest the sound, with no training. Neighbours: for any model, does a
sound's nearest neighbours in embedding space carry its tag (leave one out)?
The second works for fixed-label taggers too, whose own labels are not ours.

The tags say what a sound is used for in a game, so some are ambiguous by
ear ('attack' holds jumps, 'fall' holds a card flip). Nothing scores 100%.
"""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torchaudio

from . import benchmark

HERE = Path(__file__).resolve().parent
CACHE = HERE/'runs/tagging'
SECONDS = 10
# What each tag means in words. 'step' is scored as 'footstep'; 'misc' (one file) is left out.
PHRASES = {
    'animal': 'an animal noise', 'attack': 'a whoosh and a strike', 'bell': 'a bell ringing',
    'bird': 'a bird chirping', 'carbeep': 'a car horn', 'card': 'playing cards being shuffled or dealt',
    'chains': 'a chain or belt rattling', 'chips': 'poker chips clinking', 'click': 'a mechanical click',
    'clothes': 'cloth rustling', 'collect': 'a coin pickup chime', 'computer': 'a robot voice',
    'dice': 'dice being rolled', 'die': 'a descending failure tune', 'door': 'a door opening or closing',
    'double_jump': 'a wing flap', 'draw_weapon': 'a blade being drawn', 'explode': 'an explosion',
    'fall': 'a falling whistle', 'footstep': 'footsteps', 'forbidden': 'an error buzzer',
    'hit': 'a punch or impact', 'jump': 'a cartoon jump', 'laser': 'a laser gun',
    'magic': 'a magic spell', 'monster': 'a monster growling', 'motiv': 'a short musical jingle',
    'power_up': 'a rising power-up chime', 'select': 'a short menu beep', 'shoot': 'a gunshot',
    'slime': 'a wet squelch', 'sword': 'a sword slash', 'unlock': 'a metal latch',
    'voice': 'a person grunting or breathing'}
MERGE = {'step': 'footstep'}


def corpus():
    """-> [(tag, path)] for every tagged file we score."""
    root = benchmark.corpus_root()/'tags'
    rows = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        tag = MERGE.get(folder.name, folder.name)
        if tag in PHRASES:
            rows += [(tag, f) for f in sorted(folder.iterdir()) if f.suffix.lower() in ('.wav', '.ogg', '.flac')]
    return [row for row in rows if readable(row[1])]


def readable(path):
    import soundfile as sf
    try:
        return sf.info(str(path)).frames > 0
    except Exception:      # a handful of library files have headers libsndfile rejects
        return False


def audio(path, rate):
    from match.audio import load_audio
    wave = torch.from_numpy(load_audio(path)[:44100*SECONDS])
    return torchaudio.functional.resample(wave, 44100, rate).numpy()


class LaionClap:
    def __init__(self, name):
        from transformers import ClapModel, ClapProcessor
        self.processor, self.model = ClapProcessor.from_pretrained(name), ClapModel.from_pretrained(name).eval()

    @staticmethod
    def _tensor(output):
        return output if isinstance(output, torch.Tensor) else output.pooler_output

    @torch.no_grad()
    def sounds(self, paths):
        rows = []
        for path in paths:
            wave = audio(path, 48000)
            try:
                inputs = self.processor(audio=[wave], sampling_rate=48000, return_tensors='pt')
            except TypeError:
                inputs = self.processor(audios=[wave], sampling_rate=48000, return_tensors='pt')
            rows.append(self._tensor(self.model.get_audio_features(**inputs))[0].numpy())
        return np.stack(rows)

    @torch.no_grad()
    def texts(self, phrases):
        return self._tensor(self.model.get_text_features(**self.processor(text=phrases, return_tensors='pt', padding=True))).numpy()


class MsClap:
    def __init__(self, version):
        from msclap import CLAP
        self.model = CLAP(version=version, use_cuda=False)

    def sounds(self, paths):
        rows = []
        for path in paths:      # it reads files itself; give it mono 44.1 kHz wavs it can always decode
            import soundfile as sf
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav') as handle:
                sf.write(handle.name, audio(path, 44100), 44100)
                rows.append(self.model.get_audio_embeddings([handle.name], resample=True)[0].detach().numpy())
        return np.stack(rows)

    def texts(self, phrases):
        return self.model.get_text_embeddings(phrases).detach().numpy()


class Ast:
    """Audio Spectrogram Transformer trained on AudioSet: a fixed-label tagger."""

    def __init__(self, name='MIT/ast-finetuned-audioset-10-10-0.4593'):
        from transformers import ASTFeatureExtractor, ASTForAudioClassification
        self.extractor, self.model = ASTFeatureExtractor.from_pretrained(name), ASTForAudioClassification.from_pretrained(name).eval()
        self.labels = None

    @torch.no_grad()
    def sounds(self, paths):
        rows, labels = [], []
        for path in paths:
            inputs = self.extractor(audio(path, 16000), sampling_rate=16000, return_tensors='pt')
            out = self.model(**inputs, output_hidden_states=True)
            rows.append(out.hidden_states[-1][0, :2].mean(0).numpy())
            labels.append(self.model.config.id2label[int(out.logits[0].argmax())])
        self.labels = labels
        return np.stack(rows)


class Panns:
    """CNN14 trained on AudioSet: the small, fast fixed-label tagger."""

    def __init__(self):
        from panns_inference import AudioTagging, labels
        self.model, self.names, self.labels = AudioTagging(checkpoint_path=None, device='cpu'), labels, None

    def sounds(self, paths):
        rows, labels = [], []
        for path in paths:
            wave = audio(path, 32000)
            wave = np.pad(wave, (0, max(0, 32000-len(wave))))       # it needs at least a second
            scores, embedding = self.model.inference(wave[None])
            rows.append(embedding[0]); labels.append(self.names[int(scores[0].argmax())])
        self.labels = labels
        return np.stack(rows)


MODELS = {'laion-clap': lambda: LaionClap('laion/clap-htsat-unfused'),
          'laion-clap-larger': lambda: LaionClap('laion/larger_clap_general'),
          'ms-clap-2023': lambda: MsClap('2023'),
          'ast-audioset': Ast, 'panns-cnn14': Panns}
DEFAULT = ('laion-clap', 'laion-clap-larger', 'ast-audioset')


def unit(x):
    return x/np.linalg.norm(x, axis=1, keepdims=True).clip(1e-9)


def zero_shot(sounds, texts, tags, names):
    order = np.argsort(-(unit(sounds) @ unit(texts).T), axis=1)
    truth = np.array([names.index(t) for t in tags])
    return float(np.mean(order[:, 0] == truth)), float(np.mean((order[:, :3] == truth[:, None]).any(1))), order[:, 0]


def neighbours(sounds, tags, k=5, least=5):
    """Leave-one-out: does a similarity-weighted vote of the k nearest other sounds give the right tag?"""
    similar = unit(sounds) @ unit(sounds).T
    np.fill_diagonal(similar, -np.inf)
    counts = Counter(tags)
    hits = []
    for i, tag in enumerate(tags):
        if counts[tag] < least:
            continue
        votes = defaultdict(float)
        for j in np.argsort(-similar[i])[:k]:
            votes[tags[j]] += similar[i, j]
        hits.append(max(votes, key=votes.get) == tag)
    return float(np.mean(hits)), len(hits)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--models', nargs='+', default=list(DEFAULT), help=f'any of {list(MODELS)} or "all"')
    args = parser.parse_args()
    chosen = list(MODELS) if args.models == ['all'] else args.models
    rows = corpus()
    tags, paths, names = [r[0] for r in rows], [r[1] for r in rows], list(PHRASES)
    majority = Counter(tags).most_common(1)[0]
    print(f'{len(rows)} files, {len(set(tags))} tags; always guessing "{majority[0]}" scores {majority[1]/len(rows)*100:.0f}%')
    CACHE.mkdir(parents=True, exist_ok=True)
    best = None
    for label in chosen:
        cache = CACHE/f'{label}.npz'
        if cache.exists():
            saved = np.load(cache, allow_pickle=True)
            sounds, texts, plain, own = saved['sounds'], saved['texts'], saved['plain'], saved['own']
        else:
            try:
                model = MODELS[label]()
            except ImportError as error:
                print(f'{label}: skipped ({error})'); continue
            sounds = model.sounds(paths)
            described = hasattr(model, 'texts')
            texts = model.texts([PHRASES[n] for n in names]) if described else np.zeros(0)
            plain = model.texts([n.replace('_', ' ') for n in names]) if described else np.zeros(0)
            own = np.array(getattr(model, 'labels', None) or [], dtype=object)
            np.savez(cache, sounds=sounds, texts=texts, plain=plain, own=own)
        near, scored = neighbours(sounds, tags)
        line = f'{label:20s} neighbours {near*100:5.1f}% (n={scored})'
        if len(texts):
            top1, top3, guess = zero_shot(sounds, texts, tags, names)
            bare = zero_shot(sounds, plain, tags, names)[0]
            line += f' | zero-shot top-1 {top1*100:5.1f}%, top-3 {top3*100:5.1f}% | with bare tag words {bare*100:5.1f}%'
            if best is None or top1 > best[0]:
                best = (top1, label, guess)
        print(line, flush=True)
        if len(own):
            by_tag = defaultdict(Counter)
            for tag, mine in zip(tags, own):
                by_tag[tag][mine] += 1
            print('    its own top label per tag: ' + '; '.join(
                f'{tag} -> {by_tag[tag].most_common(1)[0][0]}' for tag in ('footstep', 'card', 'jump', 'select', 'sword', 'collect')))
    if best:
        _, label, guess = best
        print(f'\nper tag, zero-shot with {label} (tags with 5+ files):')
        per = defaultdict(list)
        for tag, g in zip(tags, guess):
            per[tag].append(names[g])
        for tag in sorted(per, key=lambda t: -np.mean([g == t for g in per[t]])):
            if len(per[tag]) >= 5:
                wrong = Counter(g for g in per[tag] if g != tag).most_common(2)
                print(f'  {tag:12s} {np.mean([g == tag for g in per[tag]])*100:4.0f}% of {len(per[tag]):2d}'
                      + (f'   mistaken for {", ".join(f"{g} x{n}" for g, n in wrong)}' if wrong else ''))


if __name__ == '__main__':
    main()
