"""Verify delivered pitch-v4 choices against actual DSP and immutable history."""
import json
from pathlib import Path
import re
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from multisynth.coverage_feedback import coverage_model
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash
from neural_invert.experiment import audition_pcm
from neural_invert.pitch_gallery import pcm_hash, refinement_seed
from neural_invert.temporal_eval import ENGINES


def main():
    torch.set_num_threads(1)
    root = Path('tools/multisynth/runs/pitch-v4-listening')
    old = Path('tools/multisynth/runs/temporal-v3-listening')
    audit_path = Path('tools/multisynth/evaluations/temporal-v3-listening-audit.json')
    old_audit = json.loads(audit_path.read_text())
    assert file_hash(old/'results.json') == old_audit['reportSha256']
    assert file_hash(old/'index.html') == old_audit['htmlSha256']
    prior_pcm = {t['name']: t['referencePcmSha256'] for t in old_audit['targets']}
    previous = json.loads((old/'results.json').read_text())
    previous_rows = {r['source']['sha256']: r for r in previous['results']}
    result = json.loads((root/'results.json').read_text())
    meta = result['metadata']
    assert meta['complete'] and meta == json.loads((root/'manifest.json').read_text())
    assert meta['previousReportSha256'] == old_audit['reportSha256']
    assert meta['previousPageSha256'] == old_audit['htmlSha256']
    targets = Path('tools/multisynth/evaluations/pitch-v4-listening-targets.json')
    assert file_hash(targets) == meta['targetManifestSha256']
    assert [r['source'] for r in result['results']] == json.loads(targets.read_text())['targets']
    tools = Path('tools')
    for relative, digest in meta['codeHashes'].items():
        assert file_hash(tools/relative) == digest, relative
    archives = {}
    for entry in meta['archives']:
        archive = Path(entry['path'])
        for relative, digest in entry['files'].items():
            assert file_hash(archive/relative) == digest
        manifest = json.loads((archive/'manifest.json').read_text())
        archives[manifest['experimentId']] = (archive, manifest)
    for engine, digest in meta['checkpointHashes'].items():
        assert file_hash(Path(meta['modelDirectory'])/engine/'best.pt') == digest
    observed = []
    replay_count = 0
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash'] == meta['sourceHash']
        for record in result['results']:
            source, diag = record['source'], record['diagnostics']
            dest = root/record['folder']
            assert file_hash(source['path']) == source['sha256']
            assert pcm_hash(dest/'target.wav') == prior_pcm[source['name']]
            assert file_hash(dest/'target.wav') == record['referenceAudioSha256']
            reference, rate = sf.read(dest/'target.wav', dtype='float32'); assert rate == 44100
            objective = MatchObjective(reference)
            before = previous_rows[source['sha256']]
            assert diag['oldGalleryFolder'] == before['folder']
            actual = []
            for row in diag['allRaw']+diag['allRefined']:
                params, wave = renderer.render(row['synth'], row['params'], row['seed'])
                assert params == row['params'] and audio_hash(wave) == row['actualRenderAudioHash']
                score = float(objective.score_batch([wave])[0])
                assert abs(score-row['score']) < 1e-6
                actual.append((row,wave)); replay_count += 1
            expected = min((r for r,w in actual), key=lambda r:r['score'])
            selected = next(c for c in record['candidates'] if c['role'] == 'selected')
            assert (selected['synth'], selected['params'], selected['seed'], selected['score']) == (expected['synth'], expected['params'], expected['seed'], expected['score'])
            _, raw = renderer.render(selected['synth'], selected['params'], selected['seed'])
            heard, _ = sf.read(dest/selected['file'], dtype='float32')
            assert audio_hash(heard) == audio_hash(audition_pcm(raw))
            assert selected['provenance']['actualRenderAudioHash'] == audio_hash(raw)
            assert abs(float(objective.score_batch([heard])[0])-selected['provenance']['auditionMatchObjectiveScore']) < 1e-6
            assert set(diag['accounting']) == set(ENGINES)
            for engine, a in diag['accounting'].items():
                assert a['expected'] == 4
                assert a['proposed'] == sum(p['synth']==engine for p in diag['proposals'])
                assert a['rendered'] == sum(p['synth']==engine for p in diag['allRaw'])
                assert a['missingProposals'] == 4-a['proposed']
                assert a['failedRenders'] == a['proposed']-a['rendered']
                seed = refinement_seed(before['folder'],engine)
                assert diag['refinementSeeds'][engine] == seed
                attempted = [t for t in diag['renderAttempts'] if t['phase']=='refinement-'+engine]
                assert len(attempted) == diag['refinementAttemptsByEngine'][engine]
                assert len(attempted) == (meta['refinementBudgetPerEngine'] if diag['refinementStatus'][engine]=='completed' else 0)
            accepted, failures, nonfinite = [], [], []
            for row in diag['proposals']:
                matches = [a for a in diag['renderAttempts'] if a['phase']=='raw-scoring' and a['synth']==row['synth'] and a['requestedParams']==row['params'] and a['seed']==row['seed']]
                assert matches
                try:
                    params,wave = renderer.render(row['synth'],row['params'],row['seed'])
                except (ValueError,RuntimeError) as error:
                    assert any(m.get('error')==str(error) for m in matches)
                    failures.append({'synth':row['synth'],'error':str(error)})
                    continue
                assert any(m.get('audioHash')==audio_hash(wave) and m.get('params')==params for m in matches)
                try:
                    if np.max(np.abs(wave)) < 1e-6:
                        raise ValueError('Silent prediction')
                    score = float(objective.score_batch([wave])[0])
                except (ValueError,RuntimeError) as error:
                    failures.append({'synth':row['synth'],'error':str(error)})
                    continue
                if not np.isfinite(score):
                    nonfinite.append({'synth':row['synth'],'params':params,'seed':row['seed'],
                        'error':'Nonfinite proposal score','audioHash':audio_hash(wave)})
                else:
                    accepted.append((row['synth'],params,row['seed'],audio_hash(wave),score))
            assert failures+nonfinite == diag['failures']
            assert len(accepted) == len(diag['allRaw'])
            for expected_raw, row in zip(accepted,diag['allRaw']):
                assert expected_raw[:4] == (row['synth'],row['params'],row['seed'],row['actualRenderAudioHash'])
                assert abs(expected_raw[4]-row['score']) < 1e-6
            choices = []
            for session,(experiment,(archive,manifest)) in enumerate(archives.items()):
                for target in manifest['targets']:
                    if target['source']['sha256'] != source['sha256']:
                        continue
                    assert target['referenceAudio']['pcmSha256'] == pcm_hash(dest/'target.wav')
                    choice = target.get('choice')
                    if not choice or choice['kind'] != 'best':
                        continue
                    assert len(choice['preferredCandidateIds']) == 1
                    cid = choice['preferredCandidateIds'][0]
                    if cid not in choice['auditionedCandidateIds']:
                        continue
                    assert cid in [c['id'] for c in target['candidates']]
                    frozen = next(c for c in manifest['candidates'] if c['id']==cid)
                    assert frozen['targetId'] == target['id']
                    choices.append((session,experiment,archive,manifest,target,frozen))
            expected_history = {}
            if choices:
                expected_history['previous'] = max(choices,key=lambda x:x[0])
            if source['name']=='die/charm2.wav':
                expected_history['anchor'] = max((c for c in choices if c[2].name=='2026-10-04-neural-v2-quick-01' and c[5]['synth']=='Transfxr'),key=lambda x:x[0])
            cards, roles = {}, {}
            for candidate in record['candidates']:
                path = dest/candidate['file']; provenance = candidate['provenance']
                assert pcm_hash(path) == provenance['auditionPcmSha256']
                assert file_hash(path) == provenance['auditionWavSha256']
                # Exact aliases remain independently auditable even when hidden from quick choices.
                aliases = [candidate]+provenance.get('identicalPcmAliases',[])
                for card in aliases:
                    roles[card['role']] = card
                    if card['role'] in ('previous','anchor'):
                        _,experiment,arc,manifest,target,frozen = expected_history[card['role']]
                        assert card['provenance']['experimentId'] == experiment
                        assert card['provenance']['candidateId'] == frozen['id']
                        assert card['provenance']['historicalChoice'] == target['choice']
                        assert pcm_hash(path) == frozen['audio']['pcmSha256'] == pcm_hash(arc/frozen['audio']['file'])
                        assert (card['synth'],card['params'],card['seed']) == (frozen['synth'],frozen['params'],frozen['seed'])
                        assert card['sourceHash'] == frozen.get('sourceHash',manifest['provenance'].get('sourceHash'))
                    elif card['role']=='original':
                        frozen = next(c for c in before['candidates'] if c['role']=='original')
                        assert file_hash(path) == file_hash(old/before['folder']/frozen['file'])
                        assert all(card[k]==frozen[k] for k in ('synth','params','seed','sourceHash'))
                cards[candidate['role']] = {'synth':candidate['synth'], 'wavSha256':file_hash(path), 'pcmSha256':pcm_hash(path)}
            assert 1 <= len(cards) <= 3
            assert set(expected_history).issubset(roles)
            if source.get('previouslyRatedReference'):
                assert 'previous' in roles
            if source['name']!='die/charm2.wav':
                assert 'original' in roles
            if source['name']=='die/charm2.wav':
                assert roles['previous']['synth']=='Bfxr' and roles['anchor']['synth']=='Transfxr'
            observed.append({'name':source['name'], 'referencePcmSha256':pcm_hash(dest/'target.wav'),
                'newSynth':selected['synth'], 'rawScore':selected['score'],
                'auditionScore':selected['provenance']['auditionMatchObjectiveScore'],
                'accounting':diag['accounting'], 'cards':cards})
    model = coverage_model(root,result['results'],meta)
    page = (root/'index.html').read_text()
    embedded = json.loads(re.search(r'<script type="application/json" id="feedback-data">(.*?)</script>',page,re.S).group(1))
    assert embedded == model
    report = {'complete':True,'experimentId':model['experimentId'], 'reportSha256':file_hash(root/'results.json'),
        'htmlSha256':file_hash(root/'index.html'), 'auditScriptSha256':file_hash(__file__),
        'priorAuditSha256':file_hash(audit_path), 'rawAndRefinedReplays':replay_count, 'targets':observed,
        'scope':'Actual final/raw candidates, exported PCM, trial accounting and exact retained history. Not human quality validation.'}
    Path('tools/multisynth/evaluations/pitch-v4-listening-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'complete':True,'experimentId':model['experimentId'],'replayed':replay_count}),flush=True)


if __name__ == '__main__':
    main()
