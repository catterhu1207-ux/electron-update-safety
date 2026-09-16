import os,sys,tempfile,unittest
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
                active=run.status(Path(sys.executable).name)
                self.assertEqual(active['status'],'running')
                self.assertTrue(active['registered_backends'])
                complete=run.wait_for_exit(12,Path(sys.executable).name)
                self.assertEqual(complete['status'],'exited')
                self.assertEqual(complete['alive_backends'],[])
                identities.append(active['run_id'])
            self.assertNotEqual(*identities)
