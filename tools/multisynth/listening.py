"""Retain exported listening judgments and exact audition audio outside runs/."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

import numpy as np
import soundfile as sf

from .feedback import feedback_gallery


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retain_feedback(feedback_path, report, output):
    feedback_path, report, output = map(Path, (feedback_path, report, output))
    raw = feedback_path.read_bytes()
    feedback = json.loads(raw)
    if feedback.get('schemaVersion') == 2:
        from .coverage_feedback import retain_coverage_feedback
        return retain_coverage_feedback(feedback_path, report, output)
    results = json.loads((report/'results.json').read_text())
    generated = feedback_gallery(results['results'], results['metadata'])
    model = json.loads(re.search(r'id="feedback-data">(.*?)</script>', generated).group(1))
    if (feedback.get('schemaVersion') != 1 or
            feedback.get('experimentId') != model['experimentId'] or
            feedback.get('provenance') != model['provenance']):
        raise ValueError('Feedback experiment/provenance does not match this report')
    expected = {t['id']: (t, r) for t, r in zip(model['targets'], results['results'])}
    targets, candidates, audio_sources = [], {}, {}
    selected_ratings, bfxr_ratings, previous_ratings, comparisons = [], [], [], Counter()
    previous_comparisons = Counter()
    seen_targets = set()

    def audio(path):
        path = path.resolve()
        if not path.is_relative_to(report.resolve()):
            raise ValueError('Audio path escapes report directory')
        info = sf.info(path)
        if info.subtype != 'PCM_16':
            raise ValueError('Lossless archival currently requires PCM_16 audition WAVs')
        wave, rate = sf.read(path, dtype='int16', always_2d=True)
        pcm_hash = digest(str((rate, wave.shape)).encode() + wave.astype('<i2').tobytes())
        relative = 'audio/'+pcm_hash+'.flac'
        audio_sources.setdefault(relative, (wave, rate))
        return {'file': relative, 'pcmSha256': pcm_hash, 'sampleRate': rate,
                'frames': len(wave), 'channels': wave.shape[1],
                'auditionWavSha256': digest(path.read_bytes())}

    for target in feedback['targets']:
        tid = target.get('id')
        if tid not in expected or tid in seen_targets:
            raise ValueError('Unknown or repeated target identity')
        seen_targets.add(tid)
        original, record = expected[tid]
        if any(target.get(key) != original.get(key) for key in ('name', 'sha256', 'folder')):
            raise ValueError('Target identity differs from report')
        if not isinstance(target.get('note', ''), str):
            raise ValueError('Note must be text')
        retained = {'id': tid, 'source': record['source'], 'note': target.get('note', ''),
                    'referenceAudio': audio(report/record['folder']/'target.wav')}
        roles = ('selected', 'bfxr', 'previous') if 'previous' in original else ('selected', 'bfxr')
        for role in roles:
            observation, identity = target.get(role), original[role]
            if observation is None and identity is None:
                retained[role] = None
                continue
            if not isinstance(observation, dict) or identity is None or any(
                    observation.get(key) != value for key, value in identity.items()):
                raise ValueError('Candidate identity differs from report')
            rating = observation.get('rating')
            if rating is not None and (type(rating) is not int or not 1 <= rating <= 5):
                raise ValueError('Ratings must be integers from 1 to 5 or null')
            cid = identity['id']
            retained[role] = cid
            candidate = (record['previous'] if role == 'previous' else
                         next(c for c in record['candidates'] if c['file'] == identity['file']))
            if cid in candidates:
                if candidates[cid]['rating'] != rating:
                    raise ValueError('Shared candidate has contradictory ratings')
            else:
                candidates[cid] = {**candidate, 'id': cid, 'targetId': tid, 'rating': rating,
                                   'audio': audio(report/record['folder']/candidate['file'])}
            if rating is not None:
                {'selected':selected_ratings, 'bfxr':bfxr_ratings,
                 'previous':previous_ratings}[role].append(rating)
        a, b = (target.get(role) or {} for role in ('selected', 'bfxr'))
        if a.get('rating') is not None and b.get('rating') is not None:
            comparisons['win' if a['rating'] > b['rating'] else
                        'loss' if a['rating'] < b['rating'] else 'tie'] += 1
        old = target.get('previous') or {}
        if a.get('rating') is not None and old.get('rating') is not None:
            previous_comparisons['win' if a['rating'] > old['rating'] else
                                 'loss' if a['rating'] < old['rating'] else 'tie'] += 1
        targets.append(retained)
    summary = {'targets': len(targets),
               'uniqueRatedCandidates': sum(c['rating'] is not None for c in candidates.values()),
               'meanSelectedRating': float(np.mean(selected_ratings)) if selected_ratings else None,
               'meanBfxrRating': float(np.mean(bfxr_ratings)) if bfxr_ratings else None,
               'selectedRatingCounts': dict(sorted(Counter(map(str, selected_ratings)).items())),
               'selectedVersusBfxr': dict(comparisons)}
    if any('previous' in t for t in model['targets']):
        summary.update(meanPreviousRating=float(np.mean(previous_ratings)) if previous_ratings else None,
                       previousRatingCounts=dict(sorted(Counter(map(str, previous_ratings)).items())),
                       selectedVersusPrevious=dict(previous_comparisons))
    manifest = {'schemaVersion': 1, 'experimentId': model['experimentId'],
                'feedbackSha256': digest(raw), 'provenance': model['provenance'],
                'ratingMeaning': 'Human likeness to reference; not a rating of fun or preset quality',
                'audioMeaning': 'Exact decoded PCM from normalized/trimmed audition WAVs, losslessly stored as FLAC',
                'summary': summary, 'targets': targets, 'candidates': list(candidates.values())}
    if output.exists():
        if ((output/'feedback.json').read_bytes() != raw or
                json.loads((output/'manifest.json').read_text()) != manifest):
            raise ValueError('Archive already exists with different data; choose a new directory')
        for relative, (wave, rate) in audio_sources.items():
            saved, saved_rate = sf.read(output/relative, dtype='int16', always_2d=True)
            if saved_rate != rate or not np.array_equal(saved, wave):
                raise ValueError('Existing archive audio failed verification')
        return summary
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.listening-', dir=output.parent))
    try:
        (staging/'audio').mkdir()
        (staging/'feedback.json').write_bytes(raw)
        for relative, (wave, rate) in audio_sources.items():
            sf.write(staging/relative, wave, rate, subtype='PCM_16')
            saved, saved_rate = sf.read(staging/relative, dtype='int16', always_2d=True)
            if saved_rate != rate or not np.array_equal(saved, wave):
                raise ValueError('Lossless archive verification failed')
        (staging/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feedback', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(retain_feedback(args.feedback, args.report, args.output), indent=2))


if __name__ == '__main__':
    main()
