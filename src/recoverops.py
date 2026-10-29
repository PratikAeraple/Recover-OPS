#!/usr/bin/env python3
"""Safe disposable fixture recovery demonstration; never targets production paths."""
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

MAX_FILE_BYTES = 1_000_000


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_manifest(root):
    root = Path(root).resolve(strict=True)
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink fixture entries are not supported")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("fixture file exceeds size limit")
            entries.append({"path": rel, "size": path.stat().st_size, "sha256": sha256(path)})
    return {"schema": 1, "algorithm": "sha256", "files": entries}


def safe_destination(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in {".", ".."} for part in rel.parts):
        raise ValueError("unsafe manifest path")
    root = Path(root).resolve()
    lexical = root
    for part in rel.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise ValueError("symlink traversal is not allowed")
    dest = lexical.resolve()
    if dest != root and root not in dest.parents:
        raise ValueError("manifest path escapes destination")
    return dest


def verify_manifest(source, manifest):
    source = Path(source).resolve(strict=True)
    if manifest.get("schema") != 1 or manifest.get("algorithm") != "sha256" or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported manifest")
    results = []
    for entry in manifest["files"]:
        path = safe_destination(source, entry.get("path", ""))
        if not path.is_file() or path.is_symlink():
            results.append({"path": entry["path"], "status": "missing"})
            continue
        actual = sha256(path)
        expected = entry.get("sha256", "")
        results.append({"path": entry["path"], "status": "verified" if actual == expected and path.stat().st_size == entry.get("size") else "mismatch"})
    return {"ok": bool(results) and all(row["status"] == "verified" for row in results), "files": results}


def restore(source, destination, manifest):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if destination.exists():
        raise ValueError("restore destination must not already exist")
    destination.mkdir(mode=0o700, parents=True)
    for entry in manifest.get("files", []):
        src = safe_destination(source, entry.get("path", ""))
        dst = safe_destination(destination, entry.get("path", ""))
        if not src.is_file() or src.is_symlink():
            raise ValueError("source fixture is missing or unsafe")
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o600)
    return verify_manifest(destination, manifest)


def retention_report(copy_dir, now=None, example_window_days=14):
    """Report age in a RECOVEROPS temporary fixture only; never deletes anything."""
    root = Path(copy_dir).resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root not in root.parents or not any(parent.name.startswith("recoverops-lab-") for parent in root.parents):
        raise ValueError("retention reporting is limited to RECOVEROPS temporary lab fixtures")
    if not 1 <= int(example_window_days) <= 3650:
        raise ValueError("example retention window must be 1..3650 days")
    now = time.time() if now is None else float(now)
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    ages = [max(0.0, (now - path.stat().st_mtime) / 86400) for path in files]
    return {"status": "LAB FIXTURE ONLY", "files_observed": len(files),
            "within_illustrative_window": sum(age <= example_window_days for age in ages),
            "older_than_illustrative_window": sum(age > example_window_days for age in ages),
            "illustrative_window_days": int(example_window_days), "deletions": 0}


SERVICE_CODE = """from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  body=b'recoverops-lab-service-ready\\n'; self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
 def log_message(self,*args): pass
HTTPServer(('127.0.0.1',int(__import__('sys').argv[1])),H).serve_forever()
"""


def service_failure_drill():
    """Stop/restart one child HTTP fixture and record observed state transitions."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}/healthz"

    def start():
        return subprocess.Popen([sys.executable, "-c", SERVICE_CODE, str(port)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                close_fds=True)

    def healthy():
        try:
            with urllib.request.urlopen(url, timeout=0.3) as response:
                return response.status == 200 and response.read(100) == b"recoverops-lab-service-ready\n"
        except (OSError, urllib.error.URLError):
            return False

    states = []
    child = start()
    try:
        for _ in range(30):
            if healthy():
                break
            if child.poll() is not None:
                raise RuntimeError("fixture service exited before readiness")
            time.sleep(0.03)
        if not healthy():
            raise RuntimeError("fixture service failed to become healthy")
        states.append("UP")
        child.terminate(); child.wait(timeout=2)
        if healthy():
            raise RuntimeError("stopped fixture remained reachable")
        states.append("DOWN_DETECTED")
        child = start()
        for _ in range(30):
            if healthy():
                break
            if child.poll() is not None:
                raise RuntimeError("restarted fixture exited before readiness")
            time.sleep(0.03)
        if not healthy():
            raise RuntimeError("fixture service did not recover")
        states.append("UP_RECOVERED")
        return {"status": "LAB VALIDATED", "observed_states": states}
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=2)


def run_demo():
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="recoverops-lab-") as temp:
        root = Path(temp)
        source = root / "source"
        backup = root / "disposable-copy"
        restored = root / "restored"
        source.mkdir(mode=0o700)
        (source / "service.conf").write_text("mode=demo\nlistener=127.0.0.1\n")
        (source / "data.txt").write_text("fixture-only recovery record\n")
        manifest = make_manifest(source)
        (backup).mkdir(mode=0o700)
        shutil.copytree(source, backup, dirs_exist_ok=True)
        shutil.rmtree(source)
        restored_result = restore(backup, restored, manifest)
        retention = retention_report(backup)
        corrupt = root / "corrupt-copy"
        shutil.copytree(backup, corrupt)
        (corrupt / "data.txt").write_text("deliberate corruption\n")
        corruption_detected = not verify_manifest(corrupt, manifest)["ok"]
        service = service_failure_drill()
        report = {"status": "LAB VALIDATED" if restored_result["ok"] and corruption_detected and service["status"] == "LAB VALIDATED" else "FAILED",
                  "files_restored_and_verified": len(restored_result["files"]),
                  "corruption_detected": corruption_detected,
                  "retention_fixture_report": retention,
                  "service_drill": service,
                  "elapsed_seconds": round(time.monotonic() - started, 4),
                  "scope": "temporary disposable fixture and loopback child service only; no production data; elapsed time is not a production RTO"}
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="run and automatically remove a disposable fixture recovery drill")
    args = parser.parse_args()
    report = run_demo()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "LAB VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
