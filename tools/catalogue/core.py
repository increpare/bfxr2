"""Inventory original recordings and import evidence-backed UCS descriptions.

Standard library only. Source folders are read-only; derived data lives in
BFXR_SFX_ROOT/_catalogue. Labels describe metadata evidence, not listening QA.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import sqlite3
import subprocess
import time
import wave
import warnings
import zipfile
import xml.etree.ElementTree as ET

AUDIO = {'.wav', '.wave', '.mp3', '.ogg', '.flac', '.aif', '.aiff', '.iff', '.if1', '.if2', '.au', '.snd', '.m4a', '.wma', '.aac', '.opus', '.mp2', '.mov'}
ARCHIVES = {'.zip', '.rar', '.7z', '.exe', '.ex_', '.cab', '.iso'}
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def native_path(path):
    """OS-facing path, including Windows extended-length local/UNC support.

    Use this for filesystem calls and decoder arguments, never catalogue keys.
    No file is renamed or modified by converting its path spelling.
    """
    value = os.path.abspath(os.fspath(path))
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        value = '\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value
    return Path(value)


def logical_path(path):
    """Remove a Windows access prefix while retaining its original source path."""
    value = os.fspath(path)
    if value.startswith('\\\\?\\UNC\\'):
        value = '\\\\' + value[8:]
    elif value.startswith('\\\\?\\'):
        value = value[4:]
    return Path(value)


def atomic_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def connect(root):
    out = root / '_catalogue'
    out.mkdir(exist_ok=True)
    db = sqlite3.connect(out / 'catalogue.sqlite', timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS sources (
        path TEXT PRIMARY KEY, library TEXT NOT NULL, size INTEGER, mtime_ns INTEGER,
        sha256 TEXT, status TEXT, error TEXT, duration REAL, sample_rate INTEGER,
        channels INTEGER, bits INTEGER, codec TEXT, format TEXT,
        duplicate_of TEXT, present INTEGER DEFAULT 1, pcm_hash TEXT, pcm_error TEXT);
      CREATE INDEX IF NOT EXISTS sources_hash ON sources(sha256);
      CREATE TABLE IF NOT EXISTS descriptions (
        id TEXT PRIMARY KEY, path TEXT NOT NULL, description TEXT NOT NULL,
        original_category TEXT, catid TEXT, category TEXT, confidence TEXT,
        reason TEXT, content TEXT, metadata_source TEXT, adapter TEXT, extra TEXT);
      CREATE INDEX IF NOT EXISTS descriptions_path ON descriptions(path);
      CREATE TABLE IF NOT EXISTS ucs (
        catid TEXT PRIMARY KEY, category TEXT, subcategory TEXT,
        explanation TEXT, synonyms TEXT);
      CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY, description_id TEXT, action TEXT, value TEXT, time TEXT);
    ''')
    return db


def taxonomy(root):
    """Read the first six columns of the user's UCS workbook, without editing it."""
    src = root / 'UCS v8.2.1 Full List.xlsx'
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(src) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(t.text or '' for t in e.findall('s:t', ns) + e.findall('s:r/s:t', ns)) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        sheet_path = 'xl/worksheets/sheet1.xml'
        if 'xl/workbook.xml' in z.namelist() and 'xl/_rels/workbook.xml.rels' in z.namelist():
            first = ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets/s:sheet', ns)
            if first is None:
                raise ValueError('UCS workbook contains no worksheets')
            rid = first.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
            target = next((r.get('Target') for r in relationships if r.get('Id') == rid and r.get('TargetMode') != 'External'), None)
            if not target:
                raise ValueError('UCS first worksheet relationship is missing')
            sheet_path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        sheet = ET.fromstring(z.read(sheet_path))
        rows = []
        for row in sheet.findall('.//s:sheetData/s:row', ns):
            cells = {}
            for c in row.findall('s:c', ns):
                col = ''.join(x for x in c.attrib['r'] if x.isalpha())
                if col not in 'ABCDEF' or len(col) != 1:
                    continue
                v = c.find('s:v', ns)
                if c.attrib.get('t') == 'inlineStr':
                    value = ''.join(t.text or '' for t in c.findall('s:is/s:t', ns) + c.findall('s:is/s:r/s:t', ns))
                else:
                    value = (v.text or '') if v is not None else ''
                    if c.attrib.get('t') == 's':
                        value = strings[int(value)]
                cells[col] = value.strip()
            if cells.get('C') and cells.get('C') != 'CatID' and cells.get('A') and cells.get('B'):
                rows.append(dict(zip(['category', 'subcategory', 'catid', 'short', 'explanation', 'synonyms'], [cells.get(c, '') for c in 'ABCDEF'])))
    if not rows:
        raise ValueError('No UCS categories found; existing taxonomy was retained')
    if len(rows) != len({r['catid'] for r in rows}):
        raise ValueError('Duplicate UCS identifiers')
    db = connect(root)
    with db:
        db.execute('DELETE FROM ucs')
        db.executemany('INSERT INTO ucs VALUES (:catid,:category,:subcategory,:explanation,:synonyms)', rows)
    atomic_json(root / '_catalogue' / 'ucs.json', rows)
    print(f"UCS: {len(rows)} leaves, {len({r['category'] for r in rows})} categories", flush=True)


def probe(path):
    path = native_path(path)
    # WAV headers are fast, but unsupported/compressed WAVs use ffprobe.
    if path.suffix.lower() in {'.wav', '.wave'}:
        try:
            with wave.open(str(path), 'rb') as w:
                return dict(duration=w.getnframes() / w.getframerate(), sample_rate=w.getframerate(), channels=w.getnchannels(), bits=w.getsampwidth()*8, codec='pcm', format='wav')
        except (wave.Error, EOFError):
            pass
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,format_name:stream=codec_type,codec_name,sample_rate,channels,bits_per_sample,bits_per_raw_sample,duration', '-of', 'json', str(path)], capture_output=True, timeout=40, creationflags=CREATE_NO_WINDOW)
    if p.returncode:
        raise ValueError(p.stderr.decode('utf-8', 'replace')[-500:])
    data = json.loads(p.stdout)
    stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
    if not stream:
        raise ValueError('No audio stream')
    fmt = data.get('format', {})
    dur = fmt.get('duration', stream.get('duration'))
    return dict(duration=float(dur) if dur not in {None, 'N/A'} else None, sample_rate=int(stream.get('sample_rate') or 0), channels=stream.get('channels'), bits=int(stream.get('bits_per_raw_sample') or stream.get('bits_per_sample') or 0), codec=stream.get('codec_name'), format=fmt.get('format_name'))


def audio_signature(path):
    """Recognize common legacy/container headers even behind an odd suffix."""
    with native_path(path).open('rb') as f:
        head = f.read(12)
    return (head[:4] in {b'RIFF', b'RF64', b'RIFX'} and head[8:12] == b'WAVE'
            or head[:4] == b'FORM' and head[8:12] in {b'AIFF', b'AIFC', b'8SVX', b'16SV'}
            or head.startswith((b'fLaC', b'OggS', b'ID3', b'.snd'))
            or head[4:8] == b'ftyp')


def inspect_file(root, path):
    root, path = logical_path(root), logical_path(path)
    rel = path.relative_to(root).as_posix()
    result = dict(path=rel, library=rel.split('/')[0], size=None, mtime_ns=None, status='pending', error=None, sha256=None, duration=None, sample_rate=None, channels=None, bits=None, codec=None, format=None, present=1)
    ext = path.suffix.lower()
    try:
        access = native_path(path)
        stat = access.stat()
        result.update(size=stat.st_size, mtime_ns=stat.st_mtime_ns)
        if ext in ARCHIVES or result['library'] == '6000sfx':
            result['status'] = 'needs_extracting'
            return result
        if ext not in AUDIO and ext and not audio_signature(path):
            result['status'] = 'ancillary'
            return result
        result.update(probe(path))
        with access.open('rb') as f:
            result['sha256'] = hashlib.file_digest(f, 'sha256').hexdigest()
        after = access.stat()
        if after.st_mtime_ns != stat.st_mtime_ns or after.st_size != stat.st_size:
            raise ValueError('File changed during scan; retry next run')
        result['status'] = 'audio'
    except Exception as exc:
        result['status'] = 'pending' if ext or result['size'] is None else 'unrecognised'
        result['sha256'] = None
        result['error'] = str(exc)[:500]
    return result


def scan(root, workers=8):
    if workers < 1:
        raise ValueError('workers must be at least 1')
    db = connect(root)
    existing = {r['path']: r for r in db.execute('SELECT * FROM sources')}
    files, seen, uncertain, scan_errors = [], [], set(), []
    root = logical_path(root)
    for accessed_library in sorted(native_path(root).iterdir()):
        library = logical_path(accessed_library)
        if library.name.startswith(('_', '.')):
            continue
        try:
            if not accessed_library.is_dir() or accessed_library.is_symlink() or getattr(accessed_library, 'is_junction', lambda: False)():
                continue
        except OSError as exc:
            uncertain.add(library.name)
            scan_errors.append(f'{library.name}: {exc}')
            continue
        def walk_error(exc):
            uncertain.add(library.name)
            scan_errors.append(f'{library.name}: {exc}')
        for directory, dirs, names in os.walk(native_path(library), followlinks=False, onerror=walk_error):
            dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink() and not getattr(Path(directory) / name, 'is_junction', lambda: False)()]
            for name in sorted(names):
                access = Path(directory) / name
                path = logical_path(access)
                if access.is_symlink():
                    continue
                try:
                    access.resolve().relative_to(native_path(root).resolve())
                except ValueError:
                    continue
                rel = path.relative_to(root).as_posix()
                seen.append((rel,))
                try:
                    stat = access.stat()
                except OSError:
                    files.append(path)
                    continue
                old = existing.get(rel)
                newly_supported = old and old['status'] == 'ancillary' and path.suffix.lower() in AUDIO
                if old and old['status'] == 'ancillary' and not newly_supported:
                    try:
                        newly_supported = audio_signature(path)
                    except OSError:
                        newly_supported = True
                if not (old and old['size'] == stat.st_size and old['mtime_ns'] == stat.st_mtime_ns and old['status'] not in {'pending', 'unrecognised', 'non_audio'} and not newly_supported):
                    files.append(path)
    with db:
        # Mark queued existing paths present before processing. An interrupted scan
        # must not make recordings disappear from the last completed inventory.
        for library in {r['library'] for r in existing.values()} - uncertain:
            db.execute('UPDATE sources SET present=0 WHERE library=?', (library,))
        db.executemany('UPDATE sources SET present=1 WHERE path=?', seen)
    print(f'Scanning {len(files)} new/changed files; {len(seen)-len(files)} unchanged', flush=True)
    pending = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, result in enumerate(pool.map(lambda p: inspect_file(root, p), files), 1):
            pending.append(result)
            if i % 200 == 0 or i == len(files):
                cols = list(result)
                with db:
                    db.executemany(f"INSERT INTO sources ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)}) ON CONFLICT(path) DO UPDATE SET " + ','.join(f'{c}=excluded.{c}' for c in cols if c != 'path') + ',pcm_hash=NULL,pcm_error=NULL', [list(r.values()) for r in pending])
                pending.clear()
                print(f'  {i}/{len(files)} scanned', flush=True)
    db.commit()
    dedupe_paths(db)
    atomic_json(root / '_catalogue' / 'scan-errors.json', scan_errors)
    print(json.dumps([dict(r) for r in db.execute('SELECT library,status,COUNT(*) AS files FROM sources WHERE present=1 GROUP BY library,status')], indent=2), flush=True)


def dedupe_paths(db):
    with db:
        db.execute('UPDATE sources SET duplicate_of=NULL')
        seen, parents = {}, {}
        def canonical(path):
            while parents[path] != path:
                parents[path] = parents[parents[path]]
                path = parents[path]
            return path
        ordered = []
        for row in db.execute("SELECT path,sha256,pcm_hash FROM sources WHERE status='audio' AND present=1 ORDER BY CASE WHEN lower(path) LIKE '%.wav' THEN 0 ELSE 1 END,path"):
            path = row['path']
            ordered.append(path)
            parents[path] = path
            keys = [('bytes', row['sha256'])] if row['sha256'] else []
            if row['pcm_hash']:
                keys.append(('pcm', row['pcm_hash']))
            matches = {canonical(seen[k]) for k in keys if k in seen}
            # Root preference is the same WAV-first, lexical order as the query.
            first = min(matches | {path}, key=lambda p: (not p.lower().endswith('.wav'), p))
            for match in matches | {path}:
                parents[match] = first
            for key in keys:
                seen[key] = first
        db.executemany('UPDATE sources SET duplicate_of=? WHERE path=?', ((canonical(p), p) for p in ordered if canonical(p) != p))


def pcm_digest(root, row):
    try:
        path = native_path(root / row['path'])
        before = path.stat()
        if (before.st_size, before.st_mtime_ns) != (row['size'], row['mtime_ns']):
            raise ValueError('Source changed since inventory; rescan before comparing samples')
        p = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-c:a', 'pcm_s32le', '-f', 'hash', '-hash', 'sha256', '-'], capture_output=True, timeout=180, creationflags=CREATE_NO_WINDOW)
        if p.returncode:
            raise ValueError(p.stderr.decode('utf-8', 'replace')[-300:])
        after = path.stat()
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise ValueError('Source changed during sample comparison; rescan first')
        value = p.stdout.decode().strip().split('=')[-1]
        if not re.fullmatch('[a-fA-F0-9]{64}', value):
            raise ValueError('Decoder returned no valid sample hash')
        digest = f"{row['sample_rate']}:{row['channels']}:" + value.lower()
        return digest, None, row['path']
    except Exception as exc:
        return None, str(exc)[:400], row['path']


def dedupe(root, workers=8, library=None):
    if workers < 1:
        raise ValueError('workers must be at least 1')
    db = connect(root)
    # Integer conversion can clip/quantize floating-point or >32-bit samples.
    # Such files still receive byte hashes but must not share an s32 PCM hash.
    with db:
        db.execute("UPDATE sources SET pcm_hash=NULL WHERE codec LIKE 'pcm_f%' OR codec LIKE 'pcm_s64%' OR codec LIKE 'pcm_u64%' OR bits>32")
    rows = [dict(r) for r in db.execute("SELECT * FROM sources WHERE status='audio' AND present=1 AND pcm_hash IS NULL") if (not library or r['library'] == library) and (r['codec'] or '').startswith(('pcm', 'flac')) and not (r['codec'] or '').startswith(('pcm_f', 'pcm_s64', 'pcm_u64')) and (r['bits'] or 0) <= 32]
    print(f'Checking decoded samples of {len(rows)} lossless files', flush=True)
    pending = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, result in enumerate(pool.map(lambda r: pcm_digest(root, r), rows), 1):
            row = rows[i-1]
            pending.append(result + (row['size'], row['mtime_ns']))
            if i % 200 == 0 or i == len(rows):
                with db:
                    db.executemany('UPDATE sources SET pcm_hash=?,pcm_error=? WHERE path=? AND size=? AND mtime_ns=?', pending)
                pending.clear()
                print(f'  {i}/{len(rows)} checked', flush=True)
    db.commit()
    dedupe_paths(db)
    print('Duplicate source paths:', db.execute('SELECT COUNT(*) FROM sources WHERE duplicate_of IS NOT NULL AND present=1').fetchone()[0], flush=True)


def import_labels(root):
    db = connect(root)
    ucs = {r['catid']: dict(r) for r in db.execute('SELECT * FROM ucs')}
    categories = {r['category'] for r in ucs.values()}
    sources = {r['path'] for r in db.execute("SELECT path FROM sources WHERE status='audio' AND present=1")}
    errors, imported, batches = [], 0, []
    existing = [dict(r) for r in db.execute('SELECT * FROM descriptions')]
    used_ids = {r['id'] for r in existing}
    def evidence_key(adapter, path, description, metadata_source, extra):
        # Numbered publisher guide entries survive corrections to their wording.
        index = extra.get('entry_index')
        anchor = ('entry', str(index)) if index is not None else ('description', description)
        return (adapter, path, metadata_source or '', anchor)
    existing_ids = {}
    for r in existing:
        extra = json.loads(r['extra'] or '{}')
        key = evidence_key(r['adapter'], r['path'], r['description'], r['metadata_source'], extra)
        existing_ids[key] = r['id']
    for file in sorted((root / '_catalogue' / 'labelling').glob('*.jsonl')):
        rows, row_ids = [], set()
        for line, raw in enumerate(file.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not raw.strip():
                continue
            try:
                r = json.loads(raw)
                if not isinstance(r, dict) or not isinstance(r.get('path'), str) or not isinstance(r.get('description'), str) or not r['description'].strip():
                    raise ValueError('Expected an object with path and nonempty description strings')
            except (ValueError, TypeError) as exc:
                raise ValueError(f'{file.name}:{line}: {exc}') from exc
            path = r['path'].replace('\\', '/')
            if path.startswith('/') or re.match(r'^[a-zA-Z]:', path) or any(part in {'', '.', '..'} for part in path.split('/')):
                raise ValueError(f'{file.name}:{line}: expected a relative source path')
            if path not in sources:
                errors.append(f'{file.name}:{line}: not a scanned audio file: {path}')
                continue
            catid, category = r.get('catid'), r.get('category')
            if catid and catid not in ucs:
                raise ValueError(f'{file}:{line}: unknown CatID {catid}')
            if catid:
                category = ucs[catid]['category']
            if category and category not in categories:
                raise ValueError(f'{file}:{line}: unknown category {category}')
            confidence = r.get('confidence', 'none')
            if confidence not in {'high', 'medium', 'low', 'none'}:
                raise ValueError(f'{file}:{line}: invalid confidence')
            known = {'path','description','original_category','catid','category','confidence','reason','content','metadata_source'}
            extra = {k: v for k, v in r.items() if k not in known}
            key = evidence_key(file.stem, path, r['description'], r.get('metadata_source'), extra)
            ident = existing_ids.get(key)
            if ident is None:
                ident = hashlib.sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:24]
                if ident in used_ids:
                    raise ValueError(f'{file.name}:{line}: description identity collision')
                existing_ids[key] = ident
                used_ids.add(ident)
            if ident in row_ids:
                raise ValueError(f'{file.name}:{line}: repeated metadata entry; give distinct guide entries an entry_index')
            row_ids.add(ident)
            rows.append((ident, path, r['description'], str(r.get('original_category') or ''), catid, category, confidence, r.get('reason', ''), r.get('content', 'unknown'), r.get('metadata_source', ''), file.stem, json.dumps(extra, ensure_ascii=False)))
        batches.append((file.stem, rows))
        imported += len(rows)
    # Validate every adapter first. A malformed later file must not leave an
    # earlier adapter replaced. Keep historical provenance for absent sources.
    with db:
        for adapter, rows in batches:
            db.executemany('DELETE FROM descriptions WHERE adapter=? AND path=?', ((adapter, path) for path in sources))
            db.executemany('INSERT INTO descriptions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    for adapter, rows in batches:
        print(f'{adapter}: {len(rows)} descriptions', flush=True)
    atomic_json(root / '_catalogue' / 'import-errors.json', errors)
    print(f'Imported {imported} descriptions, {len(errors)} unmatched input rows', flush=True)


def records(root, use_proposals=True):
    db = connect(root)
    rows = []
    overrides = {}
    ucs = {r['catid']: dict(r) for r in db.execute('SELECT * FROM ucs')}
    from .enrichment import load_proposals, apply_proposal
    from .traits import load_traits, apply_traits
    proposals = load_proposals(root, ucs) if use_proposals else {}
    traits = load_traits(root)
    description_counts = {r['path']: r['n'] for r in db.execute('SELECT path,COUNT(*) AS n FROM descriptions GROUP BY path')}
    # The append-only log is the authority; SQLite decisions are a convenience cache.
    log = root / '_catalogue' / 'overrides.jsonl'
    if log.exists():
        for line, raw in enumerate(log.read_text(encoding='utf-8').splitlines(), 1):
            if raw.strip():
                try:
                    event = json.loads(raw)
                    if not isinstance(event, dict) or not isinstance(event.get('description_id'), str) or 'catid' not in event or event.get('action', 'label') != 'label':
                        raise ValueError('Invalid review event')
                    value = event['catid']
                    if value is not None and (not isinstance(value, str) or value not in ucs):
                        raise ValueError(f'UCS identifier {value!r} is unavailable')
                    overrides[event['description_id']] = event
                except (ValueError, TypeError) as exc:
                    warnings.warn(f'Ignored review log line {line}: {exc}', RuntimeWarning)
    query = '''SELECT s.*,d.id,d.description,d.original_category,d.catid,d.category,
      d.confidence,d.reason,d.content,d.metadata_source,d.adapter,d.extra,u.subcategory
      FROM sources s LEFT JOIN descriptions d ON s.path=d.path
      LEFT JOIN ucs u ON d.catid=u.catid WHERE s.present=1 AND s.status='audio'
      ORDER BY s.library,s.path,d.id'''
    for r in db.execute(query):
        item = dict(r)
        # Equal decoded sample values at different declared rates are related
        # versions, with different playback speed/duration, not exact duplicates.
        pcm = item['pcm_hash'] or ''
        item['sample_family'] = pcm.split(':', 1)[1] if re.fullmatch(r'[0-9]+:[0-9]+:[a-f0-9]{64}', pcm) else None
        item['id'] = item['id'] or hashlib.sha256(item['path'].encode()).hexdigest()[:24]
        item['description'] = item['description'] or Path(item['path']).stem
        item['classification_status'] = 'provisional' if item['catid'] else ('broad category' if item['category'] else 'unclassified')
        item['reviewed'] = False
        if item['extra']:
            item['extra'] = json.loads(item['extra'])
        if (item.get('extra') or {}).get('source_kind') == 'raw_wavebank_element' and item['catid'] == 'DSGNSrce':
            item['classification_status'] = 'source element'
        elif (item.get('extra') or {}).get('classification_scope') == 'source_context' and item['category']:
            item['classification_status'] = 'context only'
        item['classification_method'] = 'metadata'
        item['review_needed'] = True
        item['training_eligible'] = False  # Category review alone does not verify segmentation/rights/quality.
        apply_proposal(item, proposals, ucs)
        decision = overrides.get(item['id'])
        if decision is None and description_counts.get(item['path'], 0) <= 1:
            # A review of an unlabelled recording remains applicable when one
            # description is subsequently imported for that same source path.
            decision = overrides.get(hashlib.sha256(item['path'].encode()).hexdigest()[:24])
        if decision:
            value = decision.get('catid')
            if value is not None and (not isinstance(value, str) or value not in ucs):
                warnings.warn(f"Ignored review for {item['id']}: UCS identifier {value!r} is unavailable", RuntimeWarning)
            else:
                item.update(suggested_catid=item['catid'], suggested_category=item['category'], suggested_confidence=item['confidence'], suggested_reason=item['reason'])
                item.update(catid=value, category=ucs[value]['category'] if value else None, subcategory=ucs[value]['subcategory'] if value else None, confidence='high' if value else 'none', classification_status='reviewed' if value else 'unclassified', reviewed=True, reason='Manual review in local catalogue', metadata_source=item['metadata_source'])
                item.update(classification_method='reviewed', review_needed=value is None)
        apply_traits(item, traits)
        rows.append(item)
    return rows


def build(root):
    db = connect(root)
    out = root / '_catalogue'
    (out / 'site').mkdir(exist_ok=True)
    data = records(root)
    # Rich, complete JSON for the browser; portable CSV for external tools.
    atomic_json(out / 'site' / 'catalogue.json', data)
    fields = ['id','library','path','description','category','subcategory','catid','classification_status','classification_method','review_needed','training_eligible','confidence','reason','content','duration','sample_rate','channels','bits','codec','sha256','pcm_hash','sample_family','duplicate_of','metadata_source','original_category','acoustic_traits']
    temp = out / 'catalogue.csv.tmp'
    with temp.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(row | {'acoustic_traits': '; '.join(row['acoustic_traits'])} for row in data)
    temp.replace(out / 'catalogue.csv')
    coverage = []
    for u in db.execute('SELECT * FROM ucs ORDER BY category,subcategory'):
        matching = [r for r in data if r['catid'] == u['catid']]
        coverage.append(dict(u) | dict(descriptions=len(matching), source_files=len({r['duplicate_of'] or r['path'] for r in matching}), reviewed=sum(r['reviewed'] for r in matching), libraries=sorted({r['library'] for r in matching})))
    atomic_json(out / 'coverage.json', coverage)
    families = {}
    for item in data:
        if item['sample_family']:
            families.setdefault(item['sample_family'], {})[item['path']] = item
    variants = []
    for family, by_path in sorted(families.items()):
        rates = sorted({item['sample_rate'] for item in by_path.values() if item['sample_rate'] is not None})
        if len(rates) > 1:
            fields = ('path', 'library', 'sample_rate', 'channels', 'pcm_hash', 'duplicate_of')
            variants.append(dict(sample_family=family, sample_rates=rates, source_files=len(by_path), libraries=sorted({item['library'] for item in by_path.values()}), variants=[{key: item[key] for key in fields} for _, item in sorted(by_path.items())]))
    atomic_json(out / 'sample-variants.json', variants)
    libraries = [dict(r) for r in db.execute("SELECT library,COUNT(*) AS audio_files,SUM(duplicate_of IS NULL) AS unique_files,SUM(duration) AS duration_seconds FROM sources WHERE present=1 AND status='audio' GROUP BY library")]
    summary = dict(generated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), audio_files=sum(r['audio_files'] for r in libraries), unique_files=sum(r['unique_files'] for r in libraries), descriptions=len(data), labelled_descriptions=sum(bool(r['catid']) for r in data), broad_descriptions=sum(bool(r['category']) and not r['catid'] for r in data), unclassified_descriptions=sum(not r['category'] for r in data), reviewed_descriptions=sum(r['reviewed'] for r in data), covered_leaves=sum(r['source_files'] > 0 for r in coverage), total_leaves=len(coverage), libraries=libraries, statuses=[dict(r) for r in db.execute('SELECT status,COUNT(*) AS files FROM sources WHERE present=1 GROUP BY status')])
    summary.update(sample_variant_families=len(variants), sample_variant_files=sum(item['source_files'] for item in variants))
    summary.update(audio_proposals=sum(r['classification_method'] == 'audio-model' for r in data), duplicate_proposals=sum(r['classification_method'] == 'exact-duplicate' for r in data), excerpt_proposals=sum(r['classification_method'] == 'exact-excerpt' for r in data), quality_exclusions=sum(r['classification_method'] == 'signal-analysis' for r in data))
    summary['source_element_descriptions'] = sum(r['classification_status'] == 'source element' for r in data)
    summary['context_only_descriptions'] = sum(r['classification_status'] == 'context only' for r in data)
    summary['tentative_descriptions'] = sum(r['classification_status'] == 'tentative proposal' for r in data)
    summary['unresolved_sound_roles'] = summary['unclassified_descriptions'] + summary['source_element_descriptions'] + summary['context_only_descriptions'] + summary['tentative_descriptions']
    summary['descriptions_with_acoustic_traits'] = sum(bool(r['acoustic_traits']) for r in data)
    atomic_json(out / 'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['taxonomy','scan','dedupe','import','build','status','serve'])
    p.add_argument('--root', default=os.environ.get('BFXR_SFX_ROOT'))
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--library')
    p.add_argument('--port', type=int, default=8765)
    args = p.parse_args()
    if not args.root:
        p.error('Set BFXR_SFX_ROOT to the library folder or pass --root')
    root = Path(args.root).resolve()
    if not root.is_dir():
        p.error('Sound-effects root does not exist')
    if args.command == 'taxonomy': taxonomy(root)
    elif args.command == 'scan': scan(root, args.workers)
    elif args.command == 'dedupe': dedupe(root, args.workers, args.library)
    elif args.command == 'import': import_labels(root)
    elif args.command in {'build','status'}: build(root)
    elif args.command == 'serve':
        from .server import serve
        serve(root, args.port)
