"""Diagnostic local audio captions; never authoritative UCS assignments.

Uses a standard Whisper model and explicitly constructs the captioning decoder
prefix documented by MU-NLPC. No downloaded Python/model code is executed.
"""
import argparse
import json
import os
from pathlib import Path
import time

try:
    from .acoustic import decode_windows
except ImportError:
    from acoustic import decode_windows

MODEL = 'MU-NLPC/whisper-small-audio-captioning'
REVISION = 'a75f70c313402094fce2c391ef0f00baf595c12f'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--style', default='clotho > caption: ')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((args.root / '_catalogue').resolve()):
        raise ValueError('Derived output must stay inside <root>/_catalogue')
    cache = args.root / '_catalogue' / 'models' / 'huggingface'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    import numpy as np
    import torch
    from scipy.signal import resample_poly
    from transformers import WhisperForConditionalGeneration, WhisperFeatureExtractor, WhisperTokenizer
    from transformers.generation.utils import GenerationMixin
    torch.set_num_threads(4)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = WhisperForConditionalGeneration.from_pretrained(MODEL, revision=REVISION, cache_dir=str(cache),
                                                           weights_only=True).eval().to(device)
    extractor = WhisperFeatureExtractor.from_pretrained(MODEL, revision=REVISION, cache_dir=str(cache))
    tokenizer = WhisperTokenizer.from_pretrained(MODEL, revision=REVISION, cache_dir=str(cache), language='en', task='transcribe')
    # Equivalent to the publisher's custom generate override, using standard HF
    # GenerationMixin and an explicit decoder prefix rather than remote code.
    prefix = [model.config.decoder_start_token_id]
    prefix.extend(token for _, token in tokenizer.get_decoder_prompt_ids(language='en', task='transcribe', no_timestamps=True))
    prefix.extend(tokenizer(args.style, add_special_tokens=False).input_ids)
    model.generation_config.forced_decoder_ids = None
    model.generation_config.return_timestamps = False
    model.generation_config.language = None
    model.generation_config.task = None
    rows = json.loads(args.input.read_text(encoding='utf-8'))
    if args.limit:
        rows = rows[:args.limit]
    provenance = dict(name=MODEL, revision=getattr(model.config, '_commit_hash', None),
                      style=args.style, generation='standard HF GenerationMixin; explicit caption-style decoder prefix',
                      source='https://huggingface.co/' + MODEL,
                      preprocessing='first <=10 seconds, 48k mono ffmpeg decode then 16k polyphase resample; no repetition',
                      max_new_tokens=64, beams=3, review_needed=True, training_eligible=False)
    started, processed = time.monotonic(), 0
    with args.output.open('w', encoding='utf-8') as output:
        for offset in range(0, len(rows), args.batch_size):
            batch = rows[offset:offset + args.batch_size]
            good, arrays = [], []
            for row in batch:
                try:
                    samples = decode_windows(args.root, row)[0][1]
                    arrays.append(resample_poly(samples, 1, 3).astype(np.float32))
                    good.append(row)
                except Exception as exc:
                    print(json.dumps(dict(error=str(exc), path=row['path'])), flush=True)
            if not good:
                continue
            features = extractor(arrays, sampling_rate=16000, return_tensors='pt').input_features.to(device)
            decoder = torch.tensor(prefix, device=device).unsqueeze(0).expand(len(good), -1)
            with torch.inference_mode():
                ids = GenerationMixin.generate(model, inputs=features, decoder_input_ids=decoder,
                    generation_config=model.generation_config, max_new_tokens=64, num_beams=3, do_sample=False)
            captions = tokenizer.batch_decode(ids[:, len(prefix):], skip_special_tokens=True)
            for row, caption in zip(good, captions):
                record = dict(id=row['id'], path=row['path'], sha256=row['sha256'], caption=caption.strip(),
                              expected_category=row.get('category'), expected_catid=row.get('catid'),
                              model=provenance, audio_verified=False, review_needed=True, training_eligible=False)
                output.write(json.dumps(record, ensure_ascii=False) + '\n')
                processed += 1
            output.flush()
            print(json.dumps(dict(processed=processed, total=len(rows), elapsed_seconds=round(time.monotonic()-started, 1))), flush=True)


if __name__ == '__main__':
    main()
