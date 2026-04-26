"""
M103 -- OpenSanctions PEP Fetcher -- BFIU Circular No. 29 s4.2
Fetches Bangladesh PEP entries from OpenSanctions (updated daily).
Sources: Wikidata PEPs + OpenSanctions annotations + UN SC Sanctions

Usage:
  python -m app.scripts.fetch_opensanctions_pep
  python -m app.scripts.fetch_opensanctions_pep --dry-run
  python -m app.scripts.fetch_opensanctions_pep --limit 500
"""
import csv
import logging
import sys
import uuid
import argparse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models_pep import PEPEntry, PEPListMeta, PEPAuditLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("m103_opensanctions")

BST = timezone(timedelta(hours=6))
def _bst_now(): return datetime.now(BST)

PEP_URL      = "https://data.opensanctions.org/datasets/latest/peps/targets.simple.csv"
SANC_URL     = "https://data.opensanctions.org/datasets/latest/un_sc_sanctions/targets.simple.csv"
OFAC_URL     = "https://data.opensanctions.org/datasets/latest/us_ofac_sdn/targets.simple.csv"
EU_URL       = "https://data.opensanctions.org/datasets/latest/eu_fsf/targets.simple.csv"
UK_URL       = "https://data.opensanctions.org/datasets/latest/gb_hmt_sanctions/targets.simple.csv"
LIST_NAME   = "opensanctions_bd"
LIST_VER    = "opensanctions_live"
BFIU_REF    = "BFIU Circular No. 29 s4.2"


def _fetch_bd_peps(limit: int = 0) -> list[dict]:
    """Stream PEP CSV, return only Bangladesh entries."""
    log.info("Fetching BD PEPs from OpenSanctions...")
    r = urllib.request.urlopen(PEP_URL, timeout=30)
    header_line = r.readline().decode("utf-8")
    reader = csv.reader([header_line])
    header = next(reader)

    entries = []
    total   = 0
    while True:
        line = r.readline().decode("utf-8")
        if not line:
            break
        total += 1
        if "bd" not in line:
            continue
        row = next(csv.reader([line]))
        if len(row) < len(header):
            continue
        rec = dict(zip(header, row))
        if rec.get("countries", "").strip().lower() != "bd":
            continue
        if rec.get("schema", "") not in ("Person", "LegalEntity"):
            continue
        entries.append(rec)
        if limit and len(entries) >= limit:
            break

    log.info("Scanned %d rows, found %d BD entries", total, len(entries))
    return entries


def _fetch_un_sanctions() -> list[dict]:
    """Fetch full UN SC sanctions list (337KB)."""
    log.info("Fetching UN SC sanctions...")
    r = urllib.request.urlopen(SANC_URL, timeout=30)
    data = r.read().decode("utf-8")
    lines = data.strip().split("\n")
    if not lines:
        return []
    header = next(csv.reader([lines[0]]))
    entries = []
    for line in lines[1:]:
        if not line.strip():
            continue
        row = next(csv.reader([line]))
        if len(row) < len(header):
            continue
        entries.append(dict(zip(header, row)))
    log.info("UN sanctions entries: %d", len(entries))
    return entries


def _fetch_sanctions_list(url: str, label: str) -> list[dict]:
    """Generic fetcher for any OpenSanctions CSV sanctions list."""
    log.info("Fetching %s from %s...", label, url)
    try:
        r = urllib.request.urlopen(url, timeout=30)
        data = r.read().decode("utf-8")
        lines = data.strip().split("\n")
        if not lines:
            return []
        header = next(csv.reader([lines[0]]))
        entries = []
        for line in lines[1:]:
            if not line.strip():
                continue
            row = next(csv.reader([line]))
            if len(row) < len(header):
                continue
            entries.append(dict(zip(header, row)))
        log.info("%s entries: %d", label, len(entries))
        return entries
    except Exception as e:
        log.error("Failed to fetch %s: %s", label, e)
        return []


def _map_to_pep(rec: dict, source: str) -> dict:
    """Map OpenSanctions row to PEPEntry fields."""
    name = rec.get("name", "").strip()
    aliases = rec.get("aliases", "").strip()
    dob = rec.get("birth_date", "").strip() or None
    if dob and ";" in dob:
        dob = dob.split(";")[0].strip()

    # Determine category
    datasets = rec.get("dataset", "").lower()
    sanctions = rec.get("sanctions", "").strip()
    if sanctions or "sanction" in datasets:
        category = "PEP"
        risk = "HIGH"
    elif "pep" in datasets or "politically" in datasets:
        category = "PEP"
        risk = "HIGH"
    else:
        category = "PEP"
        risk = "MEDIUM"

    return {
        "full_name_en":   name,
        "full_name_bn":   None,
        "date_of_birth":  dob,
        "national_id":    None,
        "passport_number":None,
        "nationality":    "BD",
        "category":       category,
        "position":       None,
        "ministry_or_org":rec.get("dataset", "")[:100] or None,
        "country":        "BD",
        "risk_level":     risk,
        "notes":          f"OpenSanctions ID: {rec.get('id','')} | aliases: {aliases[:100]}" if aliases else f"OpenSanctions ID: {rec.get('id','')}",
        "source":         source,
        "source_ref":     rec.get("id", ""),
    }


def _upsert(db: Session, data: dict, dry_run: bool = False) -> tuple:
    """Insert or update PEP entry. Returns (entry, action)."""
    existing = db.query(PEPEntry).filter(
        PEPEntry.full_name_en == data["full_name_en"]
    ).first()

    if existing:
        if dry_run:
            return existing, "skipped"
        existing.notes       = data.get("notes")
        existing.risk_level  = data.get("risk_level", "HIGH")
        existing.category    = data.get("category", "PEP")
        existing.ministry_or_org = data.get("ministry_or_org")
        existing.date_of_birth   = data.get("date_of_birth")
        return existing, "updated"

    if dry_run:
        return None, "would_create"

    entry = PEPEntry(
        id               = uuid.uuid4(),
        full_name_en     = data["full_name_en"],
        full_name_bn     = data.get("full_name_bn"),
        date_of_birth    = data.get("date_of_birth"),
        national_id      = data.get("national_id"),
        passport_number  = data.get("passport_number"),
        nationality      = (data.get("nationality") or "BD")[:3],
        category         = data.get("category", "PEP"),
        position         = data.get("position"),
        ministry_or_org  = (data.get("ministry_or_org") or "")[:255] or None,
        country          = (data.get("country") or "BD")[:3],
        risk_level       = data.get("risk_level", "HIGH"),
        notes            = (data.get("notes") or "")[:500] or None,
        source           = data.get("source", "OPENSANCTIONS"),
        source_reference = (data.get("source_ref") or "")[:255] or None,
        status           = "ACTIVE",
        aliases          = [],
    )
    db.add(entry)
    return entry, "created"


def _update_meta(db: Session, total: int):
    meta = db.query(PEPListMeta).filter_by(list_name=LIST_NAME).first()
    now  = _bst_now()
    ver  = f"opensanctions_{now.strftime('%Y%m%d')}"
    if meta:
        meta.version        = ver
        meta.total_entries  = total
        meta.last_updated_at = now
        meta.source_url     = PEP_URL
    else:
        db.add(PEPListMeta(
            id             = uuid.uuid4(),
            list_name      = LIST_NAME,
            version        = ver,
            total_entries  = total,
            last_updated_at = now,
            source_url     = PEP_URL,
            bfiu_ref       = BFIU_REF,
        ))


def fetch_and_load(db: Session, limit: int = 0, dry_run: bool = False) -> dict:
    """Main entry point -- fetch from OpenSanctions and load into DB."""
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    # 1. BD PEPs from OpenSanctions
    try:
        bd_peps = _fetch_bd_peps(limit=limit)
        for rec in bd_peps:
            try:
                data = _map_to_pep(rec, "OPENSANCTIONS_PEP")
                if not data["full_name_en"]:
                    stats["errors"] += 1
                    continue
                _, action = _upsert(db, data, dry_run)
                stats[action] = stats.get(action, 0) + 1
            except Exception as e:
                log.warning("PEP entry error: %s", e)
                stats["errors"] += 1
    except Exception as e:
        log.error("Failed to fetch BD PEPs: %s", e)
        stats["errors"] += 1

    # 2. UN SC Sanctions (all -- small file)
    try:
        un_entries = _fetch_un_sanctions()
        for rec in un_entries:
            try:
                data = _map_to_pep(rec, "UN_SC_SANCTIONS")
                data["category"]   = "PEP"
                data["risk_level"] = "HIGH"
                data["notes"]      = f"UN SC Sanctions | {data.get('notes','')}"
                if not data["full_name_en"]:
                    continue
                _, action = _upsert(db, data, dry_run)
                stats[action] = stats.get(action, 0) + 1
            except Exception as e:
                log.warning("UN entry error: %s", e)
                stats["errors"] += 1
    except Exception as e:
        log.error("Failed to fetch UN sanctions: %s", e)
        stats["errors"] += 1

    # 3. OFAC SDN List
    for rec in _fetch_sanctions_list(OFAC_URL, "OFAC SDN"):
        try:
            data = _map_to_pep(rec, "US_OFAC_SDN")
            data["risk_level"] = "HIGH"
            data["notes"] = f"OFAC SDN | {data.get('notes','')}"
            if not data["full_name_en"]: continue
            _, action = _upsert(db, data, dry_run)
            stats[action] = stats.get(action, 0) + 1
        except Exception as e:
            stats["errors"] += 1

    # 4. EU Financial Sanctions
    for rec in _fetch_sanctions_list(EU_URL, "EU FSF"):
        try:
            data = _map_to_pep(rec, "EU_FSF")
            data["risk_level"] = "HIGH"
            data["notes"] = f"EU Sanctions | {data.get('notes','')}"
            if not data["full_name_en"]: continue
            _, action = _upsert(db, data, dry_run)
            stats[action] = stats.get(action, 0) + 1
        except Exception as e:
            stats["errors"] += 1

    # 5. UK HMT Sanctions
    for rec in _fetch_sanctions_list(UK_URL, "UK HMT"):
        try:
            data = _map_to_pep(rec, "UK_HMT")
            data["risk_level"] = "HIGH"
            data["notes"] = f"UK Sanctions | {data.get('notes','')}"
            if not data["full_name_en"]: continue
            _, action = _upsert(db, data, dry_run)
            stats[action] = stats.get(action, 0) + 1
        except Exception as e:
            stats["errors"] += 1

    if not dry_run:
        total = db.query(PEPEntry).count()
        _update_meta(db, total)
        db.commit()

    log.info("Fetch complete: %s", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Fetch PEP data from OpenSanctions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--limit",   type=int, default=0, help="Max BD PEP entries (0=all)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = fetch_and_load(db, limit=args.limit, dry_run=args.dry_run)
        print("Done:", stats)
    finally:
        db.close()


if __name__ == "__main__":
    main()
