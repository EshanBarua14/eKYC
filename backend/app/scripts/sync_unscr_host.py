"""
Direct UN SC XML sync — BFIU Circular No. 29 §3.2.2
Source: https://scsanctions.un.org/resources/xml/en/consolidated.xml
Runs on host, writes to Docker postgres via internal IP.
"""
import sys, uuid, logging, urllib.request, ssl
import xml.etree.ElementTree as ET
import psycopg2
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("unscr_sync")

UN_XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
BST = timezone(timedelta(hours=6))

def fetch_xml():
    log.info("Fetching UN XML from %s", UN_XML_URL)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(UN_XML_URL,
        headers={"User-Agent": "XpertFintech-eKYC/1.0 (BFIU Circular 29 Compliance)"})
    r = urllib.request.urlopen(req, context=ctx, timeout=60)
    data = r.read()
    log.info("Downloaded %d bytes", len(data))
    return data

def parse_xml(data):
    root = ET.fromstring(data)
    ns = {"": root.tag.split("}")[0].lstrip("{")} if "}" in root.tag else {}
    
    def find(el, tag):
        for child in el:
            if child.tag.split("}")[-1] == tag:
                return child
        return None
    
    def findall(el, tag):
        return [c for c in el if c.tag.split("}")[-1] == tag]
    
    def text(el, tag):
        c = find(el, tag)
        return c.text.strip() if c is not None and c.text else ""
    
    entries = []
    
    # Individuals
    for ind_list in root.iter():
        if ind_list.tag.split("}")[-1] == "INDIVIDUALS":
            for ind in ind_list:
                if ind.tag.split("}")[-1] != "INDIVIDUAL":
                    continue
                ref_id = text(ind, "DATAID") or text(ind, "REFERENCE_NUMBER")
                
                # Primary name
                first = text(ind, "FIRST_NAME")
                second = text(ind, "SECOND_NAME")
                third = text(ind, "THIRD_NAME")
                fourth = text(ind, "FOURTH_NAME")
                primary = " ".join(filter(None, [first, second, third, fourth])).strip()
                if not primary:
                    continue
                
                # Aliases
                aliases = []
                for alias in ind.iter():
                    if alias.tag.split("}")[-1] == "INDIVIDUAL_ALIAS":
                        an = text(alias, "ALIAS_NAME") or text(alias, "QUALITY")
                        if an and an != primary:
                            aliases.append(an)
                
                dob = ""
                for d in ind.iter():
                    if d.tag.split("}")[-1] == "INDIVIDUAL_DATE_OF_BIRTH":
                        dob = text(d, "DATE") or text(d, "YEAR") or ""
                        if dob: break
                
                nat = ""
                for n in ind.iter():
                    if n.tag.split("}")[-1] == "NATIONALITY":
                        nat = text(n, "VALUE") or ""
                        if nat: break
                
                entries.append({
                    "un_ref_id": ref_id,
                    "entry_type": "INDIVIDUAL",
                    "primary_name": primary,
                    "aliases": aliases[:10],
                    "nationality": nat[:100] if nat else "",
                    "dob": dob[:50] if dob else "",
                    "committee": text(ind, "UN_LIST_TYPE") or text(ind, "COMMENTS1") or "",
                    "listed_on": text(ind, "LISTED_ON") or "",
                    "narrative": text(ind, "COMMENTS1")[:500] if text(ind, "COMMENTS1") else "",
                })
    
    # Entities
    for ent_list in root.iter():
        if ent_list.tag.split("}")[-1] == "ENTITIES":
            for ent in ent_list:
                if ent.tag.split("}")[-1] != "ENTITY":
                    continue
                ref_id = text(ent, "DATAID") or text(ent, "REFERENCE_NUMBER")
                primary = text(ent, "FIRST_NAME") or text(ent, "SECOND_NAME")
                if not primary:
                    continue
                aliases = []
                for alias in ent.iter():
                    if alias.tag.split("}")[-1] == "ENTITY_ALIAS":
                        an = text(alias, "ALIAS_NAME")
                        if an and an != primary:
                            aliases.append(an)
                entries.append({
                    "un_ref_id": ref_id,
                    "entry_type": "ENTITY",
                    "primary_name": primary,
                    "aliases": aliases[:10],
                    "nationality": "",
                    "dob": "",
                    "committee": text(ent, "UN_LIST_TYPE") or "",
                    "listed_on": text(ent, "LISTED_ON") or "",
                    "narrative": text(ent, "COMMENTS1")[:500] if text(ent, "COMMENTS1") else "",
                })
    
    log.info("Parsed %d entries", len(entries))
    return entries

def sync(pg_ip, db_pw):
    import json
    conn = psycopg2.connect(host=pg_ip,port=5432,user='ekyc_user',
                            password=db_pw,dbname='ekyc_db',connect_timeout=10)
    cur = conn.cursor()
    list_version = datetime.now(BST).strftime("%Y-%m-%d")
    
    data = fetch_xml()
    entries = parse_xml(data)
    
    stats = {"created":0,"updated":0,"errors":0}
    for e in entries:
        try:
            search_vec = f"{e['primary_name']} {' '.join(e['aliases'])}".lower()
            cur.execute("SELECT id FROM unscr_entries WHERE un_ref_id=%s LIMIT 1",
                       (e["un_ref_id"],))
            existing = cur.fetchone()
            if existing:
                cur.execute("""UPDATE unscr_entries SET
                    primary_name=%s,aliases=%s,nationality=%s,dob=%s,
                    committee=%s,listed_on=%s,narrative=%s,
                    search_vector=%s,list_version=%s,is_active=true,updated_at=NOW()
                    WHERE id=%s""",
                    (e["primary_name"],json.dumps(e["aliases"]),e["nationality"],
                     e["dob"],e["committee"][:100],e["listed_on"],e["narrative"],
                     search_vec,list_version,existing[0]))
                stats["updated"] += 1
            else:
                cur.execute("""INSERT INTO unscr_entries
                    (un_ref_id,entry_type,primary_name,aliases,nationality,dob,
                     committee,listed_on,narrative,search_vector,list_version,
                     is_active,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,NOW(),NOW())
                    ON CONFLICT (un_ref_id) DO UPDATE SET
                    primary_name=EXCLUDED.primary_name,
                    list_version=EXCLUDED.list_version,
                    updated_at=NOW()""",
                    (e["un_ref_id"],e["entry_type"],e["primary_name"],
                     json.dumps(e["aliases"]),e["nationality"],e["dob"],
                     e["committee"][:100],e["listed_on"],e["narrative"],
                     search_vec,list_version))
                stats["created"] += 1
        except Exception as ex:
            conn.rollback()
            stats["errors"] += 1
            log.warning("Entry error %s: %s", e.get("un_ref_id"), ex)
            continue
    
    conn.commit()
    
    # Update list meta
    cur.execute("SELECT COUNT(*) FROM unscr_entries WHERE is_active=true")
    total = cur.fetchone()[0]
    cur.execute("""INSERT INTO unscr_list_meta (list_version,pulled_at,total_entries,pull_url,new_entries,removed_entries,status,pulled_by)
                   VALUES (%s,NOW(),%s,%s,0,0,'SUCCESS','host_cron')
                   ON CONFLICT (list_version) DO UPDATE SET total_entries=EXCLUDED.total_entries,pulled_at=NOW()""",
                (list_version, total, UN_XML_URL))
    conn.commit()
    cur.close()
    conn.close()
    log.info("DONE: %s | total active: %d", stats, total)
    return stats

if __name__ == "__main__":
    pg_ip = sys.argv[1] if len(sys.argv) > 1 else "172.18.0.2"
    db_pw = sys.argv[2] if len(sys.argv) > 2 else ""
    sync(pg_ip, db_pw)
