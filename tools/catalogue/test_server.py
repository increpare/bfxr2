"""Integration checks against a temporary synthetic library, never real reviews."""
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import wave

from .core import connect, inspect_file, CREATE_NO_WINDOW


class BrowserIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        library = cls.root / 'Synthetic'
        library.mkdir()
        cls.original = library / 'test.wav'
        with wave.open(str(cls.original), 'wb') as f:
            f.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
            f.writeframes(b'\x00\x10\x00\xf0' * 2205)
        cls.before = hashlib.sha256(cls.original.read_bytes()).hexdigest()
        db = connect(cls.root)
        row = inspect_file(cls.root, cls.original)
        cols = list(row)
        with db:
            db.execute(f"INSERT INTO sources ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", list(row.values()))
            db.execute('INSERT INTO ucs VALUES (?,?,?,?,?)', ('TESTTone','TEST','TONE','Synthetic test','tone'))
        db.close()
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            cls.port = s.getsockname()[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.process = subprocess.Popen([sys.executable,'-m','catalogue','serve','--root',str(cls.root),'--port',str(cls.port)], cwd=Path(__file__).resolve().parents[1],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=CREATE_NO_WINDOW)
        for _ in range(50):
            try:
                cls.page = urllib.request.urlopen(cls.base,timeout=1).read().decode()
                break
            except urllib.error.URLError:
                time.sleep(.1)
        else:
            cls.process.terminate()
            cls.temp.cleanup()
            raise RuntimeError('Test browser server did not start')
        cls.token = re.search("token='([^']+)'",cls.page)[1]
        cls.ident = cls.get_json('/api/records')[0]['id']

    @classmethod
    def get_json(cls, path):
        with urllib.request.urlopen(cls.base+path,timeout=5) as response:
            return json.load(response)

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.temp.cleanup()

    def post(self, body, token=None, origin=None):
        headers={'Content-Type':'application/json'}
        if token: headers['X-Catalogue-Token']=token
        if origin: headers['Origin']=origin
        return urllib.request.urlopen(urllib.request.Request(self.base+'/api/review',json.dumps(body).encode(),headers=headers),timeout=10)

    def test_audio_range_and_original_integrity(self):
        request=urllib.request.Request(self.base+'/audio/'+self.ident,headers={'Range':'bytes=0-43'})
        with urllib.request.urlopen(request,timeout=20) as response:
            data=response.read()
            self.assertEqual(response.status,206)
            self.assertEqual(len(data),44)
            self.assertEqual(data[:4],b'RIFF')
            self.assertTrue(response.headers['Content-Range'].startswith('bytes 0-43/'))
        self.assertEqual(hashlib.sha256(self.original.read_bytes()).hexdigest(),self.before)

    def test_reject_unknown_audio(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base+'/audio/'+('0'*24),timeout=5)
        self.assertEqual(error.exception.code,404)

    def test_browser_dependencies_are_served_as_javascript(self):
        for script in ('browser_logic.js', 'browser_app.js'):
            with urllib.request.urlopen(self.base+'/'+script,timeout=5) as response:
                self.assertEqual(response.status,200)
                self.assertIn('javascript',response.headers['Content-Type'])
                self.assertGreater(len(response.read()),100)

    def test_review_requires_token_and_same_origin(self):
        for token,origin in [(None,None),(self.token,'https://example.com')]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post({'id':self.ident,'catid':'TESTTone'},token,origin)
            self.assertEqual(error.exception.code,403)

    def test_review_validation_and_persistence(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.post({'id':self.ident,'catid':'NOT-A-CATEGORY'},self.token)
        self.assertEqual(error.exception.code,400)
        with self.post({'id':self.ident,'catid':'TESTTone'},self.token) as response:
            self.assertEqual(response.status,200)
        record=self.get_json('/api/records')[0]
        self.assertEqual(record['catid'],'TESTTone')
        self.assertTrue(record['reviewed'])
        event=json.loads((self.root/'_catalogue'/'overrides.jsonl').read_text())
        self.assertEqual(event['description_id'],self.ident)
        self.assertEqual(hashlib.sha256(self.original.read_bytes()).hexdigest(),self.before)


if __name__ == '__main__':
    unittest.main()
