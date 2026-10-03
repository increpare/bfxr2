"""Independent contour-metric and held-out noise-seed audit of a benchmark.

These are diagnostic measurements, not another learned perceptual verdict.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from match.audio import load_audio
from match.objective import MatchObjective
from .features import VERSION, describe, distances, prepare
from .renderer import Renderer


def seed_sensitivity(renderer, candidate, target_descriptor, seeds):
    scores = []
    for seed in seeds:
        _, wave = renderer.render(candidate['synth'], candidate['params'], seed)
        scores.append(float(distances(target_descriptor, describe(wave)[None])[0]))
    return {'seeds':seeds,'scores':scores,'mean':float(np.mean(scores)),
            'std':float(np.std(scores)), 'range':float(np.ptp(scores))}


def verify_source(source):
    if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("Reference audio changed since benchmark: " + source["path"])


def audit(directory):
    data = json.loads((directory/'results.json').read_text())
    if data['metadata'].get('featureVersion') != VERSION:
        raise ValueError('Feature version changed since benchmark')
    for result in data['results']:
        verify_source(result['source'])
    records = []
    torch.set_num_threads(1)
    with Renderer() as renderer:
        if data['metadata']['sourceHash'] != renderer.inventory['sourceHash']:
            raise ValueError('Synth sources changed since benchmark')
        for result in data['results']:
            target = prepare(load_audio(result['source']['path']))
            objective = MatchObjective(target)
            descriptor = describe(target)
            winner = result['candidates'][0]
            baseline = next((r for r in result['candidates'] if r['synth']=='Bfxr'),None)
            entries = {}
            for label,candidate in [('winner',winner),('bfxr',baseline)]:
                if candidate is None:
                    continue
                _, wave = renderer.render(candidate['synth'],candidate['params'],candidate['seed'])
                entry = {'synth':candidate['synth'],'legacy_contour_distance':objective.score(wave)}
                if candidate['synth'] in ('Bfxr','Footsteppr'):
                    seeds = [candidate['seed'], (candidate['seed']+1009)%2**32, (candidate['seed']+2027)%2**32]
                    entry['noise_seed_sensitivity'] = seed_sensitivity(renderer,candidate,descriptor,seeds)
                entries[label] = entry
            record = {'source':result['source']['name'],**entries}
            records.append(record)
            print(f'{len(records)}/{len(data["results"])} {winner["synth"]}',flush=True)
    paired = [r for r in records if 'bfxr' in r]
    differences = [r['bfxr']['legacy_contour_distance']-r['winner']['legacy_contour_distance'] for r in paired]
    summary = {'targets':len(records), 'legacy_metric_wins':sum(d>1e-5 for d in differences),
               'legacy_metric_ties':sum(abs(d)<=1e-5 for d in differences),
               'legacy_metric_losses':sum(d < -1e-5 for d in differences),
               'median_legacy_winner_distance':float(np.median([r['winner']['legacy_contour_distance'] for r in paired])) if paired else None,
               'median_legacy_bfxr_distance':float(np.median([r['bfxr']['legacy_contour_distance'] for r in paired])) if paired else None}
    output = {'summary':summary,'results':records,
              'interpretation':'Legacy contour metric was not optimized by this run. Agreement is supporting evidence, not human listening validation. Noise audit uses the search seed plus two held-out seeds.'}
    (directory/'audit.json').write_text(json.dumps(output,indent=2)+'\n')
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.directory),indent=2))


if __name__ == '__main__':
    main()
