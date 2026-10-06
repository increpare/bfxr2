"""Controlled native parameter interventions; not an automatic likeness scorer."""
from copy import deepcopy
import math


def control_variants(synth, params, axis):
    """Return two predeclared variants, rejecting clipped or invalid edits.

    Only Transfxr/Pluckr pitch has an exact oscillator-semitone interpretation.
    Transfxr tone shifts filter cutoff; Zappr voltage changes several DSP cues.
    """
    out=[deepcopy(params),deepcopy(params)]
    if synth=='Transfxr' and axis in ('pitch','tone'):
        delta=6/84 if axis=='pitch' else 3/(12*math.log2(160))
        for sign,q in zip((-1,1),out):
            for edge in ('start','end'):
                q[axis][edge]=params[axis][edge]+sign*delta
                _bounded(q[axis][edge])
    else:
        key=(synth,axis)
        if key==('Zappr','voltage'):values=[params[axis]*.5,params[axis]*1.5]
        elif key==('Zappr','spark'):values=[0.,.5]
        elif key==('Squishr','wetness'):values=[.35,.65]
        elif key==('Bfxr','bitCrush'):values=[0.,.6]
        elif key==('Pluckr','pitch'):values=[params[axis]-2/48,params[axis]+2/48]
        else:raise ValueError('Unsupported native intervention')
        _bounded(params[axis])
        for q,value in zip(out,values):
            _bounded(value);q[axis]=value
    return out


def _bounded(value):
    if not math.isfinite(value) or not 0<=value<=1:
        raise ValueError('Intervention exceeds native control range; do not clamp')
