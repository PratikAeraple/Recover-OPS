# Disposable recovery drill evidence

## RO-LAB-01 — service failure and restart

**LAB VALIDATED:** a child HTTP service bound to `127.0.0.1` served a fixed health identity; the process was terminated, the failed health probe was recorded, and a fresh child process restored the service. Expected sequence: `UP → DOWN_DETECTED → UP_RECOVERED`. This is a local process drill and not a BruteHost service event.

## RO-LAB-02 — configuration/data loss and restore

**LAB VALIDATED:** two generated fixture files were copied into a disposable recovery copy, the source fixture was removed, and a fresh restore destination was populated from the copy. Both SHA-256 values matched the original manifest. A separate deliberately corrupted copy was rejected. Temporary content and manifest never leave the test's OS temporary directory.

## RO-LAB-03 — integrity and unsafe-path controls

**LAB VALIDATED:** altered content fails digest verification; absolute, traversal and symlink paths are rejected; an existing destination cannot be overwritten. These tests validate the fixture tool's safety controls, not the durability of a production storage backend.

There are no real customer incidents, backup jobs, restore times, RPO/RTO achievements or production backups represented here.
