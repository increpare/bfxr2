"""Freeze a synthetic-only specialist protocol, reserve native tests, then fit."""
import argparse
import json
from pathlib import Path
import shutil
import numpy as np
import soundfile as sf
from match.audio import prepare_target
from multisynth.cli import AUDIO_SUFFIXES, source_info
from multisynth.coverage import verify_archived_audio
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, verify_dataset_files, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.schema import ControlSchema
from neural_invert.train import train_model

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/squishr-v1'
PROTOCOL = BASE/'evaluations/squishr-v1-protocol.json'
ARCHIVE = BASE/'listening_data/2026-10-05-soft-periodicity-quick-01'
CORPUS = Path('/Users/stephenlavelle/Documents/bfxr2/tools/targets_non_bfxr_big/tags')
SHARED = BASE/'runs/neural-v2/acoustic-model/best.pt'


def freeze():
    if PROTOCOL.exists():
        raise FileExistsError('Preserve frozen protocol')
    archives, prior_files, prior_pcm = {}, set(), set()
    for path in sorted((BASE/'listening_data').glob('*/manifest.json')):
        archives[str(path)] = file_hash(path)
        manifest = json.loads(path.read_text())
        for target in manifest['targets']:
            prior_files.add(target['source'].get('sha256'))
            verify_archived_audio(path.parent, target['referenceAudio'])
            wave, sr = sf.read(path.parent/target['referenceAudio']['file'], dtype='float32')
            assert sr == 44100
            prior_pcm.add(audio_hash(wave))
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    anchor = next(t for t in manifest['targets'] if t['source']['name']=='footstep/footstep_wood_000.ogg')
    assert anchor['choice']['adequacy']['level']=='very-close'
    winner_id = anchor['choice']['preferredCandidateIds'][0]
    winner = next(c for c in manifest['candidates'] if c['id']==winner_id)
    verify_archived_audio(ARCHIVE, winner['audio'])
    wave, _ = sf.read(ARCHIVE/anchor['referenceAudio']['file'], dtype='float32')
    tagged = [dict(id='tagged-anchor', group='tagged-repeated', source=anchor['source'],
        referenceArchive=str(ARCHIVE), referenceAudio=anchor['referenceAudio'],
        auditionHash=audio_hash(wave), retainedCandidate=winner,
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'))]
    rejected = []
    # Fixed tag strata and stable path ordering, chosen without inference scores.
    # The slime tag contains only one already-judged file, so use the distinct
    # step tag instead. This choice precedes all model output inspection.
    for tag in ('footstep', 'hit', 'step', 'clothes'):
        for path in sorted(p for p in (CORPUS/tag).rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES):
            reason = None
            info = sf.info(path)
            if not .025 <= info.duration <= 1.8:
                reason = 'duration'
            elif file_hash(path) in prior_files:
                reason = 'previously-judged-file'
            else:
                wave = audition_pcm(prepare_target(path))
                if not len(wave) or np.max(np.abs(wave))<1e-6:
                    reason = 'silence'
                elif audio_hash(wave) in prior_pcm:
                    reason = 'previously-judged-or-selected-pcm'
            if reason:
                rejected.append(dict(name=str(path.relative_to(CORPUS)), reason=reason))
                continue
            tagged.append(dict(id='tagged-'+tag, group='tagged-new', source=source_info(path,CORPUS),
                tag=tag, sourceSeconds=info.duration, auditionHash=audio_hash(wave)))
            prior_pcm.add(audio_hash(wave))
            break
        else:
            raise ValueError('No eligible unjudged reference in '+tag)
    code = [__file__, 'tools/neural_invert/data.py', 'tools/neural_invert/train.py',
        'tools/neural_invert/predict.py', 'tools/neural_invert/schema.py', 'tools/neural_invert/evaluate.py',
        'tools/multisynth/soft_periodicity.py', 'tools/multisynth/features.py']
    protocol = dict(schemaVersion=1, synth='Squishr', tagged=tagged, rejected=rejected,
        archives=archives, sharedCheckpoint=str(SHARED), sharedCheckpointSha256=file_hash(SHARED),
        codeHashes={p:file_hash(p) for p in code},
        designSha256=file_hash('docs/superpowers/plans/2026-10-05-squishr-specialist.md'),
        data=dict(rows=8192, seed=20261127, sampler='existing 50% native / 30% sparse / 20% broad'),
        training=dict(epochs=60, hidden=256, batchSize=128, learningRate=.001, seed=20261128,
            device='cpu', threads=1, headMode='acoustic', lossMode='acoustic'),
        evaluation=dict(nativeSelectionSeed=20261129, nativeCount=32, nativeListeningCount=5,
            proposalsPerArm=4, refinementBudgetPerArm=128, searchSeed=20261130,
            selector='opt-in SoftPeriodicityObjective; legacy distance also reported',
            listening='All five tagged references, then first five seeded native controls; old/new refined options, retain exact approved anchor; deduplicate audio'),
        scope='Dedicated Squishr head comparison, not full ensemble benchmark. Synthetic-only training; real sources are transfer tests for the new expert. Native exact controls held out; preset families overlap. No human winners used for fitting.')
    _json_write(PROTOCOL, protocol)
    print(json.dumps(dict(frozen=[r['source']['name'] for r in tagged], protocolSha256=file_hash(PROTOCOL))), flush=True)


def train():
    protocol = json.loads(PROTOCOL.read_text())
    for path, checksum in protocol['codeHashes'].items():
        assert file_hash(path)==checksum, path
    data, fit, model = ROOT/'data', ROOT/'fit-data', ROOT/'model'
    if fit.exists() or model.exists() or (ROOT/'targets.json').exists():
        raise FileExistsError('Preserve training attempt')
    manifest = json.loads((data/'manifest.json').read_text())
    assert manifest['complete'] and manifest['engines']==['Squishr']
    verify_dataset_files(data,manifest)
    meta = json.loads((data/'Squishr.json').read_text())
    assert len(meta['rows'])==protocol['data']['rows']
    schema = ControlSchema(meta['spec'])
    def controls(row):
        unit, cat = schema.encode(row['params'])
        return tuple(unit.tolist()), tuple(cat.tolist())
    train_controls = {controls(meta['rows'][i]) for i in meta['train']}
    assert not train_controls & {controls(meta['rows'][i]) for i in meta['val']}
    # Avoid exact old training/validation controls too, including seed aliases.
    old_path = BASE/'runs/neural-v2/data-certified-v2/Squishr.json'
    old = json.loads(old_path.read_text())
    old_controls = {controls(r) for r in old['rows']}
    rows, seen = [], set()
    for idx in np.random.default_rng(protocol['evaluation']['nativeSelectionSeed']).permutation(meta['val']):
        row = meta['rows'][int(idx)]
        key = controls(row)
        if key in seen or key in old_controls:
            continue
        seen.add(key)
        rows.append(dict(id=f'Squishr-{idx:05d}', group='native-test', sourceSynth='Squishr',
            sourceParams=row['params'], sourceSeed=row['seed'], sourceRow=int(idx),
            parameterHash=row['parameterHash'], sourceAudioHash=row['audioHash']))
        if len(rows)==protocol['evaluation']['nativeCount']:
            break
    assert len(rows)==32
    test = [i for i in meta['val'] if controls(meta['rows'][i]) in seen]
    validation = [i for i in meta['val'] if controls(meta['rows'][i]) not in seen]
    assert len(test)>=32 and len(validation)>100
    fit.mkdir()
    shutil.copyfile(data/'Squishr.npz',fit/'Squishr.npz')
    fitted = {**meta, 'val':validation, 'test':test, 'originalMetadataSha256':file_hash(data/'Squishr.json'),
        'heldoutPolicy':'Exact encoded controls ignoring seeds excluded from training and checkpoint selection.',
        'splitScriptSha256':file_hash(__file__)}
    _json_write(fit/'Squishr.json',fitted)
    fitted_manifest = {**manifest, 'originalManifestSha256':file_hash(data/'manifest.json'),
        'splits':{'Squishr':dict(train=meta['train'],val=validation,test=test)},
        'files':{'Squishr':dict(npzSha256=file_hash(fit/'Squishr.npz'),metadataSha256=file_hash(fit/'Squishr.json'))}}
    _json_write(fit/'manifest.json',fitted_manifest)
    verify_dataset_files(fit,fitted_manifest)
    targets = dict(native=rows, tagged=protocol['tagged'], listeningIds=[r['id'] for r in protocol['tagged']+rows[:5]],
        protocolSha256=file_hash(PROTOCOL), fitManifestSha256=file_hash(fit/'manifest.json'),
        oldDatasetMetadataSha256=file_hash(old_path), scriptSha256=file_hash(__file__),
        splitCounts=dict(train=len(meta['train']),val=len(validation),test=len(test)))
    _json_write(ROOT/'targets.json',targets)
    _json_write(BASE/'evaluations/squishr-v1-targets.json',targets)
    p = protocol['training']
    train_model(fit,model,epochs=p['epochs'],device=p['device'],hidden=p['hidden'],batch_size=p['batchSize'],
        seed=p['seed'],threads=p['threads'],learning_rate=p['learningRate'],head_mode=p['headMode'],loss_mode=p['lossMode'])
    receipt = dict(complete=True,protocolSha256=file_hash(PROTOCOL),targetsSha256=file_hash(ROOT/'targets.json'),
        fitManifestSha256=file_hash(fit/'manifest.json'),checkpointSha256=file_hash(model/'best.pt'),
        trainingSha256=file_hash(model/'training.json'),scriptSha256=file_hash(__file__))
    _json_write(ROOT/'training-receipt.json',receipt)
    _json_write(BASE/'evaluations/squishr-v1-training-receipt.json',receipt)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage',choices=['freeze','train'])
    args = parser.parse_args()
    {'freeze':freeze,'train':train}[args.stage]()
