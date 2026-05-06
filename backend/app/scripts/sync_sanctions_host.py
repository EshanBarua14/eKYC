"""
Standalone sanctions + PEP sync — runs on host Python 3.9
Fetches from internet, writes directly to Docker postgres via internal IP.
"""
import csv, uuid, logging, urllib.request, sys
from datetime import datetime, timezone, timedelta
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sync")

BST = timezone(timedelta(hours=6))
def now_bst(): return datetime.now(BST).isoformat()

# ── Config ────────────────────────────────────────────────────────────────
DB_HOST = sys.argv[1] if len(sys.argv) > 1 else "172.18.0.2"
DB_PW   = sys.argv[2] if len(sys.argv) > 2 else ""
DB_NAME = "ekyc_db"
DB_USER = "ekyc_user"

SOURCES = {
    "UN_SC": "https://data.opensanctions.org/datasets/latest/un_sc_sanctions/targets.simple.csv",
    "OFAC":  "https://data.opensanctions.org/datasets/latest/us_ofac_sdn/targets.simple.csv",
    "EU_FSF":"https://data.opensanctions.org/datasets/latest/eu_fsf/targets.simple.csv",
    "UK_HMT":"https://data.opensanctions.org/datasets/latest/gb_hmt_sanctions/targets.simple.csv",
    "BD_PEP":"https://data.opensanctions.org/datasets/latest/peps/targets.simple.csv",
}

def fetch_csv(url, label, bd_only=False):
    log.info("Fetching %s ...", label)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "XpertFintech-eKYC/1.0"})
        r = urllib.request.urlopen(req, timeout=60)
        lines = r.read().decode("utf-8").strip().split("\n")
        header = next(csv.reader([lines[0]]))
        rows = []
        for line in lines[1:]:
            if not line.strip(): continue
            row = next(csv.reader([line]))
            if len(row) < len(header): continue
            rec = dict(zip(header, row))
            if bd_only and rec.get("countries","").strip().lower() != "bd":
                continue
            rows.append(rec)
        log.info("%s: %d entries", label, len(rows))
        return rows
    except Exception as e:
        log.error("FAILED %s: %s", label, e)
        return []

def sync():
    conn = psycopg2.connect(host=DB_HOST,port=5432,user=DB_USER,
                            password=DB_PW,dbname=DB_NAME,connect_timeout=10)
    cur = conn.cursor()
    stats = {"created":0,"updated":0,"skipped":0,"errors":0}

    for source, url in SOURCES.items():
        bd_only = (source == "BD_PEP")
        rows = fetch_csv(url, source, bd_only=bd_only)
        for rec in rows:
            name = rec.get("name","").strip()
            if not name: continue
            try:
                cur.execute("SELECT id FROM pep_entries WHERE full_name_en=%s LIMIT 1", (name,))
                existing = cur.fetchone()
                risk = "HIGH" if "sanction" in source.lower() or source != "BD_PEP" else "MEDIUM"
                notes = f"{source} | ID:{rec.get('id','')} | aliases:{rec.get('aliases','')[:80]}"
                if existing:
                    cur.execute("""UPDATE pep_entries SET risk_level=%s,notes=%s,
                                   source=%s WHERE id=%s""",
                                (risk, notes[:500], source, existing[0]))
                    stats["updated"] += 1
                else:
                    cur.execute("""INSERT INTO pep_entries
                        (id,full_name_en,nationality,category,risk_level,
                         source,notes,status,aliases,created_at,updated_at)
                        VALUES (%s,%s,'BD','PEP',%s,%s,%s,'ACTIVE','{}',NOW(),NOW())
                        ON CONFLICT DO NOTHING""",
                        (str(uuid.uuid4()),name,risk,source,notes[:500]))
                    stats["created"] += 1
            except Exception as e:
                conn.rollback()
                stats["errors"] += 1
                log.warning("Row error: %s", e)
                continue
        conn.commit()
        log.info("%s done. Stats so far: %s", source, stats)

    # Update pep_list_meta
    total = cur.execute("SELECT COUNT(*) FROM pep_entries") or cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pep_entries")
    total = cur.fetchone()[0]
    log.info("Total PEP entries: %d", total)
    conn.commit()
    cur.close()
    conn.close()
    return stats

if __name__ == "__main__":
    DB_PW = sys.argv[2] if len(sys.argv) > 2 else ""
    result = sync()
    print("DONE:", result)
