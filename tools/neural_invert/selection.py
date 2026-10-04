"""Optional human-preference reranking, separate from inverse/search quality."""
import numpy as np
from .evaluate import pitch_summary

PITCH_POLICY={'targetVoicedFraction':.75,'candidateVoicedFraction':.6,
              'registerToleranceSemitones':3.,'penaltyPerOctave':.5,
              'maxRegisterErrorOctaves':3.,'lostVoicingPenalty':2.,
              'preferredRegisterErrorOctaves':1.,
              'status':'Fixed experimental safeguard; not fitted to human ratings or validated as a perceptual metric'}


def coarse_pitch_penalty(target,candidate):
    """Allow small detuning; discourage lost voicing or a different register."""
    if target['voicedFraction']<PITCH_POLICY['targetVoicedFraction'] or not target['medianHz']:return 0.
    if candidate['voicedFraction']<PITCH_POLICY['candidateVoicedFraction'] or not candidate['medianHz']:
        return PITCH_POLICY['lostVoicingPenalty']
    octaves=min(PITCH_POLICY['maxRegisterErrorOctaves'],abs(np.log2(candidate['medianHz']/target['medianHz'])))
    return float(max(0.,octaves-PITCH_POLICY['registerToleranceSemitones']/12)*PITCH_POLICY['penaltyPerOctave'])


def select_preferred(wave,rows,metric,describe,model_hash):
    if not rows:raise ValueError('No candidates to rank')
    target=describe(wave)
    distances=np.asarray(metric.distances(target,np.stack([describe(r['wave']) for r in rows])))
    if distances.shape!=(len(rows),) or not np.isfinite(distances).all():
        raise ValueError('Selector must return one finite distance per candidate')
    reference_pitch=pitch_summary(wave)
    candidate_pitch=[pitch_summary(r['wave']) for r in rows]
    penalties=np.asarray([coarse_pitch_penalty(reference_pitch,p) for p in candidate_pitch])
    eligible=np.ones(len(rows),dtype=bool)
    matching=np.zeros(len(rows),dtype=bool)
    if reference_pitch['voicedFraction']>=PITCH_POLICY['targetVoicedFraction'] and reference_pitch['medianHz']:
        matching=np.asarray([p['voicedFraction']>=PITCH_POLICY['candidateVoicedFraction'] and bool(p['medianHz']) and
            abs(np.log2(p['medianHz']/reference_pitch['medianHz']))<=PITCH_POLICY['preferredRegisterErrorOctaves'] for p in candidate_pitch])
        if matching.any():eligible=matching
    ranking=np.where(eligible,distances+penalties,np.inf)
    index=int(ranking.argmin());row=rows[index]
    return {**row,'provenance':{**row.get('provenance',{}),
        'selectionObjective':'experimental-human-preference-rerank',
        'selectorModelSha256':model_hash,'preferenceScore':float(distances[index]),
        'selectionScore':float(distances[index]+penalties[index]),
        'coarsePitchPenalty':float(penalties[index]),'coarsePitchPolicy':PITCH_POLICY.copy(),
        'matchingRegisterCandidates':int(matching.sum()),
        'selectorRanking':[{'synth':r.get('synth'),'seed':r.get('seed'),
            'preferenceScore':float(distances[i]),'coarsePitchPenalty':float(penalties[i]),
            'eligible':bool(eligible[i]),'chosen':i==index} for i,r in enumerate(rows)],
        'poolSize':len(rows),'selectionScope':'raw experts, refined experts and original Bfxr; search score remains MatchObjective'}}
