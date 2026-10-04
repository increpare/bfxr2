"""Fixed v5 preference fit over auditory-v1 plus waveform-structure-v1.

The extended model and refitted v4 use identical reference-PCM held-out folds.
The saved v4 checkpoint overlaps training labels and is historical only.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match import audio as match_audio, features as match_features
from . import features, gesture, perceptual, preference

VERSION = 'perceptual-v5'
NAMES = preference.NAMES + tuple(name for name,_ in perceptual.EXTRA_BLOCKS)
PRIOR = np.r_[.7*preference.PRIOR,np.full(len(perceptual.EXTRA_BLOCKS),.3/len(perceptual.EXTRA_BLOCKS))]
TEMPERATURE = 4.0
REGULARIZATION = .08
SCALE_FLOOR = .01


def feature_schema_hash():
    schema = {'base':features.VERSION,'version':perceptual.VERSION,'dimension':perceptual.DIM,
              'baseBlocks':features.BLOCKS,'extraBlocks':perceptual.EXTRA_BLOCKS}
    return hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest()


def feature_code_hash():
    # Prefix comparisons depend on gesture/preference and their waveform
    # extractor, so freeze the complete local dependency chain as well.
    dependencies = (features, perceptual, preference, gesture, match_features, match_audio)
    hashes = {module.__name__:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
              for module in dependencies}
    return hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()


class PerceptualMetric:
    names = NAMES
    version = VERSION
    feature_version = perceptual.VERSION

    def __init__(self,weights=None,scales=None):
        self.weights = np.asarray(PRIOR if weights is None else weights,dtype=float).copy()
        self.scales = np.asarray(np.ones(len(NAMES)) if scales is None else scales,dtype=float).copy()
        if (self.weights.shape != (len(NAMES),) or self.scales.shape != (len(NAMES),)
                or not np.isfinite(self.weights).all() or not np.isfinite(self.scales).all()
                or np.any(self.weights < 0) or self.weights.sum() <= 0 or np.any(self.scales <= 0)):
            raise ValueError('Perceptual weights/scales require 30 finite nonnegative/positive values')
        self.weights /= self.weights.sum()
        self._base = preference.PreferenceMetric()

    def raw_components(self,target,candidates):
        target = np.asarray(target)
        candidates = np.atleast_2d(np.asarray(candidates))
        # Validate the complete representation before slicing the old prefix.
        extra = perceptual.extra_components(target,candidates)
        base = self._base.raw_components(target[:features.DIM],candidates[:,:features.DIM])
        return np.column_stack([base,*extra.values()])

    def distances(self,target,candidates):
        return self.raw_components(target,candidates) @ (self.weights/self.scales)

    def components(self,target,candidates):
        values = self.raw_components(target,candidates)*(self.weights/self.scales)
        return {name:values[:,i] for i,name in enumerate(NAMES)}

    def save(self,path,training=None):
        payload = {'objectiveVersion':VERSION,'baseFeatureVersion':features.VERSION,
                   'featureVersion':perceptual.VERSION,'featureDimension':perceptual.DIM,
                   'featureSchemaSha256':feature_schema_hash(),'featureCodeSha256':feature_code_hash(),
                   'components':list(NAMES),'weights':self.weights.tolist(),'scales':self.scales.tolist(),
                   'training':training or {}}
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        Path(path).write_text(json.dumps(payload,indent=2)+'\n')

    @classmethod
    def load(cls,path):
        payload = json.loads(Path(path).read_text())
        expected = {'objectiveVersion':VERSION,'baseFeatureVersion':features.VERSION,
                    'featureVersion':perceptual.VERSION,'featureDimension':perceptual.DIM,
                    'featureSchemaSha256':feature_schema_hash(),'featureCodeSha256':feature_code_hash(),
                    'components':list(NAMES)}
        if any(payload.get(key) != value for key,value in expected.items()):
            raise ValueError('Incompatible perceptual model version/schema/hash')
        return cls(payload['weights'],payload['scales'])


def fit(differences,preferences,groups):
    """Fixed hyperparameters; RMS scales and balancing use only supplied rows."""
    x,y,groups = np.asarray(differences,float),np.asarray(preferences,float),np.asarray(groups)
    if (x.shape != (len(y),len(NAMES)) or len(y) == 0 or groups.shape != y.shape
            or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(y == 0)):
        raise ValueError('Fit requires finite strict preferences and 30 components')
    row_weights = preference.reference_weights(groups)
    scales = np.maximum(np.sqrt(row_weights @ (x*x)),SCALE_FLOOR)
    signed = torch.tensor(TEMPERATURE*np.sign(y)[:,None]*x/scales,dtype=torch.float64)
    row_weights = torch.tensor(row_weights,dtype=torch.float64)
    prior = torch.tensor(PRIOR,dtype=torch.float64)
    logits = torch.log(prior).clone().requires_grad_(True)
    optimizer = torch.optim.Adam([logits],lr=.03)
    for _ in range(800):
        weights = torch.softmax(logits,dim=0)
        loss = row_weights @ torch.nn.functional.softplus(signed @ weights)
        loss += REGULARIZATION*torch.sum(weights*torch.log(weights/prior))
        optimizer.zero_grad(); loss.backward(); optimizer.step()
    return PerceptualMetric(torch.softmax(logits,dim=0).detach().numpy(),scales)


def training_pairs(archives):
    """Augment validated v4 observations, keeping label identities and rows intact."""
    archives = [Path(p) for p in archives]
    data = preference.training_pairs(archives)
    sources = {}
    for root in archives:
        manifest_bytes = (root/'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        key = (root.name,manifest['experimentId'])
        matching = [p for p in data.archives if (p['archive'],p['experimentId']) == key]
        if not matching or any(p['manifestSha256'] != hashlib.sha256(manifest_bytes).hexdigest() for p in matching):
            raise ValueError('Validated manifest changed before feature augmentation')
        if key in sources and sources[key][0].resolve() != root.resolve():
            raise ValueError('Ambiguous archive identity')
        sources[key] = (root,manifest)
    descriptors = {}
    def descriptor(root,audio,expected):
        if audio['pcmSha256'] != expected:
            raise ValueError('Validated observation PCM identity mismatch')
        if expected not in descriptors:
            path = (root/audio['file']).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError('Archive audio path escapes its archive')
            wave,rate = sf.read(path,dtype='int16',always_2d=True)
            digest = hashlib.sha256(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
            if digest != expected or rate != 44100 or wave.shape[1] != 1:
                raise ValueError('Archived audition audio checksum/format mismatch')
            descriptors[expected] = perceptual.describe(wave[:,0].astype('float32')/32768)
        return descriptors[expected]
    extras = []
    for observation in data.observations:
        root,manifest = sources[(observation['archive'],observation['experimentId'])]
        candidates = {c['id']:c for c in manifest['candidates']}
        ref = observation['referencePcmSha256']
        reference = next(t['referenceAudio'] for t in manifest['targets'] if t['referenceAudio']['pcmSha256'] == ref)
        target = descriptor(root,reference,ref)
        pair = [descriptor(root,candidates[observation['candidate'+suffix]]['audio'],
                           observation['candidatePcmSha256'+suffix]) for suffix in ('A','B')]
        values = perceptual.extra_components(target,pair)
        extras.append([value[0]-value[1] for value in values.values()])
    x = np.column_stack([data.x,np.asarray(extras).reshape(-1,len(perceptual.EXTRA_BLOCKS))])
    for row,values in zip(data.observations,x):
        row['componentDifference'] = values.tolist()
    return preference.TrainingData(x,data.y,data.groups,data.observations,data.archives,data.summary)


def train(archives,output,report_path=None,baseline_model=None):
    baseline_path = Path(baseline_model) if baseline_model else Path(__file__).with_name('models')/'preference-v4.json'
    destinations = [Path(output).resolve(),baseline_path.resolve()]
    if report_path: destinations.append(Path(report_path).resolve())
    if len(destinations) != len(set(destinations)):
        raise ValueError('Model, report, and baseline paths must be distinct')
    torch.set_num_threads(1)
    data = training_pairs(archives)
    x,y,groups = data.x,data.y,data.groups
    if len(np.unique(groups)) < 5:
        raise ValueError('Need at least five distinct strictly rated reference PCM groups')
    predictions = np.empty(len(y)); baseline_predictions = np.empty(len(y))
    fold_ids = np.empty(len(y),int); folds = []
    for index,(tr,te) in enumerate(preference.grouped_folds(groups)):
        model = fit(x[tr],y[tr],groups[tr])
        baseline = preference.fit(x[tr,:len(preference.NAMES)],y[tr],groups[tr])
        predictions[te] = x[te] @ (model.weights/model.scales)
        baseline_predictions[te] = x[te,:len(preference.NAMES)] @ (baseline.weights/baseline.scales)
        fold_ids[te] = index
        folds.append({'fold':index,'trainGroups':np.unique(groups[tr]).tolist(),
                      'testGroups':np.unique(groups[te]).tolist(),'trainPairs':int(tr.sum()),
                      'testPairs':int(te.sum()),'weights':model.weights.tolist(),'scales':model.scales.tolist(),
                      'score':preference.score_summary(predictions[te],y[te],groups[te]),
                      'refittedV4':{'weights':baseline.weights.tolist(),'scales':baseline.scales.tolist(),
                                    'score':preference.score_summary(baseline_predictions[te],y[te],groups[te])}})
    frozen = preference.PreferenceMetric.load(baseline_path)
    historical = x[:,:len(preference.NAMES)] @ (frozen.weights/frozen.scales)
    auditory = x[:,:len(features.BLOCKS)].sum(axis=1)
    fitted = fit(x,y,groups)
    full = x @ (fitted.weights/fitted.scales)
    for i,row in enumerate(data.observations):
        row.update(fold=int(fold_ids[i]),preferenceSign=int(np.sign(y[i])),
                   heldOutDifference=float(predictions[i]),refittedV4HeldOutDifference=float(baseline_predictions[i]),
                   auditoryDifference=float(auditory[i]),frozenV4HistoricalDifference=float(historical[i]),
                   fullFitDifference=float(full[i]))
    score_values = {'auditory-v1':auditory,'preference-v4-refitted-held-out':baseline_predictions,
                    'preference-v4-frozen-historical':historical,'perceptual-v5-held-out':predictions,
                    'perceptual-v5-full-fit-diagnostic':full}
    report = {'objectiveVersion':VERSION,'featureVersion':perceptual.VERSION,
              'baseFeatureVersion':features.VERSION,'featureDimension':perceptual.DIM,
              'featureSchemaSha256':feature_schema_hash(),'featureCodeSha256':feature_code_hash(),
              'trainingCodeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'archives':data.archives,'archiveSummary':data.summary,'strictPreferencePairs':len(y),
              'referencePcmGroups':len(np.unique(groups)),'components':list(NAMES),
              'hyperparameters':{'temperature':TEMPERATURE,'klRegularization':REGULARIZATION,
                  'scaleFloor':SCALE_FLOOR,'prior':PRIOR.tolist(),'optimizer':'Adam','learningRate':.03,
                  'steps':800,'foldSeed':1729,'folds':5,'fixedBeforeEvaluation':True},
              'method':'Reference-balanced strict-pair logistic loss; nonnegative simplex distance; KL to fixed prior; training-fold-only reference-balanced RMS pair scales',
              'labelPolicy':'Use validated preference-v4 same-session likeness pairs unchanged; ignore usefulness and rating-gap magnitude',
              'validation':'Identical five reference-PCM-grouped folds for extended v5 and freshly fitted v4; no held-out scale fitting',
              'scores':{name:preference.score_summary(values,y,groups) for name,values in score_values.items()},
              'folds':folds,'pairs':data.observations,
              'fullFitWeights':fitted.weights.tolist(),'fullFitScales':fitted.scales.tolist(),
              'frozenV4ModelSha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
              'limitations':['Saved-finalist ranking is not a prospective test of generated sound quality.',
                             'Synthetic feature diagnostics are not evidence of perceptual improvement.',
                             'Exact PCM grouping does not exclude related takes or differently normalized copies.',
                             'Frozen v4 overlaps these labels and is historical only; the refitted held-out v4 is the fair comparator.',
                             'One fixed configuration; small grouped sample leaves uncertain generalization.']}
    fitted.save(output,{k:v for k,v in report.items() if k not in ('folds','pairs')})
    if report_path:
        Path(report_path).parent.mkdir(parents=True,exist_ok=True)
        Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives',nargs='+',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--baseline-model',type=Path)
    args = parser.parse_args()
    report = train(args.archives,args.output,args.report,args.baseline_model)
    print(json.dumps({k:v for k,v in report.items() if k not in ('folds','pairs')},indent=2))


if __name__ == '__main__':
    main()
