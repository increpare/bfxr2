"""Freeze and verify the short controlled-edit listening questionnaire."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from match.objective import MatchObjective
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth');OUT=BASE/'runs/cue-calibration-v1-listening'

def main():
    if (OUT/'index.html').exists():raise FileExistsError('Preserve published gallery')
    torch.set_num_threads(1)
    generation=json.loads((OUT/'generation.json').read_text());records=generation['records']
    protocol=generation['protocol'];assert protocol['scriptSha256']==file_hash(BASE/'evaluations/cue-calibration-v1-generate.py')
    metric=PreferenceMetric.load(BASE/'models/preference-neural-v2.json');checks=[]
    for record,row in zip(records,protocol['rows']):
        root=Path(row['archive']);assert file_hash(root/'manifest.json')==row['manifestSha256']
        archived,rate=sf.read(root/row['reference']['file'],dtype='int16')
        x,rate=sf.read(OUT/record['folder']/'target.wav',dtype='int16')
        assert rate==44100 and np.array_equal(archived,x)
        ref=x.astype(np.float32)/32768;objective=MatchObjective(ref);desc=describe(ref)
        scores=[]
        for c in record['candidates']:
            path=OUT/record['folder']/c['file'];assert file_hash(path)==c['provenance']['auditionWavSha256']
            wave,sr=sf.read(path,dtype='float32');assert sr==44100 and np.isfinite(wave).all() and np.max(np.abs(wave))<=.8001
            matching=float(objective.score_batch([wave])[0]);pref=float(metric.distances(desc,describe(wave))[0])
            c['provenance'].update(auditionMatchObjective=matching,preferenceNeuralV2=pref)
            scores.append(dict(transform=c['params'],matching=matching,preference=pref))
        checks.append(dict(source=record['source']['name'],options=scores))
    metadata=dict(experiment='cue-calibration-v1-listening',complete=True,targetCount=5,
        galleryTitle='What makes these sounds feel different?',
        galleryIntro=['These are deliberately edited originals, not new synth recreations.',
            'Five short A/B comparisons. Pick the version that stays closest, then say how close it is.',
            'This helps test which pitch, timing, attack and texture errors matter. Edits remain anonymous during quick listening.'],
        metricHashes={'preferenceNeuralV2':file_hash(BASE/'models/preference-neural-v2.json')},
        scoreCodeHashes={str(p):file_hash(p) for p in [Path('tools/match/objective.py'),BASE/'features.py',BASE/'preference.py']},
        humanReviewRequired=True,purpose='local-perceptual-loss-calibration-not-reproduction',
        protocolSha256=file_hash(BASE/'evaluations/cue-calibration-v1-protocol.json'),
        generationSha256=file_hash(OUT/'generation.json'),scriptSha256=file_hash(__file__),
        selectionPolicy='Five predeclared contrasts, no metric-based trial removal or strength tuning',
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()})
    model=export_coverage(OUT,records,metadata)
    page=(OUT/'index.html').read_text()
    needle='<p class="quick-help">';assert page.count(needle)==1
    page=page.replace(needle,'<p class="quick-help"><b>These are edited originals, not synth recreations.</b> ')
    (OUT/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],checks=checks,
        referenceCopiesExact=True,repeatRenderVerified=True,protocolSha256=metadata['protocolSha256'],
        metricHashes=metadata['metricHashes'],scoreCodeHashes=metadata['scoreCodeHashes'],
        scriptSha256=file_hash(__file__),resultsSha256=file_hash(OUT/'results.json'),
        files={str(p.relative_to(OUT)):file_hash(p) for p in sorted(OUT.glob('*/*.wav'))},
        htmlSha256=file_hash(OUT/'index.html'))
    _json_write(BASE/'evaluations/cue-calibration-v1-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],checks=checks)),flush=True)

if __name__=='__main__':main()
