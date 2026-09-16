# v0.1.0

Experimental source release for hash-gated update staging and isolated Windows process validation.

- Adds `check` and `stage` with explicit file digests and version-consumer contracts.
- Adds `start`, `status`, `wait`, and `stop` with PID creation-time and executable-path identity checks.
- Preserves registered backend identities after the main process exits.
- Covers long paths, repeated runs, port conflicts, PID reuse, protected arguments, and close timeouts with synthetic tests.

No application binaries or real profile data are included.
