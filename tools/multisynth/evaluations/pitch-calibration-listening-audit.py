"""Independent actual-audio and feedback-export audit for the short gallery."""
import argparse
import json
from pathlib import Path
import re
import runpy

import numpy as np
import soundfile as sf

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.coverage_feedback import coverage_model
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash
from neural_invert.experiment import audition_pcm
from neural_invert.pitch_calibration import POLICY, select_candidates
from neural_invert.pitch_v5_eval import descriptor_pitch
from neural_invert.pitch_v5_gallery import pcm_hash
from neural_invert.temporal_gallery import backend_provenance

_audit = runpy.run_path(str(Path(__file__).with_name('pitch-calibration-audit.py')))
require, read_wave, evidence, same_candidate = (_audit[k] for k in
    ('require', 'read_wave', 'evidence', 'same_candidate'))


def all_cards(cards):
    for card in cards:
        yield card
        yield from all_cards(card.get('provenance', {}).get('identicalPcmAliases', []))


def check_anchor(card, source, heard_reference):
    provenance = card['provenance']
    root = Path(__file__).resolve().parents[1]/'listening_data'
    archives = [root/name for name in ('2026-10-04-neural-v2-quick-01',
                                       '2026-10-04-temporal-v3-quick-01')]
    for archive in archives:
        data = json.loads((archive/'manifest.json').read_text())
        if data['experimentId'] != provenance['experimentId']:
            continue
        candidate = next(c for c in data['candidates'] if c['id'] == provenance['candidateId'])
        target = next(t for t in data['targets'] if t['source']['sha256'] == source['sha256'])
        require(all(candidate[k] == card[k] for k in ('synth', 'params', 'seed', 'sourceHash')),
                'Historical anchor controls differ from archive')
        require(candidate['id'] in target['choice']['preferredCandidateIds'], 'Anchor was not a human choice')
        require(candidate['audio']['pcmSha256'] == provenance['archivedPcmSha256'] ==
                pcm_hash(archive/candidate['audio']['file']), 'Archive anchor PCM differs')
        require(target['referenceAudio']['pcmSha256'] == heard_reference, 'Anchor reference differs')
        return
    raise ValueError('Unknown historical anchor archive')


def audit_target(path, renderer, original_renderer):
    row = json.loads(path.read_text())
    source, diag = row['source'], row['diagnostics']
    require(file_hash(source['path']) == source['sha256'], 'Reference source changed')
    target_path = path.parent/'target.wav'
    require(file_hash(target_path) == row['referenceAudioSha256'], 'Reference WAV changed')
    target, rate = sf.read(target_path, dtype='float32')
    require(rate == 44100, 'Reference sample rate differs')
    if source['previouslyRatedReference']:
        require(pcm_hash(target_path) == source['archivedReferencePcmSha256'], 'Heard reference changed')
    else:
        require(audio_hash(target) == source['auditionFloat32Sha256'], 'Fresh reference PCM differs')
        require(np.array_equal(target, audition_pcm(prepare_target(source['path']))),
                'Fresh reference preparation differs')
    objective, pitch = MatchObjective(target), descriptor_pitch(target)
    require(pitch == diag['v5TargetPitch'], 'Reference pitch differs')
    originals, accepted = [], []
    for candidate in diag['originals']:
        wave = read_wave(candidate)
        if candidate.get('calibrationCompatible', True):
            params, replay = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
            require(params == candidate['params'], 'Original canonical controls differ')
        else:
            require(candidate['synth'] == 'Bfxr', 'Unexpected incompatible original')
            require(backend_provenance(original_renderer) == diag['originalBackend']['backend'],
                    'Original backend differs')
            replay = original_renderer.render(candidate['params'], seed=candidate['seed'])
        require(np.array_equal(wave, replay), 'Actual original pool replay differs')
        evidence(candidate, wave, pitch, objective)
        originals.append({**candidate, 'wave': wave})
    generated = diag['allRaw']+diag['allRefined']
    require(len(originals) == len(generated)+1 and
            all(same_candidate(a, b) for a, b in zip(originals, generated)),
            'Common original pool differs from raw/refined proposals')
    require(originals[-1]['poolRole'] == 'original-bfxr' and
            originals[-1]['audioHash'] == diag['originalBackend']['actualNativeReplay']['audioHash'],
            'Original Bfxr omitted or replaced')
    require(diag['originalBackend']['declaredBudget'] == 2000 and
            diag['originalBackend']['actualEvaluations'] == originals[-1]['provenance']['evaluations'],
            'Original Bfxr budget provenance differs')
    for engine, status in diag['refinementStatus'].items():
        if status == 'completed':
            require(diag['refinementAttemptsByEngine'][engine] == 384 and
                    sum(a['phase'] == 'refinement-'+engine for a in diag['renderAttempts']) == 384,
                    'Fresh refinement budget differs')
        elif status == 'skipped-no-audible-proposal':
            require(not any(c['synth'] == engine for c in diag['allRaw']), 'Audible engine refinement omitted')
    require(len(diag['calibrations']) == len(originals), 'Missing calibration records')
    journals = [json.loads(Path(p).read_text()) for p in diag['callJournalFiles']]
    require(all(0 <= c['sourceCandidateIndex'] < len(originals) for c in journals),
            'Journal has unknown original identity')
    expected_accepted, extra, failures = {}, 0, 0
    for index, calibration in enumerate(diag['calibrations']):
        require(calibration['sourceCandidateIndex'] == index, 'Calibration source ordering differs')
        attempts = calibration['attempts']
        require(len({a['step'] for a in attempts}) == len(attempts), 'Repeated calibration step')
        count = sum(a['renderCount'] for a in attempts)
        require(count == calibration['additionalRenderCount'] and count <= 3, 'Calibration budget differs')
        extra += count
        calls = [c for c in journals if c['sourceCandidateIndex'] == index]
        compatible = originals[index].get('calibrationCompatible', True)
        require(len(calls) == (1+count if compatible else 0), 'Pitch call journal count differs')
        if compatible:
            require(calls[0]['role'] == 'original_validation' and calls[0]['status'] == 'validated',
                    'Original calibration replay was not validated')
            require(all(calls[0][k] == originals[index][k] for k in ('synth', 'seed', 'audioHash')),
                    'Original call journal identity differs')
        else:
            require(not attempts, 'Incompatible backend received pitch adjustments')
        call_index = 1
        for attempt in attempts:
            require(attempt['renderCount'] == int(attempt['rendered']), 'Attempt accounting differs')
            if not attempt['rendered']:
                require(attempt['reason'] == 'bounds_unchanged', 'Unexplained unrendered proposal')
                continue
            call = calls[call_index]
            call_index += 1
            require(all(call[k] == attempt[k] for k in ('synth', 'seed', 'requestedParams')) and
                    call['renderCount'] == 1, 'Pitch call journal differs')
            require((call['status'] == 'render_error') == (attempt['reason'] == 'render_error'),
                    'Journal failure differs')
            if attempt['reason'] != 'render_error':
                require(all(call[k] == attempt[k] for k in ('canonicalParams', 'audioHash')),
                        'Journal actual result differs')
            try:
                params, wave = renderer.render(attempt['synth'], attempt['requestedParams'], attempt['seed'])
            except (ValueError, RuntimeError, OSError):
                require(attempt['reason'] == 'render_error', 'Unexpected proposal replay failure')
                failures += 1
                continue
            require(attempt['reason'] != 'render_error', 'Recorded failure did not replay')
            require(params == attempt['canonicalParams'] and audio_hash(wave) == attempt['audioHash'],
                    'Proposal actual replay differs')
            if 'waveFile' in attempt:
                require(np.array_equal(wave, read_wave(attempt)), 'Proposal saved WAV differs')
            else:
                artifact = attempt['failureArtifact']
                require(file_hash(artifact['path']) == artifact['sha256'], 'Invalid audio artifact changed')
                require(np.array_equal(wave, np.load(artifact['path'], allow_pickle=False), equal_nan=True),
                        'Invalid audio array differs')
            if 'score' in attempt:
                evidence(attempt, wave, pitch, objective)
            if attempt['accepted']:
                expected_accepted[(index, attempt['step'])] = attempt
    require(extra <= 3*len(originals), 'Gallery pitch budget exceeded')
    require(extra == diag['accounting']['additionalRenderCount'] and
            failures == diag['accounting']['failedRenderCalls'], 'Gallery pitch accounting differs')
    seen = set()
    for candidate in diag['accepted']:
        key = candidate['sourceCandidateIndex'], candidate['calibrationStep']
        require(key in expected_accepted and key not in seen, 'Accepted attempt identity differs')
        attempt = expected_accepted[key]
        require(all(attempt[k] == candidate[k] for k in ('synth', 'seed', 'audioHash')) and
                attempt['canonicalParams'] == candidate['params'], 'Accepted candidate differs')
        wave = read_wave(candidate)
        evidence(candidate, wave, pitch, objective)
        accepted.append({**candidate, 'wave': wave})
        seen.add(key)
    require(seen == set(expected_accepted), 'Accepted pool incomplete')
    actual = select_candidates(originals, accepted, target)
    for key in ('baseline', 'expandedObjective', 'selected'):
        require(same_candidate(actual[key], diag['selection'][key]), 'Selection differs: '+key)
        evidence(diag['selection'][key], actual[key]['wave'], pitch, objective)
    require(actual['eligibility'] == diag['selection']['eligibility'] and
            actual['reason'] == diag['selection']['reason'], 'Selection evidence differs')
    cards = row['candidates']
    require(len(cards) <= 3, 'Too many listening options')
    hashes = [pcm_hash(path.parent/card['file']) for card in cards]
    require(len(set(hashes)) == len(hashes), 'Duplicate audible option')
    for card in all_cards(cards):
        heard, rate = sf.read(path.parent/card['file'], dtype='float32')
        require(rate == 44100, 'Option sample rate differs')
        provenance = card['provenance']
        if 'archivedPcmSha256' in provenance:
            require(pcm_hash(path.parent/card['file']) == provenance['archivedPcmSha256'],
                    'Historical anchor PCM differs')
            check_anchor(card, source, pcm_hash(target_path))
        else:
            role = card['role']
            require(role in ('selected', 'baseline', 'original'), 'Unknown generated option role')
            expected = originals[-1] if role == 'original' else actual[role]
            require(all(expected[k] == card[k] for k in ('synth', 'seed', 'params', 'audioHash')) and
                    np.array_equal(heard, audition_pcm(expected['wave'])),
                    'Audition option differs from its intended actual selection')
            require(card['sourceHash'] == expected.get('renderSourceHash', renderer.inventory['sourceHash']) and
                    provenance['actualRenderAudioHash'] == expected['audioHash'],
                    'Generated option renderer provenance differs')
    if source['name'] == 'die/charm2.wav' and row['display']['included']:
        require({'previous', 'anchor'} <= {c['role'] for c in all_cards(cards)}, 'Missing charm history')
    return dict(folder=row['folder'], name=source['name'], displayed=row['display']['included'],
        originalCount=len(originals), acceptedCount=len(accepted), additionalRenders=extra,
        failedRenderCalls=failures, optionPcmSha256s=hashes,
        **{k: {field: actual[k][field] for field in ('synth', 'score', 'audioHash', 'v5PitchComparison')}
           for k in ('baseline', 'expandedObjective', 'selected')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gallery', type=Path, required=True)
    parser.add_argument('--output', type=Path,
                        default=Path('tools/multisynth/evaluations/pitch-calibration-listening-audit.json'))
    args = parser.parse_args()
    require(not args.output.exists(), 'Audit output must be fresh')
    report_path = args.gallery/'results.json'
    report = json.loads(report_path.read_text())
    meta = report['metadata']
    require(meta['complete'], 'Incomplete gallery')
    require(meta['policy'] == POLICY, 'Gallery calibration policy differs')
    require(json.loads((args.gallery/'manifest.json').read_text()) == meta, 'Gallery manifest differs')
    for group in ('inputBindings', 'outputBindings'):
        for filename, digest in meta[group].items():
            require(file_hash(filename) == digest, 'Bound gallery artifact changed: '+filename)
    for filename, digest in meta['codeHashes'].items():
        require(file_hash(Path(__file__).resolve().parents[2]/filename) == digest,
                'Gallery code changed: '+filename)
    exported = json.loads((args.gallery/'export-audit.json').read_text())
    require(exported['complete'] and exported['reportSha256'] == file_hash(report_path) and
            exported['htmlSha256'] == file_hash(args.gallery/'index.html') and
            exported['manifestSha256'] == file_hash(args.gallery/'manifest.json'),
            'Export audit differs')
    fixed_path = Path(__file__).with_name('pitch-calibration-listening-targets.json')
    fixed = json.loads(fixed_path.read_text())['targets']
    require(file_hash(fixed_path) == meta['targetManifestSha256'], 'Fixed listening manifest differs')
    require(len(meta['targetReports']) == len(fixed) == 5, 'Fixed listening population differs')
    rows, audited_records = [], []
    with Renderer() as renderer, BfxrRenderer(jobs=1) as original:
        require(meta['sourceHash'] == renderer.inventory['sourceHash'], 'Gallery DSP changed')
        for index, (entry, source) in enumerate(zip(meta['targetReports'], fixed)):
            require(file_hash(entry['reportFile']) == entry['reportFileSha256'], 'Target report changed')
            stored = json.loads(Path(entry['reportFile']).read_text())
            require(stored['folder'] == f'{index+1:03d}' and
                    all(stored['source'][k] == value for k, value in source.items()),
                    'Target identity or frozen order changed')
            rows.append(audit_target(Path(entry['reportFile']), renderer, original))
            audited_records.append(stored)
            print(json.dumps({'audited': rows[-1]['name'], 'displayed': rows[-1]['displayed']}), flush=True)
    visible = [r for r in rows if r['displayed']]
    require(0 < len(visible) <= 5 and [r['folder'] for r in visible] ==
            [r['folder'] for r in report['results']], 'Visible report population differs')
    displayed = [r for r in audited_records if r['display']['included']]
    require(displayed == report['results'], 'Exported rows differ from audited target reports')
    page = (args.gallery/'index.html').read_text()
    feedback = json.loads(re.search(r'<script type="application/json" id="feedback-data">(.*?)</script>',
                                   page, re.S).group(1))
    expected_feedback = coverage_model(args.gallery, displayed, meta)
    require(feedback == expected_feedback and exported['experimentId'] == feedback['experimentId'],
            'Feedback identities or complete render provenance differ')
    require([r['folder'] for r in feedback['targets']] == [r['folder'] for r in visible],
            'Feedback population differs')
    for ui, row in zip(feedback['targets'], report['results']):
        require(ui['sha256'] == row['source']['sha256'] and
                ui['referenceAudioSha256'] == file_hash(args.gallery/row['folder']/'target.wav'),
                'Feedback reference differs')
        require([c['audioSha256'] for c in ui['candidates']] ==
                [file_hash(args.gallery/row['folder']/c['file']) for c in row['candidates']],
                'Feedback options differ')
    result = dict(complete=True, scriptSha256=file_hash(__file__),
        coreAuditScriptSha256=file_hash(Path(__file__).with_name('pitch-calibration-audit.py')),
        fixedTargetsSha256=file_hash(fixed_path),
        reportSha256=file_hash(report_path),
        pageSha256=file_hash(args.gallery/'index.html'), experimentId=feedback['experimentId'],
        targets=rows, policy=POLICY,
        scope='Independent exact reference/anchor PCM and actual candidate/attempt replays, '
              'rescoring, selection and exported feedback identities. No auditory quality claim.')
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'complete': True, 'displayed': len(visible), 'experimentId': feedback['experimentId']}))


if __name__ == '__main__':
    main()
