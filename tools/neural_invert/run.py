"""Approximate one SFX with trained experts and export actual DSP audio/controls."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import soundfile as sf
import torch

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from .evaluate import OriginalBfxr, approximate, digest, pitch_summary, serializable
from .experiment import _write_wave,audition_pcm,audition_details
from .predict import load_model


def run(args):
    if args.output.exists():raise ValueError('Use a fresh inference output directory')
    if min(args.starts,args.budget,args.bfxr_budget)<1:raise ValueError('Budgets and starts must be positive')
    torch.set_num_threads(1)
    model,metadata=load_model(args.model)
    wave=prepare_target(args.target)
    args.output.mkdir(parents=True)
    _write_wave(args.output/'target.wav',wave)
    # Score the same PCM reference that is exported for audition.
    wave,rate=sf.read(args.output/'target.wav',dtype='float32')
    if rate!=44100:raise ValueError('Reference sample rate differs')
    started=time.monotonic()
    with Renderer() as renderer,BfxrRenderer(jobs=1) as original_renderer:
        original=OriginalBfxr(args.bfxr_checkpoint,original_renderer)
        result=approximate(model,metadata,wave,renderer,original,args.starts,args.budget,args.bfxr_budget,args.seed)
    matcher_selected=result['selected']
    if args.selector_model:
        from multisynth.features import describe
        from multisynth.preference import PreferenceMetric
        from .selection import select_preferred
        pool=[{**c,'wave':audition_pcm(c['wave'])} for c in result['allRaw']+result['allRefined']+[result['original']]]
        result['selected']=select_preferred(wave,pool,
            PreferenceMetric.load(args.selector_model),describe,digest(args.selector_model))
    info={'complete':True,'modelSha256':metadata['checkpointHash'],'sourceHash':metadata['sourceHash'],
        'modelHeadMode':metadata.get('headMode','generator'),'trainedEngines':metadata['engines'],
        'targetSha256':digest(args.target),'targetPath':str(args.target.resolve()),
        'bfxrCheckpointSha256':digest(args.bfxr_checkpoint),'seed':args.seed,
        'starts':args.starts,'budgetPerStart':args.budget,'bfxrBudget':args.bfxr_budget,
        'selectorModelSha256':digest(args.selector_model) if args.selector_model else None,
        'runCodeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'seconds':time.monotonic()-started}
    report={'metadata':info,'referencePitch':pitch_summary(wave),
        'matcherSelected':serializable(matcher_selected),'failures':result['failures'],
        'evaluations':result['evaluations'],'allRaw':[serializable(c) for c in result['allRaw']]}
    audition_objective=MatchObjective(wave)
    for role in ('raw','neural','selected','original'):
        candidate=result[role]
        report[role]=serializable(candidate)
        if candidate is not None:
            _write_wave(args.output/(role+'.wav'),candidate['wave'],canonical=role=='selected' and bool(args.selector_model))
            report[role]['pitchDiagnostic']=pitch_summary(candidate['wave'])
            report[role]['provenance']={**report[role]['provenance'],**audition_details(args.output/(role+'.wav'),audition_objective)}
    (args.output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=Path)
    for name in ('model','bfxr-checkpoint','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--selector-model',type=Path)
    parser.add_argument('--starts',type=int,default=4);parser.add_argument('--budget',type=int,default=128)
    parser.add_argument('--bfxr-budget',type=int,default=2000);parser.add_argument('--seed',type=int,default=20261006)
    args=parser.parse_args();report=run(args)
    print(json.dumps({'selectedSynth':report['selected']['synth'],'output':str(args.output.resolve()),
                      'seconds':report['metadata']['seconds']},indent=2))


if __name__=='__main__':main()
