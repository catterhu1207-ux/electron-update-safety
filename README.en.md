# electron-update-safety

Experimental Python tools for hash-gated update staging and identity-aware process checks for Windows Electron applications.

Install with `py -3 -m pip install -e .`. Use `check` before adaptation, `stage` to create a fresh verified copy, and `start/status/wait` to observe an isolated test process. The tool never terminates user applications. Python 3.10+ is required; live process inspection is Windows-only.

Related projects: [codex-history-compat](https://github.com/catterhu1207-ux/codex-history-compat) and [desktop-adaptation-lab](https://github.com/catterhu1207-ux/desktop-adaptation-lab).
