"""Listener-guided search: you pick the closest candidate, it searches around your pick.

    uv run python -m sfxmatch.guided                  # then open http://127.0.0.1:8765
    uv run python -m sfxmatch.guided warm ext-001 ..  # precompute opening screens

The objective only proposes. Each screen offers the current sound plus a few
alternatives that the objective finds plausible and that differ audibly from
one another; the listener is the judge. A session that ends at "close" proves
the synth can reach the sound; one that stalls after many screens is the
strongest evidence available that it cannot.

Every screen and pick is saved under guided_sessions/ (controls only, no
audio), so sessions are also preference data gathered right at the optimum.
"""
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

import numpy as np

from . import benchmark
from .mel import describe
from .objective import INFEASIBLE, VERSION, Objective
from .render import FastRenderer, RenderPool
from .search import Library, Space, run_cma, score_seeds

HERE = Path(__file__).resolve().parent
SESSIONS = HERE/'guided_sessions'
CACHE = HERE/'runs/guided-cache'
LIBRARY = HERE/'runs/data-1m'
SHOWN = 6           # candidates per screen, including the current sound
SAMPLES = 240       # variations rendered behind each screen
START_SIGMA = .18


class Describe:
    """Pool task (synth, params, seed) -> (canonical params, (score, whole-sound spectrum, log2 seconds))."""

    def __init__(self, target):
        self.target, self.objective = np.asarray(target, dtype=np.float32), None

    def __call__(self, renderer, task):
        if self.objective is None:
            self.objective = Objective(self.target)
        synth, params, seed = task
        canonical, wave = renderer.render(synth, params, seed)
        _, rel, duration = describe(wave)
        return canonical, (self.objective.score(wave), rel.reshape(-1), float(duration))


def scores_only(pool):
    def evaluate(tasks):
        return [(canonical, extra[0] if canonical is not None else INFEASIBLE) for canonical, extra in pool.map(tasks)]
    return evaluate


def earlier_results(target_id):
    """Finished searches for this target (reach probes, benchmark runs) make good extra seeds."""
    rows = []
    for path in sorted((HERE/'runs/systems').glob(f'*/{target_id}.json')):
        row = json.loads(path.read_text())
        if 'synth' in row and 'params' in row:
            rows.append({k: row[k] for k in ('synth', 'params', 'seed')})
    return rows


def opening(target, library, pool, synths=12, polish=400, extra=(), log=print):
    """Best candidate of each promising synth: library neighbours, then a short CMA-ES polish."""
    evaluate = scores_only(pool)
    by_synth = score_seeds(evaluate, [library.row(i) for i in library.nearest(target, 48)] + list(extra))
    chosen = sorted(by_synth, key=lambda name: by_synth[name][0]['score'])[:synths]
    log(f'opening: {sum(map(len, by_synth.values()))} seeds scored, polishing {len(chosen)} synths')
    polished = run_cma(evaluate, [by_synth[name][0] for name in chosen], library.specs, polish)
    return sorted(({k: row[k] for k in ('synth', 'params', 'seed', 'score')} for row in polished), key=lambda r: r['score'])


def variations(parent, spec, rng, count, sigma, previous=None):
    """Small moves around the parent: mostly one to three controls at a time, like a
    hand on the knobs, plus some gentler moves across a quarter of them. If the last
    pick moved somewhere, also continue that way."""
    space = Space(spec, parent['params'])
    centre, continuous = space.encode(parent['params']), len(space.schema.continuous)
    rows = []
    for index in range(count):
        x = centre.copy()
        if index % 5 < 3:
            moved = rng.choice(len(x), size=min(len(x), int(rng.integers(1, 4))), replace=False)
            scale = sigma
        else:
            moved = rng.choice(len(x), size=max(1, len(x)//4), replace=False)
            scale = sigma*.5
        for k in moved:
            if k < continuous:
                x[k] += rng.normal(0, scale)
            else:
                x[k] = rng.random()     # a categorical control: jump to any option
        rows.append(space.decode(np.clip(x, 0, 1)))
    if previous is not None and previous['synth'] == parent['synth']:
        step = centre-Space(spec, previous['params']).encode(previous['params'])
        if np.abs(step[:continuous]).max() > 1e-4:
            x = centre.copy(); x[:continuous] += .8*step[:continuous]
            rows.append(space.decode(np.clip(x, 0, 1)))
    return rows


def pick_diverse(parent, rows, count):
    """The objective's favourite, then candidates that sound least like anything already shown.

    parent and rows: (candidate, score, spectrum, duration). Only candidates the
    objective rates about as good as the parent or better are eligible, so the
    listener chooses among options the objective cannot tell apart; among those,
    audible difference decides.
    """
    rows = sorted(rows, key=lambda r: r[1])
    eligible = [r for r in rows if r[1] <= parent[1]*1.1+.1]
    if len(eligible) < count*3:
        eligible = rows[:count*3]
    feature = lambda r: np.concatenate([r[2].astype(np.float32)/255, [r[3]]])
    shown, features = [], [feature(parent)]
    while eligible and len(shown) < count:
        if not shown:
            best = 0
        else:
            best = int(np.argmax([min(np.abs(feature(r)-f).mean() for f in features) for r in eligible]))
        row = eligible.pop(best)
        shown.append(row); features.append(feature(row))
    return shown


class Session:
    def __init__(self, app, target_id, title, reference):
        self.app, self.target_id, self.title, self.reference = app, target_id, title, reference
        self.id = f'{time.strftime("%Y%m%d-%H%M%S")}-{target_id}'
        self.pool = RenderPool(Describe(reference), app.jobs)
        self.rng = np.random.default_rng(int(time.time()))
        self.synths, self.offset = None, 0
        self.current = self.previous = None
        self.sigma, self.screen, self.history, self.steps = START_SIGMA, None, [], []
        self.started = time.time()

    def describe_parent(self, candidate):
        canonical, extra = self.pool.map([(candidate['synth'], candidate['params'], candidate['seed'])])[0]
        return (candidate, *extra)

    def synth_screen(self):
        if self.synths is None:
            cache = CACHE/f'{self.target_id}.json'
            if cache.exists() and json.loads(cache.read_text()).get('objective') == VERSION:
                self.synths = json.loads(cache.read_text())['candidates']
            else:
                self.synths = opening(self.reference, self.app.library(), self.pool, extra=earlier_results(self.target_id))
        shown = self.synths[self.offset:self.offset+SHOWN] or self.synths[:SHOWN]
        self.screen = {'kind': 'synths', 'candidates': [dict(c, id=f's{self.offset+i}') for i, c in enumerate(shown)]}
        return self.screen

    def refine_screen(self):
        spec = self.app.renderer.specs[self.current['synth']]
        tasks = [(self.current['synth'], params, self.current['seed'])
                 for params in variations(self.current, spec, self.rng, SAMPLES, self.sigma, self.previous)]
        rows = [(dict(self.current, params=canonical, score=extra[0]), *extra)
                for canonical, extra in self.pool.map(tasks) if canonical is not None and extra[0] < INFEASIBLE]
        parent = self.describe_parent(self.current)
        shown = [row[0] for row in pick_diverse(parent, rows, SHOWN-1)]
        order = self.rng.permutation(len(shown))
        candidates = [dict(self.current, id='current', current=True)] + \
                     [dict(shown[i], id=f'g{len(self.steps)}-{n}') for n, i in enumerate(order)]
        self.screen = {'kind': 'refine', 'candidates': candidates}
        return self.screen

    def act(self, action, pick=None):
        before = {'action': action, 'pick': pick, 'sigma': self.sigma, 'seconds': round(time.time()-self.started, 1),
                  'screen': [{k: c[k] for k in ('id', 'synth', 'params', 'seed', 'score')} for c in self.screen['candidates']]}
        self.history.append((self.current, self.previous, self.sigma, self.offset, self.screen))
        if action == 'pick':
            chosen = next(c for c in self.screen['candidates'] if c['id'] == pick)
            chosen = {k: chosen[k] for k in ('synth', 'params', 'seed', 'score')}
            if self.screen['kind'] == 'synths':
                self.current, self.previous, self.sigma = chosen, None, START_SIGMA
            elif pick == 'current':
                self.sigma *= .6            # nothing nearby was better: look closer in
            else:
                self.previous, self.current, self.sigma = self.current, chosen, self.sigma*.9
        elif action == 'wider':
            self.sigma = min(.5, self.sigma*1.7)
        elif action == 'finer':
            self.sigma *= .5
        elif action == 'synths':
            self.offset = 0
        elif action == 'more-synths':
            self.offset = self.offset+SHOWN if self.offset+SHOWN < len(self.synths or []) else 0
        elif action == 'back':
            self.history.pop()
            if self.history:
                self.current, self.previous, self.sigma, self.offset, self.screen = self.history.pop()
            self.steps.append(before); self.save()
            return self.screen
        elif action != 'retry':
            raise ValueError(f'Unknown action {action}')
        self.steps.append(before)
        screen = self.synth_screen() if action in ('synths', 'more-synths') or self.current is None else self.refine_screen()
        self.save()
        return screen

    def save(self, final=None):
        SESSIONS.mkdir(exist_ok=True)
        keep = lambda c: c and {k: c[k] for k in ('synth', 'params', 'seed', 'score')}
        (SESSIONS/f'{self.id}.json').write_text(json.dumps({
            'target': self.target_id, 'title': self.title, 'objective': VERSION, 'steps': self.steps,
            'current': keep(self.current), 'final': final}, indent=1))

    def payload(self):
        cards = []
        for c in self.screen['candidates']:
            _, wave = self.app.renderer.render(c['synth'], c['params'], c['seed'])
            cards.append({'id': c['id'], 'synth': c['synth'], 'score': round(c['score'], 2), 'current': bool(c.get('current')),
                          'wav': 'data:audio/wav;base64,'+base64.b64encode(benchmark.wav_bytes(wave)).decode()})
        return {'session': self.id, 'title': self.title, 'kind': self.screen['kind'], 'candidates': cards,
                'sigma': round(self.sigma, 3), 'screens': len(self.steps), 'synth': self.current and self.current['synth'],
                'reference': 'data:audio/wav;base64,'+base64.b64encode(benchmark.wav_bytes(self.reference)).decode()}


class App:
    def __init__(self, jobs=None):
        self.jobs, self.lock, self.session, self._library = jobs, threading.Lock(), None, None
        self.renderer = FastRenderer()
        self.targets = {t['id']: t for t in benchmark.targets()}

    def library(self):
        if self._library is None:
            self._library = Library(LIBRARY)
        return self._library

    def load(self, target):
        """A benchmark id, or a path to any audio file."""
        if target in self.targets:
            entry = self.targets[target]
            return target, entry.get('file') or f'{entry["synth"]} · {entry["preset"]}', benchmark.reference(entry, self.renderer)
        from match.audio import prepare_target
        path = Path(target).expanduser()
        return path.stem.replace(' ', '_')[:40], path.name, prepare_target(path)

    def start(self, target):
        if self.session:
            self.session.pool.close()
        self.session = Session(self, *self.load(target))
        self.session.synth_screen()
        self.session.save()
        return self.session.payload()

    def handle(self, path, body):
        with self.lock:
            if path == '/api/targets':
                probe = [t for t in self.targets.values() if t['id'] in benchmark.PROBE]
                rest = [t for t in self.targets.values() if t['id'] not in benchmark.PROBE]
                return {'targets': [{'id': t['id'], 'title': t.get('file') or f'{t["synth"]} · {t["preset"]}',
                                     'probe': t['id'] in benchmark.PROBE} for t in probe+rest]}
            if path == '/api/start':
                return self.start(body['target'])
            session = self.session
            if session is None or session.id != body.get('session'):
                raise ValueError('No such session; start again')
            if path == '/api/act':
                session.act(body['action'], body.get('pick'))
                return session.payload()
            if path == '/api/finish':
                session.save({'rating': body['rating'], 'verdict': body.get('verdict'), 'note': body.get('note', ''),
                              'screens': len(session.steps), 'seconds': round(time.time()-session.started, 1)})
                return {'saved': str(SESSIONS/f'{session.id}.json')}
            if path == '/api/preset':
                from multisynth.report import add_preset
                collection = {}
                add_preset(collection, session.current, f'{session.title} · guided')
                return collection
        raise ValueError(f'Unknown endpoint {path}')


def serve(port, jobs, host='127.0.0.1'):
    app = App(jobs)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, kind, data):
            self.send_response(status)
            self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store'); self.send_header('Accept-Ranges', 'bytes')
            self.end_headers(); self.wfile.write(data)

        def run(self, body):
            try:
                self.reply(200, 'application/json', json.dumps(app.handle(self.path.split('?')[0], body)).encode())
            except Exception as error:  # show the listener what went wrong instead of hanging the page
                self.reply(500, 'application/json', json.dumps({'error': f'{type(error).__name__}: {error}'}).encode())

        def do_GET(self):
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                self.reply(200, 'text/html; charset=utf-8', PAGE.encode())
            elif path.startswith('/pages'):
                self.page(path[len('/pages'):].strip('/'))
            else:
                self.run({})

        def page(self, relative):
            """Benchmark listening pages, so they can be opened from the same address."""
            root = (HERE/'runs/pages').resolve()
            file = (root/relative).resolve()
            if file.is_dir() and (file/'index.html').exists() and relative:
                if not self.path.split('?')[0].endswith('/'):
                    # Without the slash the page's relative audio links resolve one level too high.
                    self.send_response(301); self.send_header('Location', f'/pages/{relative}/')
                    self.send_header('Content-Length', '0'); self.end_headers()
                    return
                file = file/'index.html'
            if not file.is_relative_to(root):
                return self.reply(404, 'text/plain', b'not found')
            if file == root:
                names = sorted(p.name for p in root.iterdir() if (p/'index.html').exists())
                links = ''.join(f'<li><a href="/pages/{n}/">{n}</a></li>' for n in names)
                return self.reply(200, 'text/html; charset=utf-8', f'<meta charset="utf-8"><h1>Listening pages</h1><ul>{links}</ul>'.encode())
            if not file.is_file():
                return self.reply(404, 'text/plain', b'not found')
            kind = {'.html': 'text/html; charset=utf-8', '.wav': 'audio/wav', '.json': 'application/json'}.get(file.suffix, 'application/octet-stream')
            data, span = file.read_bytes(), self.headers.get('Range', '')
            if span.startswith('bytes='):
                # Safari will not play audio from a server that ignores range requests.
                first, _, last = span[6:].split(',')[0].partition('-')
                start = int(first) if first else max(0, len(data)-int(last))
                end = min(int(last), len(data)-1) if first and last else len(data)-1
                chunk = data[start:end+1]
                self.send_response(206)
                self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(chunk)))
                self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}'); self.send_header('Accept-Ranges', 'bytes')
                self.end_headers(); self.wfile.write(chunk)
                return
            self.reply(200, kind, data)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            # Other devices may use benchmark targets only, never arbitrary paths on this machine.
            if self.path == '/api/start' and self.client_address[0] != '127.0.0.1' and body.get('target') not in app.targets:
                return self.reply(403, 'application/json', json.dumps({'error': 'File paths can only be used from the host machine'}).encode())
            self.run(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    print(f'Listener-guided search on http://{host}:{port}', flush=True)
    try:
        server.serve_forever()
    finally:
        if app.session:
            app.session.pool.close()
        app.renderer.close()


def warm(ids, jobs, polish=1500):
    """Precompute opening screens, with a longer polish than a live session can afford."""
    CACHE.mkdir(parents=True, exist_ok=True)
    library = Library(LIBRARY)
    with FastRenderer() as renderer:
        for target in benchmark.targets():
            if target['id'] not in ids or (CACHE/f'{target["id"]}.json').exists():
                continue
            reference = benchmark.reference(target, renderer)
            with RenderPool(Describe(reference), jobs) as pool:
                candidates = opening(reference, library, pool, polish=polish, extra=earlier_results(target['id']))
            (CACHE/f'{target["id"]}.json').write_text(json.dumps({'objective': VERSION, 'candidates': candidates}))
            print(target['id'], ', '.join(f'{c["synth"]} {c["score"]:.2f}' for c in candidates[:6]), flush=True)


PAGE = r'''<!doctype html><meta charset="utf-8"><title>Guided search · sfxmatch</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light dark;--fg:#1c1c1c;--bg:#fafaf8;--mut:#6b6b6b;--line:#d9d9d4;--acc:#2f6fde;--on:#fff}
@media(prefers-color-scheme:dark){:root{--fg:#ececec;--bg:#171717;--mut:#9a9a9a;--line:#3a3a3a;--acc:#6ea0ff;--on:#111}}
body{font:16px/1.45 system-ui,sans-serif;color:var(--fg);background:var(--bg);max-width:760px;margin:0 auto;padding:20px 16px}
h1{font-size:18px;margin:0 0 4px}.mut{color:var(--mut);font-size:14px}
.row{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--line);flex-wrap:wrap}
button,select,input{font:inherit;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:transparent;color:inherit}
button{cursor:pointer}button:disabled{opacity:.45;cursor:default}
button.play{min-width:150px;text-align:left}button.heard{border-color:var(--acc)}
button.go{background:var(--acc);border-color:var(--acc);color:var(--on)}
select{max-width:100%;flex:1;min-width:200px}input[type=text]{flex:1;min-width:200px}
nav{display:flex;gap:10px;align-items:center;margin:14px 0;flex-wrap:wrap}
kbd{border:1px solid var(--line);border-radius:4px;padding:0 5px;font-size:13px}
#busy{color:var(--acc)}.tag{font-size:13px;color:var(--mut)}
</style>
<h1>Guided search</h1>
<div class="mut">Play the reference, play the candidates, pick the closest. The next screen searches around your pick.</div>
<nav><select id="target"></select><button id="start" class="go">Start</button></nav>
<nav><input type="text" id="path" placeholder="…or a path to any audio file"><button id="startPath">Start with file</button></nav>
<div id="status" class="mut"></div><div id="busy"></div>
<div id="card"></div>
<nav id="tools" hidden>
 <button data-act="retry" title="Same search, new options">None is closer — more options (N)</button>
 <button data-act="wider">Wider</button><button data-act="finer">Finer</button>
 <button data-act="back">Back</button><button data-act="synths">Switch synth</button>
 <button data-act="more-synths" id="more">More synths</button>
</nav>
<div id="finish" hidden>
 <div class="row"><span>Finish: how close is the current sound?</span><span id="rate"></span></div>
 <div class="row"><select id="verdict" style="flex:0 1 auto"><option value="stopped">Stopping here</option>
  <option value="could-improve">Could get closer with more screens</option><option value="stuck">Stuck: this synth cannot get closer</option></select>
  <input type="text" id="note" placeholder="Note (optional)"><button id="preset">Download preset</button></div>
</div>
<p class="mut"><kbd>R</kbd> reference · <kbd>A</kbd>–<kbd>F</kbd> play · <kbd>Enter</kbd> pick the last one played · <kbd>N</kbd> none is closer.
Scale: 1 unrelated · 2 same family, wrong sound · 3 roughly similar · 4 close · 5 very close.
Picks are saved on this machine only. <a href="/pages/">Benchmark listening pages</a></p>
<script>
let S=null, last=null, audio=new Audio(), busy=false;
const $=id=>document.getElementById(id);
async function api(path,body){
  busy=true; $('busy').textContent='Searching…'; document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    const j=await r.json(); if(j.error) throw new Error(j.error); return j}
  catch(e){$('status').textContent=String(e.message||e); throw e}
  finally{busy=false; $('busy').textContent=''; document.querySelectorAll('button').forEach(b=>b.disabled=false)}
}
function play(src,button){audio.pause();audio=new Audio(src);audio.play();if(button)button.classList.add('heard')}
function draw(){
  const card=$('card'); card.innerHTML=''; last=null;
  const head=document.createElement('div'); head.className='row';
  const ref=document.createElement('button'); ref.className='play'; ref.textContent='▶ Reference (R)'; ref.onclick=()=>play(S.reference,ref);
  const title=document.createElement('span'); title.className='mut'; title.textContent=S.title; head.append(ref,title); card.append(head);
  S.candidates.forEach((c,i)=>{
    const row=document.createElement('div'); row.className='row';
    const b=document.createElement('button'); b.className='play'; b.textContent='▶ '+String.fromCharCode(65+i)+(c.current?' · current':'');
    b.onclick=()=>{last=i;play(c.wav,b)};
    const pick=document.createElement('button'); pick.textContent=c.current?'Still the closest':'Closest'; pick.onclick=()=>act('pick',c.id);
    const tag=document.createElement('span'); tag.className='tag'; tag.textContent=c.synth;
    row.append(b,pick,tag); card.append(row)});
  $('tools').hidden=false; $('finish').hidden=!S.synth; $('more').hidden=S.kind!=='synths';
  $('status').textContent=S.kind==='synths'?'Choose the synth that gets nearest.':('Screen '+S.screens+' · '+S.synth+' · step size '+S.sigma);
  play(S.reference,ref);
}
async function start(target){ if(!target) return; S=await api('/api/start',{target}); draw() }
async function act(action,pick){ if(!S||busy) return; S=await api('/api/act',{session:S.session,action,pick}); draw() }
$('start').onclick=()=>start($('target').value); $('startPath').onclick=()=>start($('path').value.trim());
document.querySelectorAll('#tools button').forEach(b=>b.onclick=()=>act(b.dataset.act));
for(let r=1;r<=5;r++){const b=document.createElement('button'); b.textContent=r; b.style.marginRight='6px';
  b.onclick=async()=>{const j=await api('/api/finish',{session:S.session,rating:r,verdict:$('verdict').value,note:$('note').value}); $('status').textContent='Saved '+r+'/5 → '+j.saved}; $('rate').append(b)}
$('preset').onclick=async()=>{const j=await api('/api/preset',{session:S.session}); const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(j,null,1)],{type:'application/json'})); a.download=S.session+'.bcol'; a.click()};
document.onkeydown=e=>{ if(!S||busy||['INPUT','SELECT'].includes(e.target.tagName)) return; const k=e.key.toLowerCase(), plays=document.querySelectorAll('#card .play');
  if(k==='r') play(S.reference,plays[0]);
  else if(k>='a'&&k<='f'&&k.charCodeAt(0)-97<S.candidates.length){const i=k.charCodeAt(0)-97;last=i;play(S.candidates[i].wav,plays[i+1])}
  else if(k==='enter'&&last!==null) act('pick',S.candidates[last].id);
  else if(k==='n') act('retry')};
api('/api/targets').then(j=>{for(const t of j.targets){const o=document.createElement('option'); o.value=t.id; o.textContent=(t.probe?'★ ':'')+t.id+' · '+t.title; $('target').append(o)}});
</script>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', nargs='?', default='serve', choices=['serve', 'warm'])
    parser.add_argument('targets', nargs='*', help='for warm: benchmark ids')
    parser.add_argument('--port', type=int, default=8765); parser.add_argument('--jobs', type=int)
    parser.add_argument('--host', default='127.0.0.1', help='0.0.0.0 to allow other devices on the network')
    parser.add_argument('--polish', type=int, default=1500, help='for warm: CMA-ES renders per synth')
    args = parser.parse_args()
    if args.command == 'warm':
        warm(set(args.targets), args.jobs, args.polish)
    else:
        serve(args.port, args.jobs, args.host)


if __name__ == '__main__':
    main()
