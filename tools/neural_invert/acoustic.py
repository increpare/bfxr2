"""Explicit acoustic-priority control loss; no surrogate/audio-loss claim.

Known DSP mappings express pitch errors in octaves. Fixed semantic priorities
emphasize temporal/pitch controls, and explicitly inactive controls are masked.
The defaults are recorded in checkpoint metadata; they are not fitted to ratings.
"""
import torch
from torch.nn import functional as F
from .schema import ControlSchema

POLICY={'version':'acoustic-controls-v2','numericWeight':8.,'octaveWeight':1.,
        'categoricalWeight':.2,'generatorWeight':.05,'pitchControlWeight':4.,
        'temporalControlWeight':2.,'otherControlWeight':1.,
        'pitchMappings':{'Bfxr':'log2(3528*(frequency_start^2+.001))',
                         'Transfxr':'log2(40)+7*pitch', 'Pluckr':'log2(55)+4*pitch'},
        'masks':'Bfxr square-only, zero-depth vibrato rate, zero-amount jump onset/repeat; Pluckr motion rate when both tremolo/vibrato are zero and one-string strum; equal-endpoint transition curves; Transfxr disabled morph.'}


def acoustic_loss(prediction,labels,spec):
    schema=ControlSchema(spec)
    names={c['name']:i for i,c in enumerate(schema.continuous)}
    cats={c['name']:i for i,c in enumerate(schema.categorical)}
    true=labels['continuous']; estimated=prediction['continuous']
    mask=torch.ones_like(true)
    def value(name):
        c=schema.continuous[names[name]]
        return true[:,names[name]]*(c['max']-c['min'])+c['min']
    def category(name):
        c=schema.categorical[cats[name]]
        return torch.tensor(c['values'],device=true.device)[labels['categorical'][:,cats[name]]]
    def gate(name,active):
        if name in names:mask[:,names[name]]=active.to(true.dtype)
    if spec['name']=='Bfxr':
        square=category('waveType')==0
        for name in ('squareDuty','dutySweep'):gate(name,square)
        gate('vibratoSpeed',value('vibratoDepth').abs()>1e-6)
        gate('pitch_jump_onset_percent',value('pitch_jump_amount').abs()>1e-6)
        gate('pitch_jump_onset2_percent',value('pitch_jump_2_amount').abs()>1e-6)
        gate('pitch_jump_repeat_speed',(value('pitch_jump_amount').abs()>1e-6)|(value('pitch_jump_2_amount').abs()>1e-6))
    if spec['name']=='Pluckr':
        gate('tremoloRate',(value('tremolo').abs()>1e-6)|(value('vibrato').abs()>1e-6))
        gate('strum',value('strings')>1)
    if spec['name']=='Transfxr':
        morph=category('waveTo')!=-1
        for name in ('morph.start','morph.end'):gate(name,morph)
    weights=[]
    for c in schema.continuous:
        name=c['name'].lower()
        weights.append(4. if any(key in name for key in ('pitch','frequency','vibrato')) else
                       2. if any(key in name for key in ('attack','sustain','decay','duration','release','repeat','strum')) else 1.)
    effective=mask*true.new_tensor(weights)[None]
    numeric=(((estimated-true)**2)*effective).sum()/effective.sum().clamp(min=1)
    octave=[]
    for name in ('frequency_start',) if spec['name']=='Bfxr' else ('pitch.start','pitch.end') if spec['name']=='Transfxr' else ('pitch',) if spec['name']=='Pluckr' else ():
        i=names[name]
        if spec['name']=='Bfxr':
            c=schema.continuous[i];p=estimated[:,i]*(c['max']-c['min'])+c['min'];t=value(name)
            delta=torch.log2((p*p+.001)/(t*t+.001))
            active=~torch.isin(category('waveType'),true.new_tensor([3,5,9]).long())
            octave.append((delta.square()*active).sum()/active.sum().clamp(min=1))
        else:
            c=schema.continuous[i];octave.append(((estimated[:,i]-true[:,i])*(c['max']-c['min'])*(7 if spec['name']=='Transfxr' else 4)).square().mean())
    discrete=[]
    for i,c in enumerate(schema.categorical):
        active=torch.ones(len(true),device=true.device,dtype=torch.bool)
        if c['name'].endswith('.curve'):
            prefix=c['name'][:-6]
            if prefix+'.start' in names:
                active=(value(prefix+'.start')-value(prefix+'.end')).abs()>1e-6
            if spec['name']=='Transfxr' and prefix=='morph':active &= category('waveTo')!=-1
        loss=F.cross_entropy(prediction['categorical'][i],labels['categorical'][:,i],reduction='none')
        if active.any():discrete.append((loss*active).sum()/active.sum())
    zero=numeric.new_zeros(())
    return numeric*8+ (torch.stack(octave).mean() if octave else zero)+\
           (torch.stack(discrete).mean()*.2 if discrete else zero)+F.cross_entropy(prediction['generator'],labels['generator'])*.05
