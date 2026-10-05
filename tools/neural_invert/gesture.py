"""Commanded Transfxr pitch motion, excluding DSP smoothing/filtering/echo.

This is supervised control-domain geometry, not a waveform or perceptual model.
"""
import math
import torch
from .schema import ControlSchema

CURVES=('Linear','Ease In','Ease Out','Smooth','Triangle','Pulse','Bounce','Steps')
POLICY=dict(version='transfxr-commanded-gesture-v2',frames=256,octaves=7,
            vibratoOctaves=.16,vibratoHz=8,weight=1.,
            reduction='expected squared octave error over discrete pitch/vibrato curve pairs',
            omissions=['control smoothing','waveform','filter','echo','audibility masking'])


def curve_bank(t, names=CURVES):
    bounce=torch.where(t<1/2.75,7.5625*t*t,
        torch.where(t<2/2.75,7.5625*(t-1.5/2.75).square()+.75,
        torch.where(t<2.5/2.75,7.5625*(t-2.25/2.75).square()+.9375,
                    7.5625*(t-2.625/2.75).square()+.984375)))
    curves=dict(zip(CURVES,(t,t*t,1-(1-t).square(),t*t*(3-2*t),
        1-(2*t-1).abs(),(1-torch.cos(2*math.pi*t))/2,bounce,(t*5).floor().div(4).clamp(max=1))))
    if any(n not in curves for n in names): raise ValueError('Unknown transition curve')
    return torch.stack([curves[n] for n in names])


def gesture_energy(prediction, labels, spec):
    if spec['name']!='Transfxr':raise ValueError('Gesture loss is Transfxr-only')
    schema=ControlSchema(spec)
    names={c['name']:i for i,c in enumerate(schema.continuous)}
    cats={c['name']:i for i,c in enumerate(schema.categorical)}
    unit=prediction['continuous']; truth=labels['continuous'][:,None]
    if unit.ndim!=3 or unit.shape[-1]!=len(schema.continuous):raise ValueError('Invalid controls')
    t=torch.linspace(0,1,POLICY['frames'],device=unit.device,dtype=unit.dtype)
    def value(u,name):
        c=schema.continuous[names[name]]
        return u[...,names[name]]*(c['max']-c['min'])+c['min']
    def transitions(u,name):
        bank=curve_bank(t,schema.categorical[cats[name+'.curve']]['values'])
        start,end=value(u,name+'.start'),value(u,name+'.end')
        return start[...,None,None]+(end-start)[...,None,None]*bank
    pitch=7*transitions(unit,'pitch')
    vibrato=.16*transitions(unit,'vibrato')*torch.sin(16*math.pi*value(unit,'duration')[...,None,None]*t)
    true_pitch=transitions(truth,'pitch')[:,0]
    true_vibrato=transitions(truth,'vibrato')[:,0]
    ids=torch.arange(len(unit),device=unit.device)
    target=7*true_pitch[ids,labels['categorical'][:,cats['pitch.curve']]]
    target=target+.16*true_vibrato[ids,labels['categorical'][:,cats['vibrato.curve']]]*torch.sin(16*math.pi*value(truth,'duration')*t)
    errors=(pitch[:,:,:,None,:]+vibrato[:,:,None,:,:]-target[:,None,None,None,:]).square().mean(-1)
    pitch_prob=prediction['categorical'][cats['pitch.curve']].softmax(-1)
    vibrato_prob=prediction['categorical'][cats['vibrato.curve']].softmax(-1)
    result=(errors*pitch_prob[:,:,:,None]*vibrato_prob[:,:,None,:]).sum((-1,-2))
    if not torch.isfinite(result).all():raise ValueError('Nonfinite trajectory loss')
    return result
