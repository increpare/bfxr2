"""Fixed-checkpoint actual-DSP audit of float versus audition-PCM inverse inputs.

All 122 existing development targets, four proposals per input, no search or
retraining. Score both pools against the same audition reference. This isolates
prediction sensitivity separately from the v5 pitch-diagnostic defect.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture import load
from neural_invert.coverage_mixture_eval import read_wave, write_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.temporal import predict_temporal

BASE = Path('tools/multisynth')
SOURCE = BASE/'runs/native-mixture-v1/evaluation/results.json'
MODEL = BASE/'runs/native-mixture-v1/models/mixture'
OUT = BASE/'runs/native-mixture-input-stability-v1'
RECEIPT = Path(__file__).with_suffix('.json')


def main():
    if OUT.exists() or RECEIPT.exists():
        raise FileExistsError('Fresh experiment output required')
    torch.set_num_threads(1)
    source = json.loads(SOURCE.read_text())
    assert source['complete'] and len(source['rows']) == 122
    model, meta = load(MODEL)
    assert meta['checkpointHash'] == source['checkpoints']['mixture']
    OUT.mkdir()
    report = dict(complete=False, scriptSha256=file_hash(__file__),
        sourceReportSha256=file_hash(SOURCE), checkpointSha256=meta['checkpointHash'],
        protocol='All 122 fixed development targets; four raw-input versus four PCM16-input proposals; identical fixed reference and audition scoring; no search or retraining.',
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/temporal.py'),
            Path('tools/neural_invert/features.py'), Path('tools/neural_invert/experiment.py'),
            *Path('tools/match').glob('*.py')]}, rows=[])
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash'] == meta['sourceHash']
        for index, row in enumerate(source['rows']):
            target = read_wave(row['target'])
            reference = audition_pcm(target)
            objective = MatchObjective(reference)
            folder = OUT/f'{index:03d}'
            folder.mkdir()
            proposals = predict_temporal(model, meta, reference, renderer, count=4)
            assert len(proposals) == 4 and len(row['pools']['mixture']) == 4
            pools = {'rawInput': [], 'pcm16Input': []}
            for arm, candidates in [('rawInput', row['pools']['mixture']), ('pcm16Input', proposals)]:
                for slot, candidate in enumerate(candidates):
                    if arm == 'rawInput':
                        wave = read_wave(candidate)
                        provenance = {k:candidate[k] for k in ('waveFile', 'waveFileSha256', 'audioHash')}
                    else:
                        params, wave = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
                        assert params == candidate['params']
                        provenance = write_wave(folder/f'pcm16-input-{slot}.wav', wave)
                    heard = audition_pcm(wave)
                    pools[arm].append(dict(synth=candidate['synth'], params=candidate['params'], seed=candidate['seed'],
                        provenance=candidate['provenance'], slot=slot, **provenance,
                        auditionHash=audio_hash(heard), score=float(objective.score_batch([heard])[0])))
            best = {arm:min(pool, key=lambda c:c['score']) for arm,pool in pools.items()}
            report['rows'].append(dict(target=row['target'], inputPcmHash=audio_hash(reference),
                inputExactlyUnchanged=bool(np.array_equal(target, reference)), pools=pools,
                bestSlot={arm:c['slot'] for arm,c in best.items()},
                scores={arm:c['score'] for arm,c in best.items()},
                selectedPatchExactlyUnchanged=best['rawInput']['params']==best['pcm16Input']['params']))
            print(json.dumps(dict(done=index+1, total=122, target=row['target']['id'],
                                  scores=report['rows'][-1]['scores'])), flush=True)
            if (index+1) % 10 == 0:
                _json_write(OUT/'results.json', report)
    groups = {}
    for row in report['rows']:
        key = row['target']['group']
        if row['target'].get('variant'):
            key += '/'+row['target']['variant']
        groups.setdefault(key, []).append(row)
    summaries = {}
    for group, rows in groups.items():
        a = np.array([r['scores']['rawInput'] for r in rows])
        b = np.array([r['scores']['pcm16Input'] for r in rows])
        summaries[group] = dict(targets=len(rows), meanRawInputScore=float(a.mean()),
            meanPcm16InputScore=float(b.mean()), meanAbsoluteScoreChange=float(np.mean(np.abs(b-a))),
            pcmInputWins=int(np.sum(b<a-1e-7)), pcmInputLosses=int(np.sum(b>a+1e-7)),
            maxScoreIncrease=float(np.max(b-a)), maxScoreDecrease=float(np.min(b-a)))
    report.update(complete=True, summary=summaries)
    _json_write(OUT/'results.json', report)
    receipt = dict(complete=True, scriptSha256=file_hash(__file__), reportSha256=file_hash(OUT/'results.json'),
        sourceReportSha256=report['sourceReportSha256'], checkpointSha256=report['checkpointSha256'],
        targets=len(report['rows']), newActualRenders=4*len(report['rows']), summary=summaries,
        interpretation='Input-format sensitivity of the same frozen model, with matching distance as a diagnostic only. Not a training improvement, perception test, or independent generalization test.')
    _json_write(RECEIPT, receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
