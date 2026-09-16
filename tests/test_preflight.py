import hashlib, json, os, shutil, tempfile, unittest
from pathlib import Path
from electron_update_safety.preflight import check_manifest, stage_source

class PreflightTests(unittest.TestCase):
    def fixture(self, root: Path):
        source=root/'source'; consumers=root/'consumers'; source.mkdir(); consumers.mkdir()
        (source/'app.bin').write_bytes(b'official'); (consumers/'adapter.py').write_text('VERSION = "1.2.3.4"',encoding='utf-8')
        manifest=root/'manifest.json'; manifest.write_text(json.dumps({'schema_version':1,'version':'1.2.3.4','source_files':{'app.bin':hashlib.sha256(b'official').hexdigest()},'required_consumers':{'adapter.py':['1.2.3.4','VERSION']}}),encoding='utf-8')
        return source,consumers,manifest
    def test_manifest_and_fresh_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source,consumers,manifest=self.fixture(root); check=check_manifest(source,manifest,consumers)
            self.assertEqual(check['status'],'passed'); first=stage_source(source,root/'work',check); (Path(first['stage_directory'])/'source/app.bin').write_bytes(b'changed')
            second=stage_source(source,root/'work',check); self.assertEqual((Path(second['stage_directory'])/'source/app.bin').read_bytes(),b'official')
    def test_missing_consumer_token_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source,consumers,manifest=self.fixture(root); (consumers/'adapter.py').write_text('VERSION="old"',encoding='utf-8')
            self.assertEqual(check_manifest(source,manifest,consumers)['status'],'blocked')
    def test_nested_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source,consumers,manifest=self.fixture(root); check=check_manifest(source,manifest,consumers)
            with self.assertRaisesRegex(ValueError,'must_not_be_nested'): stage_source(source,source/'work',check)
    def test_backend_descriptor_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source,consumers,manifest=self.fixture(root)
            value=json.loads(manifest.read_text(encoding='utf-8'))
            value['backend_descriptor']={'path':'app.bin','sha256':'0'*64}
            manifest.write_text(json.dumps(value),encoding='utf-8')
            result=check_manifest(source,manifest,consumers)
            self.assertEqual(result['status'],'blocked')
            self.assertIn('backend_descriptor_mismatch',result['errors'])
    def test_missing_consumer_file_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source,consumers,manifest=self.fixture(root)
            (consumers/'adapter.py').unlink()
            self.assertEqual(check_manifest(source,manifest,consumers)['status'],'blocked')
    @unittest.skipUnless(os.name=='nt','Windows long-path integration')
    def test_stage_supports_windows_long_paths(self):
        d=tempfile.mkdtemp()
        try:
            root=Path(d); source=root/'source'; consumers=root/'consumers'; source.mkdir(); consumers.mkdir()
            relative=Path(*(['long-segment-0123456789']*10))/'app.bin'
            extended=Path('\\\\?\\'+str(source/relative)); extended.parent.mkdir(parents=True); extended.write_bytes(b'official')
            (consumers/'adapter.py').write_text('VERSION = "1.2.3.4"',encoding='utf-8')
            manifest=root/'manifest.json'; manifest.write_text(json.dumps({'schema_version':1,'version':'1.2.3.4','source_files':{relative.as_posix():hashlib.sha256(b'official').hexdigest()},'required_consumers':{'adapter.py':['1.2.3.4']}}),encoding='utf-8')
            check=check_manifest(source,manifest,consumers)
            result=stage_source(source,root/'work',check)
            staged=Path('\\\\?\\'+str(Path(result['stage_directory'])/'source'/relative))
            self.assertEqual(staged.read_bytes(),b'official')
        finally:
            shutil.rmtree('\\\\?\\'+d)
