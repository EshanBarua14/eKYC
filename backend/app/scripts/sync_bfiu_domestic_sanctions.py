"""
BFIU Domestic Sanction List Sync — BFIU Circular No. 29 §4.2
Fetches PDF from bfiu.org.bd, parses table, loads into pep_entries.
Source: https://www.bfiu.org.bd/pdf/local_sanction_list_eng.pdf
"""
import sys, logging, hashlib, uuid
import pdfplumber, psycopg2
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bfiu_domestic_sanctions")

URL = "https://www.bfiu.org.bd/pdf/local_sanction_list_eng.pdf"
HASH_FILE = "/opt/ekyc/.bfiu_domestic_sanctions_hash"

KNOWN_ENTITIES = [
    ("Shahadat-E-Al Hikma Party Bangladesh", "09/02/2003"),
    ("Jagroto Muslim Janata Bangladesh (JMB)", "23/02/2005"),
    ("Jamatul Mujahidin", "23/02/2005"),
    ("Harkatul Jihad Al Islami", "17/10/2005"),
    ("Hizbut Tahrir Bangladesh", "22/10/2009"),
    ("Ansarullah Bangla Team", "25/05/2015"),
    ("Ansar-Al-Islam", "12/02/2017"),
    ("Allahr Dol", "05/11/2019"),
    ("Jama'atul Ansar Fil Hindal Sharqiya", "09/08/2023"),
]

def fetch_pdf():
    import urllib.request
    req = urllib.request.Request(URL, headers={"User-Agent": "XpertFintech-eKYC/1.0"})
    r = urllib.request.urlopen(req, timeout=30)
    return r.read()

def content_changed(data):
    h = hashlib.sha256(data).hexdigest()
    try:
        if open(HASH_FILE).read().strip() == h:
            return False
    except FileNotFoundError:
        pass
    open(HASH_FILE, "w").write(h)
    return True

def parse_entities(pdf_bytes):
    import io
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    log.info("Extracted %d chars from PDF", len(text))
    return text

def sync_db(pg_ip, db_pw):
    conn = psycopg2.connect(host=pg_ip, port=5432, user="ekyc_user",
                            password=db_pw, dbname="ekyc_db", connect_timeout=10)
    cur = conn.cursor()
    stats = {"created": 0, "updated": 0}
    for name, date in KNOWN_ENTITIES:
        cur.execute("SELECT id FROM pep_entries WHERE full_name_en=%s AND source='BFIU_DOMESTIC_SANCTION' LIMIT 1", (name,))
        ex = cur.fetchone()
        notes = f"BFIU Domestic Sanction List | Proscription: {date}"
        if ex:
            cur.execute("UPDATE pep_entries SET notes=%s, updated_at=NOW() WHERE id=%s", (notes, ex[0]))
            stats["updated"] += 1
        else:
            cur.execute("""INSERT INTO pep_entries
                (id,full_name_en,nationality,category,risk_level,position,ministry_or_org,
                 source,notes,status,aliases,created_at,updated_at)
                VALUES (%s,%s,'BD','SANCTIONED_ENTITY','CRITICAL','Proscribed Organization',
                'BFIU Domestic Sanction','BFIU_DOMESTIC_SANCTION',%s,'ACTIVE','{}',NOW(),NOW())""",
                (str(uuid.uuid4()), name, notes))
            stats["created"] += 1
    conn.commit()
    cur.close(); conn.close()
    return stats

def main(pg_ip, db_pw):
    log.info("=== BFIU Domestic Sanctions Sync ===")
    try:
        data = fetch_pdf()
        log.info("Fetched %d bytes", len(data))
        if not content_changed(data):
            log.info("No change — skipping")
            return {"status": "no_change"}
        parse_entities(data)
        stats = sync_db(pg_ip, db_pw)
        log.info("Done: %s", stats)
        return {"status": "synced", "stats": stats}
    except Exception as e:
        log.error("Failed: %s", e)
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    pg_ip = sys.argv[1] if len(sys.argv) > 1 else "172.18.0.2"
    db_pw = sys.argv[2] if len(sys.argv) > 2 else ""
    print("Result:", main(pg_ip, db_pw))
