"""At most five human comparisons of frozen-v3 actual-render pitch calibration.

Historical preferences select listening anchors only. No human choices, category
labels or prior ratings participate in candidate calibration or selection.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .data import _json_write, file_hash
from .evaluate import OriginalBfxr, rendered_candidates
from .experiment import audition_pcm, listening_history
from .pitch_calibration import POLICY, calibrate_candidate, select_candidates
from .pitch_calibration_eval import (ArtifactPersistenceError, _AuditedRenderer,
    _attach_audio, _bind, _check_bindings, _dataset_bindings, _hash_json, _persist,
    _read, _without_wave, read_audio, save_audio)
from .pitch_v5_eval import descriptor_pitch
from .pitch_v5_gallery import (MULTISYNTH, DEFAULT_OLD_GALLERY, DEFAULT_ARCHIVES,
    baseline_observations, copy_observation, copy_target, deduplicate_cards,
    old_reference_bindings, pcm_hash, _code_bindings as _shared_code_bindings, RecordingRenderer)
from .temporal_eval import (ENGINES, GUARD_POLICY, load_experts, proposals,
    proposal_accounting, refine_guarded, target_diagnostics)
from .temporal_gallery import backend_provenance

DEFAULT_TARGETS = MULTISYNTH/'evaluations/pitch-calibration-listening-targets.json'
DEFAULT_GATE = MULTISYNTH/'evaluations/pitch-calibration-audit.json'
DEFAULT_MODEL = MULTISYNTH/'runs/temporal-v3/hybrid-experts'
DEFAULT_CHECKPOINT = Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
OLD_AUDIT = MULTISYNTH/'evaluations/temporal-v3-listening-audit.json'
OLD_REPORT_SHA = '660fc5264771020902dc6c7df02408a25d9f43a0b374f6c3d6e542a6bf5ce315'
OLD_HTML_SHA = '9ab972ecd3ea200727be02cc4a071aad97669938d2d6449391c1020820bc7640'
ORIGINAL_CHECKPOINT_SHA = '47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98'
TARGET_NAMES = ('die/charm2.wav', 'attack/battleStart.wav', 'select/Select Beep.wav',
                'bell/impactBell_heavy_003.ogg', 'fall/Descending Fall Whistle.wav')


def prepare_reference(source, destination, old, references, bindings, old_gallery=DEFAULT_OLD_GALLERY):
    """Write already-quantized fresh audio once, or copy exact heard charm PCM."""
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Frozen source changed')
    if source.get('previouslyRatedReference'):
        if old is None or old['source']['sha256'] != source['sha256']:
            raise ValueError('Historical reference required')
        copy_target(old_gallery, old, destination, references, bindings)
        if pcm_hash(destination) != source['archivedReferencePcmSha256']:
            raise ValueError('Archived reference PCM differs')
        wave, rate = sf.read(destination, dtype='float32')
    else:
        wave = audition_pcm(prepare_target(source['path']))
        if hashlib.sha256(wave.tobytes()).hexdigest() != source['auditionFloat32Sha256']:
            raise ValueError('Fresh reference float32 binding differs')
        # audition_pcm already normalized and quantized: never transform it again.
        sf.write(destination, wave, 44100, subtype='PCM_16')
        actual, rate = sf.read(destination, dtype='float32')
        if not np.array_equal(wave, actual):
            raise ValueError('Fresh reference PCM write differs')
    if rate != 44100:
        raise ValueError('Reference rate differs')
    pcm_hash(destination)
    return wave


def audition_card(dest, row, role, label, source_hash):
    """Export a single audition transform of the exact persisted selected PCM."""
    wave = row['wave']
    if 'waveFile' in row:
        saved = read_audio(row['waveFile'], row['waveFileSha256'], row['audioHash'])
        if not np.array_equal(wave, saved):
            raise ValueError('Candidate differs from persisted PCM')
    heard = audition_pcm(wave)
    path = Path(dest)/(role+'.wav')
    sf.write(path, heard, 44100, subtype='PCM_16')
    actual, rate = sf.read(path, dtype='float32')
    if rate != 44100 or not np.array_equal(actual, heard):
        raise ValueError('Candidate audition write differs')
    return {**_without_wave(row), 'role': role, 'label': label, 'file': path.name,
        'sourceHash': row.get('renderSourceHash', source_hash),
        'provenance': {**deepcopy(row.get('provenance', {})),
            'actualRenderAudioHash': audio_hash(wave), 'auditionWavSha256': file_hash(path),
            'auditionTransform': 'single peak normalization and PCM16 quantization'}}


def make_cards(dest, selection, original, observations, source_hash):
    cards = [audition_card(dest, selection['selected'], 'selected',
                          'Pitch-calibrated approximation', source_hash)]
    if observations:
        cards.extend(copy_observation(dest, role, observation) for role, observation in observations)
    else:
        cards.extend([audition_card(dest, selection['baseline'], 'baseline',
                                    'Uncalibrated best approximation', source_hash),
                      audition_card(dest, original, 'original', 'Original Bfxr', source_hash)])
    return deduplicate_cards(dest, cards)


def display_decision(cards, heard_sets, historical):
    identities = {c['provenance']['auditionPcmSha256'] for c in cards}
    reason = ('one_distinct_option' if len(identities) < 2 else
              'previously_compared_pcm_set' if historical and any(identities <= set(s) for s in heard_sets)
              else 'new_comparison')
    return dict(included=reason == 'new_comparison', reason=reason, pcmSha256s=sorted(identities))



def persist_candidate(row, stem):
    row = {**deepcopy(row), **_persist({}, save_audio, stem, row['wave'])}
    if not row['audible'] or not np.isfinite(row['score']):
        raise ValueError('Original pool requires finite audible actual PCM')
    return row


def calibrate_pool(pool, target, renderer, output):
    """Keep every original, persist all calibration attempts, and select once."""
    output = Path(output)
    output.mkdir(parents=True)
    record = dict(complete=False, originals=[], accepted=[], calibrations=[], callJournalFiles=[],
        accounting=dict(originalPoolCount=len(pool), maximumAdditionalRenders=3*len(pool),
            originalValidationReplays=0, additionalRenderCount=0, failedRenderCalls=0,
            incompatibleOriginals=0))
    path = output/'report.json'
    _json_write(path, record)
    originals, accepted = [], []
    objective = MatchObjective(target)
    audited = None
    try:
        for index, source in enumerate(pool):
            audited = None
            source = persist_candidate({**source, 'sourceCandidateIndex': index}, output/f'original-{index:02d}')
            source.setdefault('calibrationCompatible', True)
            if not source['calibrationCompatible']:
                source = select_candidates([source], [], target)['baseline']
                originals.append(source)
                record['originals'].append(_without_wave(source))
                record['calibrations'].append(dict(sourceCandidateIndex=index,
                    status='incompatible_original_backend', additionalRenderCount=0, attempts=[]))
                record['accounting']['incompatibleOriginals'] += 1
                _json_write(path, record)
                continue
            audited = _AuditedRenderer(renderer, source, objective, output/f'candidate-{index:02d}', index)
            result = calibrate_candidate(source, target, audited, objective)
            original = _attach_audio(result['original'], audited.calls[0])
            originals.append(original)
            steps, cursor = {}, 1
            for attempt in result['attempts']:
                attempt['sourceCandidateIndex'] = index
                if attempt['renderCount']:
                    attempt.update(_without_wave(_attach_audio(attempt, audited.calls[cursor])))
                    cursor += 1
                steps[attempt['step']] = attempt
            if (cursor != len(audited.calls) or result['additionalRenderCount'] != len(audited.calls)-1
                    or result['additionalRenderCount'] > 3):
                raise ValueError('Calibration render accounting mismatch')
            for row in result['accepted']:
                step = row['provenance']['pitchCalibration']['step']
                accepted.append({**_attach_audio(row, steps[step]),
                    'sourceCandidateIndex': index, 'calibrationStep': step,
                    'renderSourceHash': renderer.inventory['sourceHash']})
            record['originals'].append(_without_wave(original))
            record['accepted'] = _without_wave(accepted)
            record['calibrations'].append(dict(sourceCandidateIndex=index, status=result['status'],
                additionalRenderCount=result['additionalRenderCount'], attempts=_without_wave(result['attempts'])))
            record['callJournalFiles'].extend(str((audited.dest/f'{n:02d}.json').resolve())
                                              for n in range(len(audited.calls)))
            record['accounting']['originalValidationReplays'] += 1
            record['accounting']['additionalRenderCount'] += result['additionalRenderCount']
            record['accounting']['failedRenderCalls'] += sum(c['status'] == 'render_error' for c in audited.calls)
            if record['accounting']['additionalRenderCount'] > record['accounting']['maximumAdditionalRenders']:
                raise ValueError('Additional actual-render budget exceeded')
            _json_write(path, record)
        # This also computes diagnostics for an incompatible native original,
        # from its own actual audio, without ever substituting shipped DSP PCM.
        record['selection'] = select_candidates(originals, accepted, target)
        record['complete'] = True
        _json_write(path, _without_wave(record))
    except BaseException as exc:
        if audited is not None and not any(c['sourceCandidateIndex'] == audited.index
                                           for c in record['calibrations']):
            record['accounting']['originalValidationReplays'] += sum(c['renderCount'] for c in audited.calls[:1])
            record['accounting']['additionalRenderCount'] += sum(c['renderCount'] for c in audited.calls[1:])
            record['accounting']['failedRenderCalls'] += sum(c['status'] == 'render_error' for c in audited.calls)
            for number in range(len(audited.calls)):
                journal_path = audited.dest/f'{number:02d}.json'
                if journal_path.is_file():
                    record['callJournalFiles'].append(str(journal_path.resolve()))
        record['complete'] = False
        record['failure'] = dict(type=type(exc).__name__, error=str(exc),
                                 renderCalls=deepcopy(audited.calls) if audited else [])
        _json_write(path, _without_wave(record))
        raise
    # Callers need actual PCM for card export, while reports never contain arrays.
    record['originals'], record['accepted'] = originals, accepted
    return record


def verify_original(candidate, native, renderer, objective, dest, backend):
    """Retain native output; a mismatch only disables its pitch adjustments."""
    replay = native.render(candidate['params'], seed=candidate['seed'])
    replay_artifact = _persist({}, save_audio, Path(dest)/'original-native-replay', replay)
    if not np.array_equal(replay, candidate['wave']):
        raise ValueError('Original Bfxr native replay differs')
    score = float(objective.score_batch([replay])[0])
    if not np.isfinite(score) or not np.isclose(score, candidate['score'], rtol=1e-9, atol=1e-9):
        raise ValueError('Original Bfxr score differs')
    diagnostic = dict(backend=deepcopy(backend), actualNativeReplay=replay_artifact,
        declaredBudget=candidate['provenance']['budget'],
        actualEvaluations=candidate['provenance']['evaluations'], shippedDspMatches=False)
    try:
        canonical, shipped = renderer.render('Bfxr', candidate['params'], candidate['seed'])
    except (ValueError, RuntimeError, OSError) as exc:
        diagnostic['shippedReplayError'] = dict(type=type(exc).__name__, error=str(exc))
    else:
        diagnostic['shippedReplay'] = dict(canonicalParams=canonical,
            **_persist({}, save_audio, Path(dest)/'original-shipped-replay', shipped))
        diagnostic['shippedDspMatches'] = canonical == candidate['params'] and np.array_equal(replay, shipped)
    row = {**candidate, 'wave': replay, 'calibrationCompatible': diagnostic['shippedDspMatches'],
        'renderSourceHash': backend['sourceHash'],
        'provenance': {**candidate['provenance'], 'renderBackend': deepcopy(backend)}}
    return row, diagnostic


GATE_SHA = '69d0a3306b452f17abaf0bdac6c2a632351db6d2b8d215e086b01a0c4585f892'
TARGETS_SHA = '673ac1409157479a6519d7f5cd0658334c786a1a7f85fb3a09874ea1d9ab21c6'


def validate_gate(path, bindings):
    _bind(bindings, path, GATE_SHA)
    gate = _read(path)
    if gate.get('complete') is not True or gate.get('gate', {}).get('passed') is not True:
        raise ValueError('Completed passing calibration gate required')
    if not gate.get('reports'):
        raise ValueError('Calibration gate has no bound reports')
    for report in gate['reports'].values():
        _bind(bindings, report['path'], report['sha256'])
        meta = _read(report['path'])['metadata']
        if meta.get('complete') is not True:
            raise ValueError('Calibration gate report is incomplete')
        for key in ('inputBindings', 'outputBindings', 'codeHashes'):
            for name, digest in meta.get(key, {}).items():
                _bind(bindings, name, digest)
    return gate


def validate_manifest(path, bindings):
    _bind(bindings, path, TARGETS_SHA)
    frozen = _read(path)
    sources = frozen['targets']
    if (frozen.get('frozenBeforeCalibrationEvaluation') is not True or
            tuple(s['name'] for s in sources) != TARGET_NAMES or
            len({s['sha256'] for s in sources}) != 5):
        raise ValueError('Fixed five-target manifest identities/order differ')
    for source in sources:
        _bind(bindings, source['path'], source['sha256'])
    return sources


def check_heard_candidate(row, card, old_gallery, folder):
    path = Path(old_gallery)/folder/card['file']
    if file_hash(path) != card['provenance']['auditionWavSha256']:
        raise ValueError('Historical candidate WAV differs')
    pcm_hash(path)
    actual, rate = sf.read(path, dtype='float32')
    if rate != 44100 or not np.array_equal(audition_pcm(row['wave']), actual):
        raise ValueError('Historical candidate audition PCM replay differs')


def cached_pool(old, wave, renderer, native, backend, dest, experts, old_gallery):
    """Replay the complete audited raw/refined pool, without rerunning search."""
    dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
    objective = MatchObjective(wave)
    raw, refined = [], []
    for role, rows, result in [('raw', old['diagnostics']['allRaw'], raw),
                               ('refined', old['diagnostics']['allRefined'], refined)]:
        for index, row in enumerate(rows):
            if row['provenance']['checkpointHash'] != experts[row['synth']][1]['checkpointHash']:
                raise ValueError('Cached candidate checkpoint differs')
            canonical, replay = renderer.render(row['synth'], row['params'], row['seed'])
            saved = _persist({}, save_audio, dest/f'cached-{role}-{index:02d}', replay)
            if canonical != row['params']:
                raise ValueError('Cached canonical controls differ')
            score = float(objective.score_batch([replay])[0])
            if not np.isfinite(score) or not np.isclose(score, row['score'], rtol=1e-9, atol=1e-9):
                raise ValueError('Cached actual-render score differs')
            result.append({**deepcopy(row), **saved, 'wave': replay, 'poolRole': role})
    chosen = min(raw+refined, key=lambda c:c['score'])
    heard = next(c for c in old['candidates'] if c['role'] == 'selected')
    if any(chosen[k] != heard[k] for k in ('synth', 'params', 'seed', 'score')):
        raise ValueError('Cached selected candidate differs')
    check_heard_candidate(chosen, heard, old_gallery, old['folder'])
    original = deepcopy(next(c for c in old['candidates'] if c['role'] == 'original'))
    if original['provenance']['checkpointSha256'] != ORIGINAL_CHECKPOINT_SHA:
        raise ValueError('Cached original checkpoint differs')
    original['wave'] = native.render(original['params'], seed=original['seed'])
    check_heard_candidate(original, original, old_gallery, old['folder'])
    original, original_diagnostic = verify_original(original, native, renderer, objective, dest, backend)
    original['poolRole'] = 'original-bfxr'
    diagnostic = dict(poolSource='cached-audited-temporal-v3', oldGalleryFolder=old['folder'],
        allRaw=_without_wave(raw), allRefined=_without_wave(refined),
        failures=deepcopy(old['diagnostics']['failures']), originalBackend=original_diagnostic,
        proposals=[], renderAttempts=[], refinementStatus={e:'cached' for e in ENGINES},
        refinementSeeds={r['synth']:r['provenance']['refinement']['seed'] for r in refined},
        refinementAttemptsByEngine={e:0 for e in ENGINES},
        cachedRefinementBudgetPerEngine=384,
        proposalAccounting={e:proposal_accounting(4, 4, sum(r['synth']==e for r in raw)) for e in ENGINES})
    return raw+refined+[original], diagnostic, original


class PoolRenderer(RecordingRenderer):
    """Keep failed raw-return PCM; refined search keeps the frozen guarded trace."""
    def __init__(self, renderer, dest):
        super().__init__(renderer)
        self.dest = Path(dest)

    def render(self, synth, params, seed):
        canonical, wave = super().render(synth, params, seed)
        if self.phase in ('proposals', 'raw-scoring'):
            attempt = self.attempts[-1]
            attempt.update(_persist(attempt, save_audio,
                                    self.dest/f'raw-call-{len(self.attempts)-1:03d}', wave))
        return canonical, wave


def fresh_pool(experts, wave, actual_renderer, native, original_model, backend, dest, index):
    dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
    objective, target = MatchObjective(wave), target_diagnostics(wave)
    renderer = PoolRenderer(actual_renderer, dest)
    diagnostic = dict(poolSource='fresh-frozen-temporal-v3', failures=[], renderAttempts=renderer.attempts,
                      refinementSeeds={}, refinementStatus={}, refinementAttemptsByEngine={})
    try:
        guessed = proposals(experts, wave, renderer, 4)
        diagnostic['proposals'] = guessed
        if (any(c['synth'] not in ENGINES for c in guessed) or
                any(sum(c['synth']==e for c in guessed) > 4 for e in ENGINES)):
            raise ValueError('Unknown engine or excess proposal budget')
        renderer.phase = 'raw-scoring'
        raw, errors = rendered_candidates(guessed, renderer, objective)
        errors.extend(dict(synth=c['synth'], params=c['params'], seed=c['seed'],
            error='Nonfinite proposal score', audioHash=audio_hash(c['wave']))
            for c in raw if not np.isfinite(c['score']))
        raw = [{**c, 'poolRole':'raw'} for c in raw if np.isfinite(c['score'])]
        diagnostic['failures'] = errors
        diagnostic['proposalAccounting'] = {e:proposal_accounting(4,
            sum(c['synth']==e for c in guessed), sum(c['synth']==e for c in raw)) for e in ENGINES}
        if not raw:
            raise ValueError('No audible frozen-v3 proposals')
        refined = []
        for engine_index, engine in enumerate(ENGINES):
            progress(str(index+1), 'refinement-'+engine)
            seed = 20261011+index*1009+engine_index*71
            diagnostic['refinementSeeds'][engine] = seed
            options = [c for c in raw if c['synth']==engine]
            if not options:
                diagnostic['refinementStatus'][engine] = 'skipped-no-audible-proposal'
                diagnostic['refinementAttemptsByEngine'][engine] = 0
                continue
            renderer.phase = 'refinement-'+engine
            row = refine_guarded(min(options, key=lambda c:c['score']), renderer, objective, target, 384, seed)
            refined.append({**row, 'poolRole':'refined'})
            count = sum(a['phase']==renderer.phase for a in renderer.attempts)
            diagnostic['refinementStatus'][engine] = 'completed'
            diagnostic['refinementAttemptsByEngine'][engine] = count
            if count != 384:
                raise ValueError('Actual refinement trial count differs')
        raw = [persist_candidate(c, dest/f'raw-{n:02d}') for n,c in enumerate(raw)]
        refined = [persist_candidate(c, dest/f'refined-{n:02d}') for n,c in enumerate(refined)]
        diagnostic.update(allRaw=_without_wave(raw), allRefined=_without_wave(refined))
        progress(str(index+1), 'original-bfxr-2000-budget')
        original = original_model.approximate(wave, objective, budget=2000, seed=20261011+index*1009)
        original, original_diagnostic = verify_original(original, native, actual_renderer, objective, dest, backend)
        original = persist_candidate({**original, 'poolRole':'original-bfxr'}, dest/'original')
        diagnostic['originalBackend'] = original_diagnostic
        _json_write(dest/'generation.json', _without_wave(diagnostic))
        return raw+refined+[original], diagnostic, original
    except BaseException as exc:
        diagnostic['failure'] = dict(type=type(exc).__name__, error=str(exc))
        _json_write(dest/'generation.json', _without_wave(diagnostic))
        raise


def _code_bindings():
    """Include original Bfxr inference code alongside frozen gallery helpers."""
    tools = Path(__file__).parents[1]
    bindings = _shared_code_bindings()
    bindings.update({str(path.relative_to(tools)): file_hash(path)
                     for path in sorted((tools/'invert').rglob('*.py'))})
    return bindings


def validate_inputs(targets, model, old_gallery, archives, checkpoint, gate, renderer):
    bindings = {}
    validate_gate(gate, bindings)
    sources = validate_manifest(targets, bindings)
    old_gallery, model = Path(old_gallery), Path(model)
    _bind(bindings, old_gallery/'results.json', OLD_REPORT_SHA)
    _bind(bindings, old_gallery/'index.html', OLD_HTML_SHA)
    _bind(bindings, OLD_AUDIT)
    old_audit = _read(OLD_AUDIT)
    if (old_audit.get('complete') is not True or old_audit['reportSha256'] != OLD_REPORT_SHA or
            old_audit['htmlSha256'] != OLD_HTML_SHA):
        raise ValueError('Historical listening audit differs')
    historical = _read(old_gallery/'results.json')
    old_rows = {r['source']['sha256']:r for r in historical['results']}
    _bind(bindings, checkpoint, ORIGINAL_CHECKPOINT_SHA)
    experts = load_experts(model)
    source_hash = renderer.inventory['sourceHash']
    if (tuple(experts) != ENGINES or historical['metadata'].get('complete') is not True or
            historical['metadata']['sourceHash'] != source_hash):
        raise ValueError('Frozen expert order or historical DSP differs')
    for name, (_, meta) in experts.items():
        expected = historical['metadata']['checkpointHashes'][name]
        if (meta['checkpointHash'] != expected or meta['sourceHash'] != source_hash or
                meta['spec'] != renderer.specs[name]):
            raise ValueError('Frozen v3 checkpoint/DSP/schema differs')
        _bind(bindings, model/name/'best.pt', expected)
        _bind(bindings, model/name/'training.json')
        parent_training = (model/name).resolve().parent/'training.json'
        if parent_training.is_file():
            _bind(bindings, parent_training)
        _dataset_bindings(bindings, meta['datasetPath'], meta['dataManifestHash'], meta['datasetFiles'])
    for name in ('assembly.json', 'training.json'):
        if (model/name).is_file():
            _bind(bindings, model/name)
    archives = sorted(map(Path, archives), key=lambda p:p.name)
    if (len(archives) != 2 or {p.name for p in archives} != {p.name for p in DEFAULT_ARCHIVES}
            or len({p.resolve() for p in archives}) != 2):
        raise ValueError('Both distinct frozen listening archives required')
    references, heard_sets = {}, {}
    for archive in archives:
        for path in sorted(archive.rglob('*')):
            if path.is_file():
                _bind(bindings, path)
        data = _read(archive/'manifest.json')
        candidates = {c['id']:c for c in data['candidates']}
        for target in data['targets']:
            digest = target['source']['sha256']
            references.setdefault(digest, []).append((archive, target['referenceAudio']))
            heard = (target.get('choice') or {}).get('auditionedCandidateIds', [])
            heard_sets.setdefault(digest, []).append({candidates[c]['audio']['pcmSha256'] for c in heard})
    history = listening_history(archives)
    observations = {s['sha256']:baseline_observations(history, s) for s in sources}
    charm = old_rows[sources[0]['sha256']]
    audit_charm = next(r for r in old_audit['targets'] if r['name'] == sources[0]['name'])
    if (charm['source']['path'] != sources[0]['path'] or charm['folder'] != '005' or
            len(charm['diagnostics']['allRaw']) != audit_charm['audibleRawCandidates'] or
            len(charm['diagnostics']['allRefined']) != 3 or
            charm['diagnostics']['failures'] != audit_charm['proposalFailures']):
        raise ValueError('Cached charm pool or failure accounting differs')
    _bind(bindings, old_gallery/charm['folder']/'target.wav')
    for c in charm['candidates']:
        _bind(bindings, old_gallery/charm['folder']/c['file'],
              audit_charm['candidates'][c['role']]['wavSha256'])
    code_hashes = _code_bindings()
    for name, digest in code_hashes.items():
        _bind(bindings, Path(__file__).parents[1]/name, digest)
    _bind(bindings, Path(__file__).parents[1]/'render/multisynth_worker.js')
    return dict(sources=sources, experts=experts, oldRows=old_rows, observations=observations,
        references=references, heardSets=heard_sets, referenceBindings=old_reference_bindings(old_gallery),
        inputBindings=bindings, codeHashes=code_hashes, sourceHash=source_hash,
        checkpointHashes={name:meta['checkpointHash'] for name, (_,meta) in experts.items()})


def progress(target, phase):
    print(json.dumps(dict(target=target, phase=phase)), flush=True)


def run(*, output, targets=DEFAULT_TARGETS, model=DEFAULT_MODEL, old_gallery=DEFAULT_OLD_GALLERY,
        archives=DEFAULT_ARCHIVES, checkpoint=DEFAULT_CHECKPOINT, gate=DEFAULT_GATE):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh output required; previous runs are immutable')
    torch.set_num_threads(1)
    with Renderer() as renderer, BfxrRenderer(jobs=1) as native:
        context = validate_inputs(targets, model, old_gallery, archives, checkpoint, gate, renderer)
        backend = backend_provenance(native)
        bindings = context['inputBindings']
        for path, digest in backend['files'].items():
            _bind(bindings, path, digest)
        metadata = dict(experiment='pitch-calibration-listening-v1', complete=False,
            galleryTitle='Pitch calibration · short comparisons',
            galleryIntro=['Choose the best recreation, a tie, or none.',
                'Optional notes: convincing, closeish, same genre, or still off.',
                'Pitch calibration is an inference experiment. A numerical result is not a human quality verdict.',
                'charm2 retains both earlier partial successes, which were not compared in the latest session.'],
            humanReviewRequired=True, targetCount=len(context['sources']), targetReports=[], skippedTargets=[],
            targetManifestPath=str(Path(targets).resolve()), targetManifestSha256=TARGETS_SHA,
            gateAuditPath=str(Path(gate).resolve()), gateAuditSha256=GATE_SHA,
            previousReportSha256=OLD_REPORT_SHA, previousPageSha256=OLD_HTML_SHA,
            sourceHash=context['sourceHash'], checkpointHashes=context['checkpointHashes'],
            modelDirectory=str(Path(model).resolve()), originalBfxrCheckpoint=str(Path(checkpoint).resolve()),
            originalBfxrCheckpointSha256=ORIGINAL_CHECKPOINT_SHA, originalBfxrBackend=backend,
            codeHashes=context['codeHashes'], inputBindings=bindings,
            policy=deepcopy(POLICY), policySha256=_hash_json(POLICY), guardPolicy=deepcopy(GUARD_POLICY),
            candidateBudgetPerEngine=4, proposalSeed=20261010, refinementBudgetPerEngine=384,
            originalBfxrDeclaredBudget=2000, maximumAdditionalRendersPerOriginal=3,
            refinementSeedPolicy='20261011 + fixed zero-based target index*1009 + frozen engine index*71',
            originalBfxrSeedPolicy='20261011 + fixed zero-based target index*1009',
            selection='Frozen select_candidates over all actual raw, refined and original Bfxr PCM; human labels only choose listening anchors.',
            scope='Curated development references; hybrid inference with extra DSP renders, not a new model or proof of likeness.',
            savingPolicy='All original and calibration return PCM is FLOAT; malformed return arrays are NPY. Refinement trials retain controls/hash/frozen guarded trace. Auditions use exactly one PCM16 transform.')
        output.mkdir(parents=True)
        _json_write(output/'manifest.json', metadata)
        records, outputs, original_model = [], {}, None
        try:
            for index, source in enumerate(context['sources']):
                progress(source['name'], 'reference')
                dest = output/f'{index+1:03d}'; dest.mkdir()
                old = context['oldRows'].get(source['sha256']) if source.get('previouslyRatedReference') else None
                wave = prepare_reference(source, dest/'target.wav', old, context['references'],
                    context['referenceBindings'], old_gallery)
                record = dict(folder=dest.name, source=source, complete=False, candidates=[],
                    referenceAudioSha256=file_hash(dest/'target.wav'),
                    referencePcmSha256=pcm_hash(dest/'target.wav'), referenceAudioHash=audio_hash(wave))
                _json_write(dest/'report.json', record)
                if old is not None:
                    progress(source['name'], 'cached-pool-replay')
                    pool, diagnostic, original = cached_pool(old, wave, renderer, native, backend,
                        dest/'pool', context['experts'], old_gallery)
                else:
                    if original_model is None:
                        original_model = OriginalBfxr(checkpoint, native)
                    progress(source['name'], 'fresh-proposals-and-refinement')
                    pool, diagnostic, original = fresh_pool(context['experts'], wave, renderer,
                        native, original_model, backend, dest/'pool', index)
                progress(source['name'], 'pitch-calibration')
                calibration = calibrate_pool(pool, wave, renderer, dest/'pitch')
                selection = calibration['selection']
                cards = make_cards(dest, selection, calibration['originals'][-1],
                    context['observations'].get(source['sha256'], []), context['sourceHash'])
                display = display_decision(cards, context['heardSets'].get(source['sha256'], []),
                                           source.get('previouslyRatedReference', False))
                record.update(complete=True, candidates=cards, display=display,
                    note='A preferred option may still be far off. Best, tie and none are all useful.',
                    diagnostics={**_without_wave(diagnostic), **_without_wave(calibration),
                        'target':target_diagnostics(wave), 'v5TargetPitch':descriptor_pitch(wave)})
                _json_write(dest/'report.json', record)
                metadata['targetReports'].append(dict(folder=dest.name,
                    reportFile=str((dest/'report.json').resolve()), reportFileSha256=file_hash(dest/'report.json')))
                if display['included']:
                    records.append(record)
                else:
                    metadata['skippedTargets'].append(dict(folder=dest.name, source=source['name'], **display))
                for path in sorted(dest.rglob('*')):
                    if path.is_file():
                        _bind(outputs, path)
                _json_write(output/'manifest.json', metadata)
            _check_bindings(bindings)
            _check_bindings(outputs)
            if context['codeHashes'] != _code_bindings() or _hash_json(POLICY) != metadata['policySha256']:
                raise ValueError('Gallery code or calibration policy changed')
            if backend_provenance(native) != backend:
                raise ValueError('Original Bfxr backend changed')
            with Renderer() as final_renderer:
                if final_renderer.inventory['sourceHash'] != metadata['sourceHash']:
                    raise ValueError('DSP changed during gallery creation')
            metadata.update(outputBindings=outputs, displayedTargetCount=len(records))
            progress('gallery', 'export')
            # The persisted manifest remains incomplete throughout export. First
            # verify the exporter can finish; then publish the final identities.
            export_coverage(output, records, metadata)
            _check_bindings(bindings)
            _check_bindings(outputs)
            metadata['complete'] = True
            result = export_coverage(output, records, metadata)
            _check_bindings(bindings)
            _check_bindings(outputs)
            _json_write(output/'manifest.json', metadata)
            _json_write(output/'export-audit.json', dict(complete=True,
                experimentId=result['experimentId'], reportSha256=file_hash(output/'results.json'),
                htmlSha256=file_hash(output/'index.html'), manifestSha256=file_hash(output/'manifest.json')))
            return result
        except BaseException as exc:
            metadata.update(complete=False, failure=dict(type=type(exc).__name__, error=str(exc)))
            _json_write(output/'manifest.json', metadata)
            if (output/'results.json').exists():
                _json_write(output/'results.json', dict(metadata=metadata, results=records))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    for name, default in [('targets', DEFAULT_TARGETS), ('model', DEFAULT_MODEL),
                          ('old-gallery', DEFAULT_OLD_GALLERY), ('checkpoint', DEFAULT_CHECKPOINT),
                          ('gate', DEFAULT_GATE)]:
        parser.add_argument('--'+name, type=Path, default=default)
    parser.add_argument('--archives', type=Path, nargs='+', default=DEFAULT_ARCHIVES)
    args = parser.parse_args()
    run(**vars(args))


if __name__ == '__main__':
    main()
