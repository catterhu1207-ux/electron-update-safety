"""Public API for electron-update-safety."""
from .preflight import check_manifest, stage_source
from .lifecycle import IsolatedRun, ProcessIdentity

__all__ = ["check_manifest", "stage_source", "IsolatedRun", "ProcessIdentity"]
__version__ = "0.1.0"
