"""Equal-budget v4/v5 refinement with selection from the same candidate pool."""
from copy import deepcopy
import json

from . import features, perceptual
from .preference import PreferenceMetric
from .refine import distinct_starts, refine


def load_banks(legacy_path,board_path,legacy_source_hash,board_source_hash,legacy_base,board_base):
    import numpy as np
    from .perceptual_library import CachedLibrary, digest
    banks=[];rows=[]
    for path,source,base,backend in [(legacy_path,legacy_source_hash,legacy_base,'legacy'),
                                     (board_path,board_source_hash,board_base,'board')]:
        bank=CachedLibrary.load(path,source_hash=source,base_library_hash=digest(base/'library.json'))
        if bank.metadata.get('subset') or bank.metadata.get('baseDescriptorHash')!=digest(base/'descriptors.npz'):
            raise ValueError('Search requires a complete, unchanged original library')
        banks.append(bank)
        rows.extend(dict(row,backend=backend,sourceHash=source) for row in bank.rows)
    return rows,np.concatenate([bank.descriptors for bank in banks])


class V4Metric:
    def __init__(self,path):
        self.model=PreferenceMetric.load(path)

    def distances(self,target,candidates):
        return self.model.distances(target[:features.DIM],candidates[:,:features.DIM])

    def components(self,target,candidates):
        return self.model.components(target[:features.DIM],candidates[:,:features.DIM])


def candidate_key(row):
    return json.dumps({key:row[key] for key in ('backend','synth','seed','params')},sort_keys=True,separators=(',',':'))


def search_pair(rows,descriptors,reference,metric_v5,metric_v4,render,legacy_specs,board_specs,
                starts=8,budget=64,seed=9182,human_seeds=(),describe_fn=perceptual.describe):
    if starts<1 or budget<0 or not rows or len(rows)!=len(descriptors):
        raise ValueError('Search needs rows, positive starts and nonnegative budget')
    initial=[]
    for name,metric in [('v5',metric_v5),('v4',metric_v4)]:
        scores=metric.distances(reference,descriptors)
        initial.extend((name,deepcopy(rows[i])) for i in distinct_starts(rows,scores,starts))
        initial.extend((name,deepcopy(row)) for row in human_seeds)
    pool={};traces=[]
    for i,(objective,start) in enumerate(initial):
        a,b=(metric_v5,metric_v4) if objective=='v5' else (metric_v4,metric_v5)
        is_board=start['backend']=='board'
        children,trace=refine(start,render,None if is_board else legacy_specs[start['synth']],
                              board_specs if is_board else None,reference,a,b,budget,seed+i*71,
                              describe_fn=describe_fn)
        for child in children:
            child['v5Score']=child['score'] if objective=='v5' else child['otherScore']
            child['v4Score']=child['otherScore'] if objective=='v5' else child['score']
            pool[candidate_key(child)]=child
        traces.append({'objective':objective,'synth':start['synth'],'backend':start['backend'],
                       'preset':start.get('signature',start.get('preset')),
                       'humanSeed':start.get('humanSeed'),**trace})
    return {'pool':list(pool.values()),'traces':traces,'evaluations':len(initial)*budget,
            'choices':{name:min(pool.values(),key=lambda row:row[name+'Score']) for name in ('v5','v4')}}
