"""Small reproducible listening comparison with exact archived baselines."""
import argparse
import hashlib
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time

import numpy as np
import soundfile as sf
import torch

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.coverage import copy_archived_audio, verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from .benchmark import audio_hash, pitch_diagnostic
from .data import _json_write, file_hash
from .evaluate import OriginalBfxr, rendered_candidates, serializable
from .experiment import audition_details, audition_pcm, listening_history, previous_best, _write_wave
from .temporal_eval import load_experts, proposals, refine_guarded, target_diagnostics, GUARD_POLICY


def previous_candidate(history, source_hash):
    observations = [o for o in history.get(source_hash, [])
                    if o.get('labelSource') == 'direct-choice' or o.get('rating') is not None]
    return previous_best(observations) if observations else None


def check_resume(output, metadata):
    output = Path(output)
    old = json.loads((output/'manifest.json').read_text())
    if old.get('complete') or (output/'results.json').exists() or (output/'index.html').exists():
        raise ValueError('Cannot resume a completed gallery')
    for key, value in metadata.items():
        if key not in ('codeSha256', 'complete') and old.get(key) != value:
            raise ValueError('Resume inputs differ: '+key)
    return old


def completed_record(dest, source):
    dest = Path(dest)
    row = json.loads((dest/'report.json').read_text())
    if row['source'] != source:
        raise ValueError('Resumed source differs')
    for c in row['candidates']:
        path = dest/c['file']
        if Path(c['file']).name != c['file'] or not path.is_file():
            raise ValueError('Resumed audio path invalid')
        p = c['provenance']
        if 'auditionWavSha256' in p:
            valid = file_hash(path) == p['auditionWavSha256']
        else:
            wave, rate = sf.read(path, dtype='int16', always_2d=True)
            digest = hashlib.sha256(str((rate, wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
            valid = digest == p.get('archivedPcmSha256')
        if not valid:
            raise ValueError('Resumed audio changed')
    return row


def retained_code_map(output, prior):
    return {p.parent.name: prior.get('generationCodeByFolder', {}).get(p.parent.name, prior['codeSha256'])
            for p in Path(output).glob('*/report.json')}


def save_candidate(dest, candidate, renderer, objective, filename='selected.wav'):
    canonical, replay = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
    if canonical != candidate['params'] or not np.array_equal(replay, candidate['wave']):
        raise ValueError('Actual candidate control/PCM replay differs')
    path = Path(dest)/filename
    _write_wave(path, candidate['wave'])
    audition, rate = sf.read(path, dtype='float32')
    if rate != 44100 or not np.array_equal(audition, audition_pcm(replay)):
        raise ValueError('Exported candidate does not match the single audition transform')
    return {**serializable(candidate), 'role': 'selected', 'label': 'New trained approximation',
            'file': filename, 'sourceHash': renderer.inventory['sourceHash'],
            'provenance': {**candidate['provenance'], 'actualRenderAudioHash': audio_hash(replay),
                'pitchDiagnostic': pitch_diagnostic(replay), **audition_details(path, objective)}}


def copy_reference(source, destination, archive, audio):
    verify_archived_audio(archive, audio)
    old, rate = sf.read(source, dtype='int16', always_2d=True)
    frozen, frozen_rate = sf.read(Path(archive)/audio['file'], dtype='int16', always_2d=True)
    if rate != frozen_rate or not np.array_equal(old, frozen):
        raise ValueError('Gallery reference differs from archived reference PCM')
    shutil.copyfile(source, destination)


def backend_provenance(renderer):
    """Bind the actual running original renderer, including native binary or Node sources."""
    from match.bfxr_io import render_cli_cmd
    args = list(renderer._workers[0].proc.args)
    root = Path(__file__).resolve().parents[2]
    paths = [Path(shutil.which(args[0]) or args[0]).resolve()]
    paths.extend(Path(a).resolve() for a in args[1:] if Path(a).is_file())
    cli = render_cli_cmd()
    paths.extend(Path(shutil.which(a) or a).resolve() for a in cli if shutil.which(a) or Path(a).is_file())
    paths.extend([root/'tools/match/renderer.py', root/'tools/match/bfxr_io.py'])
    backend = 'node' if len(args) > 1 and str(args[1]).endswith('.js') else 'native'
    if backend == 'node' or any(str(a).endswith('.js') for a in cli):
        paths.extend((root/'js').rglob('*.js'))
        paths.extend((root/'tools/render').glob('*.js'))
    files = {str(p.resolve()): file_hash(p) for p in sorted(set(paths))}
    bound = {'backend': backend, 'command': args, 'files': files}
    return {**bound, 'sourceHash': hashlib.sha256(json.dumps(bound, sort_keys=True).encode()).hexdigest()}


def run(targets, model, old_gallery, archives, checkpoint, output, budget=384, resume=False):
    output = Path(output)
    if (output.exists() and not resume) or (resume and not output.is_dir()) or budget < 0:
        raise ValueError('Fresh output and nonnegative budget required')
    torch.set_num_threads(1)
    experts = load_experts(model)
    frozen = json.loads(Path(targets).read_text())
    old_gallery = Path(old_gallery)
    historical = json.loads((old_gallery/'results.json').read_text())
    old_rows = {r['source']['sha256']: r for r in historical['results']}
    history = listening_history([Path(p) for p in archives])
    references = {}
    for archive in archives:
        archive = Path(archive)
        for target in json.loads((archive/'manifest.json').read_text())['targets']:
            references[target['source']['sha256']] = (archive, target['referenceAudio'])
    if file_hash(checkpoint) != historical['metadata']['bfxrCheckpointSha256']:
        raise ValueError('Original Bfxr checkpoint changed')
    source_hashes = {meta['sourceHash'] for _, meta in experts.values()}
    if len(source_hashes) != 1:
        raise ValueError('Expert DSP provenance differs')
    output.mkdir(parents=True, exist_ok=resume)
    metadata = {'experiment': 'temporal-v3-listening', 'complete': False,
        'galleryTitle': 'Temporal inverse · six listening comparisons',
        'galleryIntro': ['Choose the most convincing gesture and feel. “None” is useful when all approximations miss.',
            'This batch revisits five familiar examples and adds a jump sound. Earlier audio is copied exactly. A numerical improvement is only a hypothesis until you listen.',
            'Optional notes can say “close enough”, “still far off”, or what matters: attack, movement, rhythm, texture, tail.'],
        'targetManifestSha256': file_hash(targets), 'previousReportSha256': file_hash(old_gallery/'results.json'),
        'sourceHash': next(iter(source_hashes)), 'checkpointHashes': {n: m['checkpointHash'] for n, (_, m) in experts.items()},
        'modelDirectory': str(Path(model).resolve()), 'codeSha256': file_hash(__file__),
        'evaluationCodeSha256': file_hash(Path(__file__).with_name('temporal_eval.py')),
        'trainedEngines': list(experts), 'refinementBudgetPerEngine': budget,
        'guardPolicy': GUARD_POLICY, 'humanReviewRequired': True,
        'samplingPolicy': 'Fixed regression examples plus new gesture coverage; subsequent regular batches include consensus successes and uncertain cases.',
        'targetCount': len(frozen['targets'])}
    prior = check_resume(output, metadata) if resume else None
    if prior:
        prior_hash = file_hash(output/'manifest.json')
        shutil.copyfile(output/'manifest.json', output/('resume-manifest-'+prior_hash[:12]+'.json'))
        metadata['resumption'] = {'priorManifestSha256': prior_hash,
            'priorCodeSha256': prior['codeSha256'], 'reusedFolders': []}
    metadata['generationCodeByFolder'] = retained_code_map(output, prior) if prior else {}
    _json_write(output/'manifest.json', metadata)
    started = time.monotonic()
    records = []
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        original_backend = backend_provenance(bfxr)
        metadata['originalBfxrBackend'] = original_backend
        if renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('Expert training DSP differs')
        original = None
        for index, source in enumerate(frozen['targets']):
            if file_hash(source['path']) != source['sha256']:
                raise ValueError('Frozen source changed')
            dest = output/f'{index+1:03d}'
            if resume and (dest/'report.json').is_file():
                reference, rate = sf.read(dest/'target.wav', dtype='float32')
                if source['sha256'] in references:
                    archive, audio = references[source['sha256']]
                    verify_archived_audio(archive, audio)
                    expected, expected_rate = sf.read(archive/audio['file'], dtype='float32')
                else:
                    expected, expected_rate = audition_pcm(prepare_target(source['path'])), 44100
                if rate != expected_rate or not np.array_equal(reference, expected):
                    raise ValueError('Resumed reference audio changed')
                records.append(completed_record(dest, source))
                metadata['resumption']['reusedFolders'].append(dest.name)
                metadata['generationCodeByFolder'][dest.name] = prior.get('generationCodeByFolder', {}).get(dest.name, prior['codeSha256'])
                print(json.dumps({'reused': source['name']}), flush=True)
                continue
            dest.mkdir(exist_ok=resume)
            old = old_rows.get(source['sha256'])
            if old:
                ref = old_gallery/old['folder']/'target.wav'
                archive, audio = references[source['sha256']]
                copy_reference(ref, dest/'target.wav', archive, audio)
            else:
                _write_wave(dest/'target.wav', prepare_target(source['path']))
            wave, rate = sf.read(dest/'target.wav', dtype='float32')
            if rate != 44100:
                raise ValueError('Reference rate differs')
            objective, diagnostic = MatchObjective(wave), target_diagnostics(wave)
            raw, errors = rendered_candidates(proposals(experts, wave, renderer, 4), renderer, objective)
            if not raw:
                raise ValueError('No audible new model proposals')
            starts = [min([r for r in raw if r['synth'] == engine], key=lambda r:r['score'])
                      for engine in experts if any(r['synth'] == engine for r in raw)]
            refined = [refine_guarded(r, renderer, objective, diagnostic, budget, 20261011+index*1009+i*71)
                       for i, r in enumerate(starts)]
            selected = min(refined+raw, key=lambda r:r['score'])
            cards = [save_candidate(dest, selected, renderer, objective)]
            previous = previous_candidate(history, source['sha256'])
            if previous:
                c = previous['candidate']
                copy_archived_audio(previous['archive']/c['audio']['file'], dest/'previous.wav')
                cards.append({'role': 'previous', 'label': 'Earlier human choice', 'synth': c['synth'],
                    'params': c['params'], 'seed': c['seed'], 'sourceHash': previous['sourceHash'],
                    'file': 'previous.wav', 'provenance': {'experimentId': previous['experimentId'],
                        'candidateId': c['id'], 'archivedPcmSha256': c['audio']['pcmSha256'],
                        'previousLabelSource': previous.get('labelSource', 'scalar-likeness'),
                        'adequacy': 'Relative preference only; not necessarily a successful recreation.'}})
            if old:
                c = deepcopy(next(c for c in old['candidates'] if c['role'] == 'original'))
                path = old_gallery/old['folder']/c['file']
                if file_hash(path) != c['provenance']['auditionWavSha256']:
                    raise ValueError('Frozen original Bfxr audio changed')
                shutil.copyfile(path, dest/'original.wav')
                c['file'] = 'original.wav'; cards.append(c)
            else:
                if original is None:
                    original = OriginalBfxr(checkpoint, bfxr)
                c = original.approximate(wave, objective, budget=2000, seed=20261011+index*1009)
                replay = bfxr.render(c['params'], seed=c['seed'])
                if not np.array_equal(replay, c['wave']):
                    raise ValueError('Original Bfxr controls/seed replay differs')
                _write_wave(dest/'original.wav', c['wave'])
                audition, rate = sf.read(dest/'original.wav', dtype='float32')
                if rate != 44100 or not np.array_equal(audition, audition_pcm(replay)):
                    raise ValueError('Original Bfxr audition differs from actual replay')
                cards.append({**serializable(c), 'role': 'original', 'label': 'Original Bfxr',
                    'file': 'original.wav', 'sourceHash': original_backend['sourceHash'],
                    'provenance': {**c['provenance'], 'actualRenderAudioHash': audio_hash(replay),
                                   'renderBackend': original_backend,
                                   **audition_details(dest/'original.wav', objective)}})
            record = {'folder': dest.name, 'source': source, 'candidates': cards,
                'note': 'Please judge the sound even if the model and numerical score agree. A preferred option may still be far off.',
                'diagnostics': {'target': diagnostic, 'allRaw': [serializable(c) for c in raw],
                    'allRefined': [serializable(c) for c in refined], 'failures': errors}}
            _json_write(dest/'report.json', record)
            records.append(record)
            metadata['generationCodeByFolder'][dest.name] = metadata['codeSha256']
            _json_write(output/'manifest.json', metadata)
            print(json.dumps({'target': source['name'], 'newSynth': selected['synth'],
                              'score': selected['score'], 'guardActive': diagnostic['guardReliable']}), flush=True)
        if backend_provenance(bfxr) != original_backend:
            raise ValueError('Original Bfxr rendering backend changed')
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
    for name in ('targets', 'model', 'old-gallery', 'checkpoint', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--archives', type=Path, nargs='+', required=True)
    parser.add_argument('--budget', type=int, default=384)
    parser.add_argument('--resume', action='store_true', help='Reuse verified completed rows of an incomplete gallery with matching inputs')
    a = parser.parse_args()
    run(a.targets, a.model, a.old_gallery, a.archives, a.checkpoint, a.output, a.budget, a.resume)


if __name__ == '__main__':
    main()
