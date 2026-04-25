"""
M76: PEP data loading script — BFIU Circular No. 29 §4.2
Usage:
  python -m app.scripts.load_pep_data --source seed
  python -m app.scripts.load_pep_data --source csv --file /path/to/pep_list.csv
  python -m app.scripts.load_pep_data --source un_xml --file /path/to/consolidated.xml

CSV columns (header required, required: full_name_en, category):
  full_name_en,full_name_bn,date_of_birth,national_id,passport_number,
  nationality,category,position,ministry_or_org,country,risk_level,notes

Valid category values : PEP | IP | PEP_FAMILY | PEP_ASSOCIATE
Valid risk_level      : HIGH | MEDIUM | LOW
Valid status          : ACTIVE | INACTIVE | DECEASED
"""
import argparse
import csv
import sys
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models_pep import PEPEntry, PEPListMeta, PEPAuditLog

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("m76_pep_loader")

BST = timezone(timedelta(hours=6))
VALID_CATEGORIES = {"PEP", "IP", "PEP_FAMILY", "PEP_ASSOCIATE"}
VALID_RISK       = {"HIGH", "MEDIUM", "LOW"}
VALID_STATUS     = {"ACTIVE", "INACTIVE", "DECEASED"}

# ── Bangladesh seed data — BFIU §4.2 ────────────────────────────────────────
# category: PEP = Politically Exposed Person, IP = Influential Person (BFIU local)
BANGLADESH_SEED_PEPS = [
    # Head of State / Government
    dict(full_name_en="Sheikh Hasina", full_name_bn="শেখ হাসিনা",
         category="PEP", position="Prime Minister",
         ministry_or_org="Prime Minister's Office", risk_level="HIGH"),
    dict(full_name_en="Abdul Hamid", full_name_bn="মোঃ আবদুল হামিদ",
         category="PEP", position="President",
         ministry_or_org="Bangabhaban", risk_level="HIGH"),
    dict(full_name_en="Shirin Sharmin Chaudhury",
         full_name_bn="শিরীন শারমিন চৌধুরী",
         category="PEP", position="Speaker, Jatiya Sangsad",
         ministry_or_org="Jatiya Sangsad Bhaban", risk_level="HIGH"),
    # Finance & Central Bank
    dict(full_name_en="AHM Mustafa Kamal", full_name_bn="আ হ ম মুস্তফা কামাল",
         category="PEP", position="Finance Minister",
         ministry_or_org="Ministry of Finance", risk_level="HIGH"),
    dict(full_name_en="Abdur Rouf Talukder", full_name_bn="আব্দুর রউফ তালুকদার",
         category="PEP", position="Governor, Bangladesh Bank",
         ministry_or_org="Bangladesh Bank", risk_level="HIGH"),
    dict(full_name_en="Fazle Kabir", full_name_bn="ফজলে কবির",
         category="PEP", position="Former Governor, Bangladesh Bank",
         ministry_or_org="Bangladesh Bank", risk_level="HIGH"),
    # Cabinet
    dict(full_name_en="Obaidul Quader", full_name_bn="ওবায়দুল কাদের",
         category="PEP", position="Minister, Road Transport and Bridges",
         ministry_or_org="Ministry of Road Transport", risk_level="HIGH"),
    dict(full_name_en="Asaduzzaman Khan Kamal",
         full_name_bn="আসাদুজ্জামান খান কামাল",
         category="PEP", position="Minister, Home Affairs",
         ministry_or_org="Ministry of Home Affairs", risk_level="HIGH"),
    dict(full_name_en="Dipu Moni", full_name_bn="দীপু মনি",
         category="PEP", position="Minister, Education",
         ministry_or_org="Ministry of Education", risk_level="HIGH"),
    # Military Chiefs
    dict(full_name_en="SM Shafiuddin Ahmed",
         full_name_bn="এস এম শফিউদ্দিন আহমেদ",
         category="PEP", position="Chief of Army Staff",
         ministry_or_org="Bangladesh Army", risk_level="HIGH"),
    dict(full_name_en="M Nazmul Hassan", full_name_bn="এম নাজমুল হাসান",
         category="PEP", position="Chief of Naval Staff",
         ministry_or_org="Bangladesh Navy", risk_level="HIGH"),
    dict(full_name_en="Shaikh Abdul Hannan",
         full_name_bn="শেখ আব্দুল হান্নান",
         category="PEP", position="Chief of Air Staff",
         ministry_or_org="Bangladesh Air Force", risk_level="HIGH"),
    # Judiciary
    dict(full_name_en="Hasan Foez Siddique",
         full_name_bn="হাসান ফয়েজ সিদ্দিকী",
         category="PEP", position="Chief Justice",
         ministry_or_org="Supreme Court of Bangladesh", risk_level="HIGH"),
    # NRB Commission / ACC
    dict(full_name_en="Mohammad Moinuddin Abdullah",
         category="PEP", position="Chairman, Anti-Corruption Commission",
         ministry_or_org="ACC Bangladesh", risk_level="HIGH"),
    # SOE Heads — IP category (BFIU local influential persons)
    dict(full_name_en="Sonali Bank Managing Director",
         category="IP", position="Managing Director",
         ministry_or_org="Sonali Bank Limited", risk_level="HIGH"),
    dict(full_name_en="Janata Bank Managing Director",
         category="IP", position="Managing Director",
         ministry_or_org="Janata Bank Limited", risk_level="HIGH"),
    dict(full_name_en="Agrani Bank Managing Director",
         category="IP", position="Managing Director",
         ministry_or_org="Agrani Bank Limited", risk_level="HIGH"),
    dict(full_name_en="Rupali Bank Managing Director",
         category="IP", position="Managing Director",
         ministry_or_org="Rupali Bank Limited", risk_level="HIGH"),
    dict(full_name_en="Bangladesh Petroleum Corporation Chairman",
         category="IP", position="Chairman",
         ministry_or_org="Bangladesh Petroleum Corporation", risk_level="HIGH"),
    dict(full_name_en="Petrobangla Chairman",
         category="IP", position="Chairman",
         ministry_or_org="Petrobangla", risk_level="HIGH"),
    # BSEC / IDRA / RJSC regulators
    dict(full_name_en="Shibli Rubayat-Ul-Islam",
         full_name_bn="শিবলী রুবাইয়াত-উল-ইসলাম",
         category="IP", position="Chairman, Bangladesh Securities and Exchange Commission",
         ministry_or_org="BSEC", risk_level="HIGH"),
    dict(full_name_en="Mohammad Jainul Bari",
         category="IP", position="Chairman, Insurance Development and Regulatory Authority",
         ministry_or_org="IDRA", risk_level="HIGH"),
]


def _bst_now() -> datetime:
    return datetime.now(BST).replace(tzinfo=None)


def _upsert(db: Session, data: dict, source: str, source_ref: str) -> tuple[bool, str]:
    """Upsert on (full_name_en, category). Returns (created, action)."""
    existing = db.query(PEPEntry).filter(
        PEPEntry.full_name_en == data["full_name_en"],
        PEPEntry.category == data["category"],
    ).first()

    if existing:
        changed = False
        for f in ("full_name_bn", "position", "ministry_or_org", "nationality",
                  "country", "risk_level", "notes", "national_id",
                  "passport_number", "date_of_birth"):
            v = data.get(f)
            if v and getattr(existing, f) != v:
                setattr(existing, f, v)
                changed = True
        if existing.status == "INACTIVE":
            existing.status = "ACTIVE"
            changed = True
        if changed:
            existing.updated_at = _bst_now()
            return False, "updated"
        return False, "skipped"

    entry = PEPEntry(
        id=uuid.uuid4(),
        full_name_en=data["full_name_en"],
        full_name_bn=data.get("full_name_bn"),
        aliases=data.get("aliases", []),
        date_of_birth=data.get("date_of_birth"),
        national_id=data.get("national_id"),
        passport_number=data.get("passport_number"),
        nationality=data.get("nationality", "BD"),
        category=data["category"],
        position=data.get("position"),
        ministry_or_org=data.get("ministry_or_org"),
        country=data.get("country", "BD"),
        risk_level=data.get("risk_level", "HIGH"),
        edd_required=True,
        status="ACTIVE",
        source=source,
        source_reference=source_ref,
        notes=data.get("notes"),
    )
    db.add(entry)
    return True, "created"


def _update_meta(db: Session, source: str, count: int) -> None:
    meta = db.query(PEPListMeta).filter(
        PEPListMeta.list_name == source
    ).first()
    if meta:
        meta.version = _bst_now().strftime("%Y%m%d%H%M")
        meta.total_entries = db.query(PEPEntry).filter(
            PEPEntry.source == source,
            PEPEntry.status == "ACTIVE",
        ).count()
        meta.last_updated_at = _bst_now()
    else:
        db.add(PEPListMeta(
            id=uuid.uuid4(),
            list_name=source,
            version=_bst_now().strftime("%Y%m%d%H%M"),
            total_entries=count,
            bfiu_ref="BFIU Circular No. 29 §4.2",
        ))


def load_seed(db: Session) -> dict:
    stats: dict = {"created": 0, "updated": 0, "skipped": 0}
    for row in BANGLADESH_SEED_PEPS:
        _, action = _upsert(db, row, "SEED", "bangladesh_seed_v1")
        stats[action] = stats.get(action, 0) + 1
    _update_meta(db, "SEED", stats["created"])
    db.commit()
    log.info("Seed load complete: %s", stats)
    return stats


def load_csv(db: Session, filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        log.error("File not found: %s", filepath); sys.exit(1)

    stats: dict = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"full_name_en", "category"}
        if not required.issubset(set(reader.fieldnames or [])):
            log.error("CSV missing columns %s, got %s", required, reader.fieldnames)
            sys.exit(1)

        for i, row in enumerate(reader, 1):
            try:
                cat = row["category"].strip().upper()
                risk = row.get("risk_level", "HIGH").strip().upper()
                if cat not in VALID_CATEGORIES:
                    log.warning("Row %d: invalid category '%s' — skip", i, cat); stats["errors"] += 1; continue
                if risk not in VALID_RISK:
                    risk = "HIGH"
                data = {
                    "full_name_en": row["full_name_en"].strip(),
                    "full_name_bn": row.get("full_name_bn", "").strip() or None,
                    "date_of_birth": row.get("date_of_birth", "").strip() or None,
                    "national_id": row.get("national_id", "").strip() or None,
                    "passport_number": row.get("passport_number", "").strip() or None,
                    "nationality": row.get("nationality", "BD").strip()[:3],
                    "category": cat,
                    "position": row.get("position", "").strip() or None,
                    "ministry_or_org": row.get("ministry_or_org", "").strip() or None,
                    "country": row.get("country", "BD").strip()[:3],
                    "risk_level": risk,
                    "notes": row.get("notes", "").strip() or None,
                }
                if not data["full_name_en"]:
                    stats["errors"] += 1; continue
                _, action = _upsert(db, data, "BFIU_CSV", path.name)
                stats[action] = stats.get(action, 0) + 1
            except Exception as e:
                log.error("Row %d: %s", i, e); stats["errors"] += 1

    _update_meta(db, "BFIU_CSV", stats["created"])
    db.commit()
    log.info("CSV load complete: %s", stats)
    return stats


def load_un_xml(db: Session, filepath: str) -> dict:
    import xml.etree.ElementTree as ET
    from datetime import date

    path = Path(filepath)
    if not path.exists():
        log.error("File not found: %s", filepath); sys.exit(1)

    stats: dict = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
    root = ET.parse(path).getroot()
    ns = {"u": "https://scsanctions.un.org/resources/xml/en/consolidated.xsd"}

    individuals = root.findall(".//INDIVIDUAL") or root.findall(".//u:INDIVIDUAL", ns)
    log.info("UN XML: found %d individuals", len(individuals))

    for ind in individuals:
        try:
            def g(tag):
                el = ind.find(tag); el = el if el is not None else ind.find(f"u:{tag}", ns)
                return el.text.strip() if el is not None and el.text else None

            parts = [g(t) for t in ("FIRST_NAME","SECOND_NAME","THIRD_NAME","FOURTH_NAME")]
            full_name = " ".join(p for p in parts if p)
            if not full_name:
                continue

            nat_el = ind.find(".//NATIONALITY/VALUE") or ind.find(".//u:NATIONALITY/u:VALUE", ns)
            nat = nat_el.text.strip()[:3] if nat_el is not None and nat_el.text else "UNK"

            yr_el = ind.find(".//INDIVIDUAL_DATE_OF_BIRTH/YEAR") or \
                    ind.find(".//u:INDIVIDUAL_DATE_OF_BIRTH/u:YEAR", ns)
            dob = f"{yr_el.text.strip()}-01-01" if yr_el is not None and yr_el.text else None

            ref = g("REFERENCE_NUMBER") or g("DATAID") or "UN_UNKNOWN"
            data = {
                "full_name_en": full_name,
                "date_of_birth": dob,
                "nationality": nat,
                "country": nat,
                "category": "PEP",
                "position": g("DESIGNATION/VALUE"),
                "ministry_or_org": None,
                "risk_level": "HIGH",
                "notes": f"UN Consolidated List ref: {ref}",
                "source_reference": ref,
            }
            _, action = _upsert(db, data, "UN_XML", path.name)
            stats[action] = stats.get(action, 0) + 1
        except Exception as e:
            log.error("XML row error: %s", e); stats["errors"] += 1

    _update_meta(db, "UN_XML", stats["created"])
    db.commit()
    log.info("UN XML load complete: %s", stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description="M76: Load PEP data (BFIU §4.2)")
    parser.add_argument("--source", choices=["seed", "csv", "un_xml"], required=True)
    parser.add_argument("--file", help="CSV or XML path (required for csv/un_xml)")
    args = parser.parse_args()

    if args.source in ("csv", "un_xml") and not args.file:
        log.error("--file required for --source=%s", args.source); sys.exit(1)

    db: Session = SessionLocal()
    try:
        log.info("M76 start — source=%s BST=%s",
                 args.source, datetime.now(BST).strftime("%Y-%m-%d %H:%M:%S"))
        if args.source == "seed":
            stats = load_seed(db)
        elif args.source == "csv":
            stats = load_csv(db, args.file)
        else:
            stats = load_un_xml(db, args.file)
        print(f"\nM76 PEP load OK: {stats}")
    except Exception as e:
        db.rollback()
        log.error("M76 FAILED: %s", e); sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
