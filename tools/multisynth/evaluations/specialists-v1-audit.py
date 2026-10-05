"""Recompute validation on CPU and replay every selected specialist evaluation patch."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from multisynth.coverage import verify_archived_audio
from neural_invert.benchmark import audio_hash
from neural_invert.acoustic import acoustic_loss
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.predict import load_model
from neural_invert.schema import ControlSchema
from neural_invert.train import _load_dataset

ROOT = Path('tools/multisynth/runs/specialists-v1')
OUTPUT = Path(__file__).with_suffix('.json')


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve original audit')
    torch.set_num_threads(1)
    receipt = json.loads((ROOT/'training-receipt.json').read_text())
    report = json.loads((ROOT/'evaluation/results.json').read_text())
    targets = json.loads((ROOT/'targets.json').read_text())
    prior_path = Path('tools/multisynth/runs/native-mixture-input-stability-v1/results.json')
    prior = json.loads(prior_path.read_text())
    prior_rows = {r['target']['id']:r for r in prior['rows']}
    frozen_evaluation = json.loads((ROOT/'evaluation/targets.json').read_text())
    assert frozen_evaluation['priorSha256']==file_hash(prior_path)
    book_archive = Path('tools/multisynth/listening_data/2026-10-04-temporal-v3-quick-01')
    assert frozen_evaluation['bookManifestSha256']==file_hash(book_archive/'manifest.json')
    book_manifest = json.loads((book_archive/'manifest.json').read_text())
    book_target = next(t for t in book_manifest['targets'] if t['source']['name']=='card/bookClose.ogg')
    verify_archived_audio(book_archive,book_target['referenceAudio'])
    book_wave, book_rate = sf.read(book_archive/book_target['referenceAudio']['file'],dtype='float32')
    assert book_rate==44100
    assert report['complete'] and receipt['complete'] and len(report['rows'])==155
    assert report['trainingReceiptSha256']==file_hash(ROOT/'training-receipt.json')
    assert receipt['targetsSha256']==file_hash(ROOT/'targets.json')
    validation = {}
    shared_data = Path('tools/multisynth/runs/neural-v2/data')
    _, shared_meta = load_model('tools/multisynth/runs/neural-v2/acoustic-model')
    assert file_hash(shared_data/'manifest.json')==shared_meta['dataManifestHash']
    shared_manifest = json.loads((shared_data/'manifest.json').read_text())
    shared_counts = {}
    for name in ('Boomr','Footsteppr'):
        assert file_hash(shared_data/(name+'.json'))==shared_manifest['files'][name]['metadataSha256']
        meta = json.loads((shared_data/(name+'.json')).read_text())
        schema = ControlSchema(meta['spec'])
        def controls(params):
            unit, cat = schema.encode(params)
            return (tuple(unit.tolist()),tuple(cat.tolist()))
        old_controls = {controls(r['params']) for r in meta['rows']}
        for target in targets['rows']:
            if target['sourceSynth']==name:
                assert controls(target['sourceParams']) not in old_controls
        shared_counts[name] = len(meta['rows'])
    for name, binding in receipt['datasets'].items():
        data = Path(binding['path'])
        assert file_hash(data/'manifest.json')==binding['manifestSha256']
        manifest, specs, shards, mean, std = _load_dataset(data)
        model, metadata = load_model(ROOT/'models'/name)
        assert metadata['dataManifestHash']==binding['manifestSha256']
        assert metadata['checkpointHash']==receipt['models'][name]['checkpointSha256']
        assert metadata['normalization']==dict(mean=mean.tolist(),std=std.tolist())
        meta = json.loads((data/(name+'.json')).read_text())
        for target in targets['rows']:
            if target['sourceSynth']==name:
                assert target['sourceRow'] in meta['test']
                assert target['sourceRow'] not in meta['train']+meta['val']
        shard = shards[name]
        total = 0.
        with torch.no_grad():
            for ids in shard['val'].split(128):
                x = (shard['features'][ids]-torch.tensor(mean))/torch.tensor(std)
                x[:, -2] = 0
                labels = {k:shard[k][ids] for k in ('continuous','categorical','generator')}
                total += float(acoustic_loss(model(x,name),labels,specs[name]))*len(ids)
        cpu = total/len(shard['val'])
        training = json.loads((ROOT/'models'/name/'training.json').read_text())
        delta = abs(cpu-training['bestValidationLoss'])
        assert delta<1e-5
        validation[name] = dict(cpuValidation=cpu,recordedValidation=training['bestValidationLoss'],absoluteError=delta,
            trainRows=len(meta['train']),validationRows=len(meta['val']),testRows=len(meta['test']),
            selectedEpoch=metadata['checkpointEpoch'],checkpointSha256=metadata['checkpointHash'])
    file_checks = replays = 0
    max_score_error = 0.
    with Renderer() as renderer:
        for row in report['rows']:
            reference = read_wave(row['target'])
            # A second peak normalization can change PCM whose highest positive
            # sample floored to 0.499969. Verify the original single transform,
            # rather than assuming normalization is idempotent after quantization.
            target = row['target']
            if target['id'] in prior_rows:
                expected = audition_pcm(read_wave(prior_rows[target['id']]['target']))
            elif target['group']=='real-repeated-book':
                expected = book_wave
            else:
                params, raw = renderer.render(target['sourceSynth'],target['sourceParams'],target['sourceSeed'])
                assert params==target['sourceParams'] and audio_hash(raw)==target['sourceAudioHash']
                expected = audition_pcm(raw)
            assert np.array_equal(reference,expected)
            file_checks += 1
            objective = MatchObjective(reference)
            for engine, pool in row['pools'].items():
                assert len(pool)==4
                for c in pool:
                    wave = read_wave(c)
                    score = float(objective.score_batch([audition_pcm(wave)])[0])
                    error = abs(score-c['score'])
                    assert error<1e-7
                    max_score_error = max(max_score_error,error)
                    file_checks += 1
                selected = row['selected'][engine]
                assert selected==min(pool,key=lambda c:c['score'])
                params, replay = renderer.render(selected['synth'],selected['params'],selected['seed'])
                assert params==selected['params'] and np.array_equal(replay,read_wave(selected))
                replays += 1
            assert row['winner']==min(row['selected'].values(),key=lambda c:c['score'])
    result = dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(ROOT/'evaluation/results.json'),
        trainingReceiptSha256=file_hash(ROOT/'training-receipt.json'),validation=validation,
        targets=155,filePcmChecks=file_checks,selectedDspReplays=replays,maxRescoreError=max_score_error,
        oldSharedDatasetSha256=file_hash(shared_data/'manifest.json'),oldSharedExamples=shared_counts,
        nativeTestControlsAlsoAbsentFromOldSharedData=True,
        scope='New native test groups excluded from optimization and checkpoint selection. CPU validation and all selected actual DSP replays verified; no human likeness inferred.')
    _json_write(OUTPUT,result)
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
