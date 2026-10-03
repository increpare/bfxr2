"""Self-contained listening comparisons and portable feedback identities."""
import hashlib
import html
import json
from pathlib import Path


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def feedback_gallery(records, metadata):
    targets, cards = [], []
    for record in records:
        source, folder = record['source'], record['folder']
        target_id = _hash({'sha256':source.get('sha256'), 'folder':folder})
        selected = record['candidates'][0]
        bfxr = next((c for c in record['candidates'] if c['synth']=='Bfxr'), None)
        previous = record.get('previous')
        if previous is not None and (Path(previous['file']).name != previous['file'] or
                                     previous['file'] in ('', '.', '..')):
            raise ValueError('Previous candidate audio must be a file in the target folder')
        def identity(candidate):
            if candidate is None:
                return None
            return {'id':_hash({'target':target_id,'synth':candidate['synth'],
                                'params':candidate['params'],'seed':candidate.get('seed')}),
                    'synth':candidate['synth'],'file':candidate['file'],'seed':candidate.get('seed'),
                    'distance':candidate['score']}
        chosen, baseline, old = identity(selected), identity(bfxr), identity(previous)
        target = {'id':target_id,'name':source['name'],'sha256':source.get('sha256'),
                  'folder':folder,'selected':chosen,'bfxr':baseline}
        if old is not None:
            target['previous'] = old
        targets.append(target)
        def approximation(label, candidate, role):
            if candidate is None:
                return f'<article><strong>{label}</strong><p>No Bfxr result in this run.</p></article>'
            cid = candidate['id']
            buttons = ''.join(f'<label><input type="radio" name="{target_id}-{role}" data-candidate="{cid}" value="{value}"><span>{value}</span></label>' for value in range(1,6))
            score = '' if old is not None else f' · distance {candidate["distance"]:.3f}'
            return f'<article><strong>{label}</strong><small>{html.escape(candidate["synth"])}{score}</small><audio aria-label="{label} for {html.escape(source["name"],quote=True)}" controls preload="none" src="{html.escape(folder+"/"+candidate["file"],quote=True)}"></audio><fieldset class="rating"><legend>Likeness to reference</legend>{buttons}<button type="button" data-clear="{cid}" aria-label="Clear {label} rating for {html.escape(source["name"],quote=True)}">Clear</button></fieldset></article>'
        same = '<p class="same-result">The model selected Bfxr here, so these are the same sound and share one rating.</p>' if baseline and chosen['id']==baseline['id'] else ''
        if old is not None:
            ids = [c['id'] for c in (chosen, old, baseline) if c is not None]
            same = '<p class="same-result">Candidates with identical synth, parameters and seed are the same sound and share one rating.</p>' if len(set(ids)) < len(ids) else ''
        selected_label = 'New model' if old is not None else 'Model selection'
        previous_card = approximation('Previous model', old, 'previous') if old is not None else ''
        grid_class = 'comparison-grid four-way' if old is not None else 'comparison-grid'
        name = html.escape(source['name'])
        cards.append(f'<section class="comparison" id="sound-{folder}"><h2>{name}</h2><a href="{folder}/index.html">All synth alternatives</a>{same}<div class="{grid_class}"><article><strong>Reference</strong><small>Original target</small><audio aria-label="Reference for {html.escape(source["name"],quote=True)}" controls preload="none" src="{folder}/target.wav"></audio></article>{approximation(selected_label,chosen,"selected")}{previous_card}{approximation("Bfxr approximation",baseline,"bfxr")}</div><label class="note-label">Notes (optional)<textarea data-note="{target_id}" rows="2" placeholder="What is closer? What sounds fun or wrong?"></textarea></label></section>')
    provenance = {key:metadata.get(key) for key in ('sourceHash','featureVersion','libraryManifestHash','seed','budgetPerExpert','experts')}
    provenance.update({key:metadata[key] for key in ('objectiveVersion','modelHash') if key in metadata})
    model = {'provenance':provenance,'targets':targets}
    model['experimentId'] = _hash(model)
    encoded = json.dumps(model).replace('<', '\\u003c')
    script = Path(__file__).with_name('feedback.js').read_text()
    footer = '<section class="feedback-export" id="feedback"><h2>Your feedback JSON</h2><p>Only rated sounds and notes are included. Copy this and paste it into our chat whenever you are ready.</p><p id="feedback-status" role="status"></p><button type="button" id="copy-feedback">Copy feedback JSON</button> <button type="button" id="select-feedback">Select JSON</button><textarea id="feedback-json" aria-label="Feedback JSON" readonly rows="14" spellcheck="false"></textarea></section>'
    return ''.join(cards)+footer+f'<script type="application/json" id="feedback-data">{encoded}</script><script>{script}</script>'
