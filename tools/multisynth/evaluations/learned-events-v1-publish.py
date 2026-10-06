"""Publish new evidence only; do not ask the listener to rejudge identical option sets."""
import importlib.util
import json
from pathlib import Path
import hashlib
import shutil
import numpy as np
import soundfile as sf
import torch
from multisynth.coverage_feedback import export_coverage
from multisynth.coverage import verify_archived_audio
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/learned-events-v1'
FINAL=BASE/'runs/learned-events-v1-listening'
DRAFT=ROOT/'unpublished-gallery'
ARCHIVES=[BASE/'listening_data'/('2026-10-06-'+n+'-quick-01') for n in ('legacy-transfer-v1','stackr-events-v1')]

def pcm(path):
    wave,rate=sf.read(path,dtype='int16',always_2d=True)
    assert rate==44100 and wave.shape[1]==1
    return hashlib.sha256(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()

def main():
    torch.set_num_threads(1)
    if FINAL.exists() or DRAFT.exists():raise FileExistsError('Preserve previous publication')
    publication=dict(scriptSha256=file_hash(__file__),policy='Omit a trial only when the exact reference PCM and complete distinct option PCM set already occurred in a completed, fully auditioned retained trial. Do not filter on ratings, scores or which arm wins.',
        archiveHashes={str(a/'manifest.json'):file_hash(a/'manifest.json') for a in ARCHIVES},
        fittingProtocolSha256=file_hash(ROOT/'protocol.json'))
    _json_write(ROOT/'publication-protocol.json',publication)
    spec=importlib.util.spec_from_file_location('learned_events',BASE/'evaluations/learned-events-v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.GALLERY=DRAFT;module.publish()
    draft=json.loads((DRAFT/'results.json').read_text());known=[]
    for archive in ARCHIVES:
        manifest=json.loads((archive/'manifest.json').read_text());candidates={c['id']:c for c in manifest['candidates']}
        for target in manifest['targets']:
            choice=target.get('choice');ids={c['id'] for c in target['candidates']}
            if not choice or choice['kind']=='skip' or not ids<=set(choice['auditionedCandidateIds']):continue
            verify_archived_audio(archive,target['referenceAudio'])
            for cid in ids:verify_archived_audio(archive,candidates[cid]['audio'])
            known.append(dict(archive=str(archive),experimentId=manifest['experimentId'],targetId=target['id'],
                referencePcm=target['referenceAudio']['pcmSha256'],options=sorted({candidates[cid]['audio']['pcmSha256'] for cid in ids})))
    records=[];skipped=[];FINAL.mkdir()
    for record in draft['results']:
        folder=DRAFT/record['folder'];reference=pcm(folder/'target.wav')
        options=sorted({pcm(folder/c['file']) for c in record['candidates']})
        same=next((k for k in reversed(known) if k['referencePcm']==reference and k['options']==options),None)
        if same:
            skipped.append(dict(trialIndex=int(record['folder'])-1,source=record['source'],reason='Exact reference and all option PCM already judged and heard',duplicateOf=same));continue
        dest=FINAL/record['folder'];dest.mkdir()
        for name in {'target.wav',*[c['file'] for c in record['candidates']]}:shutil.copyfile(folder/name,dest/name)
        records.append(record)
    assert records,'No new comparisons require listening'
    metadata=draft['metadata'];metadata.update(targetCount=len(records),publication=publication,skippedAlreadyHeard=skipped)
    metadata['galleryIntro'][0]=f'{len(records)} external sounds with new native Stackr comparisons and your exact latest choice. An unchanged fully heard option set is omitted.'
    model=export_coverage(FINAL,records,metadata)
    page=(FINAL/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>'
    assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    info='<details class="quick-help"><summary>What is this testing?</summary><p>Five repeated external sounds with new options. Two native Stackr fits use either a newly trained event-timing CNN or the earlier waveform splitter. Both use frozen synth-control experts,128 mutations per event and128 timeline mutations; different counts mean different total work. Your latest winner is copied exactly. Identical audio is merged. The fully repeated bell trial is omitted. Native timing training used synthetic schedules only; this does not establish real-sound likeness. These sources overlap historical Bfxr training.</p></details>'
    page=page.replace('<div class="quick-topline">',info+'<div class="quick-topline">')
    (FINAL/'index.html').write_text(page)
    previousAudit=json.loads((BASE/'evaluations/learned-events-v1-listening-audit.json').read_text())
    audit=dict(complete=True,experimentId=model['experimentId'],targetCount=len(records),
        optionCounts=[len(r['candidates']) for r in records],skippedIdentical=previousAudit['skippedIdentical'],
        skippedAlreadyHeard=skipped,publication=publication,reportSha256=file_hash(ROOT/'results.json'),
        resultsSha256=file_hash(FINAL/'results.json'),htmlSha256=file_hash(FINAL/'index.html'),
        audioFiles={str(p.relative_to(FINAL)):file_hash(p) for p in sorted(FINAL.glob('*/*.wav'))},uiCodeHashes=metadata['uiCodeHashes'])
    _json_write(BASE/'evaluations/learned-events-v1-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],targets=len(records),options=audit['optionCounts'],skipped=[s['source']['name'] for s in skipped])),flush=True)

if __name__=='__main__':main()
