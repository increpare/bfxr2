"""Focused catalogue regressions; fixtures are temporary and originals untouched.

Run: python -m unittest tools.catalogue.test_core -v
"""
import contextlib
import csv
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import tempfile
import unittest
from unittest import mock
import warnings
import wave
import zipfile

from . import core


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        # Keep disposable fixtures in the writable checkout, including inside
        # restricted Windows sessions where the OS temp directory is read-only.
        fixture_parent = Path(__file__).resolve().parent
        self.temp = tempfile.TemporaryDirectory(prefix='_test_catalogue_', dir=fixture_parent)
        Path(self.temp.name).resolve().relative_to(fixture_parent)
        def cleanup_fixture():
            target = Path(self.temp.name).resolve()
            target.relative_to(fixture_parent)
            shutil.rmtree(core.native_path(target))
            self.temp.cleanup()
        self.addCleanup(cleanup_fixture)
        self.addCleanup(gc.collect)
        self.root = Path(self.temp.name)
        self.db = core.connect(self.root)
        self.addCleanup(self.db.close)
        with self.db:
            self.db.executemany('INSERT INTO ucs VALUES (?,?,?,?,?)', [
                ('ANMLDog', 'ANIMALS', 'DOG', 'Dog sounds', 'bark'),
                ('ANMLCat', 'ANIMALS', 'CAT', 'Cat sounds', 'meow'),
            ])

    def quiet(self, fn, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*args, **kwargs)

    def wav(self, rel='Library/a.wav', samples=(0, 100, -100, 32767)):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(struct.pack('<' + 'h'*len(samples), *samples))
        return path

    def source(self, path, sha='hash', pcm=None, present=1):
        with self.db:
            self.db.execute('INSERT INTO sources(path,library,status,sha256,pcm_hash,present,duration) VALUES (?,?,?,?,?,?,?)',
                            (path, path.split('/')[0], 'audio', sha, pcm, present, 1.0))

    def labels(self, rows, adapter='structured'):
        directory = self.root / '_catalogue' / 'labelling'
        directory.mkdir(exist_ok=True)
        (directory / (adapter + '.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')

    def label(self, **kwargs):
        return dict(path='Library/a.wav', description='Dog bark', catid='ANMLDog',
                    confidence='medium', reason='Publisher guide', metadata_source='guide.txt') | kwargs

    def review(self, ident, catid='ANMLCat', tail=''):
        event = dict(description_id=ident, catid=catid, action='label')
        (self.root / '_catalogue' / 'overrides.jsonl').write_text(json.dumps(event)+'\n'+tail, encoding='utf-8')

    def test_incremental_scan_preserves_pcm_and_original_bytes(self):
        path = self.wav()
        original = path.read_bytes()
        self.quiet(core.scan, self.root, workers=1)
        with self.db:
            self.db.execute("UPDATE sources SET pcm_hash='8000:1:existing'")
        with mock.patch.object(core, 'inspect_file', side_effect=AssertionError('Unchanged file was reinspected')):
            self.quiet(core.scan, self.root, workers=1)
        row = self.db.execute('SELECT * FROM sources').fetchone()
        self.assertEqual(row['pcm_hash'], '8000:1:existing')
        self.assertEqual(row['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(path.read_bytes(), original)

    def test_audio_proposal_is_reversible_and_manual_clear_wins(self):
        self.source('Library/a.wav')
        self.labels([self.label(catid=None, category=None)])
        self.quiet(core.import_labels, self.root)
        row = core.records(self.root)[0]
        proposal = dict(description_id=row['id'], path=row['path'], sha256=row['sha256'],
                        category='ANIMALS', catid='ANMLDog', method='audio-model', confidence='low')
        (self.root / '_catalogue' / 'automated-proposals.jsonl').write_text(json.dumps(proposal)+'\n', encoding='utf8')
        self.assertEqual(core.records(self.root)[0]['classification_status'], 'audio proposal')
        self.assertIsNone(core.records(self.root, use_proposals=False)[0]['category'])
        self.review(row['id'], catid=None)
        reviewed = core.records(self.root)[0]
        self.assertIsNone(reviewed['category'])
        self.assertTrue(reviewed['reviewed'])

    def test_raw_asset_grouping_does_not_claim_sound_role_resolved(self):
        self.source('Library/a.wav')
        with self.db:
            self.db.execute('INSERT INTO ucs VALUES (?,?,?,?,?)', ('DSGNSrce', 'DESIGNED', 'SOURCE', 'Source elements', ''))
        self.labels([self.label(catid='DSGNSrce', source_kind='raw_wavebank_element', semantic_role_known=False)])
        self.quiet(core.import_labels, self.root)
        self.quiet(core.build, self.root)
        summary = json.loads((self.root / '_catalogue' / 'summary.json').read_text())
        self.assertEqual(summary['unclassified_descriptions'], 0)
        self.assertEqual(summary['source_element_descriptions'], 1)
        self.assertEqual(summary['unresolved_sound_roles'], 1)
        row = core.records(self.root)[0]
        self.assertEqual(row['classification_status'], 'source element')
        self.assertFalse(row['training_eligible'])

    def test_changed_and_vanished_files(self):
        first, second = self.wav(), self.wav('Library/b.wav')
        self.quiet(core.scan, self.root, workers=1)
        with self.db:
            self.db.execute("UPDATE sources SET pcm_hash='stale'")
        self.wav(samples=(1, 2, 3, 4, 5))
        second.unlink()
        self.quiet(core.scan, self.root, workers=1)
        rows = {r['path']: r for r in self.db.execute('SELECT * FROM sources')}
        self.assertEqual(rows['Library/b.wav']['present'], 0)
        self.assertIsNone(rows['Library/a.wav']['pcm_hash'])
        self.assertEqual(rows['Library/a.wav']['size'], first.stat().st_size)
        self.assertIsNone(rows['Library/a.wav']['duplicate_of'])

    def test_a_failed_file_does_not_stop_scan_and_retries(self):
        self.wav()
        broken = self.root / 'Library' / 'broken.wav'
        broken.write_bytes(b'broken')
        with mock.patch.object(core, 'probe', side_effect=lambda p: (_ for _ in ()).throw(ValueError('bad')) if p == broken else dict(duration=1, codec='pcm')):
            self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute("SELECT status FROM sources WHERE path='Library/broken.wav'").fetchone()[0], 'pending')
        with mock.patch.object(core, 'probe', return_value=dict(duration=1, codec='pcm')) as probe:
            self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(probe.call_count, 1)
        self.assertEqual(self.db.execute("SELECT status FROM sources WHERE path='Library/broken.wav'").fetchone()[0], 'audio')

    def test_missing_file_between_enumeration_and_inspection_is_pending(self):
        result = core.inspect_file(self.root, self.root / 'Library' / 'vanished.wav')
        self.assertEqual(result['status'], 'pending')
        self.assertTrue(result['error'])
        self.assertIsNone(result['sha256'])

    def test_extensionless_failure_stays_uncertain(self):
        path = self.root / 'Library' / 'resource'
        path.parent.mkdir()
        path.write_bytes(b'unknown legacy resource')
        with mock.patch.object(core, 'probe', side_effect=ValueError('unsupported')):
            result = core.inspect_file(self.root, path)
        self.assertEqual(result['status'], 'unrecognised')

    def test_old_non_audio_cache_is_revisited(self):
        path = self.root/'Library/resource'
        path.parent.mkdir()
        path.write_bytes(b'legacy unsupported resource')
        self.source('Library/resource')
        with self.db:
            self.db.execute("UPDATE sources SET status='non_audio',size=?,mtime_ns=?", (path.stat().st_size, path.stat().st_mtime_ns))
        with mock.patch.object(core, 'probe', side_effect=ValueError('unsupported')) as probe:
            self.quiet(core.scan, self.root, workers=1)
        probe.assert_called_once()
        self.assertEqual(self.db.execute('SELECT status FROM sources').fetchone()[0], 'unrecognised')

    def test_interruption_does_not_hide_existing_queued_paths(self):
        self.wav()
        self.quiet(core.scan, self.root, workers=1)
        self.wav(samples=(1, 2, 3, 4, 5))
        with mock.patch.object(core, 'inspect_file', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT present FROM sources').fetchone()[0], 1)
        self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT size FROM sources').fetchone()[0], (self.root/'Library/a.wav').stat().st_size)

    def test_unreadable_library_retains_previous_inventory(self):
        self.wav()
        self.quiet(core.scan, self.root, workers=1)
        def inaccessible(path, followlinks, onerror):
            onerror(PermissionError('unreadable directory'))
            return iter(())
        with mock.patch.object(core.os, 'walk', side_effect=inaccessible):
            self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT present FROM sources').fetchone()[0], 1)
        self.assertTrue(json.loads((self.root/'_catalogue/scan-errors.json').read_text()))

    def test_dedupe_is_transitive_and_never_groups_null_hashes(self):
        self.source('Library/a.wav', 'bytes-a', 'pcm-a')
        self.source('Library/b.wav', 'bytes-b')
        self.source('Library/c.wav', 'bytes-b', 'pcm-a')
        self.source('Library/d.wav', None)
        self.source('Library/e.wav', None)
        core.dedupe_paths(self.db)
        groups = {r['path']: r['duplicate_of'] for r in self.db.execute('SELECT * FROM sources')}
        self.assertEqual(groups['Library/b.wav'], 'Library/a.wav')
        self.assertEqual(groups['Library/c.wav'], 'Library/a.wav')
        self.assertIsNone(groups['Library/d.wav'])
        self.assertIsNone(groups['Library/e.wav'])

    def test_dedupe_prefers_wav_and_updates_when_canonical_vanishes(self):
        self.source('Library/a.flac', 'same')
        self.source('Library/z.wav', 'same')
        core.dedupe_paths(self.db)
        self.assertEqual(self.db.execute("SELECT duplicate_of FROM sources WHERE path='Library/a.flac'").fetchone()[0], 'Library/z.wav')
        with self.db:
            self.db.execute("UPDATE sources SET present=0 WHERE path='Library/z.wav'")
        core.dedupe_paths(self.db)
        self.assertIsNone(self.db.execute("SELECT duplicate_of FROM sources WHERE path='Library/a.flac'").fetchone()[0])

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg integration tools unavailable')
    def test_decoded_samples_group_different_wav_containers(self):
        a = self.wav()
        data = a.read_bytes()
        chunk = b'JUNK' + struct.pack('<I', 4) + b'abcd'
        b = a.with_name('b.wav')
        b.write_bytes(data[:4] + struct.pack('<I', len(data)-8+len(chunk)) + data[8:12] + chunk + data[12:])
        before = {p.name: p.read_bytes() for p in (a, b)}
        self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT COUNT(DISTINCT sha256) FROM sources').fetchone()[0], 2)
        self.quiet(core.dedupe, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT COUNT(DISTINCT pcm_hash) FROM sources').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sources WHERE duplicate_of IS NOT NULL').fetchone()[0], 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (a, b)})

    @unittest.skipUnless(shutil.which('ffprobe'), 'ffprobe integration tool unavailable')
    def test_audio_under_odd_extension_and_legacy_ancillary_are_discovered(self):
        path = self.wav('Library/audio.legacy')
        self.source('Library/audio.legacy')
        with self.db:
            self.db.execute("UPDATE sources SET status='ancillary',size=?,mtime_ns=?", (path.stat().st_size, path.stat().st_mtime_ns))
        self.quiet(core.scan, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT status FROM sources').fetchone()[0], 'audio')

    def test_pcm_hash_refuses_changed_source_and_invalid_decoder_output(self):
        path = self.wav()
        row = core.inspect_file(self.root, path)
        self.wav(samples=(1, 2, 3, 4, 5))
        with mock.patch.object(core.subprocess, 'run') as run:
            digest, error, _ = core.pcm_digest(self.root, row)
        run.assert_not_called()
        self.assertIsNone(digest)
        self.assertIn('changed', error)
        row = core.inspect_file(self.root, path)
        with mock.patch.object(core.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=b'', stderr=b'')):
            digest, error, _ = core.pcm_digest(self.root, row)
        self.assertIsNone(digest)
        self.assertIn('valid sample hash', error)

    def test_dedupe_does_not_hold_write_transaction_while_decoding(self):
        self.wav()
        self.wav('Library/b.wav', (1, 2, 3, 4))
        self.quiet(core.scan, self.root, workers=1)
        def decode(root, row):
            # A second writer must be able to commit during expensive decoding.
            with sqlite3.connect(root/'_catalogue/catalogue.sqlite', timeout=.1) as other:
                other.execute("UPDATE ucs SET explanation='available'")
            return '8000:1:' + row['sha256'], None, row['path']
        with mock.patch.object(core, 'pcm_digest', side_effect=decode):
            self.quiet(core.dedupe, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT COUNT(pcm_hash) FROM sources').fetchone()[0], 2)

    def test_floating_point_pcm_cannot_be_grouped_by_quantized_s32_hash(self):
        self.source('Library/a.wav', 'bytes-a', 'old-clipped-hash')
        self.source('Library/b.wav', 'bytes-b', 'old-clipped-hash')
        with self.db:
            self.db.execute("UPDATE sources SET codec='pcm_f32le',bits=32")
        with mock.patch.object(core, 'pcm_digest', side_effect=AssertionError('Float samples must not be quantized')):
            self.quiet(core.dedupe, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT COUNT(pcm_hash) FROM sources').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(duplicate_of) FROM sources').fetchone()[0], 0)

    def test_import_retains_broad_labels_and_distinct_provenance(self):
        self.source('Library/a.wav')
        self.labels([self.label(catid=None, category='ANIMALS')], 'structured')
        self.labels([self.label(metadata_source='filename')], 'described')
        self.quiet(core.import_labels, self.root)
        rows = core.records(self.root)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r['id'] for r in rows}), 2)
        broad = next(r for r in rows if r['catid'] is None)
        self.assertEqual(broad['classification_status'], 'broad category')
        self.assertEqual(broad['category'], 'ANIMALS')
        self.assertEqual({r['metadata_source'] for r in rows}, {'guide.txt', 'filename'})

    def test_new_adapters_are_imported_without_a_filename_whitelist(self):
        self.source('Library/a.wav')
        self.labels([self.label()], 'additions')
        self.quiet(core.import_labels, self.root)
        self.assertEqual(core.records(self.root)[0]['adapter'], 'additions')

    def test_legacy_ids_review_and_guide_entry_survive_reimport(self):
        self.source('Library/a.wav')
        old_id = 'a'*24
        with self.db:
            self.db.execute('INSERT INTO descriptions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                            (old_id, 'Library/a.wav', 'Old wording', '', 'ANMLDog', 'ANIMALS', 'medium', 'Original evidence', 'sfx', 'guide.txt', 'structured', '{"entry_index": 1}'))
        self.review(old_id)
        self.labels([self.label(description='Corrected wording', entry_index=1, catid=None, category='ANIMALS')])
        self.quiet(core.import_labels, self.root)
        row = core.records(self.root)[0]
        self.assertEqual(row['id'], old_id)
        self.assertEqual(row['catid'], 'ANMLCat')
        self.assertTrue(row['reviewed'])
        self.assertEqual(row['suggested_category'], 'ANIMALS')
        self.assertIsNone(row['suggested_catid'])
        self.assertEqual(row['description'], 'Corrected wording')
        self.assertEqual(row['metadata_source'], 'guide.txt')

    def test_import_validation_is_atomic_across_adapters(self):
        self.source('Library/a.wav')
        self.labels([self.label()], 'described')
        self.quiet(core.import_labels, self.root)
        old = [dict(r) for r in self.db.execute('SELECT * FROM descriptions')]
        self.labels([self.label(description='New wording')], 'described')
        self.labels([self.label(catid='UNKNOWN')], 'structured')
        with self.assertRaises(ValueError):
            self.quiet(core.import_labels, self.root)
        self.assertEqual(old, [dict(r) for r in self.db.execute('SELECT * FROM descriptions')])

    def test_import_keeps_missing_source_provenance_until_return(self):
        self.source('Library/a.wav')
        self.labels([self.label()])
        self.quiet(core.import_labels, self.root)
        ident = core.records(self.root)[0]['id']
        with self.db:
            self.db.execute('UPDATE sources SET present=0')
        self.quiet(core.import_labels, self.root)
        self.assertEqual(self.db.execute('SELECT id FROM descriptions').fetchone()[0], ident)
        self.assertEqual(core.records(self.root), [])
        self.assertEqual(len(json.loads((self.root/'_catalogue/import-errors.json').read_text())), 1)
        with self.db:
            self.db.execute('UPDATE sources SET present=1')
        self.assertEqual(core.records(self.root)[0]['id'], ident)

    def test_bad_override_log_does_not_destroy_earlier_valid_review(self):
        self.source('Library/a.wav')
        self.labels([self.label()])
        self.quiet(core.import_labels, self.root)
        ident = core.records(self.root)[0]['id']
        self.review(ident, tail=json.dumps(dict(description_id=ident, catid='REMOVED'))+'\n{"partial":')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            row = core.records(self.root)[0]
        self.assertEqual(row['catid'], 'ANMLCat')
        self.assertEqual(len(caught), 2)

    def test_review_before_import_survives_single_description(self):
        self.source('Library/a.wav')
        ident = core.records(self.root)[0]['id']
        self.review(ident)
        self.labels([self.label()])
        self.quiet(core.import_labels, self.root)
        row = core.records(self.root)[0]
        self.assertTrue(row['reviewed'])
        self.assertEqual(row['catid'], 'ANMLCat')
        self.assertEqual(row['suggested_catid'], 'ANMLDog')

    def test_whole_recording_review_is_not_assigned_to_separate_guide_entries(self):
        self.source('Library/a.wav')
        self.review(core.records(self.root)[0]['id'])
        self.labels([self.label(entry_index=1), self.label(entry_index=2)])
        self.quiet(core.import_labels, self.root)
        rows = core.records(self.root)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(not r['reviewed'] and r['catid'] == 'ANMLDog' for r in rows))

    def test_coverage_includes_label_on_duplicate_only_and_counts_content_once(self):
        self.source('Library/a.wav', 'same')
        self.source('Library/b.wav', 'same')
        core.dedupe_paths(self.db)
        self.labels([self.label(path='Library/b.wav', entry_index=1), self.label(path='Library/b.wav', entry_index=2)])
        self.quiet(core.import_labels, self.root)
        self.quiet(core.build, self.root)
        coverage = json.loads((self.root/'_catalogue/coverage.json').read_text())
        dog = next(r for r in coverage if r['catid'] == 'ANMLDog')
        self.assertEqual(dog['source_files'], 1)
        self.assertEqual(dog['descriptions'], 2)
        summary = json.loads((self.root/'_catalogue/summary.json').read_text())
        self.assertEqual(summary['audio_files'], 2)
        self.assertEqual(summary['unique_files'], 1)
        self.assertEqual(summary['covered_leaves'], 1)

    def test_equal_samples_at_different_rates_share_family_but_are_not_duplicates(self):
        digest = 'a'*64
        self.source('Library/a.wav', 'bytes-a', '22000:1:' + digest)
        self.source('Library/b.aiff', 'bytes-b', '22255:1:' + digest)
        self.source('Library/stereo.wav', 'bytes-stereo', '22000:2:' + digest)
        self.source('Library/unknown.wav', 'bytes-unknown')
        with self.db:
            self.db.execute("UPDATE sources SET sample_rate=22000,channels=1")
            self.db.execute("UPDATE sources SET sample_rate=22255 WHERE path='Library/b.aiff'")
            self.db.execute("UPDATE sources SET channels=2 WHERE path='Library/stereo.wav'")
        core.dedupe_paths(self.db)
        rows = {r['path']: r for r in core.records(self.root)}
        self.assertEqual(rows['Library/a.wav']['sample_family'], '1:' + digest)
        self.assertEqual(rows['Library/b.aiff']['sample_family'], '1:' + digest)
        self.assertNotEqual(rows['Library/stereo.wav']['sample_family'], '1:' + digest)
        self.assertIsNone(rows['Library/unknown.wav']['sample_family'])
        self.assertTrue(all(r['duplicate_of'] is None for r in rows.values()))
        self.quiet(core.build, self.root)
        variants = json.loads((self.root/'_catalogue/sample-variants.json').read_text())
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]['sample_rates'], [22000, 22255])
        self.assertEqual(variants[0]['source_files'], 2)
        summary = json.loads((self.root/'_catalogue/summary.json').read_text())
        self.assertEqual(summary['sample_variant_families'], 1)
        self.assertEqual(summary['sample_variant_files'], 2)
        self.assertEqual(summary['unique_files'], 4)
        with (self.root/'_catalogue/catalogue.csv').open(encoding='utf-8-sig', newline='') as f:
            exported = {r['path']: r for r in csv.DictReader(f)}
        self.assertEqual(exported['Library/a.wav']['sample_family'], '1:' + digest)

    def workbook(self, sheet):
        ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with zipfile.ZipFile(self.root/'UCS v8.2.1 Full List.xlsx', 'w') as z:
            z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="UCS" sheetId="5" r:id="rId5"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId5" Target="worksheets/sheet5.xml"/></Relationships>')
            z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}"><si><r><t>ANI</t></r><r><t>MALS</t></r><rPh><t>phonetic annotation</t></rPh></si></sst>')
            z.writestr('xl/worksheets/sheet5.xml', f'<worksheet xmlns="{ns}"><sheetData>{sheet}</sheetData></worksheet>')

    def test_taxonomy_reads_actual_first_sheet_and_rich_text(self):
        self.workbook('<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="inlineStr"><is><t>DOG</t></is></c><c r="C1" t="inlineStr"><is><t> ANMLDog </t></is></c></row>')
        self.quiet(core.taxonomy, self.root)
        row = self.db.execute('SELECT * FROM ucs').fetchone()
        self.assertEqual(row['category'], 'ANIMALS')
        self.assertEqual(row['catid'], 'ANMLDog')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM ucs').fetchone()[0], 1)

    def test_empty_taxonomy_cannot_erase_existing_ucs(self):
        self.workbook('')
        with self.assertRaises(ValueError):
            self.quiet(core.taxonomy, self.root)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM ucs').fetchone()[0], 2)

    @unittest.skipUnless(os.name == 'nt', 'Windows path spelling test')
    def test_windows_path_helpers_round_trip_local_and_unc(self):
        for plain, extended in [
            ('C:\\collection\\folder\\sound.wav', '\\\\?\\C:\\collection\\folder\\sound.wav'),
            ('\\\\server\\share\\folder\\sound.wav', '\\\\?\\UNC\\server\\share\\folder\\sound.wav'),
        ]:
            self.assertEqual(str(core.native_path(plain)), extended)
            self.assertEqual(str(core.native_path(extended)), extended)
            self.assertEqual(str(core.logical_path(extended)), plain)

    @unittest.skipUnless(os.name == 'nt' and shutil.which('ffprobe') and shutil.which('ffmpeg'), 'Windows decoder integration tools unavailable')
    def test_long_path_scan_probe_pcm_and_games_adapter(self):
        from .adapters import games
        rel = 'games/Switch/' + '/'.join(('a'*80, 'b'*80, 'c'*80)) + '/asset_001.wav'
        path = self.root / rel
        self.assertGreater(len(str(path)), 260)
        access = core.native_path(path)
        access.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(access), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(struct.pack('<4h', 0, 100, -100, 32767))
        original = access.read_bytes()
        # This odd suffix forces ffprobe rather than the Python WAV fast path.
        other = access.with_suffix('.legacy')
        other.write_bytes(original)
        self.quiet(core.scan, self.root, workers=1)
        rows = [dict(r) for r in self.db.execute('SELECT * FROM sources')]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['status'] == 'audio' for r in rows))
        self.assertTrue(all(not r['path'].startswith('\\\\?\\') for r in rows))
        self.quiet(core.dedupe, self.root, workers=1)
        self.assertEqual(self.db.execute('SELECT COUNT(pcm_hash) FROM sources').fetchone()[0], 2)
        ucs = self.root/'ucs.json'
        ucs.write_text(json.dumps([dict(r) for r in self.db.execute('SELECT * FROM ucs')]), encoding='utf-8')
        output = self.root/'games.jsonl'
        with mock.patch('sys.argv', ['games', '--root', str(self.root), '--ucs', str(ucs), '--output', str(output)]):
            self.quiet(games.main)
        labels = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]['path'], rel)
        self.assertEqual(access.read_bytes(), original)
        self.assertEqual(other.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
