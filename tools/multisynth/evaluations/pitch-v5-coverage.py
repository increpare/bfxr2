"""Count upper-register descriptor evidence; this is not independent pitch ground truth."""
import json
from pathlib import Path
import numpy as np
from neural_invert.data import file_hash


def main():
    root=Path('tools/multisynth/runs/pitch-v5/data')
    manifest=json.loads((root/'manifest.json').read_text()); assert manifest['complete']
    reports={}
    for engine in ('Bfxr','Transfxr','Pluckr'):
        assert file_hash(root/(engine+'.npz')) == manifest['files'][engine]['npzSha256']
        assert file_hash(root/(engine+'.json')) == manifest['files'][engine]['metadataSha256']
        meta=json.loads((root/(engine+'.json')).read_text())
        with np.load(root/(engine+'.npz')) as data:
            x=data['features'].astype(np.float32)
        rows=[]
        for i,f in enumerate(x):
            active=f[3840:3888]>.05; voiced=active&(f[3936:3984]>=.6)
            hz=55*np.exp2(7*f[3888:3936][voiced])
            fraction=float(voiced.sum()/max(1,active.sum()))
            median=float(np.median(hz)) if len(hz) else 0.
            spread=float(12*np.log2(np.percentile(hz,90)/np.percentile(hz,10))) if len(hz) else None
            rows.append({'i':i,'structured':bool(meta['rows'][i].get('structured',False)),
                'upper':median>2000 and fraction>=.8,'stableUpper':median>2000 and fraction>=.8 and spread<=2})
        reports[engine]={}
        for split in ('train','val'):
            ids=set(manifest['splits'][engine][split]);counts={}
            for label,structured in (('native',False),('structured',True)):
                selected=[r for r in rows if r['i'] in ids and r['structured']==structured]
                counts[label]={'rows':len(selected),'upper':sum(r['upper'] for r in selected),'stableUpper':sum(r['stableUpper'] for r in selected),
                    'stableUpperIndices':[r['i'] for r in selected if r['stableUpper']]}
            reports[engine][split]=counts
    result={'complete':True,'diagnosticStatus':'Corrected v5 tracker; counts remain estimator outputs, not independently verified fundamentals or human quality.','scriptSha256':file_hash(__file__),'manifestSha256':file_hash(root/'manifest.json'),
        'rule':'Diagnostic heuristic on packed corrected features: median voiced pitch >2 kHz, >=80% of active frames voiced; stableUpper additionally requires 10th–90th percentile pitch span <=2 semitones. Not an auditory adequacy test. Actual pitches may reflect tracker errors.',
        'reports':reports}
    Path('tools/multisynth/evaluations/pitch-v5-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    for engine,r in reports.items():
        print(engine,{split:{label:{k:v for k,v in c.items() if k!='stableUpperIndices'} for label,c in counts.items()} for split,counts in r.items()})


if __name__=='__main__':
    main()
