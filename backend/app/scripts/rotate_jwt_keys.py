"""
M80: JWT RSA key rotation procedure
Rotates RS256 keypair in keys/ directory.
- Backs up current keys with timestamp
- Generates new RSA-2048 keypair
- Reloads app/core/security.py module globals
- Logs rotation event to audit

Usage:
  python -m app.scripts.rotate_jwt_keys
  python -m app.scripts.rotate_jwt_keys --force   # skip confirmation
  python -m app.scripts.rotate_jwt_keys --dry-run # show what would happen
"""
from __future__ import annotations
import argparse
import logging
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("m80_key_rotation")

BST = timezone(timedelta(hours=6))
KEYS_DIR = Path(__file__).resolve().parents[2] / "keys"
# ROTATION_LOG is computed dynamically in write_rotation_log


def _bst_now() -> str:
    return datetime.now(BST).strftime("%Y-%m-%d %H:%M:%S BST")


def _ts() -> str:
    return datetime.now(BST).strftime("%Y%m%d_%H%M%S")


def backup_current_keys(dry_run: bool = False) -> dict:
    """Backup current private.pem and public.pem with timestamp suffix."""
    ts = _ts()
    backed_up = []
    for fname in ("private.pem", "public.pem"):
        src = KEYS_DIR / fname
        if src.exists():
            dst = KEYS_DIR / f"{fname}.bak.{ts}"
            if not dry_run:
                shutil.copy2(src, dst)
            log.info("[M80] %s backup: %s → %s",
                     "Would copy" if dry_run else "Copied", src.name, dst.name)
            backed_up.append(str(dst))
    return {"backed_up": backed_up, "timestamp": ts}


def generate_and_write_keys(dry_run: bool = False) -> tuple[str, str]:
    """Generate new RSA-2048 keypair and write to keys/."""
    from app.core.security import generate_rsa_keypair
    priv, pub = generate_rsa_keypair()
    if not dry_run:
        KEYS_DIR.mkdir(exist_ok=True)
        (KEYS_DIR / "private.pem").write_text(priv)
        (KEYS_DIR / "public.pem").write_text(pub)
        log.info("[M80] New keypair written to %s", KEYS_DIR)
    else:
        log.info("[M80] DRY RUN — would write new keypair to %s", KEYS_DIR)
    return priv, pub


def reload_security_module() -> bool:
    """
    Reload app.core.security to pick up new keys.
    In production (gunicorn/uvicorn multi-worker), a rolling restart is required.
    This reloads for the current process only.
    """
    try:
        import importlib
        import app.core.security as sec_mod
        sec_mod.PRIVATE_KEY, sec_mod.PUBLIC_KEY = sec_mod.ensure_keypair_exists()
        log.info("[M80] Security module reloaded — new keys active in current process")
        log.warning("[M80] IMPORTANT: Restart all uvicorn/gunicorn workers to activate "
                    "new keys in all processes. Existing tokens signed with old key "
                    "will be invalid after restart.")
        return True
    except Exception as e:
        log.error("[M80] Module reload failed: %s", e)
        return False


def write_rotation_log(backup_info: dict, dry_run: bool = False) -> None:
    """Append rotation event to keys/rotation_log.txt for audit trail."""
    if dry_run:
        return
    entry = (
        f"[{_bst_now()}] KEY_ROTATION\n"
        f"  Backups: {backup_info['backed_up']}\n"
        f"  New keys written: keys/private.pem, keys/public.pem\n"
        f"  Operator: {os.getenv('USER', os.getenv('USERNAME', 'unknown'))}\n"
        f"  Host: {os.uname().nodename if hasattr(os, 'uname') else 'windows'}\n"
        "---\n"
    )
    with open(KEYS_DIR / 'rotation_log.txt', "a", encoding="utf-8") as f:
        f.write(entry)
    log.info("[M80] Rotation event logged to %s", KEYS_DIR / 'rotation_log.txt')


def cleanup_old_backups(keep: int = 5) -> list:
    """Keep only the N most recent backups per key file."""
    removed = []
    for prefix in ("private.pem.bak.", "public.pem.bak."):
        backups = sorted(KEYS_DIR.glob(f"{prefix}*"), key=lambda p: p.stat().st_mtime)
        to_remove = backups[:-keep] if len(backups) > keep else []
        for old in to_remove:
            old.unlink()
            removed.append(str(old))
            log.info("[M80] Removed old backup: %s", old.name)
    return removed


def rotate(force: bool = False, dry_run: bool = False) -> dict:
    """Full rotation procedure."""
    log.info("[M80] JWT RSA key rotation started — BST=%s", _bst_now())

    if dry_run:
        log.info("[M80] DRY RUN mode — no files will be modified")

    if not force and not dry_run:
        confirm = input(
            "\n⚠️  This will rotate JWT signing keys.\n"
            "All existing tokens will be invalidated after worker restart.\n"
            "Type 'yes' to continue: "
        ).strip()
        if confirm.lower() != "yes":
            log.info("[M80] Rotation cancelled by operator")
            return {"status": "CANCELLED"}

    backup_info = backup_current_keys(dry_run=dry_run)
    priv, pub = generate_and_write_keys(dry_run=dry_run)

    if not dry_run:
        reloaded = reload_security_module()
        write_rotation_log(backup_info, dry_run=dry_run)
        removed = cleanup_old_backups(keep=5)
    else:
        reloaded = False
        removed = []

    result = {
        "status": "DRY_RUN" if dry_run else "ROTATED",
        "backed_up": backup_info["backed_up"],
        "removed_old_backups": removed,
        "module_reloaded": reloaded,
        "bst_timestamp": _bst_now(),
        "action_required": "Restart all uvicorn workers to activate new keys",
    }
    log.info("[M80] Rotation complete: %s", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="M80: JWT RSA key rotation")
    parser.add_argument("--force",   action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()
    result = rotate(force=args.force, dry_run=args.dry_run)
    print(f"\nM80 result: {result}")


if __name__ == "__main__":
    main()
