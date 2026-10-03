"""Inverse retrieval over the separately human-refined Soundboard catalogue."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import torch

from .features import VERSION, describe, distances
from .library import Library
from .renderer import Renderer

REVISION = 'db9f5f8a8bf50b951b44a163dd6685222bfae859'
WORKER = Path(__file__).resolve().parents[1]/'render/soundboard_worker.js'


class BoardRenderer(Renderer):
    def __init__(self,snapshot):
        snapshot=Path(snapshot)
        provenance=json.loads((snapshot/'snapshot.json').read_text())
        if provenance['revision']!=REVISION:
            raise ValueError('Soundboard snapshot revision differs from pinned experiment')
        for name,digest in provenance['files'].items():
            if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Soundboard snapshot changed: '+name)
        self.proc = subprocess.Popen(['node',str(WORKER),str(Path(snapshot).resolve())],
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        self.inventory = self.request(op='inventory')

    def sample(self,verb,index,seed):
        return self.request(op='sample',verb=verb,index=int(index),seed=int(seed))

    def render(self,params,seed=1):
        result = self.request(op='render',params=params,seed=int(seed))
        return result['params'],np.frombuffer(base64.b64decode(result['audio']),dtype='<f4').copy()


def choose_candidates(rows,scores,verb):
    """Global winner is tag-blind; other choices are explicitly coverage probes."""
    ranked = np.argsort(scores,kind='stable')
    chosen = {'automatic':int(ranked[0])}
    used_signatures = {rows[ranked[0]]['signature']}
    for i in ranked:
        if rows[i]['verb']==verb and rows[i]['signature'] not in used_signatures:
            chosen['guided']=int(i)
            used_signatures.add(rows[i]['signature'])
            break
    # Different recipe ingredients, not a nearly identical random take.
    for i in ranked:
        if rows[i]['verb']==verb and rows[i]['signature'] not in used_signatures:
            chosen['diverse']=int(i)
            break
    return chosen


def build(snapshot,output,takes=12,jobs=4):
    if takes<1 or jobs<1:
        raise ValueError('takes and jobs must be positive')
    output=Path(output)
    if output.exists():
        raise ValueError('Use a new library directory; do not overwrite a saved experiment')
    torch.set_num_threads(1)
    with BoardRenderer(snapshot) as renderer:
        inventory=renderer.inventory
    # Reference-fitted templates are useful in the app, but not evidence of
    # general matching. Exclude them from this candidate coverage experiment.
    entries=[e for e in inventory['entries'] if not any('reference_' in r for r in e['references'])]
    excluded=[e for e in inventory['entries'] if e not in entries]
    started=time.monotonic()

    def render_entries(chunk):
        rows,descriptors,failures=[],[],[]
        with BoardRenderer(snapshot) as renderer:
            if renderer.inventory['sourceHash']!=inventory['sourceHash']:
                raise ValueError('Snapshot source changed during build')
            for entry in chunk:
                for take in range(takes):
                    seed=int.from_bytes(hashlib.sha256(f'board-v3:{entry["verb"]}:{entry["index"]}:{take}'.encode()).digest()[:4],'little')
                    try:
                        sampled=renderer.sample(entry['verb'],entry['index'],seed)
                        params,wave=renderer.render(sampled['params'],seed)
                        descriptor=describe(wave)
                    except ValueError as exc:
                        failures.append({'verb':entry['verb'],'entry':entry['index'],'seed':seed,'error':str(exc)})
                        continue
                    rows.append({'synth':'Soundboard','verb':entry['verb'],'entry':entry['index'],
                                 'signature':entry['signature'],'curatedWeight':entry['weight'],
                                 'composite':entry['composite'],'seed':seed,'params':params,
                                 'preset':entry['signature'],'ingredients':sampled['ingredients']})
                    descriptors.append(descriptor)
                print(f'{entry["verb"]} / {entry["signature"]}: {takes} draws',flush=True)
        return rows,descriptors,failures

    rows,descriptors,failures=[],[],[]
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for rr,dd,ff in executor.map(render_entries,[entries[i::jobs] for i in range(jobs)]):
            rows.extend(rr);descriptors.extend(dd);failures.extend(ff)
    metadata={'featureVersion':VERSION,'sourceHash':inventory['sourceHash'],'sourceRevision':REVISION,
              'snapshot':str(Path(snapshot).resolve()),'takesPerEntry':takes,'entries':len(entries),
              'excludedEntries':excluded,'sampling':'Equal draws per surviving catalogue entry; catalogue weights are curation provenance, not likelihood labels',
              'seconds':time.monotonic()-started,'failures':failures}
    library=Library(rows,descriptors,metadata);library.save(output)
    return {'examples':len(rows),'entries':len(entries),'failures':len(failures),'seconds':metadata['seconds']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--takes',type=int,default=12)
    parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    print(json.dumps(build(args.snapshot,args.output,args.takes,args.jobs),indent=2))


if __name__=='__main__':
    main()
