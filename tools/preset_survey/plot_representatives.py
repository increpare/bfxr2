#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze import read_audio

root=Path(sys.argv[1]);report=json.loads((root/'analysis.json').read_text());sounds={s['id']:s for s in report['sounds']}
fig,axes=plt.subplots(4,4,figsize=(16,12),layout='constrained')
for g,ax in zip(report['groups'],axes.flat):
 sound=sounds[g['exemplars'][0]];pcm,rate=read_audio(root/sound['audio'])
 n=2048;hop=256;padded=np.pad(pcm,(0,max(0,n-len(pcm))))
 frames=np.lib.stride_tricks.sliding_window_view(padded,n)[::hop]
 power=abs(np.fft.rfft(frames*np.hanning(n),axis=1))**2
 freq=np.fft.rfftfreq(n,1/rate);t=np.arange(len(frames))*hop/rate
 ax.pcolormesh(t,freq,10*np.log10(np.maximum(power.T,1e-10)),cmap='magma',vmin=-35,vmax=30,shading='auto',rasterized=True)
 ax.set_yscale('log');ax.set_ylim(40,10000);ax.set_xlim(0,max(.1,sound['features']['active_duration']))
 f=sound['features'];ax.set_title(f"{g['index']} · {sound['id']} · n={g['count']}\n{f['pitch_hz']:.0f}Hz / {f['pitch_slope_octaves']:+.1f}oct / tone {f['tonal_concentration']:.2f}",fontsize=10)
 ax.set_xlabel('Seconds');ax.set_ylabel('Hz')
fig.suptitle('Transfxr: central examples of measured audio clusters',fontsize=18)
fig.savefig(root/'representatives.png',dpi=120)
for g in report['groups']:
 sound=sounds[g['exemplars'][0]]
 print(g['index'],sound['id'],json.dumps(sound['params']))
