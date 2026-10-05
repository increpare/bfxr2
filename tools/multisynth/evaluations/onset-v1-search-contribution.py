"""Re-score original-network raw proposals and retained staged-search outputs."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash

torch.set_num_threads(1)
root=Path('tools/multisynth')
raw_path=root/'runs/onset-v1/original-raw/results.json'
raw=json.loads(raw_path.read_text())
assert raw['complete']
by_id={r['id']:r for r in raw['rows']}
results=[]
for engine in ('Bfxr','Transfxr'):
    history=root/'runs/temporal-v3/paired-shards'/f'{engine}.json'
    for row in json.loads(history.read_text())['results']:
        old=row['arms']['v1']['candidates']['original']; new=by_id[row['id']]
        assert new['audioHash']==row['audioHash']
        assert old['provenance']['checkpointSha256']==raw['checkpointSha256']
        assert file_hash(row['waveFile'])==row['waveFileSha256']
        assert file_hash(old['waveFile'])==old['waveFileSha256']
        reference,rate=sf.read(row['waveFile'],dtype='float32')
        refined,r2=sf.read(old['waveFile'],dtype='float32')
        assert rate==r2==44100 and audio_hash(reference)==row['audioHash'] and audio_hash(refined)==old['audioHash']
        candidate=new['selected']
        assert candidate is not None and file_hash(candidate['waveFile'])==candidate['waveFileSha256']
        baseline,r3=sf.read(candidate['waveFile'],dtype='float32')
        assert r3==44100 and audio_hash(baseline)==candidate['audioHash']
        objective=MatchObjective(reference)
        raw_score,refined_score=map(float,objective.score_batch([baseline,refined]))
        assert abs(raw_score-candidate['score'])<1e-5 and abs(refined_score-old['score'])<1e-5
        results.append({'id':row['id'],'engine':engine,'family':row['family'],'referencePcmSha256':row['audioHash'],
                        'rawScore':raw_score,'refinedScore':refined_score,
                        'rawPcmSha256':candidate['audioHash'],'refinedPcmSha256':old['audioHash'],
                        'declaredSearchBudget':old['provenance']['budget'],'actualSearchEvaluations':old['provenance']['evaluations']})
summary={'targets':len(results),'rawMean':float(np.mean([r['rawScore'] for r in results])),
         'refinedMean':float(np.mean([r['refinedScore'] for r in results])),
         'refinedLower':sum(r['refinedScore']<r['rawScore'] for r in results)}
result={'scriptSha256':file_hash(__file__),'rawReportSha256':file_hash(raw_path),'rows':results,'summary':summary,
        'limitations':['Existing synthetic development probes, not human likeness judgments.',
                       'Historical staged optimizer starts from three neural guesses and also uses other search stages; current raw comparator gets four guesses.',
                       'This does not isolate neural initialization versus other optimizer initializations, nor establish that a lower objective sounds closer.',
                       'No inference that these synthetic results explain every real-reference human failure.']}
path=root/'evaluations/onset-v1-search-contribution.json'
assert not path.exists()
path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(summary))
