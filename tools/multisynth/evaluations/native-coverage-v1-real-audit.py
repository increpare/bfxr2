"""Audit real refinement and separately select against the fixed raw baseline."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_selection import POLICY, select_candidate, rejection_reasons
from neural_invert.data import file_hash, _json_write


def run():
    torch.set_num_threads(1)
    root=Path('tools/multisynth/runs/native-coverage-v1')
    source=root/'real-refined/results.json';raw_path=root/'real-proposals/results.json'
    refined=json.loads(source.read_text());raw=json.loads(raw_path.read_text())
    if not refined['complete'] or not raw['complete']:raise ValueError('Wait for terminal completed refinement')
    assert refined['rawReportSha256']==file_hash(raw_path)
    script=Path('tools/multisynth/evaluations/native-coverage-v1-real-refine.py')
    assert refined['scriptSha256']==file_hash(script)
    for p,h in refined['codeHashes'].items():assert file_hash(p)==h
    prior=Path('tools/multisynth/runs/pitch-calibration-listening-v1')
    heard=json.loads((prior/'results.json').read_text())['results']
    report=dict(complete=False,scriptSha256=file_hash(__file__),rawReportSha256=file_hash(raw_path),
        refinementReportSha256=file_hash(source),priorGalleryReportSha256=file_hash(prior/'results.json'),policy=POLICY,
        correction='The private refinement report applies select_candidate against refined control, so its embedded fixed-old-four POLICY baseline description does not describe that selection. Preserve that report as a seed comparison; the new selection here uses fixed raw control and retains every raw/refined candidate.',
        scope='Repeated rejected development references. Fixed baseline guards are not human likeness. Prior gallery distance comparison is not equal compute and may describe pre-audition float PCM.',rows=[])
    assert len(refined['rows'])==len(raw['rows'])==len(heard)==5
    files=0;replays=0;max_error=0.
    with Renderer() as renderer:
        for r,initial,history in zip(refined['rows'],raw['rows'],heard):
            assert r['source']==initial['source']==history['source']
            reference=prior/r['folder']/'target.wav'
            assert file_hash(reference)==r['referenceWavSha256']==initial['referenceWavSha256']
            target,rate=sf.read(reference,dtype='float32');assert rate==44100
            objective=MatchObjective(target);pool=[]
            for arm in ('control','expanded'):
                record=r['arms'][arm];settings=record['provenance']['refinement']
                assert settings['budget']==384
                assert settings['initialScore']==initial['arms'][arm]['selected']['score']
                assert settings['finalScore']==record['score']
                pool.extend(dict(c,origin=arm,stage='raw') for c in initial['arms'][arm]['candidates'])
                pool.append(dict(record,origin=arm,stage='refined'))
            assert r['arms']['control']['provenance']['refinement']['seed']==r['arms']['expanded']['provenance']['refinement']['seed']
            for c in pool:
                assert file_hash(c['waveFile'])==c['waveFileSha256']
                wave,rate=sf.read(c['waveFile'],dtype='float32')
                assert rate==44100 and audio_hash(wave)==c['audioHash'];files+=1
                params,replay=renderer.render(c['synth'],c['params'],c['seed'])
                assert params==c['params'] and np.array_equal(replay,wave)
                error=abs(float(objective.score_batch([replay])[0])-c['score']);assert error<1e-8
                max_error=max(max_error,error);replays+=1
            baseline=next(c for c in pool if c['stage']=='raw' and c['origin']=='control' and c['audioHash']==initial['arms']['control']['selected']['audioHash'])
            fixed=select_candidate(r['targetPitch'],baseline,pool)
            raw_guard_losses=rejection_reasons(r['targetPitch'],baseline,r['selected'])
            previous=min([c for c in history['candidates'] if c.get('score') is not None],key=lambda c:c['score'])
            report['rows'].append(dict(name=r['source']['name'],referenceWavSha256=file_hash(reference),
                baseline=baseline,fixedBaselineSelected=fixed,
                privateRefinementSelectedScore=r['selected']['score'],privateSelectionRawBaselineRegressions=raw_guard_losses,
                priorDisplayedBestScore=previous['score'],priorDisplayedBestSynth=previous['synth'],
                fixedSelectedBeatsPriorDisplayedDistance=fixed['score']<previous['score'],
                armRefinedScores={a:c['score'] for a,c in r['arms'].items()}))
    report.update(complete=True,verifiedFiles=files,dspReplays=replays,maxRescoreError=max_error)
    out=Path('tools/multisynth/evaluations/native-coverage-v1-real-audit.json')
    if out.exists():raise FileExistsError('Fresh audit required')
    _json_write(out,report)
    print(json.dumps(dict(verifiedFiles=files,dspReplays=replays,maxRescoreError=max_error,
        rows=[dict(name=r['name'],selected=r['fixedBaselineSelected']['score'],origin=r['fixedBaselineSelected']['origin'],
            prior=r['priorDisplayedBestScore'],rawBaselineRegressions=r['privateSelectionRawBaselineRegressions']) for r in report['rows']])),flush=True)


if __name__=='__main__':run()
