"""Publish fresh external references with an immediate, optional mismatch question."""
import importlib.util
import json
from pathlib import Path
import torch
from match.bfxr_io import render_worker_cmd
from multisynth.coverage_feedback import export_coverage
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
SCRIPT=BASE/'evaluations/fresh-gesture-v1.py'
ROOT=BASE/'runs/fresh-gesture-v1'
GALLERY=BASE/'runs/fresh-gesture-v1-listening'
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
    assert len(frozen['priorArchives'])==24
    overlaps={r['source']['name']:r['source']['historicalBfxrSplits'] for r in frozen['rows']}
    assert len(overlaps)==8 and all(s==['train'] for s in overlaps.values())
    assert all(file_hash(r['source']['path'])==r['source']['sha256'] for r in frozen['rows'])
    spec=importlib.util.spec_from_file_location('fresh_experiment',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert file_hash(module.BFXR_MANIFEST)==frozen['historicalBfxrManifestSha256']
    assert file_hash(module.PLAN)==frozen['designSha256']
    # This construction verifies every selected waveform against actual native DSP,
    # then reproduces every score on the exact PCM16 that will be heard.
    module.gallery()
    results=json.loads((GALLERY/'results.json').read_text())
    audit_path=BASE/'evaluations/fresh-gesture-v1-listening-audit.json'
    audit=json.loads(audit_path.read_text())
    records=results['results'];metadata=results['metadata']
    metadata['galleryTitle']='Eight fresh sounds — what gets lost?'
    metadata['galleryIntro']=[
        'Eight new-to-this-listening-study tagged sounds. Existing synth-trained experts and their refinements are compared with original Bfxr.',
        'All eight files occur in the historical original-Bfxr real-audio training list. They are external inputs for the newer synthetic-trained experts, but not an unseen Bfxr test. Source families can overlap.',
        'Choose the closest, then how close it feels. For imperfect matches, one optional question asks the biggest mismatch while the sounds remain available. Skip it with S. Take the optional break after five.']
    metadata['scope']='New to retained listening feedback, with prior exact source and audition PCM excluded. All eight overlap historical original-Bfxr training. Not a family-disjoint test. Existing frozen inverses/scorers; no retraining or quality-improvement claim.'
    metadata['originalBfxrOverlap']=overlaps
    metadata['uiCodeHashes']={name:file_hash(BASE/name) for name in ASSETS}
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
    page=page.replace(help_text,help_text+' Imperfect matches have one optional mismatch question; S skips it.')
    info='<details class="quick-help"><summary>About these eight fresh sounds</summary><p>New to our listening rounds. All eight occur in original Bfxr’s historical real-audio training list; they are external inputs for the newer synth-trained experts. Source families may overlap. Existing models and scorers are used; no improvement is assumed.</p></details>'
    page=page.replace('<div class="quick-topline">',info+'<div class="quick-topline">')
    page=page.replace('S = skip / not sure · Space', '1–6 = mismatch reason when asked · S = skip / not sure · Space')
    (GALLERY/'index.html').write_text(page)
    assert all(len(t['candidates'])==3 and len({c['audioSha256'] for c in t['candidates']})==3 for t in model['targets'])
    assert audit['audioFiles']=={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))}
    assert file_hash(render_worker_cmd()[0])==frozen['bfxrBackend']['sha256']
    audit.update(experimentId=model['experimentId'],resultsSha256=file_hash(GALLERY/'results.json'),
        htmlSha256=file_hash(GALLERY/'index.html'),uiCodeHashes=metadata['uiCodeHashes'],
        publicationBindings=metadata['publicationBindings'],originalBfxrOverlap=overlaps)
    _json_write(audit_path,audit)
    _json_write(BASE/'evaluations/fresh-gesture-v1-targets.json',frozen|{'targetsSha256':file_hash(ROOT/'targets.json')})
    print(json.dumps(dict(complete=True,experimentId=model['experimentId'],targets=8,options=24)),flush=True)


if __name__=='__main__':main()
