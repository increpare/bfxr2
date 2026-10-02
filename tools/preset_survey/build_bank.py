#!/usr/bin/env python3
"""Name measured clusters, ship their exemplars, and build an audition catalogue."""
import argparse
import json
import wave
from pathlib import Path
import numpy as np

NAMES = [
 ('Bright Whistles','Clear high voices: whistles, chirps and thin ringing tones.'),
 ('Grainy Taps','Quick textured attacks: part note, part rough little rustle.'),
 ('Rocket Zips','Fast pitch climbs spanning several octaves.'),
 ('Wavering Calls','Round, sustained electronic calls with changing pitch and tone.'),
 ('Fuzzy Chirps','Brief bright fragments with a noisy or grainy coating.'),
 ('Bass Plucks','Low rounded notes with a quick onset and a soft tail.'),
 ('Soft Pips','Small rounded notes with a short, gentle envelope.'),
 ('Sand Sprays','Bright, breathy bursts with little stable pitch.'),
 ('Air Currents','Longer moving washes of filtered air and resonant noise.'),
 ('Submarine Calls','Deep sustained tones with a subdued upper edge.'),
 ('Descending Sweeps','Electronic tails that slide down in pitch or darken through a falling filter.'),
 ('Rising Bloops','Rounded upward sweeps, from small burbles to rising calls.'),
 ('Rubber Clicks','Short low pips, bouncy ticks and cushioned little clicks.'),
 ('Falling Thumps','Low falling notes and resonant groans with a quick attack.'),
 ('Reverse Bloops','Soft notes that swell towards their ending.'),
 ('Static Flecks','Very short airy flicks and fragments of static.')
]

HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Transfxr sound survey</title><style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#131818;color:#e5e4da}body{margin:0 auto;max-width:1250px;padding:30px}h1{font-size:34px;margin-bottom:8px}p{color:#b8c3bc;line-height:1.5}a{color:#a9e4c2}button,select,input{font:inherit;color:inherit;background:#23322d;border:1px solid #465a50;border-radius:5px;padding:8px}button{cursor:pointer}button:hover{background:#385a47}header{margin-bottom:24px}.stats{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.stat{background:#1d2a24;padding:15px 22px;border-radius:6px}.stat b{display:block;font-size:26px;color:#a9e4c2}.toolbar{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#131818;padding:12px 0;z-index:2}.toolbar input{flex:1;min-width:180px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(265px,1fr));gap:14px}.card{background:#1b2420;border:1px solid #344a3d;border-radius:8px;padding:16px}.card h2{font-size:19px;margin:2px 0 6px}.card p{font-size:13px;min-height:44px}.meta{font-size:12px;color:#a1b3a6}.card .buttons{display:flex;gap:8px;margin-top:12px}.section{margin-top:36px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:10px 6px;border-bottom:1px solid #344a3d}th{color:#b3cdbb}.player{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:12px;background:#243b2e;border-radius:6px;margin:18px 0}.player audio{height:34px;flex:1;min-width:220px}#status{min-height:20px}.active{outline:2px solid #a9e4c2}svg{width:100%;height:90px}.method{font-size:13px;max-width:950px}details{margin-top:24px}summary{cursor:pointer}.badge{font-size:11px;color:#a9e4c2;border:1px solid #52745e;padding:2px 5px;border-radius:3px}#listnote{margin:8px 0}
</style><body><header><h1>Transfxr: a wider palette</h1><p>512 rendered sounds, grouped by measured audio. Explore a family, compare its members, or send any sound back to the synth.</p>
<div class="stats"><div class="stat"><b>512</b>audible sounds</div><div class="stat"><b>16</b>named families</div><div class="stat"><b id="prototypeCount"></b>shipped exemplars</div><div class="stat"><b>4</b>audio feature groups</div></div>
<p class="method">These names describe measured sound profiles and are open to revision by ear. Similar families overlap; clustering is a way to organize this continuous sound space, not an objective list of sound types. Every sound below is available to audition.</p><button id="tour">Tour all 16 families</button> <a href="families_showcase.wav" download>Download the family reel</a></header>
<div class="player"><strong id="now">Choose a sound</strong><audio id="audio" controls preload="none"></audio><a id="edit" hidden target="_blank">Open in synth ↗</a></div><div id="status"></div>
<div class="toolbar"><input id="query" aria-label="Search sounds and families" placeholder="Search families or sound IDs…"><select id="family" aria-label="Filter by family"><option value="">All families</option></select><select id="sort" aria-label="Sort sounds"><option value="central">Closest to family center</option><option value="edge">Boundary examples</option><option value="duration">Shortest first</option><option value="pitch">Lowest pitch first</option></select><button id="stop">Stop</button></div>
<div class="grid" id="families"></div><section class="section"><h2 id="listTitle">All survey sounds</h2><p id="listnote"></p><table><thead><tr><th>Sound</th><th>Family</th><th>Active time</th><th>Dominant tone</th><th>Tone movement</th><th></th></tr></thead><tbody id="sounds"></tbody></table><button id="more" hidden>Show 80 more</button></section>
<details><summary>Method, coverage and reproducibility</summary><p class="method">Sampling used seed 20261002: 75% broad exploration and 25% substantial variations around the original eight recipes. The analysis uses audible duration, envelope shape, dominant-tone trajectory, spectral distribution and timbre motion, with equal weight for the four feature groups. A dominant tone can be the filter resonance rather than the oscillator fundamental. K-means++ was run with 12 restarts for 8, 10, 12, 14 and 16 groups. Sixteen groups give a usable fine-grained palette; average silhouette is __SILHOUETTE__, so boundary cases are expected. Families retain central and diverse measured exemplars with an audibility margin. Repeat clicks choose a whole exemplar, interpolate compatible states, and make small correlated changes. The runtime sampler contains no clustering dependencies.</p><p id="validation"></p><p><a href="README.md">Reproduce the survey</a> · <a href="analysis.json">Full measured analysis</a> · <a href="corpus.json">Seeded corpus and parameters</a> · <a href="Families.bcol" download>Editable family exemplars</a> · <a href="validation.json">Fresh variation checks</a></p></details>
<script>const DATA=__DATA__;
const audio=document.getElementById('audio'),now=document.getElementById('now'),edit=document.getElementById('edit');
let offset=80,filtered=[],reelToken=0;
const byId=new Map(DATA.sounds.map(s=>[s.id,s]));
function importLink(s){const serialized='Transfxr~@2~'+JSON.stringify({filename:s.id,params:s.params}).replace(/~/g,'\\u007e');return '../../../index.html?sfx='+encodeURIComponent(serialized);}
function play(id){const s=byId.get(id);reelToken++;now.textContent=s.id+' · '+DATA.groups[s.cluster].name;audio.src=s.audio;edit.href=importLink(s);edit.hidden=false;audio.play().catch(error=>document.getElementById('status').textContent=error.message);}
function sequence(ids){const token=++reelToken;let index=0;function next(){if(token!==reelToken||index>=ids.length){audio.onended=null;return;}const s=byId.get(ids[index++]);now.textContent=s.id+' · '+DATA.groups[s.cluster].name+' ('+index+'/'+ids.length+')';audio.src=s.audio;edit.href=importLink(s);edit.hidden=false;audio.onended=next;audio.play().catch(()=>{});}next();}
function profile(g){const points=g.profile.map((value,i)=>`${i/31*250},${85-value*70}`).join(' ');return `<svg viewBox="0 0 250 90" aria-label="Median loudness profile"><path d="M0 85H250" stroke="#41574a"/><polyline points="${points}" fill="none" stroke="#a9e4c2" stroke-width="2"/></svg>`;}
function render(){const query=document.getElementById('query').value.toLowerCase(),family=document.getElementById('family').value;
 const groups=DATA.groups.filter(g=>(family===''||g.index===+family)&&(!query||(g.name+' '+g.tip).toLowerCase().includes(query)));
 document.getElementById('families').innerHTML=groups.map(g=>`<article class="card"><h2>${g.name}</h2><p>${g.tip}</p>${profile(g)}<div class="meta">${g.count} sounds · ${g.summary.active_duration.toFixed(2)} s median · ${g.exemplars.length} exemplars</div><div class="buttons"><button data-play="${g.exemplars[0]}">Play center</button><button data-sequence="${g.index}">Hear 6 variants</button><button data-family="${g.index}">Explore</button></div></article>`).join('');
 filtered=DATA.sounds.filter(s=>(family===''||s.cluster===+family)&&(!query||(s.id+' '+DATA.groups[s.cluster].name+' '+DATA.groups[s.cluster].tip).toLowerCase().includes(query)));
 const sort=document.getElementById('sort').value;filtered.sort((a,b)=>sort==='edge'?b.distance-a.distance:sort==='duration'?a.features.active_duration-b.features.active_duration:sort==='pitch'?a.features.pitch_hz-b.features.pitch_hz:a.distance-b.distance);
 document.getElementById('sounds').innerHTML=filtered.slice(0,offset).map(s=>`<tr><td>${s.id} ${DATA.groups[s.cluster].exemplars.includes(s.id)?'<span class="badge">exemplar</span>':''}</td><td>${DATA.groups[s.cluster].name}</td><td>${s.features.active_duration.toFixed(2)} s</td><td>${s.features.pitch_hz?Math.round(s.features.pitch_hz)+' Hz':'unpitched'}</td><td>${s.features.pitch_slope_octaves.toFixed(1)} oct</td><td><button data-play="${s.id}">Play</button> <a target="_blank" href="${importLink(s)}">Edit ↗</a></td></tr>`).join('');
 document.getElementById('listnote').textContent=`Showing ${Math.min(offset,filtered.length)} of ${filtered.length} matching sounds. “Boundary examples” helps check ambiguous categories.`;
 document.getElementById('more').hidden=offset>=filtered.length;
}
for(const g of DATA.groups){const o=document.createElement('option');o.value=g.index;o.textContent=g.name;document.getElementById('family').appendChild(o);}
document.getElementById('prototypeCount').textContent=DATA.groups.reduce((n,g)=>n+g.exemplars.length,0);
if(DATA.validation){const v=DATA.validation;document.getElementById('validation').textContent=`Fresh variation check: ${v.count} audible, unclipped samples; ${Math.round(v.closest_family_fraction*100)}% closest to the intended family and ${Math.round(v.within_20_percent_of_closest*100)}% within 20% of the closest-family distance. This checks measured resemblance, not aesthetic quality.`;}
for(const id of ['query','family','sort'])document.getElementById(id).addEventListener(id==='query'?'input':'change',()=>{offset=80;render();});
document.addEventListener('click',event=>{const b=event.target.closest('button');if(!b)return;if(b.dataset.play)play(b.dataset.play);if(b.dataset.sequence){const g=DATA.groups[+b.dataset.sequence];sequence(g.exemplars.slice(0,6));}if(b.dataset.family){document.getElementById('family').value=b.dataset.family;offset=80;render();}if(b.id==='more'){offset+=80;render();}if(b.id==='tour')sequence(DATA.groups.map(g=>g.exemplars[0]));if(b.id==='stop'){reelToken++;audio.pause();audio.onended=null;}});
render();
</script></body></html>'''

def build(directory, bank_path):
    directory=Path(directory);report=json.loads((directory/'analysis.json').read_text());sounds={s['id']:s for s in report['sounds']}
    medoids=['T298','T248','T035','T181','T022','T497','T342','T479','T452','T274','T071','T361','T362','T481','T502','T228']
    if report['chosen_k']!=16 or [g['exemplars'][0] for g in report['groups']]!=medoids:
        raise ValueError('Labels were authored for this exact clustering; inspect and rename before rebuilding')
    bank=[];files=[]
    for group,(name,tip) in zip(report['groups'],NAMES):
        group.update(name=name,tip=tip,id=name.lower().replace(' ','_'))
        # Reserve headroom above the survey's audibility floor for filter/pitch
        # variation. Keep rejected exemplars visible in the complete catalogue.
        excluded=[id for id in group['exemplars'] if sounds[id]['rms']<.009]
        group['excluded_exemplars']=sorted(set(group.get('excluded_exemplars',[])+excluded))
        group['exemplars']=[id for id in group['exemplars'] if id not in excluded]
        exemplars=[sounds[id]['params'] for id in group['exemplars']]
        bank.append({'id':group['id'],'name':name,'tip':tip,'source_ids':group['exemplars'],'exemplars':exemplars})
        # Median time-normalized energy silhouette used in the catalogue cards.
        envelopes=[]
        from analyze import read_audio
        for id in group['members']:
            sound=sounds[id];pcm,rate=read_audio(directory/sound['audio'])
            end=max(1,int(sound['features']['active_duration']*rate));pcm=pcm[:end]
            parts=np.array_split(pcm,32);env=np.array([np.sqrt(np.mean(p**2)) if len(p) else 0 for p in parts])
            envelopes.append(env/max(1e-12,env.max()))
        group['profile']=np.median(envelopes,axis=0).round(4).tolist()
        for i,id in enumerate(group['exemplars']):
            params=json.dumps(sounds[id]['params'],separators=(',',':'))
            files.append([group['id']+'_'+id,params,params])
    Path(bank_path).write_text('// Generated from the seeded 512-sound audio survey. See tools/preset_survey.\nconst TRANSFXR_PRESET_FAMILIES = '+json.dumps(bank,separators=(',',':'))+';\n')
    (directory/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    # One exact center from every family, with a quarter-second gap.
    frames=[];reel=[];offset=0
    for group in report['groups']:
        sound=sounds[group['exemplars'][0]]
        with wave.open(str(directory/sound['audio']),'rb') as source:
            pcm=source.readframes(source.getnframes());duration=source.getnframes()/44100
        reel.append({'id':sound['id'],'family':group['name'],'start':offset,'duration':duration})
        frames.extend([pcm,b'\x00\x00'*11025]);offset+=duration+.25
    with wave.open(str(directory/'families_showcase.wav'),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(44100);output.writeframes(b''.join(frames))
    (directory/'showcase.json').write_text(json.dumps(reel,indent=2)+'\n')
    if (directory/'validation.json').exists():report['validation']=json.loads((directory/'validation.json').read_text())
    data=json.dumps(report,separators=(',',':')).replace('</','<\\/')
    score=next(t['silhouette'] for t in report['trials'] if t['k']==report['chosen_k'])
    (directory/'index.html').write_text(HTML.replace('__DATA__',data).replace('__SILHOUETTE__',f'{score:.3f}'))
    keys=list(next(iter(sounds.values()))['params']);locks={key:key=='masterVolume' for key in keys}
    collection={'Transfxr':{'files':files,'selected_file_index':0,'create_new_sound':True,'play_on_change':True,'locked_params':locks},'active_tab_index':2}
    (directory/'Families.bcol').write_text(json.dumps(collection,indent=2)+'\n')
    print('Shipped',len(bank),'families with',sum(len(f['exemplars']) for f in bank),'exemplars')
    rows='\n'.join(f"| {g['name']} | {g['count']} | {len(g['exemplars'])} | {g['tip']} |" for g in report['groups'])
    checks=report.get('validation')
    verification='' if not checks else f"\nThe separate seed {checks['seed']} produced {checks['count']} audible, unclipped fresh samples (minimum RMS {checks['minimum_rms']:.4f}, maximum peak {checks['maximum_peak']:.3f}). {checks['closest_family_fraction']:.1%} were closest to their intended family; {checks['within_20_percent_of_closest']:.1%} were within 20% of the nearest-family distance. These are feature-space checks, not listening scores. Per-family results are in [validation.json](validation.json).\n"
    (directory/'README.md').write_text(f'''# Transfxr sound survey

[Open the listening catalogue](index.html). It includes all 512 sounds, family filters, central and boundary examples, six-exemplar comparisons, a tour of the centers, and links to edit exact sounds in Transfxr. [Families.bcol](Families.bcol) imports the shipped exemplars. [families_showcase.wav](families_showcase.wav) plays one center from each family in the table order; [showcase.json](showcase.json) records timestamps.

The 16 buttons in Transfxr use {sum(len(f['exemplars']) for f in bank)} complete sound exemplars. Repeated clicks change timbre, timing and trajectory as well as pitch. A compatible partner must share the oscillator and every curve shape; small correlated variations move both endpoints together. Dry exemplars stay dry. Locks protect entire transition rows and scalar controls.

| Family | Survey sounds | Shipped exemplars | Character |
| --- | ---: | ---: | --- |
{rows}

## Method and limits

The deterministic seed 20261002 supplies 512 proposals: 75% explore broad parameter combinations and 25% vary neighborhoods of the original eight recipes. Every proposal passes through the editor's parameter validation before rendering at 44.1 kHz. The survey rejects nonfinite/clipped outputs and RMS below 0.004; all 512 normalized proposals were accepted.

NumPy extracts 25 audio features in four equally weighted groups: envelope/time, spectral timbre, timbre motion and dominant-tone motion. Features use robust scaling and clipping. The tone estimate follows a strong spectral peak and may reflect filter resonance, not the oscillator fundamental; noisier frames are marked unvoiced.

K-means++ compares 8, 10, 12, 14 and 16 groups with 12 seeded restarts each. Selection chooses the finest result with at least 12 members per group and average silhouette within 0.04 of the best eligible score. This run selects 16 groups (silhouette {score:.3f}); ten groups have the highest score. Clusters overlap. Names were authored from aggregate profiles and representative spectrograms, without claiming a human listening review. The catalogue exposes every member so the names can be judged and revised by ear.

Each bank starts with the nearest real example to its center, then uses farthest-first coverage inside the closest 92% of members, capped at 24. Exemplars with RMS below 0.009 are excluded from runtime generation to leave an audibility margin. Excluded candidates remain in the full catalogue. The build checks exact center IDs before assigning labels, preventing names from silently attaching to different clusters.
{verification}
## Reproduce

Run from the repository root with Node.js and Python 3 plus NumPy. Plotting additionally requires Matplotlib. The application itself needs none of the Python dependencies.

```sh
node tools/preset_survey/render_corpus.js examples/Transfxr/survey
python3 tools/preset_survey/analyze.py examples/Transfxr/survey
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
node tools/preset_survey/validate_families.js /private/tmp/transfxr-family-validation 32
python3 tools/preset_survey/validate_families.py examples/Transfxr/survey /private/tmp/transfxr-family-validation
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
python3 tools/preset_survey/plot_representatives.py examples/Transfxr/survey
python3 -m unittest discover -s tools/preset_survey -p 'test_*.py'
npm test
```

WAVs and the listening reel are generated locally and ignored by Git. A fresh checkout must run the renderer and bank builder before catalogue playback; the synth buttons work immediately from the shipped JavaScript bank. Serve the repository root with the normal development server to use the catalogue's editor links. Seeded parameter sampling and clustering are reproducible; use the same NumPy version to avoid differences from numeric tie-breaking. If the center-ID check changes, inspect the new clustering and update its labels before building.
''')
    return bank

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('--bank',default='js/synths/TransfxrPresets.js');args=parser.parse_args()
    if (Path(args.directory)/'curated.json').exists():
        from build_curated_catalogue import build_curated
        build_curated(args.directory,args.bank)
    else:build(args.directory,args.bank)
