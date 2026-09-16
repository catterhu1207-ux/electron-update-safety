import os,sys,tempfile,time,unittest
from pathlib import Path
from electron_update_safety.lifecycle import IsolatedRun

@unittest.skipUnless(os.name=='nt','Windows process integration')
class WindowsIntegrationTests(unittest.TestCase):
    def test_two_independent_full_lifecycles(self):
        example=Path(__file__).parents[1]/'examples/example_app.py'
        with tempfile.TemporaryDirectory() as directory:
            identities=[]
            for _ in range(2):
                run=IsolatedRun.start(Path(sys.executable),Path(directory),[str(example)])
                backend=Path(sys.executable).name
                try:
                    self.assertEqual(run._load()['shell_folders'],'inherited')
                    self.assertFalse((run.run_directory/'profile').exists())
                    deadline=time.monotonic()+5
                    while True:
                        active=run.status(backend)
                        if active['registered_backends'] or time.monotonic()>=deadline:
                            break
                        time.sleep(0.1)
                    self.assertEqual(active['status'],'running')
                    self.assertTrue(active['registered_backends'])
                    complete=run.wait_for_exit(12,backend)
                    self.assertEqual(complete['status'],'exited')
                    self.assertEqual(complete['alive_backends'],[])
                    identities.append(active['run_id'])
                finally:
                    run.wait_for_exit(12,backend)
            self.assertNotEqual(*identities)
