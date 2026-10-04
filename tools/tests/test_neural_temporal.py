"""Temporal inverse contracts: evidence packing, audible losses and strict artifacts."""
from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest
import torch


def test_packing_preserves_frequency_and_time_and_ignores_peak():
    from neural_invert.temporal import pack_features
    x = torch.arange(4083.).repeat(2, 1)
    relative, absolute, scalars = pack_features(x)
    assert relative.shape == (2, 51, 48)
    assert absolute.shape == (2, 51, 32)
    assert torch.equal(relative[:, :48], x[:, :2304].reshape(2, 48, 48))
    assert torch.equal(relative[:, 48:], x[:, 3840:3984].reshape(2, 3, 48))
    assert torch.equal(absolute[:, :48], x[:, 2304:3840].reshape(2, 48, 32))
    assert torch.equal(absolute[:, 48:], x[:, 3984:4080].reshape(2, 3, 32))
    assert torch.equal(scalars, x[:, [4080, 4082]])
    x[:, 4081] = -9999
    assert all(torch.equal(a, b) for a, b in zip((relative, absolute, scalars), pack_features(x)))


@pytest.fixture(scope='module')
def specs():
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        return deepcopy(renderer.specs)


@pytest.mark.parametrize('encoder_kind', ['temporal', 'flat'])
def test_expert_has_ordered_temporal_evidence_and_no_generator(specs, encoder_kind):
    from neural_invert.temporal import TemporalExpert
    model = TemporalExpert(specs['Bfxr'], modes=4, encoder_kind=encoder_kind).eval()
    x = torch.randn(2, 4083)
    before = model(x)
    x[:, 4081] += 100
    after = model(x)
    assert before['continuous'].shape[:2] == (2, 4)
    assert before['mode_logits'].shape == (2, 4)
    assert torch.equal(before['continuous'], after['continuous'])
    assert all(torch.equal(a,b) for a,b in zip(before['categorical'], after['categorical']))
    assert 'generator' not in before and not any('generator' in name for name, _ in model.named_parameters())
    changed = x.clone(); changed[:, :2304] = x[:, :2304].reshape(2,48,48).flip(-1).flatten(1)
    assert not torch.allclose(model(changed)['continuous'], after['continuous'])


def prediction(spec, params, modes=1):
    from neural_invert.schema import ControlSchema
    schema = ControlSchema(spec)
    unit, categorical = schema.encode(params)
    labels = {'continuous': torch.tensor(unit)[None], 'categorical': torch.tensor(categorical)[None]}
    pred = {'continuous': labels['continuous'][:,None].repeat(1,modes,1).requires_grad_(),
            'categorical': [torch.zeros(1,modes,len(c['values']),requires_grad=True) for c in schema.categorical],
            'mode_logits': torch.zeros(1,modes,requires_grad=True)}
    return pred, labels, schema


@pytest.mark.parametrize('engine', ['Bfxr','Transfxr','Pluckr'])
def test_per_row_energy_matches_acoustic_single_row_without_generator(specs, engine):
    from neural_invert.temporal import acoustic_energy
    from neural_invert.acoustic import acoustic_loss
    spec = specs[engine]
    pred, labels, _ = prediction(spec, spec['defaults'], 4)
    pred['continuous'] = torch.rand_like(pred['continuous'])
    pred['categorical'] = [torch.randn_like(v) for v in pred['categorical']]
    energy = acoustic_energy(pred, labels, spec)
    assert energy.shape == (1,4)
    for mode in range(4):
        old = {'continuous':pred['continuous'][:,mode], 'categorical':[v[:,mode] for v in pred['categorical']],
               'generator':torch.zeros(1,len(spec['presets']))}
        expected = acoustic_loss(old,dict(labels,generator=torch.tensor([0])),spec)-.05*np.log(len(spec['presets']))
        assert float(energy[0,mode]) == pytest.approx(float(expected), abs=2e-6)


def test_inactive_controls_and_physical_octaves(specs):
    from neural_invert.temporal import acoustic_energy
    from match.optimizer import freq_param_from_hz
    params = deepcopy(specs['Bfxr']['defaults'])
    params.update(waveType=2,vibratoDepth=0,pitch_jump_amount=0,pitch_jump_2_amount=0,frequency_start=freq_param_from_hz(220))
    pred,labels,schema=prediction(specs['Bfxr'],params)
    names=[c['name'] for c in schema.continuous]
    base=acoustic_energy(pred,labels,specs['Bfxr'])
    changed=deepcopy({k:v.detach() if isinstance(v,torch.Tensor) else [q.detach() for q in v] for k,v in pred.items()})
    for name in ('squareDuty','dutySweep','vibratoSpeed','pitch_jump_onset_percent','pitch_jump_onset2_percent','pitch_jump_repeat_speed'):
        changed['continuous'][0,0,names.index(name)]=.99
    assert torch.equal(base,acoustic_energy(changed,labels,specs['Bfxr']))
    changed['continuous'][0,0,names.index('frequency_start')]=freq_param_from_hz(440)
    assert acoustic_energy(changed,labels,specs['Bfxr']).item() > base.item()+.99
    for name, octaves in [('Transfxr',7),('Pluckr',4)]:
        pred,labels,schema=prediction(specs[name],specs[name]['defaults'])
        baseline=acoustic_energy(pred,labels,specs[name]).item()
        pitch_indices=[i for i,c in enumerate(schema.continuous) if c['name'] in ('pitch','pitch.start','pitch.end')]
        changed=dict(pred,continuous=pred['continuous'].detach().clone())
        for i in pitch_indices:changed['continuous'][0,0,i] += 1/octaves
        assert acoustic_energy(changed,labels,specs[name]).item() > baseline+.99


def test_mixture_uses_soft_minimum_and_single_mode_has_no_routing_penalty():
    from neural_invert.temporal import mixture_loss
    energy=torch.tensor([[0.,8.],[8.,0.]],requires_grad=True)
    logits=torch.zeros(2,2,requires_grad=True)
    loss,info=mixture_loss(energy,logits)
    assert loss.item()==pytest.approx(.1*np.log(2),abs=1e-6)
    assert loss.item() < energy.mean().item()/10
    assert torch.allclose(info['utilization'],torch.tensor([.5,.5]))
    loss.backward();assert torch.isfinite(energy.grad).all() and torch.isfinite(logits.grad).all()
    single,info=mixture_loss(torch.tensor([[2.],[4.]]),torch.zeros(2,1))
    assert single.item()==3 and info['routingKL'].item()==0


def test_balanced_weights_count_old_and_new_structured_together():
    from neural_invert.temporal import balanced_weights
    rows=[{}, {'origin':'native'}, {'origin':'structured'}, {'structured':True}, {'mode':'structured'}]
    weights=balanced_weights(rows,list(range(5)))
    assert weights[:2].sum().item()==pytest.approx(2.5)
    assert weights[2:].sum().item()==pytest.approx(2.5)
    assert torch.equal(balanced_weights(rows,[0,1]),torch.ones(2))


@pytest.fixture(scope='module')
def trained(tmp_path_factory):
    from neural_invert.data import generate_dataset, file_hash
    from neural_invert.temporal import train_temporal
    root=tmp_path_factory.mktemp('temporal')
    data=root/'data';manifest=generate_dataset(data,per_synth=8,jobs=1,synths=['Bfxr','Pluckr'])
    for name in manifest['engines']:
        path=data/(name+'.json');meta=json.loads(path.read_text())
        for split in ('train','val'):
            for i in meta[split][::2]:meta['rows'][i]['structured']=True
        path.write_text(json.dumps(meta));manifest['files'][name]['metadataSha256']=file_hash(path)
        with np.load(data/(name+'.npz')) as saved:arrays={k:saved[k].copy() for k in saved.files}
        arrays['features'][meta['val']]+=np.float16(2.)
        np.savez_compressed(data/(name+'.npz'),**arrays);manifest['files'][name]['npzSha256']=file_hash(data/(name+'.npz'))
    (data/'manifest.json').write_text(json.dumps(manifest))
    report=train_temporal(data,root/'model',engines=['Bfxr'],epochs=1,device='cpu',batch_size=3)
    return root,report


def test_one_epoch_processes_every_row_global_train_normalization_and_roundtrip(trained):
    from neural_invert.temporal import load_temporal
    root,report=trained
    model,metadata=load_temporal(root/'model'/'Bfxr')
    assert model.encoder_kind=='temporal' and model.modes==1
    training=[]
    for name in ('Bfxr','Pluckr'):
        meta=json.loads((root/'data'/(name+'.json')).read_text())
        with np.load(root/'data'/(name+'.npz')) as saved:training.extend(saved['features'][meta['train']].astype(np.float64))
    np.testing.assert_allclose(metadata['normalization']['mean'],np.mean(training,0),atol=1e-6)
    np.testing.assert_allclose(metadata['normalization']['std'],np.maximum(np.std(training,0),.025),atol=1e-6)
    meta=json.loads((root/'data'/'Bfxr.json').read_text())
    engine=report['perEngine']['Bfxr'];history=engine['history'][0]
    assert history['trainRows']==len(meta['train']) and history['validationRows']==len(meta['val'])
    assert engine['bestEpoch']==1 and np.isfinite(engine['bestValidation']['total'])
    assert engine['checkpointHash']==metadata['checkpointHash']
    assert history['validation']['utilization']==[1.]
    assert metadata['normalization']['engines']==['Bfxr','Pluckr']
    with np.load(root/'data'/'Bfxr.npz') as saved:x=torch.tensor(saved['features'][:1].astype(np.float32))
    checkpoint=torch.load(root/'model'/'Bfxr'/'best.pt',weights_only=True)
    from neural_invert.temporal import TemporalExpert
    other=TemporalExpert(metadata['spec']);other.load_state_dict(checkpoint['model'])
    assert torch.equal(model(x)['continuous'],other(x)['continuous'])


def test_fresh_output_required(tmp_path):
    from neural_invert.temporal import train_temporal
    output=tmp_path/'exists';output.mkdir();(output/'keep').write_text('keep')
    with pytest.raises(FileExistsError):train_temporal(tmp_path/'absent',output,epochs=1)
    assert (output/'keep').read_text()=='keep'


@pytest.mark.parametrize('setting,value',[('modes',2),('epochs',True),('epochs',0),('encoder_kind','other'),('batch_size',1.5),('seed',-1)])
def test_invalid_recipe_does_not_create_output(tmp_path,setting,value):
    from neural_invert.temporal import train_temporal
    with pytest.raises(ValueError):train_temporal(tmp_path/'absent',tmp_path/'output',**{setting:value})
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('field',['missing-report','checkpointHash','recipe','sourceHash','temporalCodeHash','acousticCodeHash','normalization','datasetFiles','splitHash','nonfinite-weights','bestEpoch'])
def test_checkpoint_tampering_rejected_even_when_file_hash_rebound(trained,tmp_path,field):
    from neural_invert.temporal import load_temporal
    import shutil
    root,_=trained;shutil.copytree(root/'model'/'Bfxr',tmp_path/'model')
    path=tmp_path/'model'/'best.pt';reportpath=path.parent/'training.json'
    report=json.loads(reportpath.read_text());checkpoint=torch.load(path,weights_only=True)
    if field=='missing-report':reportpath.unlink()
    elif field=='checkpointHash':report['checkpointHash']='bad'
    elif field=='bestEpoch':report['bestEpoch']=2
    else:
        if field=='recipe':checkpoint['metadata']['trainingRecipe']['epochs']=2
        elif field=='normalization':checkpoint['metadata']['normalization']['std'][0]=0
        elif field=='nonfinite-weights':next(iter(checkpoint['model'].values())).flatten()[0]=float('nan')
        else:checkpoint['metadata'][field]='bad'
        torch.save(checkpoint,path);report['checkpointHash']=hashlib.sha256(path.read_bytes()).hexdigest()
        report['metadata']=checkpoint['metadata']
    if field!='missing-report':reportpath.write_text(json.dumps(report))
    with pytest.raises(ValueError):load_temporal(path)


def test_categorical_beam_ranks_joint_probability_and_keeps_multiple_changes():
    from neural_invert.temporal import categorical_beam
    logits=[torch.tensor([0.,-.1]),torch.tensor([0.,-.2])]
    rows=categorical_beam(logits,4)
    assert [row for row,score in rows]==[[0,0],[1,0],[0,1],[1,1]]
    assert all(rows[i][1]>=rows[i+1][1] for i in range(3))


def test_prediction_uses_defaults_without_generator_sampling(trained):
    from neural_invert.temporal import load_temporal,predict_temporal
    from multisynth.renderer import Renderer
    root,_=trained;model,metadata=load_temporal(root/'model'/'Bfxr')
    with Renderer() as renderer:
        _,wave=renderer.render('Bfxr',renderer.specs['Bfxr']['defaults'],123)
        def forbidden(*args,**kwargs):raise AssertionError('generator sampling is forbidden')
        renderer.sample=forbidden
        rows=predict_temporal(model,metadata,wave,renderer,count=4)
    assert len(rows)==4
    assert len({tuple(row['provenance']['categoricalProposal']) for row in rows})==4
    assert all(row['synth']=='Bfxr' and row['provenance']['neuralRaw'] for row in rows)
    assert all('generator' not in row['provenance'] for row in rows)
    assert all(np.isfinite(row['provenance']['jointLogProbability']) for row in rows)


def test_batched_energies_do_not_mix_active_masks_between_rows(specs):
    from neural_invert.temporal import acoustic_energy
    from neural_invert.acoustic import acoustic_loss
    spec=specs['Transfxr'];params=deepcopy(spec['defaults'])
    params['pitch']={'start':.2,'end':.8,'curve':'Linear'};params['waveTo']=-1
    first,labels,_=prediction(spec,params,4)
    second,other,_=prediction(spec,spec['defaults'],4)
    true={key:torch.cat((labels[key],other[key])) for key in labels}
    pred={'continuous':torch.rand(2,4,labels['continuous'].shape[-1]),
          'categorical':[torch.randn(2,4,v.shape[-1]) for v in first['categorical']]}
    energies=acoustic_energy(pred,true,spec)
    for row in range(2):
        for mode in range(4):
            old={'continuous':pred['continuous'][row:row+1,mode],
                 'categorical':[v[row:row+1,mode] for v in pred['categorical']],
                 'generator':torch.zeros(1,len(spec['presets']))}
            single={key:value[row:row+1] for key,value in true.items()};single['generator']=torch.tensor([0])
            expected=acoustic_loss(old,single,spec)-.05*np.log(len(spec['presets']))
            assert energies[row,mode].item()==pytest.approx(expected.item(),abs=2e-6)


def test_flat_four_mode_train_reload_and_mode_coverage(trained,tmp_path):
    from neural_invert.temporal import train_temporal,load_temporal,predict_temporal
    from multisynth.renderer import Renderer
    root,_=trained
    report=train_temporal(root/'data',tmp_path/'flat',engines=['Bfxr'],epochs=1,modes=4,encoder_kind='flat',device='cpu')
    model,metadata=load_temporal(tmp_path/'flat'/'Bfxr')
    assert model.encoder_kind=='flat' and model.modes==4
    assert len(report['perEngine']['Bfxr']['bestValidation']['utilization'])==4
    with Renderer() as renderer:
        _,wave=renderer.render('Bfxr',renderer.specs['Bfxr']['defaults'],123)
        rows=predict_temporal(model,metadata,wave,renderer,count=4)
    assert {row['provenance']['mode'] for row in rows}=={0,1,2,3}
    assert all(row['provenance']['proposalSource']=='mode-primary' for row in rows)
    assert [row['provenance']['modeProbability'] for row in rows]==sorted([row['provenance']['modeProbability'] for row in rows],reverse=True)


def test_identical_modes_are_deduplicated_then_filled_with_categorical_alternatives(trained):
    from neural_invert.temporal import TemporalExpert,load_temporal,predict_temporal
    from multisynth.renderer import Renderer
    root,_=trained;_,metadata=load_temporal(root/'model'/'Bfxr')
    model=TemporalExpert(metadata['spec'],modes=4)
    metadata=dict(metadata,modes=4)
    with torch.no_grad():
        for p in model.parameters():p.zero_()
    with Renderer() as renderer:
        _,wave=renderer.render('Bfxr',renderer.specs['Bfxr']['defaults'],123)
        rows=predict_temporal(model,metadata,wave,renderer,count=4)
    assert len(rows)==4
    assert len({json.dumps(row['params'],sort_keys=True) for row in rows})==4
    assert [row['provenance']['proposalSource'] for row in rows]==['mode-primary']+['categorical-alternative']*3


def test_dataset_tampering_is_rejected_after_model_report_are_rebound(trained,tmp_path):
    from neural_invert.temporal import load_temporal
    import shutil
    root,_=trained
    shutil.copytree(root/'data',tmp_path/'data');shutil.copytree(root/'model'/'Bfxr',tmp_path/'model')
    path=tmp_path/'model'/'best.pt';checkpoint=torch.load(path,weights_only=True)
    checkpoint['metadata']['datasetPath']=str(tmp_path/'data');torch.save(checkpoint,path)
    reportpath=path.parent/'training.json';report=json.loads(reportpath.read_text())
    report['metadata']=checkpoint['metadata'];report['checkpointHash']=hashlib.sha256(path.read_bytes()).hexdigest()
    reportpath.write_text(json.dumps(report))
    npz=tmp_path/'data'/'Pluckr.npz'
    with npz.open('ab') as handle:handle.write(b'tamper')
    with pytest.raises(ValueError,match='integrity'):load_temporal(path)


@pytest.mark.parametrize('case',['fractional-category','nonfinite-feature','empty-split','overlapping-split','duplicate-controls'])
def test_invalid_normalization_donor_is_rejected_before_output_creation(trained,tmp_path,case):
    from neural_invert.temporal import train_temporal
    from neural_invert.data import file_hash
    import shutil
    root,_=trained;data=tmp_path/'data';shutil.copytree(root/'data',data)
    path=data/'Pluckr.json';meta=json.loads(path.read_text());manifest=json.loads((data/'manifest.json').read_text())
    if case=='empty-split':meta['val']=[]
    elif case=='overlapping-split':meta['val']=meta['train'][:1]
    elif case=='duplicate-controls':meta['rows'][meta['val'][0]]['parameterHash']=meta['rows'][meta['train'][0]]['parameterHash']
    else:
        with np.load(data/'Pluckr.npz') as saved:arrays={key:saved[key].copy() for key in saved.files}
        if case=='fractional-category':arrays['categorical']=arrays['categorical'].astype(np.float32)+.5
        else:arrays['features'][0,0]=np.nan
        np.savez_compressed(data/'Pluckr.npz',**arrays);manifest['files']['Pluckr']['npzSha256']=file_hash(data/'Pluckr.npz')
    path.write_text(json.dumps(meta));manifest['files']['Pluckr']['metadataSha256']=file_hash(path)
    manifest['splits']['Pluckr']={k:meta[k] for k in ('train','val')}
    (data/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):train_temporal(data,tmp_path/'model',engines=['Bfxr'],epochs=1,device='cpu')
    assert not (tmp_path/'model').exists()
