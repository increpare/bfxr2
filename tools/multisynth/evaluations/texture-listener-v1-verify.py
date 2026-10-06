"""Recompute grouped predictions and training-only scaling from saved evidence."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from multisynth.preference import reference_weights,score_summary,PreferenceMetric
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/texture-listener-v1'
OUTPUT=BASE/'evaluations/texture-listener-v1-verification.json'


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve verification receipt')
    spec=importlib.util.spec_from_file_location('texture_experiment',BASE/'evaluations/texture-listener-v1.py')
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    protocol=json.loads((ROOT/'protocol.json').read_text());experiment.verify(protocol)
    result=json.loads((ROOT/'evaluation.json').read_text());data=json.loads((ROOT/'data.json').read_text())
    assert data['protocolSha256']==result['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert result['dataJsonSha256']==file_hash(ROOT/'data.json') and data['dataSha256']==result['dataSha256']==file_hash(ROOT/'data.npz')
    with np.load(ROOT/'data.npz',allow_pickle=False) as z:x,y,refs,groups=(z[n] for n in ('x','y','references','groups'))
    assert x.shape==(219,27) and len(set(refs))==72 and len(set(groups))==44
    scores={(o['reference'],o['candidate']):np.array(o['values']) for o in data['extraScores']}
    for i,o in enumerate(data['observations']):
        ref=o['referencePcmSha256'];assert ref==refs[i] and groups[i]==protocol['groups'][ref]
        np.testing.assert_array_equal(x[i,:20],o['componentDifference'])
        np.testing.assert_array_equal(x[i,20:],scores[ref,o['candidatePcmSha256A']]-scores[ref,o['candidatePcmSha256B']])
        assert np.sign(y[i])==o['preferenceSign']
    assignments=np.zeros(len(y),int);pred={n:np.zeros(len(y)) for n in ('texture-heldout','base21-heldout')}
    for fold in result['folds']:
        tr=np.isin(groups,fold['trainGroups']);te=np.isin(groups,fold['testGroups'])
        assert not (tr&te).any() and (tr|te).all() and not set(refs[tr])&set(refs[te])
        assert sorted(set(refs[tr]))==fold['trainReferences'] and sorted(set(refs[te]))==fold['testReferences']
        assignments+=te
        for name,m in fold['models'].items():
            w=np.array(m['weights']);s=np.array(m['scales']);n=len(w)
            assert (w>=0).all() and abs(w.sum()-1)<1e-12
            expected=np.maximum(np.sqrt(reference_weights(refs[tr])@(x[tr,:n]**2)),.01)
            np.testing.assert_allclose(s,expected,rtol=1e-12,atol=1e-12)
            pred[name][te]=x[te,:n]@(w/s)
            assert score_summary(pred[name][te],y[te],refs[te])==m['scores']
    assert (assignments==1).all()
    old=PreferenceMetric.load(experiment.OLD)
    pred['old-preference-historical']=x[:,:20]@(old.weights/old.scales);pred['soft-periodicity']=x[:,20]
    for name,values in pred.items():
        assert score_summary(values,y,refs)==result['scores'][name]
        np.testing.assert_allclose(values,[o['differences'][name] for o in result['observations']],rtol=1e-12,atol=1e-12)
    acc={n:s['referenceBalancedAccuracy'] for n,s in result['scores'].items()}
    gate=bool(acc['texture-heldout']>=acc['base21-heldout']+.03 and acc['texture-heldout']>=max(acc['old-preference-historical'],acc['soft-periodicity']))
    assert gate==result['gatePassed']==False and not (ROOT/'metric.json').exists()
    receipt=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),evaluationSha256=file_hash(ROOT/'evaluation.json'),
        verifierSha256=file_hash(__file__),externalPairs=len(y),references=len(set(refs)),groups=len(set(groups)),folds=len(result['folds']),
        gatePassed=False,fullDataModelSaved=False,verified=['one held-out prediction per pair','reference/group separation',
            'training-only component scales','pair component reconstruction','prediction scores','fixed gate failure'],
        scope='Numerical experiment integrity only; no human quality claim.')
    _json_write(OUTPUT,receipt);print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
