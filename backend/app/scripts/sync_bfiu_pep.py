"""
BFIU Official PEP List Auto-Sync — BFIU Circular No. 29 §4.2
Probes known BFIU URLs daily. Auto-loads when published.
"""
import sys, csv, io, logging, urllib.request, hashlib, uuid
from datetime import datetime, timezone, timedelta
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bfiu_pep_sync")
BST = timezone(timedelta(hours=6))
HASH_FILE = "/opt/ekyc/.bfiu_pep_hash"

BFIU_PROBE_URLS = [
    "https://bfiu.org.bd/pep-list.csv",
    "https://bfiu.org.bd/downloads/pep-list.csv",
    "https://bfiu.org.bd/downloads/pep_list.csv",
    "https://bfiu.org.bd/wp-content/uploads/pep-list.csv",
    "https://bfiu.org.bd/wp-content/uploads/pep_list.csv",
    "https://www.bb.org.bd/fnansys/paymentsys/bfiu/pep-list.csv",
    "https://bfiu.org.bd/pep_list.xlsx",
    "https://bfiu.org.bd/downloads/pep.csv",
]

def probe_url(url):
    try:
        req = urllib.request.Request(url,
            headers={"User-Agent":"XpertFintech-eKYC/1.0 (BFIU Circular 29)"})
        r = urllib.request.urlopen(req, timeout=15)
        if r.status == 200:
            data = r.read()
            log.info("HIT: %s (%d bytes)", url, len(data))
            return data
    except Exception as e:
        log.debug("MISS %s: %s", url, e)
    return None

def content_changed(data):
    new_hash = hashlib.sha256(data).hexdigest()
    try:
        if open(HASH_FILE).read().strip() == new_hash:
            return False
    except FileNotFoundError:
        pass
    open(HASH_FILE,"w").write(new_hash)
    return True

def parse_csv(data):
    text = data.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))

def map_row(row):
    name = (row.get("Name") or row.get("name") or row.get("Full Name") or
            row.get("full_name") or row.get("NAME") or "").strip()
    if not name: return None
    return {
        "full_name_en":    name,
        "position":        (row.get("Position") or row.get("Designation") or "")[:255],
        "ministry_or_org": (row.get("Ministry") or row.get("Organization") or "")[:255],
        "notes":           f"BFIU Official PEP List | {str(row)[:400]}",
    }

def load_db(rows, pg_ip, db_pw):
    conn = psycopg2.connect(host=pg_ip,port=5432,user='ekyc_user',
                            password=db_pw,dbname='ekyc_db',connect_timeout=10)
    cur = conn.cursor()
    stats = {"created":0,"updated":0,"skipped":0}
    for row in rows:
        d = map_row(row)
        if not d:
            stats["skipped"] += 1
            continue
        try:
            cur.execute("SELECT id FROM pep_entries WHERE full_name_en=%s AND source='BFIU_OFFICIAL' LIMIT 1",
                       (d["full_name_en"],))
            ex = cur.fetchone()
            if ex:
                cur.execute("UPDATE pep_entries SET position=%s,ministry_or_org=%s,notes=%s,updated_at=NOW() WHERE id=%s",
                            (d["position"],d["ministry_or_org"],d["notes"],ex[0]))
                stats["updated"] += 1
            else:
                cur.execute("""INSERT INTO pep_entries
                    (id,full_name_en,nationality,category,risk_level,position,
                     ministry_or_org,source,notes,status,aliases,created_at,updated_at)
                    VALUES (%s,%s,'BD','PEP','HIGH',%s,%s,'BFIU_OFFICIAL',%s,'ACTIVE','{}',NOW(),NOW())""",
                    (str(uuid.uuid4()),d["full_name_en"],d["position"],d["ministry_or_org"],d["notes"]))
                stats["created"] += 1
        except Exception as e:
            conn.rollback()
            log.warning("Row error: %s", e)
    conn.commit()
    cur.close(); conn.close()
    return stats

def main(pg_ip, db_pw):
    log.info("=== BFIU PEP Auto-Sync ===")
    for url in BFIU_PROBE_URLS:
        data = probe_url(url)
        if data is None: continue
        if not content_changed(data):
            log.info("No change — skipping")
            return {"status":"no_change","url":url}
        rows = parse_csv(data)
        log.info("Parsed %d rows from %s", len(rows), url)
        stats = load_db(rows, pg_ip, db_pw)
        log.info("Done: %s", stats)
        return {"status":"loaded","url":url,"stats":stats}
    log.info("BFIU PEP list not yet published — retry tomorrow")
    return {"status":"not_published"}

if __name__ == "__main__":
    pg_ip = sys.argv[1] if len(sys.argv)>1 else "172.18.0.2"
    db_pw = sys.argv[2] if len(sys.argv)>2 else ""
    print("Result:", main(pg_ip, db_pw))
