"""Publish matched legacy/preference transfer with immediate listening questions."""
import importlib.util
import json
from pathlib import Path
import torch
from match.bfxr_io import render_worker_cmd
from multisynth.coverage_feedback import export_coverage
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
SCRIPT=BASE/'evaluations/legacy-transfer-v1.py'
ROOT=BASE/'runs/legacy-transfer-v1'
GALLERY=BASE/'runs/legacy-transfer-v1-listening'
ASSETS=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js',
        'quick_listening.html','quick_listening.css','quick_mismatch.js',
        'quick_mismatch.css','quick_listening_diagnostic.js']


def main():
    torch.set_num_threads(1)
    if GALLERY.exists():raise FileExistsError('Never revise a published session')
    frozen=json.loads((ROOT/'targets.json').read_text())
    assert frozen['scriptSha256']==file_hash(SCRIPT)
    assert frozen['bfxrBackend']['command']==render_worker_cmd()
    assert frozen['bfxrBackend']['sha256']==file_hash(render_worker_cmd()[0])
    assert all(file_hash(p)==h for p,h in frozen['codeHashes'].items())
    assert all(file_hash(p)==h for p,h in frozen['priorArchives'].items())
    assert len(frozen['priorArchives'])==27
    overlaps={r['source']['name']:r['source']['historicalBfxrSplits'] for r in frozen['rows']}
    assert len(overlaps)==6 and all(splits==['train'] for splits in overlaps.values())
    assert all(file_hash(r['source']['path'])==r['source']['sha256'] for r in frozen['rows'])
    spec=importlib.util.spec_from_file_location('fresh_experiment',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert file_hash(module.BFXR_MANIFEST)==frozen['historicalBfxrManifestSha256']
    assert file_hash(module.PLAN)==frozen['designSha256']
    # This construction verifies every selected waveform against actual native DSP,
    # then reproduces every score on the exact PCM16 that will be heard.
    module.gallery()
    results=json.loads((GALLERY/'results.json').read_text())
    audit_path=BASE/'evaluations/legacy-transfer-v1-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    records=results['results'];metadata=results['metadata']
    metadata['galleryTitle']='Six fresh sounds — does the old matching recipe help?' 
    metadata['galleryIntro']=[
        'Six new-to-this-listening-study tagged sounds. Existing inverse models propose the same candidates to two matching objectives.',
        'Both general-synth fits get two starts and 1,024 native refinement attempts: original MatchObjective versus the learned preference selector. Original Bfxr remains a separate third option with its own optimizer.',
        'Choose the closest, then how close. Optional mismatch questions appear while the sounds remain available. All six files occur in historical original-Bfxr training; source families may overlap. No model improvement is assumed.']
    metadata['scope']='Fresh to retained feedback, prior exact files and audition PCM excluded. Repeated source families and historical Bfxr training may overlap. Existing inverse weights; equal general-arm proposal/refinement budgets, independent original Bfxr budget2000. No quality claim.'
    metadata['originalBfxrOverlap']=overlaps
    metadata['uiCodeHashes']={name:file_hash(BASE/name) for name in ASSETS}
    metadata['priorNegativeTextureResultSha256']=file_hash(BASE/'evaluations/texture-listener-v1-evaluation.json')
    metadata['selectionPolicy']=frozen['listeningPolicy']
    metadata['diagnosticQuestion']={
        'version':'quick-mismatch-v1','optional':True,
        'trigger':'similar, least-bad, or none close',
        'answers':['pitch','movement/rhythm','texture/timbre','attack/decay','several things','unsure'],
        'storage':'Scoped target note with exact candidate IDs; unchanged schema3',
        'reloadPolicy':'Completed judgments remain saved even if the optional question was left unanswered.'}
    metadata['publicationBindings']={
        'scriptSha256':file_hash(__file__),'bfxrBackend':frozen['bfxrBackend'],
        'historicalManifestSha256':frozen['historicalBfxrManifestSha256'],
        'backendHashTiming':'Frozen before inference and rechecked at publication.'}
    for row in records:
        row['note']='Choose the closest and judge likeness. The optional mismatch question refers to the chosen option, tied options, or all presented options, as labelled.'
        for candidate in row['candidates']:
            if candidate.get('expert')=='original-bfxr':
                assert candidate['originalBfxrBackend']==frozen['bfxrBackend']
                candidate['provenance']['originalBfxrBackend']=frozen['bfxrBackend']
    model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text()
    old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>'
    assert page.count(old)==1
    new='<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>'
    page=page.replace(old,new).replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    # The quick view uses its own help text, rather than the detailed header.
    help_text='Choose the closest, then say how close it is while it’s still here.'
    assert page.count(help_text)==1
    page=page.replace(help_text,'Six fresh comparisons. '+help_text+' Imperfect matches have one optional mismatch question; S skips it.')
    overlap_text='; '.join(f'{name}: {", ".join(splits) if splits else "not found"}' for name,splits in overlaps.items())
    import html
    info='<details class="quick-help"><summary>What is this testing?</summary><p>Six new listening references. The same newer-synth predictions are refined with either original MatchObjective or the learned selector, with equal 1,024-attempt budgets. Original Bfxr is the independent third option. No inverse weights were retrained. All six files occur in historical original-Bfxr training. Source families can overlap.</p><p>Historical original-Bfxr real-data membership: '+html.escape(overlap_text)+'. This is not an unseen Bfxr benchmark.</p></details>'
    page=page.replace('<div class="quick-topline">',info+'<div class="quick-topline">')
    page=page.replace('S = skip / not sure · Space', '1–6 = mismatch reason when asked · S = skip / not sure · Space')
    (GALLERY/'index.html').write_text(page)
    assert all(2<=len(t['candidates'])<=3 and len({c['audioSha256'] for c in t['candidates']})==len(t['candidates']) for t in model['targets'])
    assert audit['audioFiles']=={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))}
    assert file_hash(render_worker_cmd()[0])==frozen['bfxrBackend']['sha256']
    audit.update(experimentId=model['experimentId'],resultsSha256=file_hash(GALLERY/'results.json'),
        htmlSha256=file_hash(GALLERY/'index.html'),uiCodeHashes=metadata['uiCodeHashes'],
        publicationBindings=metadata['publicationBindings'],originalBfxrOverlap=overlaps)
    _json_write(audit_path,audit)
    _json_write(BASE/'evaluations/legacy-transfer-v1-targets.json',frozen|{'targetsSha256':file_hash(ROOT/'targets.json')})
    print(json.dumps(dict(complete=True,experimentId=model['experimentId'],targets=6,options=sum(len(t['candidates']) for t in model['targets']))),flush=True)


if __name__=='__main__':main()
