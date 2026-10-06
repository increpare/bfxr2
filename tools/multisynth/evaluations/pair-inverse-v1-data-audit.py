"""Replay stratified source-mixture rows and verify exact generated features."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import soundfile as sf
from multisynth.composition import CompositionRenderer
from neural_invert.pair_data import ROOT, SOURCE
from neural_invert.pair_train import read_data
from neural_invert.features import describe
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write


def main():
    manifest,bankdoc,rows,shard,codec=read_data(ROOT)
    groups=defaultdict(list)
    for key,component in bankdoc['bank'].items():groups[component['audioHash']].append(component)
    overlap=[v for v in groups.values() if len({r['split'] for r in v})>1]
    assert not overlap and len(groups)==len(bankdoc['bank'])
    normalized=defaultdict(list)
    for component in bankdoc['bank'].values():
        wave,_=sf.read(component['file'],dtype='float32')
        normalized[audio_hash(audition_pcm(wave))].append(component['split'])
    assert len(normalized)==len(groups) and not any(len(set(v))>1 for v in normalized.values())
    parent=json.loads((SOURCE/'manifest.json').read_text())
    assert file_hash(SOURCE/'manifest.json')==bankdoc['sourceManifestSha256'] and parent['complete']
    for name,stamp in bankdoc['parentMetadataSha256'].items():
        assert file_hash(SOURCE/(name+'.json'))==stamp==parent['files'][name]['metadataSha256']
    ids=[]
    for split in ('train','val','test'):
        for kind in ('both','Boomr','Transfxr'):
            selected=[i for i,r in enumerate(rows) if r['split']==split and r['kind']==kind]
            ids.extend([selected[0],selected[-1]])
    checked=[]
    with CompositionRenderer() as renderer:
        assert renderer.inventory==manifest['inventory']
        for i in ids:
            params,wave=renderer.render(rows[i]['params'],uncached=True);heard=audition_pcm(wave)
            assert params==rows[i]['params'] and audio_hash(wave)==rows[i]['audioHash']
            assert audio_hash(heard)==rows[i]['auditionHash']
            feature=describe(heard);assert np.array_equal(feature,shard['features'][i].numpy())
            unit,cat=codec.encode(params)
            assert np.array_equal(unit,shard['continuous'][i].numpy()) and np.array_equal(cat,shard['categorical'][i].numpy())
            checked.append(dict(index=i,id=rows[i]['id'],rawHash=audio_hash(wave),auditionHash=audio_hash(heard)))
    report=dict(complete=True,components=len(groups),crossSplitIdenticalPCM=len(overlap),uniqueNormalizedSourcePCM=len(normalized),crossSplitIdenticalNormalizedPCM=0,examples=len(rows),
        splitCounts={k:len(v) for k,v in manifest['splits'].items()},replayedRows=checked,
        allBankFilesAndExactLabelsValidated=True,dataManifestSha256=file_hash(ROOT/'manifest.json'),
        scriptSha256=file_hash(__file__),compositionWrapperSha256=file_hash('tools/multisynth/composition.py'),
        scope='Exact component controls and source PCM disjoint; shared preset families and possible historical baseline component overlap remain.18stratified uncached native replays reproduce exact features and labels.')
    _json_write(Path('tools/multisynth/evaluations/pair-inverse-v1-data-audit.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k!='replayedRows'}),flush=True)


if __name__=='__main__':main()
