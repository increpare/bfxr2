"""Sort generated sounds into game-audio tags, and browse the best of each.

    uv run --with transformers --with torchvision python -m sfxmatch.tags encode --data sfxmatch/runs/mix-1m
    ... then `clap`, `audioset` or `spread` in place of `encode` to build each page

Two taggers, two pages:

* CLAP turns a sound and any phrase into vectors in one space; a sound's tag is
  the phrase it sits nearest, so the vocabulary (TAGS) is ours to write. Raw
  similarity favours a few catch-all phrases, so each tag's scores are first
  standardised across all the sounds, and each sound goes to one tag.
* EfficientAT gives a probability for each of AudioSet's 527 fixed labels. A
  sound may sit under several labels; each label keeps its most probable.

`spread` ignores tags and picks the sounds least like one another in CLAP's
space, to show the range of what the synth makes.

A bucket holds three sounds from three different pairs of synths.
`encode` renders each sound once and runs both models on the GPU; its output
is stored per dataset shard, so it resumes, and changing TAGS or thresholds
afterwards costs seconds.
The AudioSet model needs github.com/fschmid56/EfficientAT cloned into runs/.
"""
import argparse
import html
import json
from pathlib import Path

import numpy as np

from . import benchmark
from .render import FastRenderer, RenderPool

HERE = Path(__file__).resolve().parent
MODEL = 'laion/clap-htsat-unfused'
RATE = 48000
BUCKET = 3
FLOOR = .15     # an AudioSet label is shown once some sound reaches this probability
# (group, tag, phrase given to CLAP)
TAGS = [
    ('Interface', 'click', 'a short user interface click'),
    ('Interface', 'confirm', 'a positive confirmation chime in a menu'),
    ('Interface', 'error', 'an error buzzer, access denied'),
    ('Interface', 'notification', 'a notification alert tone'),
    ('Interface', 'typing', 'typing on a keyboard'),
    ('Interface', 'beep', 'an electronic beep'),
    ('Rewards', 'coin', 'picking up a coin in a video game'),
    ('Rewards', 'power-up', 'a video game power-up, rising tones'),
    ('Rewards', 'level up', 'a triumphant level-up fanfare'),
    ('Rewards', 'game over', 'a sad game over jingle, falling tones'),
    ('Movement', 'jump', 'a cartoon jump sound'),
    ('Movement', 'footstep', 'a footstep'),
    ('Movement', 'whoosh', 'a fast whoosh of something moving through the air'),
    ('Movement', 'bounce', 'a rubbery bounce, boing'),
    ('Movement', 'slide', 'something sliding or scraping along a surface'),
    ('Movement', 'teleport', 'a science fiction teleport'),
    ('Combat', 'laser', 'a laser gun firing'),
    ('Combat', 'gunshot', 'a gunshot'),
    ('Combat', 'explosion', 'an explosion'),
    ('Combat', 'punch', 'a punch or body impact'),
    ('Combat', 'sword', 'a sword slash, metal blade'),
    ('Combat', 'hurt', 'a character taking damage, a grunt of pain'),
    ('Combat', 'shield', 'an energy shield activating'),
    ('Combat', 'charge', 'a weapon charging up'),
    ('Magic', 'spell', 'a magic spell being cast, sparkling'),
    ('Magic', 'heal', 'a gentle healing spell, shimmering'),
    ('Magic', 'eerie', 'an eerie ghostly sound'),
    ('Creatures', 'monster', 'a monster growl or roar'),
    ('Creatures', 'bird', 'a bird chirping'),
    ('Creatures', 'insect', 'insects buzzing'),
    ('Creatures', 'small creature', 'a small cute creature squeaking'),
    ('Creatures', 'alien', 'an alien creature vocalising'),
    ('Creatures', 'robot voice', 'a robot talking, computer speech'),
    ('Machines', 'engine', 'an engine or motor running'),
    ('Machines', 'alarm', 'an alarm or siren'),
    ('Machines', 'electric zap', 'an electric zap, sparks'),
    ('Machines', 'glitch', 'digital glitch, data corruption noise'),
    ('Machines', 'mechanism', 'a mechanical ratchet or clockwork mechanism'),
    ('Machines', 'spaceship', 'a spaceship humming'),
    ('Materials', 'door', 'a door opening or closing'),
    ('Materials', 'glass', 'glass breaking'),
    ('Materials', 'metal', 'a metallic clang'),
    ('Materials', 'wood', 'a knock on wood'),
    ('Materials', 'rocks', 'rocks crumbling, rubble'),
    ('Materials', 'squish', 'a wet squelch, slime'),
    ('Materials', 'cloth', 'cloth or paper rustling'),
    ('Nature', 'water', 'a water splash'),
    ('Nature', 'bubbles', 'bubbles'),
    ('Nature', 'fire', 'fire crackling'),
    ('Nature', 'wind', 'wind blowing'),
    ('Nature', 'thunder', 'thunder rumbling'),
    ('Music', 'bell', 'a bell ringing'),
    ('Music', 'drum', 'a drum hit'),
    ('Music', 'plucked string', 'a plucked string instrument note'),
    ('Music', 'choir', 'a choir or sung voice'),
]


class Sounds:
    """A mixdata directory without loading a million recipes: lengths and synth pairs up front, recipes on demand."""

    def __init__(self, data, count=None):
        self.path = Path(data)
        self.files, pairs, lengths, total = [], [], [], 0
        for shard in sorted(s for s in self.path.glob('mix-*.npz') if not s.name.endswith('.tmp.npz')):
            with np.load(shard) as z:
                pairs.append(z['synth']); lengths.append(2.**z['duration'])
            self.files.append(shard); total += len(lengths[-1])
            if count and total >= count:
                break
        self.count = min(total, count or total)
        self.starts = np.cumsum([0]+[len(x) for x in lengths])
        self.pairs, self.seconds = np.concatenate(pairs)[:self.count], np.concatenate(lengths)[:self.count]
        self._shard = (None, None)

    def __len__(self):
        return self.count

    def pair(self, index):
        return tuple(self.pairs[index])

    def patch(self, index):
        shard = int(np.searchsorted(self.starts, index, side='right'))-1
        if self._shard[0] != shard:
            self._shard = (shard, self.files[shard].with_suffix('.jsonl').read_text().splitlines())
        return json.loads(self._shard[1][index-self.starts[shard]])


def clap():
    import torch
    from transformers import ClapModel, ClapProcessor
    torch.set_num_threads(6)
    return ClapModel.from_pretrained(MODEL).eval(), ClapProcessor.from_pretrained(MODEL)


def vector(out):
    """Library versions differ on whether features come back bare or wrapped."""
    return out if hasattr(out, 'shape') else out.pooler_output


def efficientat():
    """EfficientAT mn10 trained on AudioSet (about 18 MB, fetched on first use) and the label names."""
    import os
    import sys
    root = HERE/'runs/EfficientAT'
    if not root.exists():
        raise FileNotFoundError(f'Clone https://github.com/fschmid56/EfficientAT into {root}')
    sys.path.insert(0, str(root))
    here = os.getcwd()
    os.chdir(root)       # the repository reads its label file and stores weights relative to itself
    try:
        from helpers.utils import NAME_TO_WIDTH, labels
        from models.mn.model import get_model
        model = get_model(width_mult=NAME_TO_WIDTH('mn10_as'), pretrained_name='mn10_as').eval()
    finally:
        os.chdir(here)
    return model, list(labels)


class Inputs:
    """Pool task: a saved mix -> the spectrogram each tagger wants, so only the networks run on the GPU.

    Both models were built for ten-second clips. CLAP's own front end loops a short sound to fill
    them. The AudioSet model gets the sound followed by silence: on shorter input it returns
    confident nonsense, and looped input makes nearly everything "Music".
    """

    def __init__(self):
        self.front = None

    def __call__(self, renderer, task):
        import torch
        import torchaudio
        if self.front is None:
            import sys
            from transformers import ClapFeatureExtractor
            sys.path.insert(0, str(HERE/'runs/EfficientAT'))
            from models.preprocess import AugmentMelSTFT
            self.front = (ClapFeatureExtractor.from_pretrained(MODEL),
                          AugmentMelSTFT(n_mels=128, sr=32000, win_length=800, hopsize=320).eval())
        _, _, wave, _ = renderer.mix(task['sources'], task['balance'])
        peak = float(np.max(np.abs(wave)))
        if peak < 1e-6:
            raise ValueError('Silent mix')
        wave = torch.from_numpy(wave/peak)
        for_clap = torchaudio.functional.resample(wave, 44100, RATE)[:RATE*10].numpy()
        clap_in = self.front[0](for_clap, sampling_rate=RATE, return_tensors='np')['input_features'][0]
        for_audioset = torch.zeros(320000)
        short = torchaudio.functional.resample(wave, 44100, 32000)[:320000]
        for_audioset[:len(short)] = short
        with torch.no_grad():
            spec = self.front[1](for_audioset[None])[0].numpy()
        return True, (clap_in.astype(np.float16), spec.astype(np.float16))


def store(data):
    return HERE/'runs/tags'/Path(data).name


def encode(data, jobs=None, batch=32, limit=None):
    """Run every mix through both taggers on the GPU, one output file pair per dataset shard.
    Shards already done are skipped, so this resumes after an interruption."""
    import torch
    from .render import RenderPool
    out = store(data); out.mkdir(parents=True, exist_ok=True)
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    clap_model = clap()[0].to(device)
    audioset_model = efficientat()[0].to(device)
    shards = sorted(s for s in Path(data).glob('mix-*.jsonl'))[:limit]
    import time
    started, done = time.monotonic(), 0
    with RenderPool(Inputs(), jobs) as pool, torch.no_grad():
        for shard in shards:
            index = shard.stem.split('-')[1]
            if (out/f'clap-{index}.npy').exists() and (out/f'audioset-{index}.npy').exists():
                continue
            patches = [json.loads(line) for line in shard.read_text().splitlines()]
            vectors = np.zeros((len(patches), 512), np.float16)      # a failed render keeps a row of zeros
            labels = np.zeros((len(patches), 527), np.float16)
            waiting = []

            def flush():
                rows = [row for row, _ in waiting]
                a = torch.from_numpy(np.stack([x[0] for _, x in waiting])).float().to(device)
                b = torch.from_numpy(np.stack([x[1] for _, x in waiting])).float().to(device)
                found = vector(clap_model.get_audio_features(input_features=a, is_longer=torch.zeros(len(rows), 1, dtype=torch.bool, device=device)))
                vectors[rows] = torch.nn.functional.normalize(found, dim=-1).cpu().numpy()
                labels[rows] = torch.sigmoid(audioset_model(b.unsqueeze(1))[0].float()).reshape(len(rows), -1).cpu().numpy()
                waiting.clear()

            for row, result in enumerate(pool.stream(patches)):
                if result[0] is not None:
                    waiting.append((row, result[1]))
                if len(waiting) == batch:
                    flush()
            if waiting:
                flush()
            np.save(out/f'audioset-{index}.npy', labels)
            np.save(out/f'clap-{index}.npy', vectors)
            done += len(patches)
            print(f'shard {index}: {done} sounds this run, {done/(time.monotonic()-started):.0f} a second', flush=True)


def scores(kind, data, count=None):
    """Stored tagger outputs ('clap' unit vectors or 'audioset' probabilities) for the leading shards that have them."""
    parts, total = [], 0
    for file in sorted(store(data).glob(f'{kind}-*.npy')):
        if parts and int(file.stem.split('-')[1]) != len(parts):
            break                                             # stop at the first gap
        parts.append(np.load(file).astype(np.float32)); total += len(parts[-1])
        if count and total >= count:
            break
    if not parts:
        raise FileNotFoundError(f'No {kind} scores for {data}; run `python -m sfxmatch.tags encode --data {data}` first')
    return np.concatenate(parts)[:count]


def text_vectors():
    import torch
    model, processor = clap()
    with torch.no_grad():
        out = vector(model.get_text_features(**processor(text=[phrase for _, _, phrase in TAGS], return_tensors='pt', padding=True)))
    return torch.nn.functional.normalize(out, dim=-1).numpy()


def best_three(order, sounds, score):
    """Walk candidates best first, keeping three from three different pairs of synths."""
    chosen, pairs = [], set()
    for index in order:
        pair = sounds.pair(index)
        if pair not in pairs:
            pairs.add(pair)
            chosen.append({'row': int(index), 'score': float(score[index])})
            if len(chosen) == BUCKET:
                break
    return chosen


def clap_buckets(audio, text, sounds):
    """Each sound goes to the one tag it matches most unusually well; each tag keeps its best three."""
    alive = np.abs(audio).sum(1) > 0
    similarity = audio @ text.T
    standard = (similarity-similarity[alive].mean(0))/similarity[alive].std(0)
    standard[~alive] = -np.inf
    best = standard.argmax(1)
    buckets = []
    for tag in range(len(TAGS)):
        mine = np.flatnonzero((best == tag) & alive)
        buckets.append({'assigned': int(len(mine)),
                        'sounds': best_three(mine[np.argsort(-standard[mine, tag])], sounds, standard[:, tag])})
    return buckets


def audioset_buckets(probability, sounds, floor=FLOOR):
    """Every label with at least one sound above `floor` keeps its three most probable sounds."""
    buckets = []
    for label in range(probability.shape[1]):
        mine = np.flatnonzero(probability[:, label] >= floor)
        buckets.append({'assigned': int(len(mine)),
                        'sounds': best_three(mine[np.argsort(-probability[mine, label])], sounds, probability[:, label])})
    return buckets


def spread(audio, picks, usable=None):
    """The `picks` sounds least like one another: start from the most typical sound, then keep
    taking whichever sound is furthest (cosine distance) from everything picked so far.

    Returns (rows in pick order, each one's distance from the earlier picks when it was chosen,
    the share of all sounds that sit nearer to it than to any other pick).
    """
    alive = np.abs(audio).sum(1) > 0
    if usable is not None:
        alive &= usable
    first = int(np.where(alive, audio @ audio[alive].mean(0), -np.inf).argmax())
    nearest = np.where(alive, 1-audio @ audio[first], -1.)
    chosen, gaps = [first], [0.]
    while len(chosen) < picks:
        index = int(nearest.argmax())
        chosen.append(index); gaps.append(float(nearest[index]))
        nearest = np.minimum(nearest, 1-audio @ audio[index])
    owner = (audio[alive] @ audio[chosen].T).argmax(1)
    share = np.bincount(owner, minlength=len(chosen))/alive.sum()
    return chosen, gaps, share


def page(name, title, intro, sections, sounds, other=None):
    """sections: [(group, tag, note, bucket)]. Audio is written beside the page and fetched on demand."""
    output = HERE/'runs/pages'/name
    (output/'audio').mkdir(parents=True, exist_ok=True)
    groups = {}
    with FastRenderer() as renderer:
        for group, tag, note, bucket in sections:
            entries = []
            for sound in bucket['sounds']:
                patch = sounds.patch(sound['row'])
                sources, balance, wave, _ = renderer.mix(patch['sources'], patch['balance'])
                file = output/'audio'/f'{sound["row"]}.wav'
                if not file.exists():
                    file.write_bytes(benchmark.wav_bytes(wave[:44100*6]))
                preset = {'masterVolume': .5, 'seed': .5, 'balance': balance, 'sources': json.dumps(
                    [{'synth': s['synth'], 'name': s['synth'], 'params': s['params'], 'renderSeed': s['seed']} for s in sources])}
                entries.append({'synths': ' + '.join(s['synth'] for s in sources), 'balance': round(balance, 2) if len(sources) == 2 else None,
                               'score': sound.get('label', round(sound['score'], 2)), 'preset': preset, 'file': file.name})
            groups.setdefault(group, []).append({'tag': tag, 'note': note, 'sounds': entries})
    data = {'title': title, 'intro': intro, 'other': other, 'groups': [{'group': g, 'tags': t} for g, t in groups.items()]}
    (output/'index.html').write_text(PAGE.replace('__NAME__', html.escape(title)).replace('__DATA__', json.dumps(data)))
    return output/'index.html'


PAGE = r'''<!doctype html><meta charset="utf-8"><title>__NAME__</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light dark;--fg:#1c1c1c;--bg:#fafaf8;--mut:#6b6b6b;--line:#d9d9d4;--acc:#2f6fde;--on:#fff;--card:#fff}
@media(prefers-color-scheme:dark){:root{--fg:#ececec;--bg:#171717;--mut:#9a9a9a;--line:#3a3a3a;--acc:#6ea0ff;--on:#111;--card:#1f1f1f}}
body{font:16px/1.45 system-ui,sans-serif;color:var(--fg);background:var(--bg);max-width:1100px;margin:0 auto;padding:20px 16px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:26px 0 10px;color:var(--mut);font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.mut{color:var(--mut);font-size:14px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{border:1px solid var(--line);border-radius:10px;padding:12px;background:var(--card)}
.card h3{margin:0;font-size:16px}.card .mut{font-size:13px;margin-bottom:8px}
.sound{display:flex;align-items:center;gap:8px;padding:5px 0}
button,input{font:inherit;border:1px solid var(--line);border-radius:8px;background:transparent;color:inherit;padding:6px 10px}
button{cursor:pointer}button.play{min-width:44px}button.playing{background:var(--acc);border-color:var(--acc);color:var(--on)}
button.save{font-size:13px;padding:4px 8px;color:var(--mut)}.what{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.score{font-size:12px;color:var(--mut);font-variant-numeric:tabular-nums}
nav{position:sticky;top:0;background:var(--bg);padding:8px 0;display:flex;gap:10px;flex-wrap:wrap;align-items:center;z-index:1}
nav a{font-size:14px;color:var(--acc);text-decoration:none}nav input{flex:1;min-width:160px}
</style>
<h1 id="title"></h1>
<div class="mut" id="intro"></div>
<nav id="nav"><button id="all">▶ Play all</button><input id="find" type="search" placeholder="Filter tags…"></nav><div id="root"></div>
<script>
const DATA=__DATA__;
let context=null, current=null, lit=null; const decoded=new Map();
let queue=null;                                 // when playing everything: the buttons still to come
function halt(){if(current){try{current.onended=null;current.stop()}catch(e){}current=null}if(lit){lit.classList.remove('playing');lit.textContent='▶';lit=null}}
function stop(){queue=null;document.getElementById('all').textContent='▶ Play all';halt()}
function next(){halt();while(queue&&queue.length){const b=queue.shift();if(b.offsetParent!==null){b.scrollIntoView({block:'center',behavior:'smooth'});start(b.sound,b);return}}stop()}
async function play(sound,button){const again=lit===button; stop(); if(!again) start(sound,button)}
async function start(sound,button){
  context=context||new (window.AudioContext||window.webkitAudioContext)();
  if(context.state==='suspended') await context.resume();
  lit=button; button.classList.add('playing'); button.textContent='■';
  if(!decoded.has(sound.file)){
    const reply=await fetch('audio/'+sound.file); if(!reply.ok){stop();button.textContent='!';return}
    decoded.set(sound.file,await context.decodeAudioData(await reply.arrayBuffer()));
  }
  if(lit!==button) return;                         // something else was clicked while this one loaded
  const node=context.createBufferSource(); node.buffer=decoded.get(sound.file); node.connect(context.destination);
  node.onended=()=>{if(current===node){if(queue)setTimeout(next,350);else stop()}}; node.start(); current=node;
}
function save(tag,sound){
  const params=JSON.stringify(sound.preset);
  const file={Mixr:{files:[[tag+' · '+sound.synths,params,params]],selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params:{masterVolume:true}},active_tab_name:'Mixr'};
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([JSON.stringify(file,null,1)],{type:'application/json'}));
  a.download=(tag+' '+sound.synths).replace(/[^a-z0-9]+/gi,'-').toLowerCase()+'.bcol'; a.click();
}
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
document.getElementById('title').textContent=DATA.title; document.getElementById('intro').textContent=DATA.intro;
const nav=document.getElementById('nav'), cards=[];
if(DATA.other){const a=el('a','',DATA.other[0]+' →'); a.href=DATA.other[1]; nav.append(a)}
for(const group of DATA.groups){
  const h=el('h2','',group.group), grid=el('div','grid');
  if(DATA.groups.length>1){h.id='g-'+group.group; const link=el('a','',group.group); link.href='#'+h.id; nav.append(link)}
  for(const t of group.tags){
    const card=el('div','card'); card.append(el('h3','',t.tag), el('div','mut',t.note));
    for(const s of t.sounds){ const row=el('div','sound'); const b=el('button','play','▶'); b.sound=s; b.onclick=()=>play(s,b);
      const d=el('button','save','preset'); d.title='Download as a Mixr preset (.bcol)'; d.onclick=()=>save(t.tag,s);
      row.append(b,el('span','what',s.synths+(s.balance===null?'':' · balance '+s.balance)),el('span','score',s.score),d); card.append(row)}
    cards.push([t.tag.toLowerCase()+' '+t.note.toLowerCase(),card,grid,h]); grid.append(card)}
  document.getElementById('root').append(h,grid)}
document.getElementById('all').onclick=()=>{if(queue){stop();return}stop();queue=[...document.querySelectorAll('button.play')];document.getElementById('all').textContent='■ Stop';next()};
document.getElementById('find').oninput=e=>{const q=e.target.value.trim().toLowerCase(); const seen=new Map();
  for(const [text,card,grid,h] of cards){const on=!q||text.includes(q); card.style.display=on?'':'none'; seen.set(h,(seen.get(h)||false)||on)}
  for(const [h,on] of seen){h.style.display=on?'':'none'}};
</script>'''


def retrieve(data, count, name, only):
    """For benchmark recordings: the library sounds CLAP hears as most like each one. No model, no objective."""
    import torch
    import torchaudio
    from .systems import save
    audio = scores('clap', data, count)
    sounds = Sounds(data, len(audio))
    model, processor = clap()
    root = HERE/'runs/systems'
    with FastRenderer() as renderer, torch.no_grad():
        for target in benchmark.targets('external'):
            if only and target['id'] not in only:
                continue
            wave = benchmark.reference(target, renderer)
            clip = torchaudio.functional.resample(torch.from_numpy(wave/np.max(np.abs(wave))), 44100, RATE).numpy()[:RATE*10]
            query = torch.nn.functional.normalize(vector(model.get_audio_features(
                **processor(audio=[clip], sampling_rate=RATE, return_tensors='pt'))), dim=-1).numpy()[0]
            likeness = audio @ query
            picks = best_three(np.argsort(-likeness), sounds, likeness)
            for rank, pick in enumerate(picks, 1):
                patch = sounds.patch(pick['row'])
                save(root/f'{name}-{rank}', target['id'], renderer.mix(patch['sources'], patch['balance'])[2],
                     {'sources': patch['sources'], 'balance': patch['balance'], 'clap': pick['score']})
            print(f'{target["id"]} {target["file"][:34]:34s} ' + ', '.join(
                f'{" + ".join(s["synth"] for s in sounds.patch(x["row"])["sources"])} ({x["score"]:.2f})' for x in picks), flush=True)
    systems = {f'CLAP neighbour {rank}': root/f'{name}-{rank}' for rank in (1, 2, 3)}
    systems['round 2 search (single synth)'] = root/'reach2'
    print(f'{len(audio):,} library sounds searched')
    print(benchmark.page(name, systems, only=only, inline=True)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['encode', 'clap', 'audioset', 'spread', 'retrieve'])
    parser.add_argument('--data', required=True)
    parser.add_argument('--count', type=int, help='use only the first N sounds (default: all that are encoded)')
    parser.add_argument('--jobs', type=int); parser.add_argument('--picks', type=int, default=100)
    parser.add_argument('--shards', type=int, help='for encode: stop after this many dataset shards')
    parser.add_argument('--name', default='probe-clap', help='for retrieve: page name')
    parser.add_argument('--only', nargs='+', help='for retrieve: benchmark ids')
    args = parser.parse_args()
    if args.command == 'retrieve':
        retrieve(args.data, args.count, args.name, args.only)
        return
    if args.command == 'encode':
        encode(args.data, args.jobs, limit=args.shards)
        return
    if args.command == 'audioset':
        probability = scores('audioset', args.data, args.count)
        sounds = Sounds(args.data, len(probability))
        buckets = audioset_buckets(probability, sounds)
        sections = [('AudioSet labels, in ontology order', label, f'{bucket["assigned"]:,} sounds above {FLOOR}', bucket)
                    for label, bucket in zip(efficientat()[1], buckets) if bucket['sounds']]
        intro = (f'{len(probability):,} random Mixr sounds scored against AudioSet\'s 527 labels by EfficientAT; '
                 f'{len(sections)} labels have at least one sound above {FLOOR} and show their three most probable. '
                 'A sound can appear under several labels. The number is the probability. Click ▶ to play, again to stop.')
        index = page('mix-audioset', 'Mixr by AudioSet label', intro, sections, sounds, ('CLAP tags', '../mix-tags/'))
    else:
        audio = scores('clap', args.data, args.count)
        sounds = Sounds(args.data, len(audio))
        text = text_vectors()
        if args.command == 'clap':
            buckets = clap_buckets(audio, text, sounds)
            sections = [(group, tag, f'“{phrase}” · {bucket["assigned"]:,} sounds landed here', bucket)
                        for (group, tag, phrase), bucket in zip(TAGS, buckets)]
            intro = (f'{len(audio):,} random Mixr sounds, each sent to the one tag it matches best according to CLAP; '
                     'each tag shows its three best. The number is how unusually well the sound fits (standard deviations). '
                     'Click ▶ to play, again to stop.')
            index = page('mix-tags', 'Mixr by tag (CLAP)', intro, sections, sounds, ('AudioSet labels', '../mix-audioset/'))
        else:
            chosen, gaps, share = spread(audio, args.picks, sounds.seconds >= .05)      # a 10 ms blip is not a sound
            similarity = audio @ text.T
            alive = np.abs(audio).sum(1) > 0
            standard = (similarity-similarity[alive].mean(0))/similarity[alive].std(0)
            by_tag = {}
            for order, (row, gap, part) in enumerate(zip(chosen, gaps, share), 1):
                by_tag.setdefault(int(standard[row].argmax()), []).append(
                    {'row': row, 'score': gap, 'label': f'#{order} · {part*100:.2g}%'})
            sections = [(group, tag, f'nearest tag: “{phrase}”', {'assigned': len(by_tag[i]), 'sounds': by_tag[i]})
                        for i, (group, tag, phrase) in enumerate(TAGS) if i in by_tag]
            intro = (f'The {args.picks} sounds least like one another among {len(audio):,} random Mixr sounds, measured in CLAP\'s space. '
                     '# is the order picked: #1 is the most typical sound, then each pick is the one furthest from all earlier picks, '
                     'so low numbers are the extremes. The percentage is how much of the whole set sits nearer to that sound than to any '
                     'other pick. They are filed under the tag each is nearest to, only to make the page navigable.')
            index = page('mix-spread', f'Mixr: the {args.picks} most different sounds', intro, sections, sounds, ('CLAP tags', '../mix-tags/'))
            print(f'gap when picked: #2 {gaps[1]:.2f}, #10 {gaps[9]:.2f}, #50 {gaps[min(49, len(gaps)-1)]:.2f}, last {gaps[-1]:.2f}; '
                  f'largest share {share.max()*100:.1f}%, smallest {share.min()*100:.3f}%')
    for group, tag, note, bucket in sections:
        print(f'{tag[:34]:34s} {bucket["assigned"]:7d}  ' + ', '.join(
            f'{" + ".join(s["synth"] for s in sounds.patch(x["row"])["sources"])} ({x["score"]:.2f})' for x in bucket['sounds']))
    print(index)


if __name__ == '__main__':
    main()
