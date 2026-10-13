"""Offline Qwen audio descriptions with explicit uncertainty, no UCS assignment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

try:
    from . import acoustic
except ImportError:
    import acoustic

MODEL = 'Qwen/Qwen2.5-Omni-3B'
REVISION = 'f75b40e3da2003cdd6e1829b1f420ca70797c34e'
PIPELINE_VERSION = 'qwen-offline-leftpad-conditional-repeat-v1'
PROMPT = (
    'Describe this isolated sound-effect sample in one or two concise English sentences. '
    'Describe only what you hear: its timbre, pitch or noise, attack and decay. '
    'Name a broad acoustic family only if clear. Do not invent a scene, a physical source, or its use in a game. '
    'If the source is unclear, say unidentified source. Stop after the description.'
)
SYSTEM = 'You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--batch-size', type=int, default=2)
    parser.add_argument('--min-seconds', type=float, default=1.0)
    parser.add_argument('--short-policy', choices=['pad', 'repeat'], default='pad')
    parser.add_argument('--official-wrapper', action='store_true')
    parser.add_argument('--prompt', default=PROMPT)
    parser.add_argument('--max-seconds', type=float, default=10)
    parser.add_argument('--verbose-features', action='store_true')
    parser.add_argument('--repeat-below-seconds', type=float, default=0)
    parser.add_argument('--repeat-seconds', type=float, default=2)
    args = parser.parse_args()
    acoustic.CLIP_SECONDS = args.max_seconds
    if not args.output.resolve().is_relative_to((args.root / '_catalogue').resolve()):
        raise ValueError('Derived output must stay inside <root>/_catalogue')
    records = json.loads(args.input.read_text(encoding='utf-8'))
    if args.limit:
        records = records[:args.limit]
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    import numpy as np
    import torch
    import transformers
    from scipy.signal import resample_poly
    from transformers import Qwen2_5OmniConfig, Qwen2_5OmniThinkerForConditionalGeneration, Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
    torch.set_num_threads(6)
    torch.manual_seed(0)
    cache = args.root / '_catalogue' / 'models' / 'huggingface'
    checkpoint = cache / 'models--Qwen--Qwen2.5-Omni-3B' / 'snapshots' / REVISION
    print(json.dumps(dict(stage='loading_thinker', checkpoint=str(checkpoint))), flush=True)
    config = Qwen2_5OmniConfig.from_pretrained(checkpoint)
    if args.official_wrapper:
        config.enable_audio_output = False
        model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            checkpoint, config=config, dtype=torch.bfloat16, device_map='auto',
            max_memory={0: '12GiB', 'cpu': '24GiB'}, attn_implementation='sdpa', use_safetensors=True)
        loading_info = dict(note='Official wrapper does not return loading diagnostics; direct-thinker loading checked separately.')
        generator = model.thinker
    else:
        model, loading_info = Qwen2_5OmniThinkerForConditionalGeneration.from_pretrained(
            checkpoint, config=config.thinker_config, dtype=torch.bfloat16, device_map='auto',
            max_memory={0: '12GiB', 'cpu': '24GiB'}, attn_implementation='sdpa',
            use_safetensors=True, output_loading_info=True)
        generator = model
    model.eval()
    args.output.with_suffix('.loading.json').write_text(json.dumps(loading_info, indent=2), encoding='utf-8')
    print(json.dumps(dict(stage='loading_verified', missing_keys=len(loading_info['missing_keys']) if 'missing_keys' in loading_info else None,
                          mismatched_keys=len(loading_info['mismatched_keys']) if 'mismatched_keys' in loading_info else None)), flush=True)
    generator.generation_config.eos_token_id = 151645
    generator.generation_config.pad_token_id = 151643
    processor = Qwen2_5OmniProcessor.from_pretrained(checkpoint, use_fast=True)
    processor.tokenizer.padding_side = 'left'
    if not processor.chat_template:
        processor.chat_template = processor.tokenizer.chat_template
    provenance = dict(name=MODEL, revision=REVISION, component='official_wrapper_text_only' if args.official_wrapper else 'thinker_only', dtype='bfloat16',
                      attention='sdpa', prompt=args.prompt, system=SYSTEM, eos_token_id=151645, pad_token_id=151643,
                      pipeline_version=PIPELINE_VERSION,
                      prompt_sha256=hashlib.sha256((PIPELINE_VERSION + SYSTEM + args.prompt + str(args.min_seconds) + args.short_policy + str(args.max_seconds) + str(args.official_wrapper) + str(args.repeat_below_seconds) + str(args.repeat_seconds)).encode()).hexdigest(),
                      preprocessing=f'first <={args.max_seconds} seconds, mono 48k decode then 16k polyphase resample; minimum {args.min_seconds}s {args.short_policy}',
                      sampling_rate=16000, padding_side='left', max_new_tokens=80, stop_strings=['\nHuman:', '\nUser:'],
                      source='https://huggingface.co/' + MODEL,
                      repeat_below_seconds=args.repeat_below_seconds, repeat_seconds=args.repeat_seconds,
                      torch=torch.__version__, transformers=transformers.__version__, cuda_memory_allocated=torch.cuda.memory_allocated())
    seen = set()
    if args.resume and args.output.exists():
        for line in args.output.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['model']['prompt_sha256'] != provenance['prompt_sha256'] or row['model']['revision'] != REVISION:
                raise ValueError('Resume provenance differs; preserve earlier output and use a fresh output')
            seen.add((row['id'], row['sha256']))
    records = [x for x in records if (x['id'], x['sha256']) not in seen]
    print(json.dumps(dict(stage='caption', rows=len(records), device=str(model.device),
                          cuda_memory_allocated=torch.cuda.memory_allocated())), flush=True)
    started, done, errors = time.monotonic(), 0, []
    with args.output.open('a' if args.resume else 'w', encoding='utf-8') as output:
        for offset in range(0, len(records), args.batch_size):
            batch = records[offset:offset + args.batch_size]
            audios, good, measurements = [], [], []
            for row in batch:
                try:
                    samples = resample_poly(acoustic.decode_windows(args.root, row)[0][1], 1, 3).astype(np.float32)
                    measurement = dict(decoded_seconds=len(samples)/16000, rms=float(np.sqrt(np.square(samples, dtype=np.float64).mean())),
                                       peak=float(np.abs(samples).max()), sampled_silent=bool(np.abs(samples).max() <= 1e-7))
                    minimum = int(args.min_seconds * 16000)
                    if len(samples) < int(args.repeat_below_seconds * 16000):
                        target = int(args.repeat_seconds * 16000)
                        samples = np.tile(samples, int(np.ceil(target / len(samples))))[:target]
                        measurement['preprocessing'] = f'repeated short excerpt to {args.repeat_seconds}s; repetition is not part of original source'
                    elif len(samples) < minimum:
                        samples = (np.tile(samples, int(np.ceil(minimum / len(samples))))[:minimum] if args.short_policy == 'repeat'
                                   else np.pad(samples, (0, minimum - len(samples))))
                        measurement['preprocessing'] = f'{args.short_policy} to minimum {args.min_seconds}s'
                    else:
                        measurement['preprocessing'] = 'no padding or repetition'
                    audios.append(samples)
                    good.append(row)
                    measurements.append(measurement)
                except Exception as exc:
                    print(json.dumps(dict(stage='decode_error', path=row['path'], error=str(exc))), flush=True)
                    failure = dict(id=row['id'], path=row['path'], sha256=row['sha256'], caption=None,
                                   error=str(exc), model=provenance, accepted=False, review_needed=True,
                                   audio_verified=False, training_eligible=False)
                    errors.append(dict(id=row['id'], path=row['path'], error=str(exc)))
                    output.write(json.dumps(failure, ensure_ascii=False) + '\n')
            if not good:
                continue
            conversations = [[dict(role='system', content=[dict(type='text', text=SYSTEM)]),
                              dict(role='user', content=[dict(type='audio', audio='local'), dict(type='text', text=args.prompt)])]
                             for _ in good]
            texts = [processor.apply_chat_template(x, add_generation_prompt=True, tokenize=False) for x in conversations]
            inputs = processor(text=texts, audio=audios, sampling_rate=16000, return_tensors='pt', padding=True)
            feature_lengths = inputs.feature_attention_mask.sum(-1).tolist()
            audio_tokens = (inputs.input_ids==processor.tokenizer.convert_tokens_to_ids('<|AUDIO|>')).sum(-1).tolist()
            if args.verbose_features or offset == 0:
                print(json.dumps(dict(stage='features', paths=[x['path'] for x in good], waveform_lengths=[len(x) for x in audios],
                    feature_shape=list(inputs.input_features.shape), feature_attention_sums=feature_lengths,
                    token_counts=audio_tokens)), flush=True)
            inputs = inputs.to(model.device).to(model.dtype)
            with torch.inference_mode():
                extra = dict(return_audio=False, thinker_max_new_tokens=80) if args.official_wrapper else {}
                generated = model.generate(**inputs, max_new_tokens=80, do_sample=False,
                                           eos_token_id=151645, pad_token_id=151643,
                                           stop_strings=['\nHuman:', '\nUser:'], tokenizer=processor.tokenizer, **extra)
            captions = processor.batch_decode(generated[:, inputs.input_ids.shape[1]:], skip_special_tokens=True,
                                              clean_up_tokenization_spaces=False)
            for row, caption, measurement, frames, tokens in zip(good, captions, measurements, feature_lengths, audio_tokens):
                result = dict(id=row['id'], path=row['path'], sha256=row['sha256'], caption=caption.strip(),
                              expected_category=row.get('category'), expected_catid=row.get('catid'),
                              model=provenance, accepted=False, review_needed=True, measurements=measurement,
                              feature_frames=frames, audio_tokens=tokens,
                              audio_verified=False, training_eligible=False)
                output.write(json.dumps(result, ensure_ascii=False) + '\n')
                done += 1
            output.flush()
            print(json.dumps(dict(processed=done, total=len(records), elapsed_seconds=round(time.monotonic()-started, 1))), flush=True)
    args.output.with_suffix('.report.json').write_text(json.dumps(dict(processed=done, decode_errors=errors, requested=len(records), resumed=len(seen),
        elapsed_seconds=round(time.monotonic()-started, 2), model=provenance), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
