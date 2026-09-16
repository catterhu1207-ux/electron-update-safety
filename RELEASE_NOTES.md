# v0.1.3

Graceful shutdown support for Electron applications that remain in the tray after their last window closes.

- Records an explicitly requested local DevTools port in the run identity.
- Uses the Chrome DevTools Protocol `Browser.close` request during `stop`, after checking the run identity.
- Keeps close timeouts non-destructive when the endpoint is unavailable.

# v0.1.2

Compatibility fix for Electron applications that resolve Windows known folders during startup.

- Keeps Windows shell folders inherited by default while continuing to isolate Electron `--user-data-dir`.
- Adds the explicit `--isolate-shell-folders` option for applications that support redirected shell folders.
- Records the selected shell-folder mode in each run record.

# v0.1.1

Maintenance release for deterministic Windows integration validation.

- Waits up to five seconds for a newly spawned backend to appear in the Windows process table.
- Ensures a failed assertion still waits for the test-owned process tree to exit naturally.
- Leaves runtime process-status semantics unchanged.

# v0.1.0

Experimental source release for hash-gated update staging and isolated Windows process validation.

- Adds `check` and `stage` with explicit file digests and version-consumer contracts.
- Adds `start`, `status`, `wait`, and `stop` with PID creation-time and executable-path identity checks.
- Preserves registered backend identities after the main process exits.
- Covers long paths, repeated runs, port conflicts, PID reuse, protected arguments, and close timeouts with synthetic tests.

No application binaries or real profile data are included.
