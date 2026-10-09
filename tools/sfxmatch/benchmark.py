"""One frozen benchmark, one rating protocol.

    python -m sfxmatch.benchmark freeze                 # once; writes benchmark.json
    python -m sfxmatch.benchmark page NAME label=dir .. # blind listening page
    python -m sfxmatch.benchmark score ratings/*.json   # the trend line

A system is a directory of <target id>.wav files. Rate at milestones, not per
tweak: every rating session should answer "is this version better than the
last one on the same targets and the same scale".
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
BENCHMARK = HERE/'benchmark.json'
SCALE = {1: 'unrelated', 2: 'same family, wrong sound', 3: 'roughly similar', 4: 'close', 5: 'very close'}
SKIP_TAGS = {'voice'}  # speech is out of scope for these synths
# Development targets: used in the reach probes and to revise the objective.
# Report them apart from the other external targets, which stay untouched.
PROBE = ('ext-001', 'ext-005', 'ext-009', 'ext-013', 'ext-017', 'ext-021',
         'ext-025', 'ext-029', 'ext-033', 'ext-037', 'ext-041', 'ext-045')


def corpus_root():
    root = Path(os.environ.get('SFX_TARGETS', HERE.parent/'targets_non_bfxr_big'))
    if not (root/'tags').is_dir():
        raise FileNotFoundError('Set SFX_TARGETS or symlink tools/targets_non_bfxr_big to the tagged corpus')
    return root


def load():
    return json.loads(BENCHMARK.read_text())


def targets(kind=None):
    data = load()
    return [t for key in ('external', 'native') if kind in (None, key) for t in data[key]]


def reference(target, renderer=None):
    """Trimmed, peak-normalised 44.1 kHz mono reference audio for a benchmark target."""
    from match.audio import normalize_peak, prepare_target, trim_silence
    if 'file' in target:
        return prepare_target(corpus_root()/'tags'/target['file'])
    return normalize_peak(trim_silence(renderer.render(target['synth'], target['params'], target['seed'])[1]))


def freeze(external=50, per_synth=2, seed=20261007):
    from match.audio import prepare_target
    from .render import FastRenderer, active_synths
    if BENCHMARK.exists():
        raise FileExistsError(f'{BENCHMARK} already exists; the benchmark is frozen')
    heard = set()
    for manifest in (HERE.parent/'multisynth/listening_data').glob('*/manifest.json'):
        heard |= {t['source'].get('sha256') for t in json.loads(manifest.read_text())['targets']
                  if isinstance(t.get('source'), dict)}
    rng = np.random.default_rng(seed)
    root = corpus_root()/'tags'
    files = {}
    for tag in sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in SKIP_TAGS):
        names = sorted(f.name for f in (root/tag).iterdir() if f.suffix.lower() in ('.wav', '.ogg', '.flac'))
        files[tag] = [names[i] for i in rng.permutation(len(names))]
    chosen = []
    # One per tag first, then extra passes through the larger tags.
    order = sorted(files, key=lambda tag: (-len(files[tag]), tag))
    while len(chosen) < external and any(files.values()):
        for tag in order:
            while files[tag] and len(chosen) < external:
                name = files[tag].pop()
                try:
                    seconds = len(prepare_target(root/tag/name))/44100
                except Exception:
                    continue
                if not .05 <= seconds <= 4:
                    continue
                digest = hashlib.sha256((root/tag/name).read_bytes()).hexdigest()
                chosen.append({'tag': tag, 'file': f'{tag}/{name}', 'sha256': digest,
                               'seconds': round(seconds, 3), 'heardBefore': digest in heard})
                break
    chosen.sort(key=lambda t: t['file'])
    native = []
    with FastRenderer() as renderer:
        for name in active_synths(renderer):
            presets = renderer.specs[name]['presets']
            for i in rng.choice(len(presets), size=min(per_synth, len(presets)), replace=False):
                sample_seed, render_seed = (int(v) for v in rng.integers(0, 2**32, 2))
                params = renderer.sample(name, presets[int(i)], sample_seed)
                canonical, _ = renderer.render(name, params, render_seed)
                native.append({'synth': name, 'preset': presets[int(i)], 'params': canonical, 'seed': render_seed})
    for i, t in enumerate(chosen):
        t['id'] = f'ext-{i+1:03d}'
    for i, t in enumerate(native):
        t['id'] = f'nat-{i+1:03d}'
    BENCHMARK.write_text(json.dumps({'version': 1, 'seed': seed, 'scale': SCALE,
                                     'external': chosen, 'native': native}, indent=1)+'\n')
    return chosen, native


def wav_bytes(wave):
    """PCM16 WAV at peak 0.5 with 3 ms fades so hard edges never click on playback."""
    import io
    wave = np.asarray(wave, dtype=np.float32)
    wave = wave/max(float(np.max(np.abs(wave))), 1e-9)*.5
    fade = min(132, len(wave)//2)
    ramp = np.linspace(0, 1, fade, dtype=np.float32)
    wave = wave.copy(); wave[:fade] *= ramp; wave[len(wave)-fade:] *= ramp[::-1]
    buffer = io.BytesIO()
    sf.write(buffer, wave, 44100, subtype='PCM_16', format='WAV')
    return buffer.getvalue()


def write_wav(path, wave):
    Path(path).write_bytes(wav_bytes(wave))


def page(name, systems, output=None, only=None, inline=False):
    """inline=True embeds the audio in the HTML so the single file can be sent anywhere."""
    from .render import FastRenderer
    output = Path(output or HERE/'runs/pages'/name)
    (output/'audio').mkdir(parents=True, exist_ok=True)
    rows = []
    with FastRenderer() as renderer:
        for target in targets():
            if only and target['id'] not in only:
                continue
            found = {label: Path(d)/f'{target["id"]}.wav' for label, d in systems.items()}
            found = {label: path for label, path in found.items() if path.exists()}
            if not found:
                continue
            write_wav(output/'audio'/f'{target["id"]}-ref.wav', reference(target, renderer))
            order = sorted(found, key=lambda label: hashlib.sha256(f'{name}/{target["id"]}/{label}'.encode()).hexdigest())
            candidates = []
            for slot, label in enumerate(order):
                wave, rate = sf.read(found[label], dtype='float32', always_2d=True)
                if rate != 44100:
                    raise ValueError(f'{found[label]} is not 44.1 kHz')
                file = f'{target["id"]}-{slot}.wav'
                write_wav(output/'audio'/file, wave[:, 0])
                candidates.append({'system': label, 'file': file})
            rows.append({'id': target['id'], 'title': target.get('file') or f'{target["synth"]} · {target["preset"]}',
                         'candidates': candidates})
    data = {'page': name, 'scale': SCALE, 'targets': rows}
    if inline:
        import base64
        data['audio'] = {f.name: 'data:audio/wav;base64,'+base64.b64encode(f.read_bytes()).decode()
                         for f in sorted((output/'audio').glob('*.wav'))}
    document = PAGE.replace('__NAME__', html.escape(name)).replace('__DATA__', json.dumps(data))
    (output/'index.html').write_text(document)
    return output/'index.html', len(rows)


def score(files):
    kinds = {t['id']: ('probe' if t['id'] in PROBE else 'external' if 'file' in t else 'native') for t in targets()}
    for file in files:
        data = json.loads(Path(file).read_text())
        print(f'\n{data["page"]}  ({file})')
        table = {}
        for row in data['ratings']:
            table.setdefault((row['system'], kinds.get(row['target'], '?')), []).append(row['rating'])
        for (system, kind), values in sorted(table.items()):
            values = np.asarray(values)
            print(f'  {system:28s} {kind:8s} n={len(values):3d}  mean {values.mean():.2f}'
                  f'  close-or-better {np.mean(values >= 4)*100:3.0f}%  similar-or-better {np.mean(values >= 3)*100:3.0f}%')


PAGE = r'''<!doctype html><meta charset="utf-8"><title>__NAME__ · sfxmatch benchmark</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light dark;--fg:#1c1c1c;--bg:#fafaf8;--mut:#6b6b6b;--line:#d9d9d4;--acc:#2f6fde;--on:#fff}
@media(prefers-color-scheme:dark){:root{--fg:#ececec;--bg:#171717;--mut:#9a9a9a;--line:#3a3a3a;--acc:#6ea0ff;--on:#111}}
body{font:16px/1.45 system-ui,sans-serif;color:var(--fg);background:var(--bg);max-width:720px;margin:0 auto;padding:20px 16px}
h1{font-size:18px;margin:0 0 4px}.mut{color:var(--mut);font-size:14px}
.row{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--line);flex-wrap:wrap}
button{font:inherit;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:transparent;color:inherit;cursor:pointer}
button.play{min-width:118px;text-align:left}button.on{background:var(--acc);border-color:var(--acc);color:var(--on)}
button.heard{border-color:var(--acc)}.rate button{min-width:40px;padding:8px 0}.rate{display:flex;gap:6px}
nav{display:flex;gap:10px;align-items:center;margin:16px 0;flex-wrap:wrap}progress{flex:1;min-width:120px}
kbd{border:1px solid var(--line);border-radius:4px;padding:0 5px;font-size:13px}
</style>
<h1>__NAME__</h1><div class="mut" id="scale"></div>
<nav><button id="prev">← Prev</button><span id="where"></span><progress id="bar" value="0" max="1"></progress>
<button id="next">Next →</button><button id="save">Download ratings</button></nav>
<div id="card"></div>
<p class="mut"><kbd>R</kbd> reference · <kbd>A</kbd>–<kbd>F</kbd> candidates · <kbd>1</kbd>–<kbd>5</kbd> rate the last one played · <kbd>N</kbd>/<kbd>P</kbd> next/previous. Rate how close each candidate is to the reference. Candidates are shuffled and unlabelled.</p>
<script>
const DATA=__DATA__, KEY='sfxmatch-'+DATA.page;
let state={}; try{state=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
let at=0, last=null, audio=new Audio();
const $=id=>document.getElementById(id);
$('scale').textContent=Object.entries(DATA.scale).map(([k,v])=>k+' = '+v).join(' · ');
function store(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}}
function play(file,button){audio.pause();audio=new Audio(DATA.audio?DATA.audio[file]:'audio/'+file);audio.play();if(button)button.classList.add('heard')}
function rated(t){return t.candidates.every(c=>state[t.id+'/'+c.system])}
function draw(){
  const t=DATA.targets[at]; last=null; const card=$('card'); card.innerHTML='';
  const head=document.createElement('div'); head.className='row';
  const ref=document.createElement('button'); ref.className='play'; ref.textContent='▶ Reference (R)'; ref.onclick=()=>play(t.id+'-ref.wav',ref);
  const title=document.createElement('span'); title.className='mut'; title.textContent=t.id+' · '+t.title;
  head.append(ref,title); card.append(head);
  t.candidates.forEach((c,i)=>{
    const row=document.createElement('div'); row.className='row';
    const b=document.createElement('button'); b.className='play'; b.textContent='▶ '+String.fromCharCode(65+i); b.onclick=()=>{last=i;play(c.file,b)};
    const rate=document.createElement('div'); rate.className='rate';
    for(let r=1;r<=5;r++){const k=document.createElement('button'); k.textContent=r; k.title=DATA.scale[r];
      if(state[t.id+'/'+c.system]===r)k.classList.add('on');
      k.onclick=()=>{state[t.id+'/'+c.system]=r;store();draw()}; rate.append(k)}
    row.append(b,rate); card.append(row)});
  const done=DATA.targets.filter(rated).length;
  $('where').textContent=(at+1)+' / '+DATA.targets.length+' · '+done+' rated'; $('bar').value=done/DATA.targets.length;
  card.dataset.ref=t.id;
}
function go(d){at=Math.max(0,Math.min(DATA.targets.length-1,at+d));draw();play(DATA.targets[at].id+'-ref.wav')}
$('prev').onclick=()=>go(-1); $('next').onclick=()=>go(1);
$('save').onclick=()=>{const ratings=[];for(const t of DATA.targets)for(const c of t.candidates){const r=state[t.id+'/'+c.system];if(r)ratings.push({target:t.id,system:c.system,rating:r})}
  const blob=new Blob([JSON.stringify({page:DATA.page,saved:new Date().toISOString(),ratings},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=DATA.page+'-ratings.json';a.click()};
document.onkeydown=e=>{const t=DATA.targets[at],k=e.key.toLowerCase();
  if(k==='r')play(t.id+'-ref.wav',document.querySelector('#card .play'));
  else if(k==='n')go(1); else if(k==='p')go(-1);
  else if(k>='a'&&k<='f'&&k.charCodeAt(0)-97<t.candidates.length){const i=k.charCodeAt(0)-97;last=i;play(t.candidates[i].file,document.querySelectorAll('#card .play')[i+1])}
  else if(k>='1'&&k<='5'&&last!==null){state[t.id+'/'+t.candidates[last].system]=+k;store();const keep=last;draw();last=keep}};
at=Math.max(0,DATA.targets.findIndex(t=>!rated(t))); draw();
</script>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('freeze')
    make = commands.add_parser('page')
    make.add_argument('name'); make.add_argument('systems', nargs='+', help='label=directory')
    make.add_argument('--only', nargs='+')
    make.add_argument('--inline', action='store_true', help='embed audio in the HTML (one portable file)')
    tally = commands.add_parser('score'); tally.add_argument('files', nargs='+')
    args = parser.parse_args()
    if args.command == 'freeze':
        chosen, native = freeze()
        print(f'{len(chosen)} external ({sum(t["heardBefore"] for t in chosen)} heard before), {len(native)} native')
    elif args.command == 'page':
        index, count = page(args.name, dict(s.split('=', 1) for s in args.systems), only=args.only, inline=args.inline)
        print(f'{count} targets -> {index}')
    else:
        score(args.files)


if __name__ == '__main__':
    main()
