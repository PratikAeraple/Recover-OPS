# Disposable recovery drill runbook

This exercise touches only a newly created directory under the system temporary directory. It refuses paths outside the OS temporary directory and refuses to reuse an existing workspace. Do not change the guard to point at application or production data.

```bash
python3 -m unittest discover -s tests -v
python3 src/recoverops.py demo
```

The demonstration creates a random disposable fixture, writes a SHA-256 manifest, simulates loss of a file, restores to a new directory, compares hashes, and emits a summary without fixture contents. It also creates a deliberate corrupted copy and proves the verifier rejects it. The workspace is removed on exit.

## Recovery acceptance checks

- Source and destination are separate directories.
- Manifest paths are relative, normalized and cannot escape the workspace.
- Hash algorithm and digest shape are validated before reading a file.
- A corrupted or missing file fails closed.
- Successful restore is accepted only when every expected digest matches.
- Lab output is labeled `LAB VALIDATED`; it is not evidence for a production backup or a measured business RTO.

## Future real-platform procedure (DESIGNED)

1. Confirm incident scope, restore point, application consistency and owner authorization.
2. Isolate destination; verify independent-copy credentials and manifest authenticity.
3. Restore to a clean disposable VM/volume with network access denied by default.
4. Validate file hashes, application startup, data consistency, permissions and security controls.
5. Obtain service-owner acceptance before reconnecting traffic.
6. Record actual timestamps, source copy ID, result, exceptions and evidence location without exposing data.
7. Preserve incident evidence and conduct a controlled post-incident review.

Production backups on BruteHost are **DEFERRED / NOT IMPLEMENTED**. This runbook does not authorize snapshots, ZFS pool creation, disk writes or production restores.
