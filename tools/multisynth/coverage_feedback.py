"""Diagnostic candidate gallery and immutable schema-2 listening archives."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote, urlsplit

import numpy as np
import soundfile as sf


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _hash(value):
    return _digest(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def _audio_path(report, folder, filename):
    if not isinstance(folder, str) or not folder or Path(folder).is_absolute() or '..' in Path(folder).parts:
        raise ValueError('Invalid target folder path')
    if not isinstance(filename, str) or Path(filename).name != filename or filename in ('', '.', '..'):
        raise ValueError('Candidate audio must be a file in its target folder')
    path = (report/folder/filename).resolve()
    if not path.is_relative_to(report.resolve()):
        raise ValueError('Audio path escapes report directory')
    return path


def coverage_model(report, records, metadata):
    """Derive identities from actual audition bytes and full render provenance.

    Role, label and filename are intentionally excluded from the shared identity;
    identical aliases within one reference share ratings. Different references do
    not share likeness ratings, even if their candidate audio happens to match.
    """
    report = Path(report)
    targets, seen = [], set()
    for record in records:
        source, folder = record['source'], record['folder']
        reference_hash = _digest(_audio_path(report, folder, 'target.wav').read_bytes())
        tid = _hash({'source':source, 'folder':folder, 'referenceAudioSha256':reference_hash})
        if folder in seen:
            raise ValueError('Repeated target folder')
        seen.add(folder)
        candidates = []
        for candidate in record['candidates']:
            if not isinstance(candidate.get('sourceHash'), str) or not candidate['sourceHash']:
                raise ValueError('Candidate requires render sourceHash')
            if not isinstance(candidate.get('params'), dict) or not isinstance(candidate.get('provenance'), dict):
                raise ValueError('Candidate requires full parameters and render provenance')
            if type(candidate.get('seed')) is not int:
                raise ValueError('Candidate seed must be an integer')
            audio_hash = _digest(_audio_path(report, folder, candidate['file']).read_bytes())
            shared = {'targetId':tid, 'synth':candidate['synth'], 'paramsSha256':_hash(candidate['params']),
                      'seed':candidate['seed'], 'sourceHash':candidate['sourceHash'],
                      'audioSha256':audio_hash, 'provenance':candidate['provenance']}
            candidates.append({'id':_hash(shared), **{k:v for k,v in shared.items() if k != 'targetId'},
                               'file':candidate['file'], 'role':candidate['role'], 'label':candidate['label']})
        if not candidates:
            raise ValueError('A diagnostic reference requires candidates')
        targets.append({'id':tid, 'name':source['name'], 'sha256':source.get('sha256'), 'folder':folder,
                        'referenceAudioSha256':reference_hash, 'candidates':candidates})
    model = {'provenance':metadata, 'targets':targets}
    return {**model, 'experimentId':_hash(model)}


def _local_link(url, label):
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/') or '\\' in url or any(ord(c) < 32 for c in url):
        raise ValueError('Gallery links must be relative local URLs')
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def export_coverage(output, records, metadata):
    """Write results.json and a standalone gallery beside existing audition WAVs."""
    output = Path(output)
    model = coverage_model(output, records, metadata)
    esc = html.escape
    sections = []
    for record, target in zip(records, model['targets']):
        tid, folder, name = target['id'], target['folder'], esc(target['name'])
        def player(filename, label):
            url = quote(folder+'/'+filename, safe='/')
            return f'<audio controls preload="none" aria-label="{esc(label, quote=True)} for {name}" src="{url}"></audio>'
        cards = [f'<article class="reference"><strong>Reference</strong><p>Original target</p>{player("target.wav", "Reference")}</article>']
        for index, (candidate, identity) in enumerate(zip(record['candidates'], target['candidates'])):
            cid = identity['id']
            ratings = []
            for dimension, label in [('likeness','Likeness to reference'),('usefulness','Useful/fun game sound')]:
                buttons = ''.join(f'<label><input type="radio" name="{tid}-{index}-{dimension}" data-candidate="{cid}" data-dimension="{dimension}" value="{v}"><span>{v}</span></label>' for v in range(1,6))
                ratings.append(f'<fieldset><legend>{label}</legend>{buttons}<button type="button" data-clear="{cid}" data-dimension="{dimension}" aria-label="Clear {label} for {esc(candidate["label"])}">Clear</button></fieldset>')
            ingredients = f'<p class="ingredients">{esc(candidate["ingredients"])}</p>' if candidate.get('ingredients') else ''
            editor = '<p>'+_local_link(candidate['editUrl'], 'Open in Soundboard')+'</p>' if candidate.get('editUrl') else ''
            cards.append(f'<article><strong>{esc(candidate["label"])}</strong><p>{esc(candidate["synth"])}</p>{player(candidate["file"],candidate["label"])}{ingredients}{"".join(ratings)}{editor}</article>')
        shared = '<p>Exact audio aliases with the same render provenance share both ratings.</p>' if len({c['id'] for c in target['candidates']}) < len(target['candidates']) else ''
        note = f'<p>{esc(record["note"])}</p>' if record.get('note') else ''
        sections.append(f'<section><h2>{name}</h2>{note}{shared}<div class="cards">{"".join(cards)}</div><label class="notes">Notes (optional)<textarea data-note="{tid}" rows="2" placeholder="What resembles the reference? What would work well in a game?"></textarea></label></section>')
    encoded = json.dumps(model, allow_nan=False).replace('<', '\\u003c')
    script = Path(__file__).with_suffix('.js').read_text()
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Which recreations work?</title>
<style>body{font:16px/1.5 system-ui,sans-serif;background:#111722;color:#edf0f8;margin:0;padding:28px}main{max-width:1600px;margin:auto}h1{margin-bottom:8px}header p{max-width:1000px;color:#c7d0df}section{margin:34px 0;border-top:1px solid #42506a;padding-top:20px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(265px,1fr));gap:14px}article{background:#1c2535;padding:18px;border:1px solid #42506a;border-radius:10px;min-width:0}article.reference{background:#263449}article strong{font-size:18px}article p{font-size:14px;color:#c7d0df;margin:6px 0 12px}audio{width:100%;margin:8px 0}fieldset{border:0;padding:10px 0;margin:0}legend{font-size:14px;font-weight:600}fieldset label{display:inline-block;margin:2px}input{accent-color:#8bc7ff}button{cursor:pointer;background:#d5e8ff;border:0;border-radius:5px;padding:7px 10px;color:#132033}fieldset button{margin-left:6px}textarea{box-sizing:border-box;width:100%;background:#0d1320;color:#edf0f8;border:1px solid #596880;border-radius:6px;padding:10px;font:inherit}.notes{display:block;margin-top:18px}#feedback-json{margin-top:15px;font:12px/1.4 ui-monospace,monospace}a{color:#a6d4ff}:focus-visible{outline:3px solid #ffdb85;outline-offset:2px}</style><main><header><h1>Which recreations work?</h1>
<p>A small development diagnostic on references already reviewed, not an unseen test or evidence of a quality win.</p>
<p><b>Automatic match</b> searches the whole candidate library using global audio matching, without category tags. <b>Category-guided diagnostic</b> explicitly uses the reference category to explore coverage. <b>Best previously rated reference</b> replays a prior candidate chosen using existing human likeness ratings. A structurally different alternative may also be included.</p>
<p>Rate each sound independently: <b>Likeness to reference</b> (1 = far off, 5 = very close) and <b>Useful/fun game sound</b> (1 = not useful, 5 = very useful or fun). Either rating may be left blank. A useful sound can be a poor recreation.</p></header>'''
    if metadata.get('galleryIntro'):
        title = esc(metadata.get('galleryTitle','Which recreations work?'))
        intro = ''.join('<p>'+esc(paragraph)+'</p>' for paragraph in metadata['galleryIntro'])
        header_start = page.index('<header>')
        page = page[:header_start]+'<header><h1>'+title+'</h1>'+intro+'</header>'
        page = page.replace('<title>Which recreations work?</title>','<title>'+title+'</title>')
    if metadata.get('collectionUrl'):
        page += '<p>'+_local_link(metadata['collectionUrl'], 'Download new Soundboard choices')+'</p>'
    page += ''.join(sections)
    page += '<section><h2>Your feedback JSON</h2><p>Only references with ratings or notes are submitted. Unrated dimensions remain null. Nothing is sent automatically.</p><p id="feedback-status" role="status"></p><button type="button" id="copy-feedback">Copy feedback JSON</button> <button type="button" id="select-feedback">Select JSON</button><textarea id="feedback-json" readonly rows="14" aria-label="Feedback JSON" spellcheck="false"></textarea></section>'
    page += f'<script type="application/json" id="feedback-data">{encoded}</script><script>{script}</script></main></html>'
    (output/'results.json').write_text(json.dumps({'metadata':metadata,'results':records}, indent=2, allow_nan=False)+'\n')
    (output/'index.html').write_text(page)
    return model


def retain_coverage_feedback(feedback_path, report, output):
    """Validate every submitted identity before atomically retaining PCM16 audio."""
    feedback_path, report, output = map(Path, (feedback_path, report, output))
    raw = feedback_path.read_bytes()
    feedback = json.loads(raw)
    results = json.loads((report/'results.json').read_text())
    model = coverage_model(report, results['results'], results['metadata'])
    if (feedback.get('schemaVersion') != 2 or feedback.get('experimentId') != model['experimentId'] or
            feedback.get('provenance') != model['provenance']):
        raise ValueError('Feedback experiment/provenance does not match this report')
    if not isinstance(feedback.get('targets'), list):
        raise ValueError('Feedback targets must be an array')
    expected = {t['id']:(t,r) for t,r in zip(model['targets'],results['results'])}
    targets, candidates, audio_sources, seen = [], {}, {}, set()

    def audio(path):
        info = sf.info(path)
        if info.subtype != 'PCM_16':
            raise ValueError('Lossless archival requires PCM_16 audition WAVs')
        wave, rate = sf.read(path, dtype='int16', always_2d=True)
        pcm_hash = _digest(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes())
        relative = 'audio/'+pcm_hash+'.flac'
        audio_sources.setdefault(relative,(wave,rate))
        return {'file':relative,'pcmSha256':pcm_hash,'sampleRate':rate,'frames':len(wave),
                'channels':wave.shape[1],'auditionWavSha256':_digest(path.read_bytes())}

    for target in feedback['targets']:
        if not isinstance(target, dict) or target.get('id') not in expected or target['id'] in seen:
            raise ValueError('Unknown or repeated target identity')
        tid = target['id']
        seen.add(tid)
        original, record = expected[tid]
        if any(target.get(k) != v for k,v in original.items() if k != 'candidates'):
            raise ValueError('Target identity differs from report')
        if not isinstance(target.get('note',''), str):
            raise ValueError('Note must be text')
        observations = target.get('candidates')
        if not isinstance(observations, list) or len(observations) != len(original['candidates']):
            raise ValueError('Candidate identities differ from report')
        retained = {'id':tid,'source':record['source'],'note':target.get('note',''),
                    'referenceAudio':audio(_audio_path(report,record['folder'],'target.wav')),'candidates':[]}
        for observation, identity, candidate in zip(observations,original['candidates'],record['candidates']):
            if not isinstance(observation,dict) or any(observation.get(k) != v for k,v in identity.items()):
                raise ValueError('Candidate identity differs from report')
            ratings = {key:observation.get(key) for key in ('likeness','usefulness')}
            for value in ratings.values():
                if value is not None and (type(value) is not int or not 1 <= value <= 5):
                    raise ValueError('Ratings must be integers from 1 to 5 or null')
            cid = identity['id']
            retained['candidates'].append({'id':cid,'role':candidate['role'],'label':candidate['label'],'file':candidate['file']})
            if cid in candidates:
                if any(candidates[cid][key] != value for key,value in ratings.items()):
                    raise ValueError('Shared candidate has contradictory ratings')
            else:
                candidates[cid] = {**candidate, **identity, 'targetId':tid, **ratings,
                                   'audio':audio(_audio_path(report,record['folder'],candidate['file']))}
        targets.append(retained)
    summary = {'targets':len(targets),'uniqueRatedCandidates':sum(
        c['likeness'] is not None or c['usefulness'] is not None for c in candidates.values()),
        'likenessRatings':sum(c['likeness'] is not None for c in candidates.values()),
        'usefulnessRatings':sum(c['usefulness'] is not None for c in candidates.values())}
    manifest = {'schemaVersion':2,'experimentId':model['experimentId'],'feedbackSha256':_digest(raw),
                'provenance':model['provenance'],'summary':summary,'targets':targets,'candidates':list(candidates.values()),
                'ratingMeaning':{'likeness':'Human likeness to reference','usefulness':'Useful/fun game sound'},
                'audioMeaning':'Exact decoded PCM from audition WAVs, losslessly stored as PCM16 FLAC'}

    # Serialize during validation, before creating any archive directories.
    manifest_json = json.dumps(manifest,indent=2,allow_nan=False)+'\n'

    def verify_audio(root):
        for relative,(wave,rate) in audio_sources.items():
            path = (root/relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError('Archive audio path escapes archive directory')
            saved,saved_rate = sf.read(path,dtype='int16',always_2d=True)
            info = sf.info(path)
            if info.format != 'FLAC' or info.subtype != 'PCM_16' or saved_rate != rate or not np.array_equal(saved,wave):
                raise ValueError('Archive audio failed verification')

    if output.exists():
        if ((output/'feedback.json').read_bytes() != raw or
                json.loads((output/'manifest.json').read_text()) != manifest):
            raise ValueError('Archive already exists with different data; choose a new directory')
        verify_audio(output)
        return summary
    output.parent.mkdir(parents=True,exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.coverage-listening-',dir=output.parent))
    try:
        (staging/'audio').mkdir()
        (staging/'feedback.json').write_bytes(raw)
        for relative,(wave,rate) in audio_sources.items():
            sf.write(staging/relative,wave,rate,subtype='PCM_16')
        verify_audio(staging)
        (staging/'manifest.json').write_text(manifest_json)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary
