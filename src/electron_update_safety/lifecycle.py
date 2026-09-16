from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    parent_pid: int
    executable: str
    created: str


def _processes() -> list[ProcessIdentity]:
    if os.name != "nt":
        raise RuntimeError("process_inspection_requires_windows")
    command = "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,ExecutablePath,CreationDate | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True, timeout=15)
    rows = json.loads(result.stdout or "[]")
    rows = rows if isinstance(rows, list) else [rows]
    return [ProcessIdentity(int(r["ProcessId"]), int(r["ParentProcessId"]), r.get("ExecutablePath") or "", r.get("CreationDate") or "") for r in rows]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _same(expected: ProcessIdentity, current: ProcessIdentity | None) -> bool:
    return bool(current and current.created == expected.created and Path(current.executable).resolve() == Path(expected.executable).resolve())


class IsolatedRun:
    def __init__(self, run_directory: Path):
        self.run_directory = run_directory.resolve()
        self.record_path = self.run_directory / "run.json"
        self._process: subprocess.Popen[bytes] | None = None

    @classmethod
    def start(cls, executable: Path, runs_root: Path, args: list[str] | None = None, environment: dict[str, str] | None = None, debug_port: int | None = None) -> "IsolatedRun":
        executable = executable.resolve()
        if not executable.is_file():
            raise ValueError("executable_not_found")
        args = list(args or [])
        if any(item.startswith("--user-data-dir") for item in args):
            raise ValueError("user_data_dir_is_managed_by_the_tool")
        for protected in ("USERPROFILE","LOCALAPPDATA","APPDATA"):
            if environment and protected in environment: raise ValueError(f"protected_environment_override:{protected}")
        if debug_port is not None:
            with socket.socket() as probe:
                try: probe.bind(("127.0.0.1", debug_port))
                except OSError as error: raise ValueError("debug_port_unavailable") from error
            args.append(f"--remote-debugging-port={debug_port}")
        run = runs_root.resolve() / f"run-{uuid.uuid4().hex}"
        run.mkdir(parents=True, exist_ok=False)
        profile = run / "profile"; local = run / "local-app-data"; roaming = run / "app-data"; user_data = run / "user-data"
        for path in (profile, local, roaming, user_data): path.mkdir()
        isolated_environment = {"USERPROFILE":str(profile),"LOCALAPPDATA":str(local),"APPDATA":str(roaming)}
        stdout = (run / "stdout.log").open("xb")
        stderr = (run / "stderr.log").open("xb")
        try:
            process = subprocess.Popen([str(executable), *args, f"--user-data-dir={user_data}"], cwd=executable.parent, env={**os.environ, **isolated_environment, **(environment or {})}, stdout=stdout, stderr=stderr)
        finally:
            stdout.close(); stderr.close()
        time.sleep(0.2)
        current = next((p for p in _processes() if p.pid == process.pid), None)
        if current is None:
            raise RuntimeError("main_exited_before_identity_capture")
        record = {
            "schema_version": 1,
            "status": "started",
            "run_id": run.name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "main": asdict(current),
            "registered_backends": [],
            "executable_sha256": _sha256(executable),
        }
        (run / "run.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        instance = cls(run)
        instance._process = process
        return instance

    def _reap_started_process(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._process.wait(timeout=0)
            self._process = None

    def _load(self) -> dict:
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def _save(self, value: dict) -> None:
        temporary = self.record_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
        os.replace(temporary, self.record_path)

    def status(self, backend_name: str | None = None) -> dict:
        self._reap_started_process()
        record = self._load()
        rows = _processes()
        by_pid = {row.pid: row for row in rows}
        expected_main = ProcessIdentity(**record["main"])
        main_alive = _same(expected_main, by_pid.get(expected_main.pid))
        descendants = []
        frontier = [expected_main.pid]
        while frontier:
            parent = frontier.pop()
            children = [row for row in rows if row.parent_pid == parent]
            descendants.extend(children); frontier.extend(row.pid for row in children)
        if backend_name:
            for row in descendants:
                if Path(row.executable).name.casefold() == backend_name.casefold() and asdict(row) not in record["registered_backends"]:
                    record["registered_backends"].append(asdict(row))
            self._save(record)
        registered = [ProcessIdentity(**row) for row in record["registered_backends"]]
        alive_backends = [asdict(item) for item in registered if _same(item, by_pid.get(item.pid))]
        state = "running" if main_alive else "exited"
        if main_alive and backend_name and not record["registered_backends"]:
            state = "running_without_backend"
        if not main_alive and alive_backends:
            state = "backend_orphaned"
        if not main_alive:
            self._reap_started_process()
        return {**record, "status": state, "main_identity_match": main_alive, "alive_backends": alive_backends}

    def request_close(self, timeout: float, backend_name: str | None = None) -> dict:
        before = self.status(backend_name)
        if not before["main_identity_match"]:
            return {**before, "close_status": "refused_identity_mismatch"}
        if os.name != "nt":
            return {**before, "close_status": "unsupported_platform"}
        import ctypes
        user32 = ctypes.windll.user32; sent = 0; WM_CLOSE = 0x0010
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        expected_pid = int(before["main"]["pid"])
        def callback(hwnd, _):
            nonlocal sent
            owner = ctypes.c_ulong(); user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == expected_pid and user32.IsWindowVisible(hwnd):
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0); sent += 1
            return True
        user32.EnumWindows(callback_type(callback), 0)
        result = self.wait_for_exit(timeout, backend_name)
        return {**result, "close_status": "closed" if result.get("status") == "exited" else "timeout", "close_messages_sent": sent}

    def wait_for_exit(self, timeout: float, backend_name: str | None = None) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.status(backend_name)
            if result["status"] == "exited":
                return result
            time.sleep(0.25)
        result = self.status(backend_name)
        return {**result, "wait_status": "timeout"}
