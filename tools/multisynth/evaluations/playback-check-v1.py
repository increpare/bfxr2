"""Build a separate click diagnostic without modifying rated audio or pages."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/playback-check-v1'
if ROOT.exists():raise FileExistsError('Preserve existing diagnostic; use a fresh path')
ROOT.mkdir();sr=44100;n=int(sr*1.2);a=np.arange(n)/sr;w=.25*np.sin(2*np.pi*440*a);fade=round(sr*.02)
w[:fade]*=np.linspace(0,1,fade);w[-fade:]*=np.linspace(1,0,fade)
sf.write(ROOT/'tone.wav',w,sr,subtype='PCM_16');assets={}
for dest,src in [('snow-reference.wav','002/target.wav'),('snow-bfxr.wav','002/bfxr.wav'),('snow-whole.wav','002/whole.wav'),('coin-whole.wav','006/whole.wav')]:
 p=BASE/'runs/support-transfer-v1-listening'/src;(ROOT/dest).write_bytes(p.read_bytes())
 assets[dest]=dict(source=str(p),sha256=file_hash(p))
(ROOT/'index.html').write_bytes((BASE/'playback_check.html').read_bytes())
_json_write(ROOT/'provenance.json',dict(purpose='Playback diagnosis only, no model judgments',exactCopies=assets,
 tone=dict(frequencyHz=440,seconds=1.2,peak=.25,edgeFadeSeconds=.02,sampleRate=sr),manualStopReleaseSeconds=.005))
