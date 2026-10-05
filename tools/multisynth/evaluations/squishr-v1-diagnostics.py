"""Describe parameter recovery separately from actual-audio metric selection.

Ground-truth controls are used only here, after predictions and selection have
finished. They never choose displayed candidates or supply a quality label.
"""
import json
from pathlib import Path
import numpy as np
from neural_invert.data import file_hash, _json_write
from neural_invert.schema import ControlSchema

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/squishr-v1'


def main():
    report = json.loads((ROOT/'evaluation/results.json').read_text())
    assert report['complete']
    meta = json.loads((ROOT/'fit-data/Squishr.json').read_text())
    schema = ControlSchema(meta['spec'])
    rows = [r for r in report['rows'] if r['target']['group']=='native-test']
    assert len(rows)==32 and len(schema.categorical)==1
    assert schema.categorical[0]['name']=='texture'
    summary = {}
    for arm in ('shared','specialist'):
        errors, top1, covered, selected, base_pitch, duration_ratio = [], [], [], [], [], []
        for row in rows:
            truth, categories = schema.encode(row['target']['sourceParams'])
            pool = row['arms'][arm]['raw']
            first = min(pool,key=lambda c:c['provenance']['proposalRank'])
            assert first['provenance']['proposalRank']==0, 'Cannot label a surviving alternative as model top-1'
            unit, cat = schema.encode(first['params'])
            for c in pool:
                assert np.array_equal(unit,schema.encode(c['params'])[0])
            errors.append(np.abs(unit-truth))
            true_params = row['target']['sourceParams']
            # Actual Squishr DSP: base=1650*2**(-3.8*bubbleSize). This is a
            # control-derived base frequency, not a measured event pitch.
            base_pitch.append(3.8*abs(first['params']['bubbleSize']-true_params['bubbleSize']))
            duration_ratio.append(abs(float(np.log2(first['params']['duration']/true_params['duration']))))
            top1.append(bool(np.array_equal(cat,categories)))
            covered.append(any(np.array_equal(schema.encode(c['params'])[1],categories) for c in pool))
            selected.append(bool(np.array_equal(schema.encode(row['arms'][arm]['selectedRaw']['params'])[1],categories)))
        mean = np.mean(errors,axis=0)
        summary[arm] = dict(numericMeanAbsoluteErrorNormalized=float(np.mean(mean)),
            byControl={c['name']:dict(normalizedMAE=float(e),controlUnitsMAE=float(e*(c['max']-c['min'])))
                for c,e in zip(schema.continuous,mean)},
            topRankTextureCorrect=sum(top1),trueTextureCoveredByProposals=sum(covered),
            softSelectedRawTextureCorrect=sum(selected),count=len(rows),
            nominalBaseFrequencyMAEOctaves=float(np.mean(base_pitch)),
            durationControlMeanAbsLog2Ratio=float(np.mean(duration_ratio)))
    _json_write(BASE/'evaluations/squishr-v1-control-diagnostics.json',dict(complete=True,
        reportSha256=file_hash(ROOT/'evaluation/results.json'),scriptSha256=file_hash(__file__),summary=summary,
        scope='Post-hoc native-test diagnostic. Ground-truth controls never influence inference, checkpoint selection, or displayed choices. Parameter agreement does not establish perceptual equivalence; alternative controls may be valid.'))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
