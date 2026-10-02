#!/usr/bin/env python3
"""Show the reviewed species without presenting discovery outliers as presets."""
import hashlib
import json
import re
import shutil
import wave
from pathlib import Path
from runtime_provenance import require_current_runtime

def build_curated(directory,bank_path):
    from build_bank import HTML
    directory=Path(directory);report=json.loads((directory/'curated.json').read_text())
    checks=report['validation'];digest=hashlib.sha256(Path(bank_path).read_bytes()).hexdigest()
    require_current_runtime(report);require_current_runtime(checks)
    if checks['bank_sha256']!=digest or checks['failures'] or not checks['count']:
        raise ValueError('Measure and validate the current bank before building its catalogue')
    # Preserve the original complete survey, including its rejected preset outliers.
    archive=directory/'archive.html'
    if not archive.exists():
        old=(directory/'index.html').read_text()
        if '"revision":2' in old:raise ValueError('Original discovery catalogue missing; do not archive a curated page')
        old=old.replace('Transfxr: a wider palette','Transfxr discovery archive').replace('Families.bcol','Discovery.bcol')
        old=old.replace('<header><h1>','<header><p><a href="index.html">← Revised preset families</a></p><p>This is the original 512-sound exploration, before listening refinement. Its cluster labels are historical; outliers here are not current preset exemplars.</p><h1>')
        old=old.replace('</script>',"const requestedSource=new URLSearchParams(location.search).get('source');if(requestedSource){document.getElementById('query').value=requestedSource;render();}</script>")
        archive.write_text(old)
        shutil.copyfile(directory/'Families.bcol',directory/'Discovery.bcol')
    # The revised reel is rebuilt below. The archive's tour still plays its own
    # original T-number centers, but must not download the revised C-number reel.
    archive.write_text(archive.read_text().replace(' <a href="families_showcase.wav" download>Download the family reel</a>',''))
    sounds={s['id']:s for s in report['sounds']};families=report['groups'];count=len(families)
    page=HTML.replace('512 rendered sounds, grouped by measured audio.','Curated voices revised from your listening feedback.')
    page=page.replace('<b>512</b>audible sounds',f'<b>{report["count"]}</b>curated exemplars')
    page=page.replace('<b>16</b>named families',f'<b>{count}</b>revised families')
    page=page.replace('<div class="stat"><b id="prototypeCount"></b>shipped exemplars</div>','<div class="stat"><b>512</b>discovery sounds in the archive</div>')
    page=page.replace('<div class="stat"><b>4</b>audio feature groups</div>','')
    page=page.replace('These names describe measured sound profiles and are open to revision by ear. Similar families overlap; clustering is a way to organize this continuous sound space, not an objective list of sound types. Every sound below is available to audition.',
        'Each preset now has a narrower voice: short taps stay short, wavering calls keep their quiver, and sand and air have different textures. The samples below are the revised bank, with source links back to the discovery survey. Your listening notes guide these changes; this pass is ready to audition.')
    page=page.replace('Tour all 16 families',f'Tour all {count} families')
    page=page.replace('All survey sounds','All curated exemplars').replace('Boundary examples','Least typical exemplars')
    page=page.replace('Closest to family center','Most typical first')
    page=page.replace('document.getElementById(\'prototypeCount\').textContent=DATA.groups.reduce((n,g)=>n+g.exemplars.length,0);','')
    page=page.replace("if(DATA.validation){const v=DATA.validation;document.getElementById('validation').textContent=`Fresh variation check: ${v.count} audible, unclipped samples; ${Math.round(v.closest_family_fraction*100)}% closest to the intended family and ${Math.round(v.within_20_percent_of_closest*100)}% within 20% of the closest-family distance. This checks measured resemblance, not aesthetic quality.`;}",
        "if(DATA.validation){const v=DATA.validation;document.getElementById('validation').textContent=`${v.exemplar_count} bank exemplars and ${v.count} fresh variations passed checks for duration, envelope, noise, brightness and sustained wobble. These verify the specified traits; listening remains the quality test.`;}")
    page=page.replace('<td>${s.id} ${DATA.groups[s.cluster].exemplars.includes(s.id)?\'<span class="badge">exemplar</span>\':\'\'}</td>',
        '<td>${s.id}<br><a href="archive.html?source=${s.survey_source}">${s.survey_source} source</a></td>')
    page=page.replace('${g.count} sounds ·','${g.count} exemplars ·').replace(' · ${g.exemplars.length} exemplars','')
    method='''<details><summary>Listening refinement and reproducibility</summary><p class="method">The original 512-sound clustering helped explore the space. Listening feedback showed that broad acoustic similarity was insufficient for a preset voice. The revised bank retains the successful bass plucks, rubber clicks and low calls, then curates the other complete sound states with duration, timbre and trajectory limits. The short banks are dry; wavering calls use sustained eight-Hz vibrato; soft pips use a clean sine voice; sand is a bright quick spray and air a dark slow breath. Generic rising/falling groups have become specific arcade and bubble voices. “Hear 6 variants” compares typical revised bank exemplars. Every bank member remains available in the table.</p><p id="validation"></p><p><a href="archive.html">Original 512-sound discovery archive</a> · <a href="README.md">Method and reproduction</a> · <a href="curated.json">Curated states and source IDs</a> · <a href="curated-validation.json">Trait checks</a> · <a href="Families.bcol" download>Editable revised bank</a></p></details>'''
    page=re.sub(r'<details>.*?</details>',lambda _:method,page,flags=re.S)
    page=page.replace('__DATA__',json.dumps(report,separators=(',',':')).replace('</','<\\/'))
    (directory/'index.html').write_text(page)
    files=[];frames=[];reel=[];offset=0
    for family in families:
        for id in family['exemplars']:
            params=json.dumps(sounds[id]['params'],separators=(',',':'));files.append([family['name'].replace(' ','')+'_'+id,params,params])
        sound=sounds[family['exemplars'][0]]
        with wave.open(str(directory/sound['audio']),'rb') as audio:
            frames.extend([audio.readframes(audio.getnframes()),b'\x00\x00'*11025]);duration=audio.getnframes()/44100
        reel.append(dict(id=sound['id'],family=family['name'],start=offset,duration=duration));offset+=duration+.25
    with wave.open(str(directory/'families_showcase.wav'),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(44100);audio.writeframes(b''.join(frames))
    (directory/'showcase.json').write_text(json.dumps(reel,indent=2)+'\n')
    keys=list(next(iter(sounds.values()))['params']);collection={'Transfxr':{'files':files,'selected_file_index':0,'create_new_sound':True,'play_on_change':True,'locked_params':{key:key=='masterVolume' for key in keys}},'active_tab_index':2}
    (directory/'Families.bcol').write_text(json.dumps(collection,indent=2)+'\n')
    rows='\n'.join(f"| {f['name']} | {f['count']} | {f['tip']} |" for f in families)
    (directory/'README.md').write_text(f'''# Transfxr listening refinement

[Audition the revised bank](index.html), [download its editable collection](Families.bcol), or play [the family reel](families_showcase.wav). The reel follows the table order; [showcase.json](showcase.json) gives timestamps. [The original survey archive](archive.html) preserves all 512 discovery sounds and the earlier exploratory labels.

The user's listening review found that short sound labels admitted long tails, some wavering calls had no wobble, soft pips were rough, sand included pitched outliers, sand/air overlapped, and direction-only groups had no common voice. The revised bank has {count} species and {report['count']} exemplars. Bass Plucks and Rubber Clicks keep their successful surveyed character. Submarine Calls becomes Mournful Calls; Static Flecks becomes Radio Spits. Descending Sweeps and Rising Bloops become concrete Arcade Zaps and Bubble Pops, Falling Thumps is retired, and Reverse Bloops becomes a tightly defined Bubble Swells voice.

| Family | Exemplars | Character |
| --- | ---: | --- |
{rows}

## How this pass works

Family profiles are explicit in `tools/preset_survey/family_profiles.json`, authored by `create_profiles.py`. They select central full states from the measured survey and monotonically remap selected controls into the intended voice, retaining their joint ordering. Fixed oscillator/curve choices and bounded intervals preserve the family character. Successful original banks keep their states. Every C-number records its original T-number in [curated.json](curated.json); editorial projections are recorded per family. Exact curated PCM and editable params are rendered from the current synth.

Runtime generation chooses whole curated states, blends compatible trajectories and nudges controls, then enforces each family's limits. Constraints apply before SynthBase respects user locks. A deliberately locked control may therefore change the resulting voice. Dry short species keep zero echo. The first six catalogue examples are typical members of the revised bank, while all exemplars remain inspectable.

All {report['count']} exemplars and {checks['count']} fresh seeded variations passed finite/audible/unclipped and family-trait checks. Checks measure whole rendered durations, spectral separation for sand/air and soft pips, and actual eight-Hz pitch motion for wavering calls. Minimum fresh RMS is {checks['minimum_rms']:.4f}; maximum peak is {checks['maximum_peak']:.3f}. [Per-family results](curated-validation.json) are tied by SHA-256 to the bank, sampler, renderer and parameter validation sources. Rebuilding rejects stale measurements. These verify traits, not aesthetic quality; this revision incorporates the user's listening notes without claiming another human ear review.

## Reproduce

Use Node.js and Python 3 with NumPy, from the repository root. The saved discovery corpus and analysis are inputs to this editorial pass; they remain unmodified.

```sh
python3 tools/preset_survey/create_profiles.py
node tools/preset_survey/curate_families.js examples/Transfxr/survey
node tools/preset_survey/validate_families.js /private/tmp/transfxr-listening-validation 32
python3 tools/preset_survey/measure_curated.py examples/Transfxr/survey /private/tmp/transfxr-listening-validation
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
node --test tests/preset-character.test.js tests/preset-family.test.js tests/preset-survey.test.js
python3 -m unittest discover -s tools/preset_survey -p 'test_*.py'
```

Curated WAVs and the reel are generated locally and ignored by Git; a fresh checkout runs the commands above before catalogue playback. The runtime JavaScript bank works immediately. To restore archive audio from its saved original states with the current renderer, run `node tools/preset_survey/render_saved_corpus.js examples/Transfxr/survey`. This leaves `corpus.json` and `analysis.json` unchanged. Serve the repository root to use editor links.
''')
    print(f'Built revised catalogue: {count} families, {report["count"]} exemplars, {checks["count"]} fresh trait checks')
