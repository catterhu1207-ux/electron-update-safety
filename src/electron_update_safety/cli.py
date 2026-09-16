from __future__ import annotations
import argparse, json
from pathlib import Path
from .preflight import check_manifest, stage_source
from .lifecycle import IsolatedRun

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    for item in (check, sub.add_parser("stage")):
        item.add_argument("--source", required=True, type=Path); item.add_argument("--manifest", required=True, type=Path); item.add_argument("--consumer-root", required=True, type=Path)
    sub.choices["stage"].add_argument("--work-root", required=True, type=Path)
    start = sub.add_parser("start"); start.add_argument("--executable", required=True, type=Path); start.add_argument("--runs-root", required=True, type=Path); start.add_argument("--arg", action="append", default=[]); start.add_argument("--debug-port",type=int); start.add_argument("--isolate-shell-folders", action="store_true")
    status = sub.add_parser("status"); status.add_argument("--run", required=True, type=Path); status.add_argument("--backend-name")
    wait = sub.add_parser("wait"); wait.add_argument("--run", required=True, type=Path); wait.add_argument("--backend-name"); wait.add_argument("--timeout", type=float, default=20)
    stop = sub.add_parser("stop"); stop.add_argument("--run",required=True,type=Path); stop.add_argument("--backend-name"); stop.add_argument("--timeout",type=float,default=20)
    args = parser.parse_args()
    if args.command in {"check", "stage"}:
        result = check_manifest(args.source, args.manifest, args.consumer_root)
        if args.command == "stage": result = stage_source(args.source, args.work_root, result)
    elif args.command == "start":
        result = IsolatedRun.start(args.executable, args.runs_root, args.arg, debug_port=args.debug_port, isolate_shell_folders=args.isolate_shell_folders)._load()
    elif args.command == "status": result = IsolatedRun(args.run).status(args.backend_name)
    elif args.command == "wait": result = IsolatedRun(args.run).wait_for_exit(args.timeout, args.backend_name)
    else: result = IsolatedRun(args.run).request_close(args.timeout,args.backend_name)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") not in {"blocked", "backend_orphaned"} and result.get("wait_status") != "timeout" and result.get("close_status") != "timeout" else 2
