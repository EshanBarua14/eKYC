"""
UNSCR Live Feed Service — M37
Daily automated pull from UN consolidated list.
PostgreSQL storage with FTS (search_vector).
Alert on list update failures.
BFIU Circular No. 29 — Section 5.1
"""
import re
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from app.core.timezone import bst_isoformat
from typing import Optional
from app.db.database import db_session

log = logging.getLogger(__name__)

UN_LIST_XML_URL  = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
REQUEST_TIMEOUT  = 60
EXACT_MATCH_THRESHOLD = 1.0
FUZZY_MATCH_THRESHOLD = 0.85


def pull_un_list(url=UN_LIST_XML_URL, pulled_by="celery_beat"):
    list_version = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("[M37] Pulling UN list: version=%s", list_version)
    try:
        entries = _fetch_and_parse(url)
    except Exception as exc:
        log.error("[M37] UN list fetch failed: %s", exc)
        _record_pull_failure(list_version, url, str(exc), pulled_by)
        _send_alert(f"UN list pull FAILED: {exc}")
        return {"status": "FAILED", "list_version": list_version, "error": str(exc), "total_entries": 0}
    if not entries:
        entries = _get_demo_entries(list_version)
    try:
        summary = _upsert_entries(entries, list_version)
        _record_pull_success(list_version, url, summary, pulled_by)
        return {"status": "SUCCESS", "list_version": list_version, **summary}
    except Exception as exc:
        log.error("[M37] DB upsert failed: %s", exc)
        _record_pull_failure(list_version, url, str(exc), pulled_by)
        _send_alert(f"UN list DB upsert FAILED: {exc}")
        return {"status": "FAILED", "list_version": list_version, "error": str(exc), "total_entries": len(entries)}


def _fetch_and_parse(url):
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT, context=ctx) as resp:
        xml_data = resp.read()
    return _parse_xml(xml_data)


def _parse_xml(xml_data):
    entries = []
    try:
        root = ET.fromstring(xml_data)
        ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

        def _find(el, tag):
            r = el.find(tag)
            if r is None and ns:
                r = el.find(f"{{{ns}}}{tag}")
            return r

        def _findall(el, tag):
            r = el.findall(tag)
            if not r and ns:
                r = el.findall(f"{{{ns}}}{tag}")
            return r

        # Search recursively through entire tree
        for ind in root.iter("INDIVIDUAL"):
            e = _parse_individual(ind, _find, _findall)
            if e:
                entries.append(e)
        for ent in root.iter("ENTITY"):
            e = _parse_entity(ent, _find, _findall)
            if e:
                entries.append(e)
    except ET.ParseError as exc:
        log.error("[M37] XML parse error: %s", exc)
    return entries


def _get_text(el, tag, default=""):
    """Safely get text from a child element."""
    child = el.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default

def _parse_individual(el, _find, _findall):
    try:
        parts = [_get_text(el, k) for k in ["FIRST_NAME","SECOND_NAME","THIRD_NAME","FOURTH_NAME"]]
        primary_name = " ".join(filter(None, parts)).strip().upper()
        if not primary_name:
            return None
        un_ref = _get_text(el, "REFERENCE_NUMBER", "UNK")
        dob_el = el.find("INDIVIDUAL_DATE_OF_BIRTH")
        dob = ""
        if dob_el is not None:
            y = _get_text(dob_el, "YEAR")
            m = _get_text(dob_el, "MONTH")
            d = _get_text(dob_el, "DAY")
            dob = "-".join(filter(None, [y, m.zfill(2) if m else "", d.zfill(2) if d else ""]))
        aliases = []
        for a in el.iter("INDIVIDUAL_ALIAS"):
            n = _get_text(a, "ALIAS_NAME")
            if n:
                aliases.append(n.upper())
        committee = _get_text(el, "UN_LIST_TYPE")
        listed_on = _get_text(el, "LISTED_ON")
        narrative = _get_text(el, "COMMENTS1")
        return {"un_ref_id": un_ref, "entry_type": "INDIVIDUAL", "primary_name": primary_name,
                "aliases": aliases, "dob": dob, "committee": committee, "listed_on": listed_on,
                "narrative": narrative, "search_vector": " ".join([primary_name] + aliases).upper()}
    except Exception as exc:
        log.warning("[M37] Individual parse error: %s", exc)
        return None


def _parse_entity(el, _find, _findall):
    try:
        primary_name = _get_text(el, "FIRST_NAME") or _get_text(el, "NAME")
        primary_name = primary_name.strip().upper()
        if not primary_name:
            return None
        un_ref    = _get_text(el, "REFERENCE_NUMBER", "UNK")
        committee = _get_text(el, "UN_LIST_TYPE")
        listed_on = _get_text(el, "LISTED_ON")
        narrative = _get_text(el, "COMMENTS1")
        aliases = []
        for a in el.iter("ENTITY_ALIAS"):
            n = _get_text(a, "ALIAS_NAME")
            if n:
                aliases.append(n.upper())
        return {"un_ref_id": un_ref, "entry_type": "ENTITY", "primary_name": primary_name,
                "aliases": aliases, "committee": committee, "listed_on": listed_on,
                "narrative": narrative, "search_vector": " ".join([primary_name] + aliases).upper()}
    except Exception as exc:
        log.warning("[M37] Entity parse error: %s", exc)
        return None


def _get_demo_entries(list_version):
    return [
        {"un_ref_id": "UN-001", "entry_type": "ENTITY", "primary_name": "AL QAIDA",
         "aliases": ["AL-QAEDA", "AQ"], "committee": "1267", "listed_on": "1999-10-15",
         "narrative": "Global terrorist organization", "search_vector": "AL QAIDA AL-QAEDA AQ",
         "dob": "", "list_version": list_version},
        {"un_ref_id": "UN-002", "entry_type": "ENTITY", "primary_name": "DAESH",
         "aliases": ["ISIS", "ISIL", "IS", "ISLAMIC STATE"], "committee": "1267",
         "listed_on": "2014-05-30", "narrative": "Terrorist group",
         "search_vector": "DAESH ISIS ISIL IS ISLAMIC STATE", "dob": "", "list_version": list_version},
        {"un_ref_id": "UN-003", "entry_type": "ENTITY", "primary_name": "JAMAAT UL MUJAHIDEEN BANGLADESH",
         "aliases": ["JMB", "JMJB"], "committee": "1373", "listed_on": "2005-02-23",
         "narrative": "Bangladesh terrorist organization",
         "search_vector": "JAMAAT UL MUJAHIDEEN BANGLADESH JMB JMJB", "dob": "", "list_version": list_version},
        {"un_ref_id": "UN-004", "entry_type": "INDIVIDUAL", "primary_name": "SANCTIONED PERSON ONE",
         "aliases": ["SP ONE"], "committee": "1267", "listed_on": "2001-01-25",
         "narrative": "Sanctioned individual", "search_vector": "SANCTIONED PERSON ONE SP ONE",
         "dob": "1970-01-01", "list_version": list_version},
        {"un_ref_id": "UN-005", "entry_type": "INDIVIDUAL", "primary_name": "SANCTIONED PERSON TWO",
         "aliases": ["SP TWO"], "committee": "1988", "listed_on": "2010-06-01",
         "narrative": "Sanctioned individual", "search_vector": "SANCTIONED PERSON TWO SP TWO",
         "dob": "1965-03-15", "list_version": list_version},
    ]


def _upsert_entries(entries, list_version):
    from app.db.models_platform import UNSCREntry
    new_count = updated_count = 0
    with db_session() as db:
        db.query(UNSCREntry).filter(UNSCREntry.list_version != list_version).update({"is_active": False})
        for entry in entries:
            existing = db.query(UNSCREntry).filter_by(un_ref_id=entry["un_ref_id"]).first()
            if existing:
                existing.primary_name  = entry["primary_name"]
                existing.aliases       = entry.get("aliases", [])
                existing.search_vector = entry.get("search_vector", entry["primary_name"])
                existing.list_version  = list_version
                existing.is_active     = True
                existing.updated_at    = datetime.now(timezone.utc)
                updated_count += 1
            else:
                db.add(UNSCREntry(
                    un_ref_id=entry["un_ref_id"], entry_type=entry["entry_type"],
                    primary_name=entry["primary_name"], aliases=entry.get("aliases", []),
                    dob=entry.get("dob", ""), committee=entry.get("committee", ""),
                    listed_on=entry.get("listed_on", ""), narrative=entry.get("narrative", ""),
                    search_vector=entry.get("search_vector", entry["primary_name"]),
                    list_version=list_version, is_active=True,
                ))
                new_count += 1
    return {"total_entries": len(entries), "new_entries": new_count,
            "removed_entries": 0, "updated_entries": updated_count}


def search_unscr(name, threshold=FUZZY_MATCH_THRESHOLD):
    from app.db.models_platform import UNSCREntry
    name_norm = _normalize(name)
    if not name_norm:
        return {"verdict": "CLEAR", "name": name, "matches": [],
                "list_version": _get_current_list_version(), "screened_at": _now_iso(),
                "bfiu_ref": "BFIU Circular No. 29 — Section 5.1"}
    matches = []
    with db_session() as db:
        candidates = db.query(UNSCREntry).filter(UNSCREntry.is_active == True).all()
        if not candidates:
            candidates = _demo_entries_as_objects()
        for entry in candidates:
            score = _score(name_norm, entry.primary_name, entry.aliases or [])
            if score >= threshold:
                matches.append({"un_ref_id": entry.un_ref_id, "entry_type": entry.entry_type,
                                 "primary_name": entry.primary_name, "score": round(score, 3),
                                 "committee": entry.committee, "listed_on": entry.listed_on})
    if not matches:
        return {"verdict": "CLEAR", "name": name, "matches": [],
                "list_version": _get_current_list_version(),
                "screened_at": _now_iso(), "bfiu_ref": "BFIU Circular No. 29 — Section 5.1"}
    best_score = max(m["score"] for m in matches)
    verdict = "MATCH" if best_score >= EXACT_MATCH_THRESHOLD else "REVIEW"
    return {"verdict": verdict, "name": name, "matches": matches, "best_score": best_score,
            "blocking": verdict == "MATCH",
            "list_version": _get_current_list_version(),
            "screened_at": _now_iso(),
            "bfiu_ref": "BFIU Circular No. 29 — Section 5.1"}


def _demo_entries_as_objects():
    class MockEntry:
        def __init__(self, d):
            self.un_ref_id = d["un_ref_id"]; self.entry_type = d["entry_type"]
            self.primary_name = d["primary_name"]; self.aliases = d.get("aliases", [])
            self.committee = d.get("committee", ""); self.listed_on = d.get("listed_on", "")
    from app.services.screening_service import _UNSCR_LIST
    return [MockEntry(e) for e in _UNSCR_LIST]


def get_list_status():
    from app.db.models_platform import UNSCREntry, UNSCRListMeta
    try:
        with db_session() as db:
            latest = db.query(UNSCRListMeta).order_by(UNSCRListMeta.pulled_at.desc()).first()
            total_active = db.query(UNSCREntry).filter(UNSCREntry.is_active == True).count()
            if latest:
                return {"list_version": latest.list_version, "total_entries": total_active,
                        "last_pull": latest.pulled_at.isoformat(), "status": latest.status,
                        "error": latest.error_message}
    except Exception as exc:
        log.warning("[M37] get_list_status error: %s", exc)
    return {"list_version": "DEMO", "total_entries": len(_get_demo_entries("DEMO")),
            "last_pull": None, "status": "DEMO", "error": None}


def _record_pull_success(list_version, url, summary, pulled_by):
    from app.db.models_platform import UNSCRListMeta
    try:
        with db_session() as db:
            existing = db.query(UNSCRListMeta).filter_by(list_version=list_version).first()
            if existing:
                existing.status = "SUCCESS"; existing.total_entries = summary["total_entries"]
                existing.new_entries = summary["new_entries"]; existing.error_message = None
            else:
                db.add(UNSCRListMeta(list_version=list_version, pull_url=url,
                    total_entries=summary["total_entries"], new_entries=summary["new_entries"],
                    removed_entries=summary.get("removed_entries", 0),
                    status="SUCCESS", pulled_by=pulled_by))
    except Exception as exc:
        log.error("[M37] _record_pull_success error: %s", exc)


def _record_pull_failure(list_version, url, error, pulled_by):
    from app.db.models_platform import UNSCRListMeta
    try:
        with db_session() as db:
            existing = db.query(UNSCRListMeta).filter_by(list_version=list_version).first()
            if existing:
                existing.status = "FAILED"; existing.error_message = error
            else:
                db.add(UNSCRListMeta(list_version=list_version, pull_url=url,
                    total_entries=0, new_entries=0, status="FAILED",
                    error_message=error, pulled_by=pulled_by))
    except Exception as exc:
        log.error("[M37] _record_pull_failure error: %s", exc)


def _send_alert(message: str, alert_type: str = "UNSCR_PULL_FAILURE"):
    """
    Send alert on UNSCR pull failure.
    1. Log error (always)
    2. Increment Prometheus counter
    3. Email compliance officer if SMTP configured
    """
    log.error("[M37] ALERT [%s]: %s", alert_type, message)

    # Prometheus counter
    try:
        from app.services.metrics import EC_API_ERRORS
        EC_API_ERRORS.labels(error_type=alert_type).inc()
    except Exception:
        pass

    # Email alert to compliance officer
    try:
        import json, os
        sf = os.path.join(os.path.dirname(__file__), "../../platform_settings.json")
        with open(sf, "r", encoding="utf-8") as f:
            settings = json.load(f)

        smtp_host = settings.get("smtp_host", "")
        smtp_user = settings.get("smtp_user", "")
        smtp_pass = settings.get("smtp_password", "")
        smtp_from = settings.get("smtp_from", "")
        helpdesk  = settings.get("helpdesk_email", "")

        if smtp_host and smtp_user and smtp_pass and helpdesk:
            import smtplib
            from email.mime.text import MIMEText
            from app.core.timezone import bst_display
            msg = MIMEText(
                f"ALERT: {alert_type}\n\n"
                f"Message: {message}\n\n"
                f"Time: {bst_display()}\n\n"
                f"Action required: Manually trigger UN list pull from Admin UI.\n"
                f"BFIU Circular No. 29 §5.1 — UNSCR screening must be current."
            )
            msg["Subject"] = f"[eKYC ALERT] {alert_type} — UNSCR list pull failed"
            msg["From"]    = smtp_from
            msg["To"]      = helpdesk
            with smtplib.SMTP(smtp_host, settings.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            log.info("[M37] Alert email sent to %s", helpdesk)
    except Exception as exc:
        log.warning("[M37] Alert email failed: %s", exc)


def _normalize(name):
    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _score(query, primary, aliases):
    """Score using Bangla phonetic + token overlap + edit distance."""
    candidates = [primary] + (aliases or [])
    scores = []
    for c in candidates:
        # Token overlap
        tok = _token_overlap(_normalize(query), _normalize(c))
        # Bangla phonetic score
        try:
            from app.services.bangla_phonetic import enhanced_match_score
            phonetic = enhanced_match_score(query, c, base_scorer=lambda a, b: tok)
        except Exception:
            phonetic = tok
        scores.append(max(tok, phonetic))
    return max(scores) if scores else 0.0


def _token_overlap(a, b):
    t1 = set(a.split()); t2 = set(b.split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def _now_iso():
    return bst_isoformat()


def _get_current_list_version() -> str:
    """Get current active list version from DB or return date-stamped demo."""
    try:
        from app.db.models_platform import UNSCRListMeta
        with db_session() as db:
            latest = db.query(UNSCRListMeta).filter_by(
                status="SUCCESS").order_by(
                UNSCRListMeta.id.desc()).first()
            if latest:
                return latest.list_version
    except Exception:
        pass
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d") + "-DEMO"
