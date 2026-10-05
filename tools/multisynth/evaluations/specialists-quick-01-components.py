"""Describe scorer disagreements without turning correlates into causal claims."""
import json
from pathlib import Path
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.coverage import verify_archived_audio
from neural_invert.data import file_hash, _json_write

BASE = Path('tools/multisynth')
ARCHIVE = BASE/'listening_data/2026-10-05-specialists-quick-01'
OUTPUT = Path(__file__).with_suffix('.json')


def main():
    if OUTPUT.exists():
        raise FileExistsError('Preserve original diagnostic')
    torch.set_num_threads(1)
    manifest = json.loads((ARCHIVE/'manifest.json').read_text())
    review_path = BASE/'evaluations/specialists-quick-01-human-review.json'
    review = json.loads(review_path.read_text())
    assert review['manifestSha256']==file_hash(ARCHIVE/'manifest.json')
    candidates = {c['id']:c for c in manifest['candidates']}
    rows = []
    for target in manifest['targets']:
        verify_archived_audio(ARCHIVE,target['referenceAudio'])
        reference,rate = sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32')
        assert rate==44100
        objective = MatchObjective(reference)
        options = []
        for item in target['candidates']:
            c = candidates[item['id']]
            verify_archived_audio(ARCHIVE,c['audio'])
            wave,rate = sf.read(ARCHIVE/c['audio']['file'],dtype='float32')
            assert rate==44100
            terms = {k:float(v) for k,v in objective.score_components(wave).items()}
            score = float(objective.score_batch([wave])[0])
            assert abs(score-sum(terms.values()))<1e-7
            assert abs(score-c['provenance']['auditionMatchObjective'])<1e-7
            options.append(dict(id=c['id'],role=c['role'],pcmSha256=c['audio']['pcmSha256'],terms=terms,total=score,
                withoutPitchAndVoicing=score-sum(v for k,v in terms.items() if k in ('pitch','voiced_mismatch','pitch_slope','pitch_movement','structure_pitch'))))
        rows.append(dict(name=target['source']['name'],choice=target['choice'],options=options))
    _json_write(OUTPUT,dict(complete=True,scriptSha256=file_hash(__file__),
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),humanReviewSha256=file_hash(review_path),rows=rows,
        interpretation=[
            'The preferred new footstep is better by envelope, coverage, mel and timbre terms, but incurs pitch=1.2568 versus zero for the older option. Removing pitch/voicing contributions changes this pair ordering.',
            'This suggests investigating voicing-confidence and noisy-transient pitch estimates. It does not establish that the pitch estimate is objectively wrong or that pitch should be globally discounted.',
            'The preferred older short burst is worse on coverage, envelope, envelope motion, timbre and mel, but better on voiced mismatch. Pitch is zero on both. The footstep explanation does not resolve this disagreement.',
            'All terms were inspected after human outcomes. These are exploratory diagnostics, not an independently validated new distance, causal experiment, or deployed selection rule.']))


if __name__=='__main__':
    main()
