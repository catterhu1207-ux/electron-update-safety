import json, socket, tempfile, unittest
from pathlib import Path
from unittest import mock
from electron_update_safety.lifecycle import IsolatedRun, ProcessIdentity

class LifecycleTests(unittest.TestCase):
    def make_run(self, root: Path):
        d=root/'run'; d.mkdir(); (d/'run.json').write_text(json.dumps({'schema_version':1,'status':'started','main':{'pid':1,'parent_pid':0,'executable':'C:/demo/app.exe','created':'a'},'registered_backends':[{'pid':2,'parent_pid':1,'executable':'C:/demo/backend.exe','created':'b'}]})); return IsolatedRun(d)
    def test_main_exit_does_not_hide_backend(self):
        with tempfile.TemporaryDirectory() as d:
            run=self.make_run(Path(d)); rows=[ProcessIdentity(2,1,'C:/demo/backend.exe','b')]
            with mock.patch('electron_update_safety.lifecycle._processes',return_value=rows): self.assertEqual(run.status('backend.exe')['status'],'backend_orphaned')
    def test_pid_reuse_is_not_identity_match(self):
        with tempfile.TemporaryDirectory() as d:
            run=self.make_run(Path(d)); rows=[ProcessIdentity(1,0,'C:/demo/app.exe','new')]
            with mock.patch('electron_update_safety.lifecycle._processes',return_value=rows): self.assertFalse(run.status()['main_identity_match'])
    def test_protected_environment_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as d:
            executable=Path(d)/'app.exe'; executable.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'protected_environment_override'):
                IsolatedRun.start(executable,Path(d)/'runs',environment={'USERPROFILE':'unsafe'})
    def test_user_data_directory_argument_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as d:
            executable=Path(d)/'app.exe'; executable.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'user_data_dir_is_managed'):
                IsolatedRun.start(executable,Path(d)/'runs',args=['--user-data-dir=unsafe'])
    def test_debug_port_conflict_blocks_before_start(self):
        with tempfile.TemporaryDirectory() as d, socket.socket() as listener:
            executable=Path(d)/'app.exe'; executable.write_bytes(b'x')
            listener.bind(('127.0.0.1',0)); port=listener.getsockname()[1]
            with self.assertRaisesRegex(ValueError,'debug_port_unavailable'):
                IsolatedRun.start(executable,Path(d)/'runs',debug_port=port)
    def test_wait_timeout_reports_without_terminating(self):
        with tempfile.TemporaryDirectory() as d:
            run=self.make_run(Path(d)); rows=[ProcessIdentity(1,0,'C:/demo/app.exe','a')]
            with mock.patch('electron_update_safety.lifecycle._processes',return_value=rows):
                result=run.wait_for_exit(0)
            self.assertEqual(result['wait_status'],'timeout')
            self.assertTrue(result['main_identity_match'])
