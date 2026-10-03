"""Fit a small regularized preference distance; evaluate by reference group."""
import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from .features import describe, distances
from .gesture import GestureMetric, PRIOR


def grouped_folds(groups, count=5):
    unique = np.unique(groups)
    np.random.default_rng(1729).shuffle(unique)
    for heldout in np.array_split(unique,min(count,len(unique))):
        test = np.isin(groups,heldout)
        yield ~test, test


def fit_weights(differences, preferences, prior=PRIOR):
    """Pair log loss with shrinkage to the gesture prior; no negative distances."""
    if not len(differences):
        return np.array(prior)/np.sum(prior)
    x = torch.tensor(np.asarray(differences),dtype=torch.float64)
    y = torch.tensor(np.sign(preferences),dtype=torch.float64)
    confidence = torch.tensor(np.abs(preferences),dtype=torch.float64)
    base = torch.tensor(prior/np.sum(prior),dtype=torch.float64)
    logits = torch.log(base).clone().requires_grad_(True)
    optimizer = torch.optim.Adam([logits],lr=.04)
    for _ in range(400):
        weights = torch.softmax(logits,dim=0)
        preference_logit = -12*(x@weights)
        loss = (torch.nn.functional.softplus(-y*preference_logit)*confidence).mean()
        # KL keeps small-data fits close to sensible event-shape weights.
        loss = loss + .15*(weights*torch.log(weights/base)).sum()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return torch.softmax(logits,dim=0).detach().numpy()


def training_pairs(archive):
    archive = Path(archive)
    raw = (archive/'manifest.json').read_bytes()
    manifest = json.loads(raw)
    if hashlib.sha256((archive/'feedback.json').read_bytes()).hexdigest() != manifest['feedbackSha256']:
        raise ValueError('Archived feedback checksum mismatch')
    candidates = {c['id']:c for c in manifest['candidates']}
    metric = GestureMetric()
    pairs, preferences, groups, legacy, observations = [],[],[],[],[]

    def descriptor(audio):
        wave, rate = sf.read(archive/audio['file'],dtype='int16',always_2d=True)
        pcm_hash = hashlib.sha256(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
        if pcm_hash != audio['pcmSha256'] or rate != 44100 or wave.shape[1] != 1:
            raise ValueError('Archived audition audio checksum/format mismatch')
        return describe(wave[:,0].astype('float32')/32768)

    for target in manifest['targets']:
        ids = list(dict.fromkeys(target.get(role) for role in ('selected','bfxr','previous')))
        rated = [candidates[cid] for cid in ids if cid in candidates and candidates[cid]['rating'] is not None]
        strict = [(a,b) for a,b in combinations(rated,2) if a['rating'] != b['rating']]
        if not strict:
            continue
        ref = descriptor(target['referenceAudio'])
        descriptors = {c['id']:descriptor(c['audio']) for c in rated}
        for a,b in strict:
            aa, bb = descriptors[a['id']], descriptors[b['id']]
            diff = metric.raw_components(ref,[aa,bb])
            pairs.append(diff[0]-diff[1])
            preferences.append(a['rating']-b['rating'])
            groups.append(target['referenceAudio']['pcmSha256'])
            scores = distances(ref,[aa,bb])
            legacy.append(scores[0]-scores[1])
            observations.append({'target':target['source']['name'],'candidateA':a['id'],'candidateB':b['id'],
                                 'ratingA':a['rating'],'ratingB':b['rating'],
                                 'componentDifference':pairs[-1].tolist()})
    return np.array(pairs),np.array(preferences),np.array(groups),np.array(legacy),observations,manifest


def train(archive, output):
    torch.set_num_threads(1)
    x,y,groups,legacy,observations,manifest = training_pairs(archive)
    if len(np.unique(groups)) < 5:
        raise ValueError('Need at least five distinct strictly rated references for grouped validation')
    predictions = np.empty(len(y))
    folds = []
    for train_rows,test in grouped_folds(groups):
        w = fit_weights(x[train_rows],y[train_rows])
        predictions[test] = x[test]@w
        folds.append({'trainReferences':len(np.unique(groups[train_rows])),
                      'testReferences':len(np.unique(groups[test])),
                      'trainPairs':int(train_rows.sum()),'testPairs':int(test.sum()),
                      'testGroups':np.unique(groups[test]).tolist(),'weights':w.tolist()})
    correct = lambda d: int(np.sum(-np.sign(d) == np.sign(y)))
    fitted = fit_weights(x,y)
    for i,row in enumerate(observations):
        row.update(legacyDifference=float(legacy[i]), priorDifference=float(x[i]@PRIOR),
                   heldOutDifference=float(predictions[i]),fittedDifference=float(x[i]@fitted))
    report = {'feedbackExperimentId':manifest['experimentId'],
              'feedbackSha256':manifest['feedbackSha256'],
              'archiveManifestSha256':hashlib.sha256((Path(archive)/'manifest.json').read_bytes()).hexdigest(),
              'trainingMethod':'Nonnegative pairwise logistic distance with KL shrinkage to gesture prior',
              'strictPreferencePairs':len(y),'ratedCandidatesInArchive':manifest['summary']['uniqueRatedCandidates'],
              'validation':'Five folds grouped by exact reference audition PCM; related takes may remain',
              'legacyCorrect':correct(legacy),'gesturePriorCorrect':correct(x@PRIOR),
              'heldOutFitCorrect':correct(predictions),'trainingFitCorrect':correct(x@fitted),
              'folds':folds,'pairs':observations,
              'limitations':'Preferences among saved finalists do not establish quality of newly generated candidates. Ties and absolute ratings are retained but not used as strict preference labels.'}
    GestureMetric(fitted).save(output,report)
    return {k:v for k,v in report.items() if k not in ('folds','pairs')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(train(args.archive,args.output),indent=2))


if __name__ == '__main__':
    main()
