"""Local listening galleries and app-editable collections."""
import html
import json
from pathlib import Path
import soundfile as sf
from .features import prepare

STYLE = '''body{font:16px system-ui;background:#181d25;color:#edf0f4;max-width:1180px;margin:40px auto;padding:0 24px}a{color:#a9d4ff}h1{font-size:30px}h2{font-size:21px}p{line-height:1.6;color:#bfcbd8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}article{padding:18px;border:1px solid #475463;border-radius:10px;background:#232c37}audio{width:100%;margin-top:12px}small{display:block;margin-top:10px;color:#bac6d4}table{width:100%;border-collapse:collapse;table-layout:fixed}td{overflow-wrap:anywhere}audio{min-width:0}th:nth-child(1){width:40%}th:nth-child(2){width:32%}@media(max-width:760px){thead{display:none}table,tbody,tr,td{display:block;width:auto}tr{margin:18px 0;border:1px solid #475463;border-radius:10px;padding:8px}td{border:0!important}td:nth-child(3)::before{content:"Winner distance: "}td:nth-child(4)::before{content:"Bfxr distance: "}}td,th{text-align:left;padding:12px;border-bottom:1px solid #475463}summary{cursor:pointer}pre{white-space:pre-wrap;font-size:12px}'''


def _page(title, body):
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><body>{body}<script>document.addEventListener("play",e=>{{for(const a of document.querySelectorAll("audio"))if(a!==e.target)a.pause()}},true)</script></body></html>'


def add_preset(collection, candidate, name):
    synth = candidate['synth']
    group = collection.setdefault(synth, {'files':[], 'selected_file_index':0,
        'create_new_sound':True,'play_on_change':True,'locked_params':{'masterVolume':True}})
    params = json.dumps(candidate['params'])
    group['files'].append([name, params, params])
    collection.setdefault('active_tab_name', synth)


def export_match(output, target, result, source):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    sf.write(output/'target.wav', prepare(target)*.5, 44100, subtype='PCM_16')
    collection, cards, saved = {}, [], []
    for rank, row in enumerate(result['candidates'], 1):
        file = f'{rank:02d}-{row["synth"]}.wav'
        sf.write(output/file, prepare(row['wave'])*.5, 44100, subtype='PCM_16')
        add_preset(collection, row, f'{source["name"]} · {row["synth"]}')
        record = {k:v for k,v in row.items() if k != 'wave'}
        record['file'] = file
        saved.append(record)
        cards.append(f'<article><strong>{rank}. {html.escape(row["synth"])}</strong><audio controls preload="none" src="{file}"></audio><small>Distance {row["score"]:.3f} · initial {row["initial_score"]:.3f}</small><details><summary>Score components</summary><pre>{html.escape(json.dumps(row["components"],indent=2))}</pre></details></article>')
    report = {k:v for k,v in result.items() if k!='candidates'} | {'source':source,'candidates':saved}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'matches.bcol').write_text(json.dumps(collection, indent=2)+'\n')
    title = source['name']
    body = f'<h1>{html.escape(title)}</h1><p>Automatic multi-synth recreations. Lower distance is better under a heuristic auditory metric; listening remains the quality check. Playback is peak-normalized and silence-trimmed.</p><p><a href="matches.bcol" download>Download editable collection</a> · <a href="report.json">Scores and parameters</a></p><article><strong>Reference</strong><audio controls preload="none" src="target.wav"></audio></article><h2>Ranked synths</h2><div class="grid">{"".join(cards)}</div>'
    (output/'index.html').write_text(_page(title, body))
    return report


def export_benchmark(output, records, metadata):
    output = Path(output)
    winners, rows = {}, []
    gains, synth_counts = [], {}
    for record in records:
        candidates = record['candidates']
        best = candidates[0]
        baseline = next((r for r in candidates if r['synth']=='Bfxr'), None)
        if baseline:
            gains.append((baseline['score']-best['score'])/max(baseline['score'],1e-9))
        synth_counts[best['synth']] = synth_counts.get(best['synth'],0)+1
        add_preset(winners, best, record['source']['name'])
        folder = record['folder']
        name = html.escape(record['source']['name'])
        score = baseline['score'] if baseline else float('nan')
        rows.append(f'<tr><td><a href="{folder}/index.html">{name}</a><audio controls preload="none" src="{folder}/target.wav"></audio></td><td>{best["synth"]}<audio controls preload="none" src="{folder}/{best["file"]}"></audio></td><td>{best["score"]:.3f}</td><td>{score:.3f}</td></tr>')
    import numpy as np
    stats = {'targets':len(records),'winner_counts':synth_counts,
             'mean_relative_distance_reduction':float(np.mean(gains)) if gains else None,
             'median_relative_distance_reduction':float(np.median(gains)) if gains else None,
             'strict_improvements':sum(g>1e-5 for g in gains)}
    (output/'results.json').write_text(json.dumps({'metadata':metadata,'summary':stats,'results':records},indent=2)+'\n')
    (output/'winners.bcol').write_text(json.dumps(winners,indent=2)+'\n')
    extras = ''
    if (output/'six-pairs.wav').exists():
        extras += '<article><strong>Six quick comparisons · reference then recreation</strong><audio controls preload="none" src="six-pairs.wav"></audio></article>'
    if (output/'audit.json').exists():
        audit = json.loads((output/'audit.json').read_text())['summary']
        extras += f'<p>Independent metric check: {audit["legacy_metric_wins"]} wins, {audit["legacy_metric_ties"]} ties, {audit["legacy_metric_losses"]} losses versus Bfxr. <a href="audit.json">Audit details</a>. Human listening has not been scored.</p>'
    body = f'<h1>Multi-synth approximation lab</h1><p>{len(records)} reference sounds and automatic recreations. Listen for likeness and useful surprises; open any row for alternative synths.</p><p><a href="winners.bcol" download>Editable winners</a> · <a href="results.json">Full experiment data</a></p>{extras}<details><summary>How to read the scores</summary><p>Lower is closer under a heuristic audio metric. Bfxr gets the same per-preset sample count and per-expert refinement budget. Multi-synth search uses more total renders; this is not an equal-compute comparison with the old neural matcher. Scores are not percentages of audible likeness.</p></details><table><thead><tr><th>Reference / alternatives</th><th>Selected recreation</th><th>Distance</th><th>Bfxr distance</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    (output/'index.html').write_text(_page('Multi-synth approximation lab',body))
    return stats
