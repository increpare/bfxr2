#!/usr/bin/env python3
"""Check fresh samples against the original measured regions; never refit clusters."""
import argparse
import json
from pathlib import Path
import numpy as np
from analyze import FEATURE_NAMES,extract_features,read_audio,transform,distances

def validate(corpus_directory,sample_directory):
    corpus_directory=Path(corpus_directory);sample_directory=Path(sample_directory)
    report=json.loads((corpus_directory/'analysis.json').read_text())
    samples=json.loads((sample_directory/'samples.json').read_text())
    matrix=[]
    for sound in samples['sounds']:
        features=extract_features(*read_audio(sample_directory/sound['audio']))
        matrix.append([features[n] for n in FEATURE_NAMES])
    x=transform(np.array(matrix),report['scaler']);centers=np.array([g['center'] for g in report['groups']])
    d=np.sqrt(distances(x,centers));predicted=d.argmin(axis=1)
    result={'seed':samples['seed'],'count':len(x),'minimum_rms':min(s['rms'] for s in samples['sounds']),
        'maximum_peak':max(s['peak'] for s in samples['sounds']),'families':[]}
    for group in report['groups']:
        j=group['index'];indices=[i for i,s in enumerate(samples['sounds']) if s['cluster']==j]
        membership=float(np.mean(predicted[indices]==j))
        # A neighboring family may be almost equally close. Keep both strict and
        # tolerant measures so overlap isn't hidden by an invented hard boundary.
        near=float(np.mean(d[indices,j]<=d[indices].min(axis=1)*1.2))
        info={'name':group['name'],'count':len(indices),'closest_family_fraction':membership,'within_20_percent_of_closest':near}
        result['families'].append(info);print(group['name'],round(membership,3),round(near,3),flush=True)
    result['closest_family_fraction']=float(np.mean(predicted==np.array([s['cluster'] for s in samples['sounds']])))
    result['within_20_percent_of_closest']=float(np.mean([d[i,s['cluster']]<=d[i].min()*1.2 for i,s in enumerate(samples['sounds'])]))
    (corpus_directory/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='families'},indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('corpus');parser.add_argument('samples');args=parser.parse_args();validate(args.corpus,args.samples)
