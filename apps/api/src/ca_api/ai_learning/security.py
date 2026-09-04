"""Deployment attestation for the encrypted-volume operational control."""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOG = logging.getLogger(__name__)
_minimal_data_mode = False


def verify_encrypted_volume() -> bool:
    """Require infrastructure attestation in production; disk inspection is not portable."""
    production = os.environ.get("NHIPQUAN_ENV", "development").strip().lower() == "production"
    return not production or os.environ.get("NHIPQUAN_ENCRYPTED_VOLUME_VERIFIED", "").lower() == "true"


def configure_data_protection() -> bool:
    global _minimal_data_mode
    verified = verify_encrypted_volume()
    _minimal_data_mode = not verified
    if not verified:
        LOG.critical("encrypted-volume attestation failed; AI learning is in minimal-data mode")
    return verified


def minimal_data_mode() -> bool:
    return _minimal_data_mode


def encrypted_data_root() -> Path | None:
    """Return the attested encrypted root in production, or no constraint in development."""
    production = os.environ.get("NHIPQUAN_ENV", "development").strip().lower() == "production"
    if not production:
        return None
    configured = os.environ.get("NHIPQUAN_ENCRYPTED_DATA_ROOT", "").strip()
    if not configured:
        return None
    return Path(configured).resolve()


def require_encrypted_data_path(path: Path) -> None:
    """Fail closed when production data leaves the explicitly attested encrypted root."""
    production = os.environ.get("NHIPQUAN_ENV", "development").strip().lower() == "production"
    if not production:
        return
    root = encrypted_data_root()
    if not verify_encrypted_volume() or root is None:
        raise ValueError("ai_learning_encrypted_storage_unverified")
    try:
        path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("ai_learning_backup_outside_encrypted_root") from error