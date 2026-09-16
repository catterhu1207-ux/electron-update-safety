"""Self-authored process fixture for lifecycle testing."""
import subprocess,sys,time
if '--backend' in sys.argv:
    time.sleep(8.0)
else:
    child=subprocess.Popen([sys.executable,__file__,'--backend'])
    time.sleep(0.5)
    child.wait()
