"""Post-hoc target-confidence ablation; no training or listening promotion."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.features import describe
from neural_invert.forward import load_forward, feature_loss, FEATURE_GROUPS
from neural_invert.forward_probe import _loss, _normalization, _fixed_controls
from neural_invert.local_gradient import local_step
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.rendered_gradient import slope
from neural_invert.schema import ControlSchema

OMIT = {'relativePitch', 'absolutePitch', 'combinedVoicing'}
SOURCE = Path('tools/multisynth/runs/rendered-gradient-v1/results.json')
OUTPUT = Path('tools/multisynth/runs/confidence-gradient-v1')


def conditional_loss(loss, reliable):
    if reliable:
        return loss['total']
    kept = [v for k, v in loss['groups'].items() if k not in OMIT]
    assert len(kept) == 6
    return sum(kept)/len(kept)


def summarize(rows, arm):
    def value(c, name):
        return c['featureLoss']['total'] if name == 'fullLoss' else c[name]
    return {name: dict(before=float(np.mean([value(r['before'], name) for r in rows])),
                      after=float(np.mean([value(r['steps'][arm], name) for r in rows])),
                      improvements=sum(value(r['steps'][arm], name) < value(r['before'], name) for r in rows))
            for name in ('fullLoss', 'conditionalLoss', 'objective')}


def run():
    torch.set_num_threads(1)
    source = json.loads(SOURCE.read_text()); assert source['complete']
    for path, digest in source['codeHashes'].items():
        assert file_hash(path) == digest
    model, meta = load_forward('tools/multisynth/runs/forward-audio-pilot-v1/model/Transfxr')
    assert meta['checkpointHash'] == source['checkpointSha256']
    assert meta['normalizationHash'] == source['normalizationHash']
    assert len(source['rows']) == 8 and sum(not r['targetPitch']['reliable'] for r in source['rows']) == 3
    schema = ControlSchema(meta['spec']); mean, std = _normalization(meta, 'cpu')
    model.eval()
    for weight in model.parameters():
        weight.requires_grad_(False)
    OUTPUT.mkdir(exist_ok=False)
    report = dict(complete=False, sourceReportSha256=file_hash(SOURCE), scriptSha256=file_hash(__file__),
                  checkpointSha256=meta['checkpointHash'], normalizationHash=meta['normalizationHash'],
                  omittedGroups=sorted(OMIT), codeHashes=source['codeHashes'],
                  scope='Eight reused development cases; three unreliable targets changed. Post-hoc mechanistic diagnostic, no promotion.', rows=[])
    _json_write(OUTPUT/'results.json', report)
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash'] == meta['sourceHash']
        for old in source['rows']:
            reliable = old['targetPitch']['reliable']; before = old['before']
            p, target = renderer.render('Transfxr', old['targetParams'], old['targetSeed'])
            assert p == old['targetParams'] and audio_hash(target) == old['targetAudioHash']
            assert descriptor_pitch(target) == old['targetPitch']
            features = describe(target); objective = MatchObjective(target)
            normalized = ((torch.tensor(features)-mean)/std)[None]
            unit, cats = schema.encode(before['params'])
            u = torch.tensor(unit[None], requires_grad=True)
            total, groups = feature_loss(model(u, torch.tensor(cats[None], dtype=torch.long)), normalized)
            old_gradient = torch.autograd.grad(total, u, retain_graph=True)[0][0].numpy()
            assert np.array_equal(old_gradient, old['surrogateGradient'])
            if reliable:
                actual, surrogate = old['gradient'], old['surrogateGradient']
            else:
                masked = torch.stack([v for k, v in groups.items() if k not in OMIT]).mean()
                surrogate = torch.autograd.grad(masked, u)[0][0].numpy().tolist()
                actual = []
                for secant in old['secants']:
                    low, high = secant['low'], secant['high']
                    for c in (low, high):
                        assert file_hash(c['waveFile']) == c['waveFileSha256']
                        wave, rate = sf.read(c['waveFile'], dtype='float32')
                        assert rate == 44100 and audio_hash(wave) == c['audioHash']
                        assert _loss(describe(wave), features, meta) == c['featureLoss']
                    actual.append(slope(conditional_loss(low['featureLoss'], False),
                                        conditional_loss(high['featureLoss'], False), low['actualUnit'], high['actualUnit']))
            norm = np.linalg.norm(actual)*np.linalg.norm(surrogate)
            row = dict(id=old['id'], reliable=reliable, before=deepcopy(before), steps={},
                       renderedGradient=list(actual), surrogateGradient=list(surrogate),
                       oldCosine=old['cosineAgreement'], cosine=float(np.dot(actual, surrogate)/norm) if norm else None)
            row['before']['conditionalLoss'] = conditional_loss(before['featureLoss'], reliable)
            for key, c in old['steps'].items():
                row['steps']['original-'+key] = {**c, 'conditionalLoss':conditional_loss(c['featureLoss'], reliable)}
            folder = OUTPUT/old['id']; folder.mkdir()
            for method, gradient in [('rendered', actual), ('surrogate', surrogate)]:
                for radius, direction in ((.001, 1), (.005, 1), (.005, -1)):
                    key = f'{method}-{radius:g}-{direction:+d}'
                    if reliable:
                        row['steps']['conditional-'+key] = deepcopy(row['steps']['original-'+key])
                        continue
                    updated = local_step(unit, gradient, radius, direction)
                    params = deepcopy(before['params'])
                    for control, value in zip(schema.continuous, updated):
                        schema._write(params, control['path'], float(control['min']+value*(control['max']-control['min'])))
                    p, wave = renderer.render('Transfxr', params, before['seed'])
                    _fixed_controls(schema, before['params'], p)
                    path = folder/(key+'.wav'); sf.write(path, wave, 44100, subtype='FLOAT')
                    decoded, rate = sf.read(path, dtype='float32')
                    assert rate == 44100 and np.array_equal(wave, decoded)
                    loss = _loss(describe(wave), features, meta); pitch = descriptor_pitch(wave)
                    row['steps']['conditional-'+key] = dict(params=p, seed=before['seed'],
                        audioHash=audio_hash(wave), waveFile=str(path.resolve()), waveFileSha256=file_hash(path),
                        featureLoss=loss, conditionalLoss=conditional_loss(loss, reliable),
                        objective=float(objective.score_batch([wave])[0]), pitch=pitch,
                        pitchComparison=compare_descriptor_pitch(old['targetPitch'], pitch))
            report['rows'].append(row); _json_write(OUTPUT/'results.json', report)
            print(json.dumps(dict(id=row['id'], reliable=reliable, oldCosine=row['oldCosine'], cosine=row['cosine'])), flush=True)
    report['summaries'] = {group:{arm:summarize(rows, arm) for arm in rows[0]['steps']}
        for group, rows in [('all', report['rows']), ('unreliable', [r for r in report['rows'] if not r['reliable']])]}
    report['complete'] = True; _json_write(OUTPUT/'results.json', report)
    print(json.dumps(report['summaries']['unreliable']), flush=True)


if __name__ == '__main__':
    run()
