"""Local CLAP audio-to-UCS proposals, separate from authoritative metadata.

Run with the isolated CUDA Python under <root>/_catalogue/models/runtime.
No audio is uploaded and no catalogue database or original recording is edited.
Similarity scores rank prompts; they are NOT probabilities or validation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time

MODEL = 'laion/clap-htsat-unfused'
SAMPLE_RATE = 48000
CLIP_SECONDS = 10.0
PROMPT_VERSION = 'ucs-natural-synthesized-ensemble-v2'
PROMPTS_PER_LEAF = 3


def prompts_for(taxonomy, broad=False):
    """Natural and electronic views, excluding non-acoustic ARCHIVED."""
    labels, prompts = [], []
    if broad:
        try:
            from .acoustic_prompts import CATEGORY_DESCRIPTIONS
        except ImportError:
            from acoustic_prompts import CATEGORY_DESCRIPTIONS
        categories = sorted({x['category'] for x in taxonomy} - {'ARCHIVED'})
        for category in categories:
            description = CATEGORY_DESCRIPTIONS[category]
            labels.append(dict(category=category, catid=None, subcategory=''))
            prompts.extend([f'The sound of {description}.', f'An audio recording of {description}.',
                            f'This is {description}.'])
        return labels, prompts
    for leaf in taxonomy:
        if leaf['category'] == 'ARCHIVED':
            continue
        labels.append(leaf)
        name = f"{leaf['category'].lower()}, {leaf['subcategory'].lower()}"
        prompts.extend([f'The sound of {name}.',
                        f"The sound of {name}. {leaf['explanation']}",
                        f'A short synthesized electronic retro video game sound effect imitating {name}.'])
    return labels, prompts


def decode_windows(root, record):
    """Deterministic beginning/middle/end windows, bounded to 30 seconds."""
    import numpy as np
    duration = float(record.get('duration') or CLIP_SECONDS)
    starts = [0.0]
    if duration > CLIP_SECONDS:
        starts += [max(0.0, (duration - CLIP_SECONDS) / 2), max(0.0, duration - CLIP_SECONDS)]
    starts = sorted(set(round(x, 6) for x in starts))
    path = (root / record['path']).resolve()
    if not path.is_relative_to(root.resolve()) or '_catalogue' in path.relative_to(root.resolve()).parts:
        raise ValueError('Source must be an original recording inside the sound root')
    native = os.path.abspath(str(path))
    if os.name == 'nt' and not native.startswith('\\\\?\\'):
        native = '\\\\?\\UNC\\' + native[2:] if native.startswith('\\\\') else '\\\\?\\' + native
    windows = []
    for start in starts:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(start),
                                 '-i', native, '-t', str(CLIP_SECONDS), '-vn', '-ac', '1',
                                 '-ar', str(SAMPLE_RATE), '-f', 'f32le', '-'],
                                capture_output=True, timeout=60, check=True)
        samples = np.frombuffer(result.stdout, dtype='<f4').copy()
        if not len(samples) or not np.isfinite(samples).all():
            raise ValueError('Decoded audio is empty or contains nonfinite samples')
        windows.append((start, samples))
    return windows


def result_row(record, labels, scores, window_scores, windows, provenance):
    """Keep ranked multi-label hypotheses and honest review/training state."""
    import numpy as np
    ranked = np.argsort(scores)[::-1][:5]
    best = labels[int(ranked[0])]
    alternatives = [dict(catid=labels[int(i)]['catid'], category=labels[int(i)]['category'],
                         subcategory=labels[int(i)]['subcategory'], cosine_similarity=round(float(scores[i]), 6))
                    for i in ranked]
    segment_predictions = []
    measurements = []
    for (start, samples), values in zip(windows, window_scores):
        peak = float(np.abs(samples).max())
        rms = float(np.sqrt(np.square(samples, dtype=np.float64).mean()))
        measurements.append(dict(start_seconds=start, rms=rms, peak=peak,
                                 near_silent=peak <= 1e-7))
        top = np.argsort(values)[::-1][:3]
        segment_predictions.append(dict(start_seconds=start, duration_seconds=len(samples) / SAMPLE_RATE,
            candidates=[dict(catid=labels[int(i)]['catid'], category=labels[int(i)]['category'],
                             cosine_similarity=round(float(values[i]), 6)) for i in top]))
    top_score = float(scores[ranked[0]])
    margin = top_score - float(scores[ranked[1]])
    # Always low: UCS was not the model's training taxonomy and no human listened.
    proposal_name = best['category'] + (f" / {best['subcategory']}" if best['subcategory'] else '')
    reason = (f'Local CLAP audio similarity proposal: {proposal_name}; '
              f'cosine {top_score:.3f}, next-candidate margin {margin:.3f}. '
              'Uncalibrated model hypothesis; listening review required. '
              'Long recordings are sampled at beginning, middle and end; other events may be missed.')
    result = dict(id=record['id'], description_id=record['id'], path=record['path'], sha256=record['sha256'],
                category=best['category'], catid=best['catid'], confidence='low', reason=reason,
                model=provenance, cosine_similarity=round(top_score, 6), margin=round(margin, 6),
                alternatives=alternatives, segment_predictions=segment_predictions,
                review_needed=True, audio_verified=False, training_eligible=False,
                expected_category=record.get('category'), expected_catid=record.get('catid'),
                measurements=measurements, silent=all(x['near_silent'] for x in measurements),
                accepted=False, label_status='provisional', evidence_type='local_audio_model')
    if result['silent']:
        result.update(category=None, catid=None, confidence='none', alternatives=[], segment_predictions=[],
                      reason='All sampled windows are effectively silent (absolute PCM peak <= 1e-7); no acoustic category proposed.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--revision', default='8fa0f1c6d0433df6e97c127f64b2a1d6c0dcda8a')
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--include-labelled', action='store_true')
    parser.add_argument('--broad', action='store_true', help='Use simple acoustic descriptions of broad UCS categories')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    work = root / '_catalogue' / 'work'
    work.mkdir(parents=True, exist_ok=True)
    output = args.output or work / 'acoustic-proposals.jsonl'
    if not output.resolve().is_relative_to((root / '_catalogue').resolve()):
        raise ValueError('Derived output must stay inside <root>/_catalogue')
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = root / '_catalogue' / 'models' / 'huggingface'
    os.environ['HF_HOME'] = str(cache)
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    import numpy as np
    import torch
    import transformers
    from transformers import ClapModel, ClapProcessor
    torch.set_num_threads(4)
    torch.manual_seed(0)
    np.random.seed(0)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(json.dumps(dict(stage='load_model', device=device, model=args.model)), flush=True)
    model = ClapModel.from_pretrained(args.model, revision=args.revision, cache_dir=str(cache),
                                     weights_only=True).eval().to(device)
    processor = ClapProcessor.from_pretrained(args.model, revision=args.revision, cache_dir=str(cache))
    revision = getattr(model.config, '_commit_hash', None) or args.revision
    taxonomy = json.loads((root / '_catalogue' / 'ucs.json').read_text(encoding='utf-8'))
    labels, prompts = prompts_for(taxonomy, args.broad)
    prompt_hash = hashlib.sha256(json.dumps(prompts, ensure_ascii=False).encode()).hexdigest()
    provenance = dict(name=args.model, revision=revision,
                      prompt_version='ucs-broad-acoustic-descriptions-v1' if args.broad else PROMPT_VERSION,
                      candidate_level='broad_category' if args.broad else 'subcategory',
                      prompt_sha256=prompt_hash, candidate_count=len(labels), torch=torch.__version__,
                      transformers=transformers.__version__, device=device, sample_rate=SAMPLE_RATE,
                      window_seconds=CLIP_SECONDS, window_policy='beginning_middle_end_max_3',
                      score='cosine similarity of L2-normalised CLAP embeddings; not probability',
                      aggregation=('mean of three acoustic description templates per category; max across audio windows' if args.broad
                                   else 'mean of natural/explanation/synthesized text prompts per leaf; max across audio windows'),
                      source='https://huggingface.co/' + args.model)
    (work / 'acoustic-model.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    (work / 'acoustic-prompts.json').write_text(json.dumps(dict(labels=labels, prompts=prompts), indent=2), encoding='utf-8')
    text_cache = cache / f'text-{hashlib.sha256((args.model + revision + prompt_hash).encode()).hexdigest()[:24]}.npy'
    if text_cache.exists():
        text_features = torch.from_numpy(np.load(text_cache)).to(device)
    else:
        embeddings = []
        with torch.inference_mode():
            for offset in range(0, len(prompts), 32):
                inputs = processor(text=prompts[offset:offset + 32], padding=True, truncation=True,
                                   return_tensors='pt').to(device)
                features = model.get_text_features(**inputs)
                embeddings.append(torch.nn.functional.normalize(features, dim=-1).cpu())
        text_features = torch.cat(embeddings).to(device)
        np.save(text_cache, text_features.cpu().numpy())
    records = json.loads((args.input or root / '_catalogue' / 'site' / 'catalogue.json').read_text(encoding='utf-8'))
    records = [r for r in records if args.include_labelled or not r.get('category')]
    if args.sample:
        random.Random(20261010).shuffle(records)
    if args.limit:
        records = records[:args.limit]
    existing = set()
    if args.resume and output.exists():
        for line in output.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:
                    item = json.loads(line)
                    if item.get('model', {}).get('prompt_sha256') == prompt_hash and item.get('model', {}).get('revision') == revision:
                        existing.add((item['id'], item['sha256']))
                    else:
                        raise ValueError('Resume provenance differs; use a fresh output to preserve the earlier run')
                except (ValueError, KeyError):
                    raise ValueError('Resume file contains malformed/incomplete JSON; preserve and repair before resuming')
    records = [r for r in records if (r['id'], r['sha256']) not in existing]
    audio_cache = cache / 'audio-embeddings' / revision[:12]
    audio_cache.mkdir(parents=True, exist_ok=True)
    print(json.dumps(dict(stage='classify', rows=len(records), resumed=len(existing), leaves=len(labels))), flush=True)
    started, processed, errors = time.monotonic(), 0, []
    with output.open('a' if args.resume else 'w', encoding='utf-8') as stream, ThreadPoolExecutor(max_workers=args.workers) as pool:
        for offset in range(0, len(records), args.batch_size):
            batch = records[offset:offset + args.batch_size]
            jobs = [pool.submit(decode_windows, root, r) for r in batch]
            good, windows_all, arrays = [], [], []
            for r, job in zip(batch, jobs):
                try:
                    windows = job.result()
                    good.append(r)
                    windows_all.append(windows)
                    arrays.extend(samples for _, samples in windows)
                except Exception as exc:
                    errors.append(dict(id=r['id'], path=r['path'], error=str(exc)))
                    print(json.dumps(dict(stage='decode_error', path=r['path'], error=str(exc))), flush=True)
            if arrays:
                chunks, audio_chunks = [], []
                with torch.inference_mode():
                    for pos in range(0, len(arrays), args.batch_size):
                        inputs = processor(audio=arrays[pos:pos + args.batch_size], sampling_rate=SAMPLE_RATE,
                                           padding='repeatpad', return_tensors='pt').to(device)
                        audio = torch.nn.functional.normalize(model.get_audio_features(**inputs), dim=-1)
                        audio_chunks.append(audio.cpu().numpy())
                        similarities = (audio @ text_features.T).reshape(-1, len(labels), PROMPTS_PER_LEAF).mean(dim=-1)
                        chunks.append(similarities.cpu().numpy())
                all_scores = np.concatenate(chunks)
                all_audio = np.concatenate(audio_chunks)
                cursor = 0
                for r, windows in zip(good, windows_all):
                    scores = all_scores[cursor:cursor + len(windows)]
                    features = all_audio[cursor:cursor + len(windows)]
                    cursor += len(windows)
                    row = result_row(r, labels, scores.max(axis=0), scores, windows, provenance)
                    np.savez_compressed(audio_cache / (r['sha256'] + '.npz'), features=features,
                                        starts=np.array([x[0] for x in windows]),
                                        rms=np.array([x['rms'] for x in row['measurements']]),
                                        peak=np.array([x['peak'] for x in row['measurements']]))
                    stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                    processed += 1
                stream.flush()
            print(json.dumps(dict(stage='progress', processed=processed, total=len(records), errors=len(errors),
                                  elapsed_seconds=round(time.monotonic() - started, 1))), flush=True)
    report = dict(processed=processed, resumed=len(existing), errors=errors,
                  elapsed_seconds=round(time.monotonic() - started, 2), output=str(output), model=provenance)
    output.with_suffix('.report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
