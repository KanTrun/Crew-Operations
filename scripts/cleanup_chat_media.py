#!/usr/bin/env python3
"""Cron script to cleanup expired chat media uploads according to data retention policy."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Default retention: 365 days (1 year) or configurable via env
RETENTION_DAYS = int(os.environ.get("CHAT_MEDIA_RETENTION_DAYS", "365"))
MAX_AGE_SECONDS = RETENTION_DAYS * 86400

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "data" / "uploads" / "chat"


def cleanup_expired_media(dry_run: bool = False) -> int:
    if not UPLOAD_DIR.exists():
        print(f"Directory {UPLOAD_DIR} does not exist. Nothing to clean.")
        return 0

    now = time.time()
    deleted_count = 0
    reclaimed_bytes = 0

    print(f"Scanning {UPLOAD_DIR} for files older than {RETENTION_DAYS} days...")

    for file_path in UPLOAD_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            stat = file_path.stat()
            file_age = now - stat.st_mtime
            if file_age > MAX_AGE_SECONDS:
                file_size = stat.st_size
                if not dry_run:
                    file_path.unlink()
                deleted_count += 1
                reclaimed_bytes += file_size
                print(f"{'[DRY RUN] Would delete' if dry_run else 'Deleted'}: {file_path.name} ({file_size} bytes)")
        except Exception as exc:
            print(f"Error checking {file_path}: {exc}", file=sys.stderr)

    mb_reclaimed = reclaimed_bytes / (1024 * 1024)
    print(f"Cleanup complete. Removed {deleted_count} files, reclaimed {mb_reclaimed:.2f} MB.")
    return deleted_count


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    cleanup_expired_media(dry_run=is_dry)
