"""Five short pitch-recovery comparisons with exact historical listening PCM."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import time

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.coverage import copy_archived_audio, verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .data import _json_write, file_hash
from .evaluate import rendered_candidates, serializable
from .experiment import listening_history
from .pitch_v5_eval import load_experts, proposals, descriptor_pitch, compare_descriptor_pitch
from .temporal_eval import ENGINES, GUARD_POLICY, proposal_accounting, refine_guarded, target_diagnostics
from .temporal_gallery import copy_reference, save_candidate


MULTISYNTH = Path(__file__).resolve().parents[1]/'multisynth'
DEFAULT_TARGETS = MULTISYNTH/'evaluations/pitch-v5-listening-targets.json'
DEFAULT_OLD_GALLERY = MULTISYNTH/'runs/temporal-v3-listening'
DEFAULT_ARCHIVES = tuple(MULTISYNTH/'listening_data'/name for name in (
    '2026-10-04-neural-v2-quick-01', '2026-10-04-temporal-v3-quick-01'))

def pcm_hash(path):
    """Hash decoded PCM using the immutable listening archive convention."""
    info = sf.info(path)
    if info.samplerate != 44100 or info.channels != 1 or info.subtype != 'PCM_16':
        raise ValueError('Expected mono 44.1 kHz PCM16 audition audio')
    wave, rate = sf.read(path, dtype='int16', always_2d=True)
    return hashlib.sha256(str((rate, wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()


def baseline_observations(history, source):
    """Latest heard winner, retaining charm's separately heard earlier anchor."""
    choices = [o for o in history.get(source['sha256'], []) if o.get('labelSource') == 'direct-choice'
               and Path(o['archive']).name in {p.name for p in DEFAULT_ARCHIVES}]
    latest = max(choices, key=lambda o: o['session']) if choices else None
    if source.get('previouslyRatedReference') and latest is None:
        raise ValueError('Judged reference requires a heard historical winner')
    result = [('previous', latest)] if latest else []
    if source['name'] == 'die/charm2.wav':
        anchors = [o for o in choices if o['candidate']['synth'] == 'Transfxr'
                   and o['archive'].name == '2026-10-04-neural-v2-quick-01']
        if not anchors:
            raise ValueError('charm2 requires its earlier heard Transfxr anchor')
        result.append(('anchor', max(anchors, key=lambda o: o['session'])))
    return result


def copy_observation(dest, role, observation):
    c = observation['candidate']
    verify_archived_audio(observation['archive'], c['audio'])
    path = Path(dest)/(role+'.wav')
    copy_archived_audio(observation['archive']/c['audio']['file'], path)
    if pcm_hash(path) != c['audio']['pcmSha256']:
        raise ValueError('Copied historical PCM changed')
    return {'role': role, 'label': 'Earlier Transfxr choice' if role == 'anchor' else 'Latest heard human choice',
        'synth': c['synth'], 'params': deepcopy(c['params']), 'seed': c['seed'],
        'sourceHash': observation['sourceHash'], 'file': path.name,
        'provenance': {'experimentId': observation['experimentId'], 'candidateId': c['id'],
            'archivedPcmSha256': c['audio']['pcmSha256'], 'auditionWavSha256': file_hash(path),
            'archivedCandidateProvenance': deepcopy(c.get('provenance', {})),
            'previousLabelSource': observation['labelSource'],
            'historicalChoice': deepcopy(observation['target']['choice']),
            'adequacy': 'Relative preference only; not necessarily a convincing recreation.',
            'comparisonScope': 'The latest charm2 choice did not audition the earlier Transfxr anchor.'
                               if role == 'anchor' else 'Preference among auditioned options only.'}}


def deduplicate_cards(dest, cards):
    """One quick option per exact PCM, preserving each alias's provenance."""
    unique, by_hash = [], {}
    for original in cards:
        card = deepcopy(original)
        digest = pcm_hash(Path(dest)/card['file'])
        if digest in by_hash:
            by_hash[digest]['provenance'].setdefault('identicalPcmAliases', []).append(card)
        else:
            card['provenance']['auditionPcmSha256'] = digest
            unique.append(card)
            by_hash[digest] = card
    if len(unique) > 3:
        raise ValueError('Quick listening requires at most three distinct PCM options')
    return unique


def old_reference_bindings(old_gallery):
    """Read the frozen export's reference WAV identities, including unjudged Egg."""
    page = (Path(old_gallery)/'index.html').read_text()
    match = re.search(r'<script type="application/json" id="feedback-data">(.*?)</script>', page, re.S)
    if not match:
        raise ValueError('Old gallery has no reference audio identity')
    model = json.loads(match.group(1))
    return {t['folder']: t['referenceAudioSha256'] for t in model['targets']}


def copy_target(old_gallery, old_row, destination, references, bindings):
    """Require all supplied archives to use the same reference preparation.

    The neural-v2 and temporal-v3 quick archives satisfy this contract; older
    archives may contain a different preparation of the same source file.
    """
    source = old_row['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Frozen source changed')
    path = Path(old_gallery)/old_row['folder']/'target.wav'
    if file_hash(path) != bindings.get(old_row['folder']):
        raise ValueError('Old reference WAV checksum differs')
    pcm_hash(path)  # Require the same audition encoding as all archived references.
    matching = references.get(source['sha256'], [])
    for archive, audio in matching:
        verify_archived_audio(archive, audio)
        if pcm_hash(path) != audio['pcmSha256']:
            raise ValueError('Gallery reference differs from archived reference PCM')
    if matching:
        copy_reference(path, destination, *matching[-1])
    else:
        shutil.copyfile(path, destination)


def refinement_seed(old_folder, engine):
    return 20261011+(int(old_folder)-1)*1009+ENGINES.index(engine)*71


class RecordingRenderer:
    """Observe every trial without modifying frozen DSP or search behavior."""
    def __init__(self, renderer):
        self.renderer = renderer
        self.inventory, self.specs = renderer.inventory, renderer.specs
        self.attempts = []
        self.phase = 'proposals'

    def render(self, synth, params, seed):
        attempt = {'phase': self.phase, 'synth': synth, 'requestedParams': deepcopy(params), 'seed': seed}
        self.attempts.append(attempt)
        try:
            canonical, wave = self.renderer.render(synth, params, seed)
        except (ValueError, RuntimeError) as error:
            attempt['error'] = str(error)
            raise
        attempt.update(params=deepcopy(canonical), audioHash=audio_hash(wave), samples=len(wave))
        return canonical, wave


def _original_card(old_gallery, row, dest):
    card = deepcopy(next(c for c in row['candidates'] if c['role'] == 'original'))
    path = Path(old_gallery)/row['folder']/card['file']
    if file_hash(path) != card['provenance']['auditionWavSha256']:
        raise ValueError('Frozen original Bfxr WAV checksum differs')
    pcm_hash(path)
    shutil.copyfile(path, Path(dest)/'original.wav')
    card['file'] = 'original.wav'
    return card


def _code_bindings():
    tools = Path(__file__).resolve().parents[1]
    paths = list((tools/'match').glob('*.py')) + list((tools/'neural_invert').glob('*.py'))
    paths += [tools/'multisynth'/name for name in ('renderer.py', 'coverage.py', 'coverage_feedback.py',
        'coverage_feedback.js', 'quick_feedback.py', 'quick_choice.js', 'quick_audio.js',
        'quick_listening.js', 'quick_listening.html', 'quick_listening.css')]
    return {str(p.relative_to(tools)): file_hash(p) for p in sorted(paths)}


def run(targets, model, old_gallery, archives, output, budget=384):
    output, old_gallery = Path(output), Path(old_gallery)
    if output.exists():
        raise ValueError('Fresh output required; listening experiments are immutable')
    if type(budget) is not int or budget < 0:
        raise ValueError('Nonnegative integer refinement budget required')
    torch.set_num_threads(1)
    bundle = load_experts(model, 'pitch-v5')
    experts = bundle[0]
    if tuple(experts) != tuple(ENGINES):
        raise ValueError('Expected the three frozen experts in their original order')
    frozen = json.loads(Path(targets).read_text())
    sources = frozen['targets']
    if not sources or len({s['sha256'] for s in sources}) != len(sources):
        raise ValueError('Nonempty unique target sources required')
    historical = json.loads((old_gallery/'results.json').read_text())
    old_rows = {r['source']['sha256']: r for r in historical['results']}
    bindings = old_reference_bindings(old_gallery)
    archives = sorted([Path(p) for p in archives], key=lambda p: p.name)
    if len({p.resolve() for p in archives}) != len(archives):
        raise ValueError('Duplicate archive')
    history = listening_history(archives)
    references = {}
    for archive in archives:
        for target in json.loads((archive/'manifest.json').read_text())['targets']:
            references.setdefault(target['source']['sha256'], []).append((archive, target['referenceAudio']))
    baselines = {s['sha256']: baseline_observations(history, s) for s in sources}
    if any(s['sha256'] not in old_rows for s in sources):
        raise ValueError('Every reference requires its exact old gallery audio')
    source_hashes = {meta['sourceHash'] for _, meta in experts.values()}
    if len(source_hashes) != 1:
        raise ValueError('Expert DSP provenance differs')
    metadata = {'experiment': 'pitch-v5-listening', 'complete': False,
        'galleryTitle': 'Pitch recovery · five short comparisons',
        'galleryIntro': ['Choose the most convincing gesture and feel; “none” and ties are useful.',
            'Earlier audio is copied exactly. A preferred option may still be far off. Please listen even when numerical scores agree.',
            'charm2 retains both the latest Bfxr choice and the earlier Transfxr choice: they were not compared by listening in the latest session.'],
        'targetManifestSha256': file_hash(targets), 'previousReportSha256': file_hash(old_gallery/'results.json'),
        'previousPageSha256': file_hash(old_gallery/'index.html'),
        'archives': [{'path': str(a.resolve()), 'files': {str(p.relative_to(a)): file_hash(p)
                     for p in sorted(a.rglob('*')) if p.is_file()}} for a in archives],
        'codeHashes': _code_bindings(), 'sourceHash': next(iter(source_hashes)),
        'checkpointHashes': {n: m['checkpointHash'] for n, (_, m) in experts.items()},
        'modelDirectory': str(Path(model).resolve()), 'trainedEngines': list(experts),
        'candidateBudgetPerEngine': 4, 'proposalSeed': 20261010,
        'refinementBudgetPerEngine': budget, 'guardPolicy': GUARD_POLICY,
        'refinementSeedPolicy': '20261011 + (old gallery folder number - 1)*1009 + frozen engine index*71',
        'humanReviewRequired': True, 'targetCount': len(sources),
        'selection': 'Minimum unchanged MatchObjective over actual DSP raw and guarded refined candidates; input-only experiment.',
        'baselinePolicy': 'Latest heard winner plus original Bfxr; charm2 reserves its third option for the earlier heard Transfxr anchor. Exact PCM aliases deduplicate.'}
    output.mkdir(parents=True)
    _json_write(output/'manifest.json', metadata)
    started, records = time.monotonic(), []
    with Renderer() as actual_renderer:
        if actual_renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('Expert training DSP differs')
        for index, source in enumerate(sources):
            old = old_rows[source['sha256']]
            if old['source']['path'] != source['path']:
                raise ValueError('Frozen source path differs from old gallery')
            dest = output/f'{index+1:03d}'; dest.mkdir()
            copy_target(old_gallery, old, dest/'target.wav', references, bindings)
            wave, rate = sf.read(dest/'target.wav', dtype='float32')
            if rate != 44100:
                raise ValueError('Reference rate differs')
            objective, diagnostic = MatchObjective(wave), target_diagnostics(wave)
            v5_target = descriptor_pitch(wave)
            renderer = RecordingRenderer(actual_renderer)
            guessed = proposals(bundle, wave, renderer, 4)
            if (any(c['synth'] not in ENGINES for c in guessed)
                    or any(sum(c['synth'] == engine for c in guessed) > 4 for engine in ENGINES)):
                raise ValueError('Unknown engine or excess proposal budget')
            renderer.phase = 'raw-scoring'
            raw, errors = rendered_candidates(guessed, renderer, objective)
            errors.extend({'synth': c['synth'], 'params': c['params'], 'seed': c['seed'],
                           'error': 'Nonfinite proposal score', 'audioHash': audio_hash(c['wave'])}
                          for c in raw if not np.isfinite(c['score']))
            raw = [c for c in raw if np.isfinite(c['score'])]
            accounting = {e: proposal_accounting(4, sum(c['synth'] == e for c in guessed),
                                                sum(c['synth'] == e for c in raw)) for e in ENGINES}
            if not raw:
                _json_write(dest/'failed-generation.json', {'proposals': guessed, 'failures': errors,
                    'accounting': accounting, 'renderAttempts': renderer.attempts})
                raise ValueError('No audible new model proposals')
            refined, seeds, statuses = [], {}, {}
            for engine in ENGINES:
                seed = refinement_seed(old['folder'], engine); seeds[engine] = seed
                options = [c for c in raw if c['synth'] == engine]
                if not options:
                    statuses[engine] = 'skipped-no-audible-proposal'
                    continue
                renderer.phase = 'refinement-'+engine
                refined.append(refine_guarded(min(options, key=lambda c: c['score']), renderer,
                                              objective, diagnostic, budget, seed))
                statuses[engine] = 'completed'
            selected = min(raw+refined, key=lambda c: c['score'])
            renderer.phase = 'selected-replay'
            cards = [save_candidate(dest, selected, renderer, objective)]
            for role, observation in baselines[source['sha256']]:
                cards.append(copy_observation(dest, role, observation))
            if source['name'] != 'die/charm2.wav':
                cards.append(_original_card(old_gallery, old, dest))
            cards = deduplicate_cards(dest, cards)
            def diagnostic_row(c):
                pitch = descriptor_pitch(c['wave'])
                return {**serializable(c), 'actualRenderAudioHash': audio_hash(c['wave']),
                        'v5Pitch': pitch, 'v5PitchComparison': compare_descriptor_pitch(v5_target, pitch)}
            record = {'folder': dest.name, 'source': source, 'candidates': cards,
                'referenceAudioSha256': file_hash(dest/'target.wav'),
                'note': 'A relative preference can still be an unconvincing recreation. Please judge the sound even when the numerical score agrees.',
                'diagnostics': {'target': diagnostic, 'legacyGuardTarget': diagnostic, 'v5TargetPitch': v5_target, 'oldGalleryFolder': old['folder'],
                    'refinementSeeds': seeds, 'proposals': guessed, 'accounting': accounting,
                    'refinementStatus': statuses,
                    'allRaw': [diagnostic_row(c) for c in raw],
                    'allRefined': [diagnostic_row(c) for c in refined], 'failures': errors,
                    'renderAttempts': renderer.attempts,
                    'refinementAttemptsByEngine': {e: sum(a['phase'] == 'refinement-'+e for a in renderer.attempts) for e in ENGINES}}}
            if any(n != (budget if statuses[e] == 'completed' else 0)
                   for e, n in record['diagnostics']['refinementAttemptsByEngine'].items()):
                raise ValueError('Actual refinement trial budget differs')
            _json_write(dest/'report.json', record); records.append(record)
            print(json.dumps({'target': source['name'], 'newSynth': selected['synth'], 'score': selected['score'],
                              'distinctOptions': len(cards)}), flush=True)
    if metadata['codeHashes'] != _code_bindings():
        raise ValueError('Code changed during gallery creation')
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('DSP changed during gallery creation')
    metadata.update(complete=True, seconds=time.monotonic()-started)
    result = export_coverage(output, records, metadata)
    _json_write(output/'manifest.json', metadata)
    print(json.dumps({'experimentId': result['experimentId'], 'targets': len(records)}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--targets', type=Path, default=DEFAULT_TARGETS)
    parser.add_argument('--old-gallery', type=Path, default=DEFAULT_OLD_GALLERY)
    parser.add_argument('--archives', type=Path, nargs='+', default=DEFAULT_ARCHIVES)
    parser.add_argument('--budget', type=int, default=384)
    args = parser.parse_args()
    run(args.targets, args.model, args.old_gallery, args.archives, args.output, args.budget)


if __name__ == '__main__':
    main()
