"""Publish the transfer gallery with explicit historical Bfxr overlap and backend binding."""
import importlib.util
import json
from pathlib import Path
import soundfile as sf
import torch
from match.bfxr_io import render_worker_cmd
from match.renderer import BfxrRenderer
from multisynth.coverage_feedback import export_coverage
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth')
SCRIPT=BASE/'evaluations/off-model-transfer-v1.py'
ROOT=BASE/'runs/off-model-transfer-v1'
GALLERY=BASE/'runs/off-model-transfer-v1-listening'
OVERLAP=BASE/'evaluations/off-model-transfer-v1-bfxr-training-overlap.json'
BACKEND=BASE/'evaluations/off-model-transfer-v1-bfxr-backend.json'


def main():
    torch.set_num_threads(1)
    if GALLERY.exists(): raise FileExistsError('Never revise a published session')
    backend=json.loads(BACKEND.read_text())
    overlap=json.loads(OVERLAP.read_text())
    assert backend['command']==render_worker_cmd()
    assert file_hash(backend['command'][0])==backend['backendSha256']
    assert backend['targetsSha256']==file_hash(ROOT/'targets.json')
    assert file_hash(overlap['manifest'])==overlap['manifestSha256']
    frozen=json.loads((ROOT/'targets.json').read_text())
    source_meta={r['source']['name']:r['source'] for r in frozen['rows']}
    statuses={}
    for item in overlap['exactFileMatches']:
        assert file_hash(item['source']['path'])==source_meta[item['target']]['sha256']
        statuses.setdefault(item['target'],set()).add(item['source']['split'])
    assert len(statuses)==8
    assert sum('train' in s for s in statuses.values())==6
    assert sum(s=={'holdout'} for s in statuses.values())==2
    spec=importlib.util.spec_from_file_location('transfer_experiment',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Build and verify all audio before finalizing publication metadata.
    module.gallery()
    results=json.loads((GALLERY/'results.json').read_text())
    audit_path=BASE/'evaluations/off-model-transfer-v1-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    records=results['results']
    originals_checked=0
    with BfxrRenderer(jobs=1) as renderer:
        for row in records:
            row['source']['historicalBfxrSplits']=sorted(statuses[row['source']['name']])
            for c in row['candidates']:
                if c.get('expert')!='original-bfxr':continue
                actual=audition_pcm(renderer.render(c['params'],seed=c['seed']))
                recorded,rate=sf.read(GALLERY/row['folder']/c['file'],dtype='float32')
                assert rate==44100 and audio_hash(actual)==audio_hash(recorded)
                c['provenance']['originalBfxrBackend']=backend
                originals_checked+=1
    assert originals_checked==8
    assert file_hash(backend['command'][0])==backend['backendSha256']
    metadata=results['metadata']
    metadata['galleryIntro']=[
        'Eight external tagged sounds; no native synth test sounds. Take the optional break after five.',
        'This tests transfer for the newer synth-trained experts. Original Bfxr is a familiar baseline: six files appeared in its real-audio training list, and two in its holdout list.',
        'Choose the closest, then say how close it feels. None close is useful. Alternatives include disagreements between scoring methods.']
    metadata['scope']='External references for the synthetic-trained newer experts. Original Bfxr has known real-finetune overlap (six train, two holdout); it is an anchor, not an independently unseen baseline. Exact prior feedback file/PCM excluded; source families may overlap development.'
    metadata['originalBfxrOverlap']={k:sorted(v) for k,v in statuses.items()}
    metadata['publicationBindings']=dict(scriptSha256=file_hash(__file__),overlapAuditSha256=file_hash(OVERLAP),
        backendAuditSha256=file_hash(BACKEND),backendReplays=originals_checked,
        backendHashTiming='Captured during inference, rechecked and all original outputs replayed at publication; not claimed frozen before inference.')
    model=export_coverage(GALLERY,records,metadata)
    audit.update(experimentId=model['experimentId'],resultsSha256=file_hash(GALLERY/'results.json'),
        htmlSha256=file_hash(GALLERY/'index.html'),publicationBindings=metadata['publicationBindings'])
    assert audit['audioFiles']=={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))}
    _json_write(audit_path,audit)
    print(json.dumps(dict(complete=True,experimentId=model['experimentId'],targets=8,options=24,backendReplays=originals_checked)),flush=True)

if __name__=='__main__': main()
