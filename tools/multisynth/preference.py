"""Preference-v4: nonnegative auditory + gesture distance, fitted to likeness.

Hyperparameters are fixed before grouped evaluation. Only strict within-session
comparisons are labels; usefulness is never a substitute for likeness. The 20
components retain spectral evolution from auditory-v1 as well as gesture-v2's
coarse event summaries. No additional extractor or DTW is required at search time.
"""
import argparse
from dataclasses import dataclass
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from . import features
from .gesture import NAMES as GESTURE_NAMES, PRIOR as GESTURE_PRIOR, GestureMetric, representation

VERSION = 'preference-v4'
NAMES = tuple('auditory_'+name for name,_,_ in features.BLOCKS) + tuple('gesture_'+name for name in GESTURE_NAMES) + tuple('spectrum_pool_'+str(n) for n in (4,8,16))
# Fixed a priori: auditory .5, gesture .4, coarse full-band spectral evolution .1.
PRIOR = np.r_[np.full(8,.5/8),np.full(9,.4/9),np.full(3,.1/3)]
TEMPERATURE = 4.0
REGULARIZATION = .08
SCALE_FLOOR = .01


class PreferenceMetric:
    names = NAMES
    version = VERSION

    def __init__(self, weights=None, scales=None):
        self.weights = np.asarray(PRIOR if weights is None else weights,dtype=float).copy()
        self.scales = np.asarray(np.ones(len(NAMES)) if scales is None else scales,dtype=float).copy()
        if (self.weights.shape != (len(NAMES),) or self.scales.shape != (len(NAMES),)
                or not np.isfinite(self.weights).all() or not np.isfinite(self.scales).all()
                or np.any(self.weights < 0) or self.weights.sum() <= 0 or np.any(self.scales <= 0)):
            raise ValueError('Preference weights/scales must have 20 finite nonnegative/positive values')
        self.weights /= self.weights.sum()
        self._target = None
        self._target_repr = None

    def prepare(self, target):
        target = np.asarray(target)
        if target.shape != (features.DIM,) or not np.isfinite(target).all():
            raise ValueError('Preference metric requires a finite auditory-v1 target')
        if self._target is None or not np.array_equal(target,self._target):
            self._target = target.copy()
            self._target_repr = representation(target)
            spectrum = target[:1280].reshape(40,32)
            self._target_spectra = [spectrum.reshape(40,n,32//n).mean(axis=-1) for n in (4,8,16)]
        return self

    def raw_components(self, target, candidates):
        self.prepare(target)
        candidates = np.atleast_2d(np.asarray(candidates))
        if candidates.shape[1] != features.DIM or not np.isfinite(candidates).all():
            raise ValueError('Preference metric requires finite auditory-v1 descriptors')
        result = np.empty((len(candidates),len(NAMES)))
        # Avoid large temporary spectral arrays when scoring the full library.
        for start in range(0,len(candidates),512):
            batch = candidates[start:start+512]
            auditory = features.components(self._target,batch)
            gesture = representation(batch)
            spectrum = batch[:,:1280].reshape(-1,40,32)
            pooled = [np.mean(np.abs(spectrum.reshape(-1,40,n,32//n).mean(axis=-1)-ref),axis=(1,2))
                      for n,ref in zip((4,8,16),self._target_spectra)]
            result[start:start+len(batch)] = np.column_stack(
                list(auditory.values()) + [np.mean(np.abs(self._target_repr[k]-gesture[k]),axis=1)
                                           for k in GESTURE_NAMES] + pooled)
        return result

    def distances(self,target,candidates):
        return self.raw_components(target,candidates) @ (self.weights/self.scales)

    def components(self,target,candidates):
        values = self.raw_components(target,candidates)*(self.weights/self.scales)
        return {key:values[:,i] for i,key in enumerate(NAMES)}

    def save(self,path,training=None):
        payload = {'objectiveVersion':VERSION,'baseFeatureVersion':features.VERSION,
                   'components':list(NAMES),'weights':self.weights.tolist(),'scales':self.scales.tolist(),
                   'training':training or {}}
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        Path(path).write_text(json.dumps(payload,indent=2)+'\n')

    @classmethod
    def load(cls,path):
        payload = json.loads(Path(path).read_text())
        if (payload.get('objectiveVersion') != VERSION or payload.get('baseFeatureVersion') != features.VERSION
                or payload.get('components') != list(NAMES)):
            raise ValueError('Incompatible preference model')
        return cls(payload['weights'],payload['scales'])


def reference_weights(groups):
    _,inverse,counts = np.unique(groups,return_inverse=True,return_counts=True)
    weights = 1/counts[inverse]
    return weights/weights.sum()


def grouped_folds(groups,count=5):
    unique = np.unique(groups)
    np.random.default_rng(1729).shuffle(unique)
    for heldout in np.array_split(unique,min(count,len(unique))):
        test = np.isin(groups,heldout)
        yield ~test,test


def fit(differences,preferences,groups):
    """Reference-balanced logistic loss; all normalization uses these rows only."""
    x,y,groups = np.asarray(differences,float),np.asarray(preferences,float),np.asarray(groups)
    if (x.shape != (len(y),len(NAMES)) or len(y) == 0 or len(groups) != len(y)
            or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(y == 0)):
        raise ValueError('Fit requires finite strict preferences and 20 components')
    row_weights = reference_weights(groups)
    scales = np.maximum(np.sqrt(row_weights @ (x*x)),SCALE_FLOOR)
    signed = torch.tensor(TEMPERATURE*np.sign(y)[:,None]*x/scales,dtype=torch.float64)
    row_weights = torch.tensor(row_weights,dtype=torch.float64)
    prior = torch.tensor(PRIOR,dtype=torch.float64)
    logits = torch.log(prior).clone().requires_grad_(True)
    optimizer = torch.optim.Adam([logits],lr=.03)
    # Lower distance is better: positive rating(A)-rating(B) needs negative
    # distance(A)-distance(B). Rating gap magnitude is deliberately unused.
    for _ in range(800):
        weights = torch.softmax(logits,dim=0)
        loss = row_weights @ torch.nn.functional.softplus(signed @ weights)
        loss += REGULARIZATION*torch.sum(weights*torch.log(weights/prior))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return PreferenceMetric(torch.softmax(logits,dim=0).detach().numpy(),scales)



@dataclass
class TrainingData:
    x: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    observations: list
    archives: list
    summary: dict


def _raw_candidates(target,schema):
    if schema >= 2:
        return target.get('candidates',[])
    return [target[role] for role in ('selected','bfxr','previous') if target.get(role)]


def training_pairs(archives):
    """Validate archive bytes/PCM and preserve exact session-local label provenance."""
    from .quick_feedback import validate_choice, choice_counts

    metric = PreferenceMetric()
    waves,descriptors,validated = {},{},set()
    rows,labels,groups,observations,provenance = [],[],[],[],[]
    summary = {'targets':0,'likenessRatings':0,'usefulnessRatings':0,'duplicateAudioAliases':0,
               'conflictingAudioRatingGroups':0,'tiedPairs':0,'duplicateSessionPairs':0,
               'directChoicePairs':0, **choice_counts([])}
    seen_pairs = set()
    scalar_pairs = []
    def read_audio(root,audio):
        path = (root/audio['file']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Archive audio path escapes its archive')
        key = (str(path),audio['pcmSha256'])
        if key not in validated:
            wave,rate = sf.read(path,dtype='int16',always_2d=True)
            pcm = hashlib.sha256(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
            if pcm != audio['pcmSha256'] or rate != 44100 or wave.shape[1] != 1:
                raise ValueError('Archived audition audio checksum/format mismatch')
            waves[pcm] = wave[:,0].astype('float32')/32768
            validated.add(key)
        return audio['pcmSha256']
    def descriptor(pcm):
        if pcm not in descriptors:
            descriptors[pcm] = features.describe(waves[pcm])
        return descriptors[pcm]
    def add_pair(root, manifest, target, ref, a, b, value, source, choice=None):
        key = (manifest['experimentId'],ref,*sorted((a[0],b[0])))
        if key in seen_pairs:
            summary['duplicateSessionPairs'] += 1
            return
        seen_pairs.add(key)
        values = metric.raw_components(descriptor(ref),[descriptor(a[0]),descriptor(b[0])])
        rows.append(values[0]-values[1]);labels.append(value);groups.append(ref)
        observation = {'archive':root.name,'experimentId':manifest['experimentId'],
                       'target':target['source']['name'],'referencePcmSha256':ref,
                       'candidateA':a[1]['id'],'candidateB':b[1]['id'],
                       'candidateAliasesA':a[3],'candidateAliasesB':b[3],
                       'candidatePcmSha256A':a[0],'candidatePcmSha256B':b[0],
                       'likenessA':a[2],'likenessB':b[2],
                       'labelSource':source,'preferenceSign':int(np.sign(value)),
                       'componentDifference':rows[-1].tolist()}
        if choice is not None:
            observation.update(choice=choice, usefulnessA=a[1].get('usefulness'),
                               usefulnessB=b[1].get('usefulness'))
            summary['directChoicePairs'] += 1
        observations.append(observation)

    for archive in archives:
        root = Path(archive)
        manifest_bytes = (root/'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        raw_bytes = (root/'feedback.json').read_bytes()
        sha = hashlib.sha256(raw_bytes).hexdigest()
        if sha != manifest['feedbackSha256']:
            raise ValueError('Archived feedback checksum mismatch')
        raw = json.loads(raw_bytes)
        schema = raw.get('schemaVersion',1)
        if (schema not in (1,2,3) or raw['experimentId'] != manifest['experimentId']
                or manifest.get('schemaVersion',1) != schema):
            raise ValueError('Archived feedback schema/experiment mismatch')
        label = 'likeness' if schema >= 2 else 'rating'
        raw_targets = {t['id']:t for t in raw['targets']}
        candidates = {c['id']:c for c in manifest['candidates']}
        if len(candidates) != len(manifest['candidates']):
            raise ValueError('Duplicate archive candidate identity')
        provenance.append({'archive':root.name,'experimentId':manifest['experimentId'],
                           'schemaVersion':schema,'feedbackSha256':sha,
                           'manifestSha256':hashlib.sha256(manifest_bytes).hexdigest()})
        for target in manifest['targets']:
            summary['targets'] += 1
            ref = read_audio(root,target['referenceAudio'])
            raw_target = raw_targets.get(target['id'])
            if raw_target is None:
                raise ValueError('Archive target missing from raw feedback')
            raw_cs = _raw_candidates(raw_target,schema)
            raw_by_id = {}
            for c in raw_cs:
                value = c.get(label)
                if c['id'] in raw_by_id and raw_by_id[c['id']].get(label) != value:
                    raise ValueError('Conflicting raw feedback aliases')
                raw_by_id[c['id']] = c
            ids = ([c['id'] for c in target['candidates']] if 'candidates' in target else
                   [target[role] for role in ('selected','bfxr','previous') if target.get(role)])
            if schema == 3:
                choice = validate_choice(raw_target.get('choice'), raw_by_id)
                if (('choice' in raw_target) != ('choice' in target)
                        or target.get('choice') != choice):
                    raise ValueError('Archived choice differs from raw feedback')
                validate_choice(choice, ids)
                if choice is not None:
                    summary['choices'] += 1
                    summary['choiceKinds'][choice['kind']] += 1
            else:
                choice = None
            audio_groups, by_id, pcm_aliases = {}, {}, {}
            for cid in dict.fromkeys(ids):
                c = candidates[cid]
                value = c.get(label)
                if cid not in raw_by_id or raw_by_id[cid].get(label) != value:
                    raise ValueError('Archived likeness differs from raw feedback')
                if value is not None and (type(value) is not int or not 1 <= value <= 5):
                    raise ValueError('Invalid likeness rating')
                if schema == 3:
                    usefulness = c.get('usefulness')
                    if raw_by_id[cid].get('usefulness') != usefulness:
                        raise ValueError('Archived usefulness differs from raw feedback')
                    if usefulness is not None and (type(usefulness) is not int or not 1 <= usefulness <= 5):
                        raise ValueError('Invalid usefulness rating')
                pcm = read_audio(root,c['audio'])
                by_id[cid] = (pcm,c,value)
                pcm_aliases.setdefault(pcm,[]).append(cid)
                summary['usefulnessRatings'] += c.get('usefulness') is not None
                if value is None:
                    continue
                summary['likenessRatings'] += 1
                audio_groups.setdefault(pcm,[]).append((c,value))
            if choice is not None and choice['kind'] == 'best':
                winner = choice['preferredCandidateIds'][0]
                heard = choice['auditionedCandidateIds']
                if winner in heard:
                    a = by_id[winner]
                    emitted = {a[0]}
                    for cid in heard:
                        b = by_id[cid]
                        if b[0] in emitted:
                            continue
                        emitted.add(b[0])
                        add_pair(root,manifest,target,ref,(*a,pcm_aliases[a[0]]),
                                 (*b,pcm_aliases[b[0]]),1,'direct-choice',choice)
            rated = []
            for pcm,aliases in audio_groups.items():
                summary['duplicateAudioAliases'] += len(aliases)-1
                if len({value for _,value in aliases}) != 1:
                    summary['conflictingAudioRatingGroups'] += 1
                    continue
                c,value = aliases[0]
                rated.append((pcm,c,value,[a['id'] for a,_ in aliases]))
            for a,b in combinations(rated,2):
                if a[2] == b[2]:
                    summary['tiedPairs'] += 1
                    continue
                scalar_pairs.append((root,manifest,target,ref,a,b,a[2]-b[2]))
    # Explicit heard choices reserve their session/PCM pairs before scalar labels.
    for args in scalar_pairs:
        add_pair(*args,'scalar-rating')
    summary['validatedAudioFiles'] = len(validated)
    summary['uniqueAudioPcm'] = len(waves)
    return TrainingData(np.asarray(rows).reshape(-1,len(NAMES)),np.asarray(labels),np.asarray(groups),
                        observations,provenance,summary)


def score_summary(differences,y,groups):
    correct = (-np.sign(differences) == np.sign(y)).astype(float)
    tied = differences == 0
    return {'correct':int(correct.sum()),'pairs':len(y),'predictionTies':int(tied.sum()),
            'pairAccuracy':float(correct.mean()),
            'referenceBalancedAccuracy':float(reference_weights(groups) @ correct)}


def train(archives,output,report_path=None):
    torch.set_num_threads(1)
    data = training_pairs(archives)
    x,y,groups = data.x,data.y,data.groups
    if len(np.unique(groups)) < 5:
        raise ValueError('Need at least five distinct strictly rated reference PCM groups')
    predictions = np.empty(len(y));fold_ids = np.empty(len(y),int);folds = []
    for index,(tr,te) in enumerate(grouped_folds(groups)):
        model = fit(x[tr],y[tr],groups[tr])
        predictions[te] = x[te] @ (model.weights/model.scales)
        fold_ids[te] = index
        folds.append({'fold':index,'trainGroups':np.unique(groups[tr]).tolist(),
                      'testGroups':np.unique(groups[te]).tolist(),'trainPairs':int(tr.sum()),
                      'testPairs':int(te.sum()),'weights':model.weights.tolist(),'scales':model.scales.tolist(),
                      'score':score_summary(predictions[te],y[te],groups[te])})
    auditory = x[:,:8].sum(axis=1)
    gesture_prior = x[:,8:17] @ GESTURE_PRIOR
    gesture_path = Path(__file__).with_name('models')/'gesture-v2.json'
    gesture = GestureMetric.load(gesture_path)
    gesture_saved = x[:,8:17] @ gesture.weights
    fitted = fit(x,y,groups)
    full_predictions = x @ (fitted.weights/fitted.scales)
    for i,row in enumerate(data.observations):
        row.update(fold=int(fold_ids[i]),heldOutDifference=float(predictions[i]),
                   auditoryDifference=float(auditory[i]),gesturePriorDifference=float(gesture_prior[i]),
                   gestureSavedDifference=float(gesture_saved[i]),fullFitDifference=float(full_predictions[i]))
    scores = {'auditory-v1':score_summary(auditory,y,groups),
              'gesture-prior':score_summary(gesture_prior,y,groups),
              'gesture-v2-frozen':score_summary(gesture_saved,y,groups),
              'preference-v4-held-out':score_summary(predictions,y,groups),
              'preference-v4-full-fit-diagnostic':score_summary(full_predictions,y,groups)}
    report = {'objectiveVersion':VERSION,'archives':data.archives,'archiveSummary':data.summary,
              'strictPreferencePairs':len(y),'referencePcmGroups':len(np.unique(groups)),
              'components':list(NAMES),'hyperparameters':{'temperature':TEMPERATURE,
                  'klRegularization':REGULARIZATION,'scaleFloor':SCALE_FLOOR,'prior':PRIOR.tolist(),
                  'optimizer':'Adam','learningRate':.03,'steps':800,'foldSeed':1729,'folds':5,'fixedBeforeEvaluation':True},
              'method':'Nonnegative simplex distance; reference-balanced strict pair logistic loss; KL to fixed family prior; reference-balanced RMS pair-difference scale learned on training fold only',
              'labelPolicy':'Strict same-session likeness only; rating gap magnitude ignored; equal total weight per exact reference PCM; candidate audio aliases deduplicated; conflicting audio labels excluded; ties retained in archives but not strict training pairs; usefulness unused',
              'validation':'Five folds grouped across every archive by exact reference audition PCM; no pair or scale fitting on held-out reference groups',
              'scores':scores,'folds':folds,'pairs':data.observations,
              'frozenGestureModelSha256':hashlib.sha256(gesture_path.read_bytes()).hexdigest(),
              'limitations':['Saved-finalist ranking is not a prospective test of newly generated sound likeness.',
                             'Exact PCM grouping does not rule out related takes or differently normalized copies.',
                             'Frozen gesture-v2 previously trained on part of these archives; its result is a historical comparator, not independent validation.',
                             'Only one fixed model configuration evaluated; small grouped sample gives uncertain generalization.']}
    summary = {k:v for k,v in report.items() if k not in ('folds','pairs')}
    fitted.save(output,summary)
    if report_path:
        Path(report_path).parent.mkdir(parents=True,exist_ok=True)
        Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives',nargs='+',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args = parser.parse_args()
    report = train(args.archives,args.output,args.report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('folds','pairs')},indent=2))


if __name__ == '__main__':
    main()
