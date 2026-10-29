# RECOVEROPS automation and evidence

| Capability | Status | Evidence |
|---|---|---|
| Fixture checksums and restore verification | IMPLEMENTED / LAB VALIDATED | `src/recoverops.py demo` and tests |
| Corruption and missing-file detection | IMPLEMENTED / LAB VALIDATED | Disposable manifest tests and drill |
| Local service failure/detection/recovery | IMPLEMENTED / LAB VALIDATED | Loopback-only child HTTP service in demo |
| Host health summary | IMPLEMENTED | Read-only `scripts/collect-health.sh` |
| Fixture retention report | IMPLEMENTED / LAB VALIDATED | Read-only age summary; no deletions |
| Proxmox, guest layout and ZFS | DESIGNED / PLANNED | `docs/architecture.md`; no host install/pool |
| Production BruteHost backup | DEFERRED / NOT IMPLEMENTED | Explicitly excluded from fixture lab |

Run the disposable drill with `python3 src/recoverops.py demo`. It creates all files in a fresh `TemporaryDirectory`, uses a child HTTP process bound only to loopback, detects stop/recovery, verifies restored fixture hashes, detects a deliberately corrupted copy, then removes all temporary state. The output contains status and counts only, not fixture content.

`retention_report` reads only a named RECOVEROPS temporary fixture and uses an illustrative 14-day window; it never deletes files and is not an active retention policy. `scripts/collect-health.sh` reads host uptime, load, memory, root filesystem usage and two generic service states. It does not change state or transmit data. The lab recovery duration is a local test measurement and must never be presented as a business RTO.
