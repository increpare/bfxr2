"""Profile tagged reference inputs before calibration outputs exist."""
import json
from pathlib import Path
import soundfile as sf
import torch
from match.audio import prepare_target
from neural_invert.experiment import audition_pcm
from neural_invert.pitch_v5_eval import descriptor_pitch
from neural_invert.pitch_v5_features import FEATURE_CODE_HASH
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash


def main():
    torch.set_num_threads(1)
    root=Path('/Users/stephenlavelle/Documents/bfxr2/tools/targets_non_bfxr_big/tags')
    archives=list(Path('tools/multisynth/listening_data').glob('*/manifest.json'))
    prior={}
    for path in archives:
        for row in json.loads(path.read_text()).get('targets',[]):
            sha=row.get('source',{}).get('sha256')
            if sha:prior.setdefault(sha,[]).append(str(path.parent))
    rows=[];skipped=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.wav','.ogg','.flac','.aif','.aiff'):continue
        try:
            info=sf.info(path)
        except sf.LibsndfileError as error:
            skipped.append({'path':str(path),'sha256':file_hash(path),'reason':'audio decoder rejected file','error':str(error)})
            continue
        if not .12<=info.duration<=2.5:
            skipped.append({'path':str(path),'duration':info.duration,'reason':'outside predeclared .12–2.5 second range'});continue
        wave=audition_pcm(prepare_target(path));pitch=descriptor_pitch(wave)
        sha=file_hash(path)
        rows.append({'name':str(path.relative_to(root)),'path':str(path),'sha256':sha,'tag':path.parent.name,
            'durationSeconds':len(wave)/44100,'auditionFloat32Sha256':audio_hash(wave),
            'priorArchives':prior.get(sha,[]),'pitch':{k:pitch[k] for k in ('medianHz','voicedFraction','voicedFrames','activeFrames','reliable','spanSemitones','startToEndSemitones','direction')},
            'strongPitch':bool(pitch['reliable'] and pitch['voicedFraction']>=.8 and pitch['voicedFrames']>=16)})
    result={'complete':True,'scriptSha256':file_hash(__file__),'featureCodeSha256':FEATURE_CODE_HASH,
        'archiveManifests':{str(p):file_hash(p) for p in archives},'rows':rows,'skipped':skipped,
        'scope':'Input-only tagged reference profile before calibration outputs; no new model output or human label inferred. Strong pitch is a diagnostic inclusion rule, not auditory certainty.'}
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:
        if row['strongPitch']:
            p=row['pitch'];print(row['name'],round(row['durationSeconds'],2),'Hz',round(p['medianHz']), 'span',round(p['spanSemitones'],1),'prior',bool(row['priorArchives']))


if __name__=='__main__':main()
