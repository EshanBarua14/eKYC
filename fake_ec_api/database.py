"""
Fake EC API — PostgreSQL Database
SQLAlchemy models + seed data.
"""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = os.getenv(
    "FAKE_EC_DB_URL",
    "postgresql://ec_api_user:ec_api_pass_2026@localhost:5432/fake_ec_db"
)
engine       = create_engine(DB_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base         = declarative_base()

# ─────────────────────────────── Models ───────────────────────────────────

class NIDRecord(Base):
    __tablename__ = "nid_records"
    nid_number        = Column(String(20),  primary_key=True, index=True)
    smart_card_number = Column(String(30),  nullable=True)
    pin               = Column(String(20),  nullable=True)
    full_name_en      = Column(String(200), nullable=False)
    full_name_bn      = Column(String(200), nullable=False)
    date_of_birth     = Column(String(10),  nullable=False)
    fathers_name_en   = Column(String(200), nullable=True)
    fathers_name_bn   = Column(String(200), nullable=True)
    mothers_name_en   = Column(String(200), nullable=True)
    mothers_name_bn   = Column(String(200), nullable=True)
    spouse_name_en    = Column(String(200), nullable=True)
    spouse_name_bn    = Column(String(200), nullable=True)
    present_address   = Column(Text,        nullable=True)
    permanent_address = Column(Text,        nullable=True)
    place_of_birth    = Column(String(100), nullable=True)
    district          = Column(String(100), nullable=True)
    division          = Column(String(100), nullable=True)
    blood_group       = Column(String(5),   nullable=True)
    gender            = Column(String(1),   nullable=False)
    nationality       = Column(String(50),  nullable=True, default="Bangladeshi")
    religion          = Column(String(50),  nullable=True)
    occupation        = Column(String(100), nullable=True)
    education         = Column(String(100), nullable=True)
    issue_date        = Column(String(10),  nullable=True)
    expiry_date       = Column(String(10),  nullable=True)
    photo_url         = Column(String(500), nullable=True)
    nid_type          = Column(String(20),  nullable=True,  default="SMART")
    status            = Column(String(20),  nullable=False, default="ACTIVE")
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Institution(Base):
    __tablename__ = "ec_institutions"
    client_id     = Column(String(100), primary_key=True)
    client_secret = Column(String(200), nullable=False)
    name          = Column(String(200), nullable=False)
    status        = Column(String(20),  nullable=False, default="active")
    scope         = Column(String(200), nullable=False, default="nid:verify nid:read")

class AuditLog(Base):
    __tablename__ = "ec_audit_log"
    id             = Column(Integer,     primary_key=True, autoincrement=True)
    request_id     = Column(String(50),  nullable=False, index=True)
    institution_id = Column(String(100), nullable=False, index=True)
    nid_last4      = Column(String(4),   nullable=False)
    endpoint       = Column(String(100), nullable=False)
    result         = Column(String(20),  nullable=False)
    reason         = Column(String(200), nullable=True)
    requested_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# ─────────────────────────────── DB helper ─────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)

# ─────────────────────────────── Seed data ─────────────────────────────────

SEED_NIDS = [
    {"nid_number":"2375411929","smart_card_number":"BGD2375411929","pin":"2375411929",
     "full_name_en":"ESHAN BARUA","full_name_bn":"ঈশান বড়ুয়া","date_of_birth":"1994-08-14",
     "fathers_name_en":"PRODIP BARUA","fathers_name_bn":"প্রদীপ বড়ুয়া",
     "mothers_name_en":"SHIMA BARUA","mothers_name_bn":"সীমা বড়ুয়া",
     "present_address":"বাসা/হোল্ডিং: ৯৭, সবুজবাগ, রাজারবাগ, ঢাকা দক্ষিণ সিটি কর্পোরেশন, ঢাকা",
     "permanent_address":"বাসা/হোল্ডিং: ৯৭, সবুজবাগ, রাজারবাগ, ঢাকা দক্ষিণ সিটি কর্পোরেশন, ঢাকা",
     "place_of_birth":"DHAKA","district":"Dhaka","division":"Dhaka",
     "blood_group":"O+","gender":"M","religion":"Hindu","occupation":"Service",
     "education":"Graduate","issue_date":"2016-08-30","nid_type":"SMART","status":"ACTIVE"},

    {"nid_number":"19858524905063671","smart_card_number":None,"pin":"19858524905063671",
     "full_name_en":"MD ABUL MOSHAD CHOWDHURY","full_name_bn":"মোঃ আবুল মোশাদ চৌধুরী",
     "date_of_birth":"1985-03-03","fathers_name_en":"MD ABUL MASUD CHOWDHURY",
     "fathers_name_bn":"মোঃ আবুল মাসুদ চৌধুরী","mothers_name_en":"JANI CHOWDHURY",
     "mothers_name_bn":"জানী চৌধুরী",
     "present_address":"বাসা/হোল্ডিং: ৭৫, গোমস্তা পাড়া, ডাকঘর: রংপুর-৫৪০০, রংপুর সদর, রংপুর",
     "permanent_address":"বাসা/হোল্ডিং: ৭৫, গোমস্তা পাড়া, ডাকঘর: রংপুর-৫৪০০, রংপুর সদর, রংপুর",
     "place_of_birth":"RANGPUR","district":"Rangpur","division":"Rangpur",
     "blood_group":None,"gender":"M","religion":"Islam","occupation":"Business",
     "education":"HSC","issue_date":"2016-05-10","nid_type":"OLD_SMART","status":"ACTIVE"},

    {"nid_number":"1234567890123","smart_card_number":"BGD1234567890123","pin":"1234567890123",
     "full_name_en":"RAHMAN HOSSAIN CHOWDHURY","full_name_bn":"রহমান হোসেন চৌধুরী",
     "date_of_birth":"1990-01-15","fathers_name_en":"ABDUR RAHMAN CHOWDHURY",
     "fathers_name_bn":"আব্দুর রহমান চৌধুরী","mothers_name_en":"MST RASHIDA BEGUM",
     "mothers_name_bn":"মোসাম্মাৎ রাশিদা বেগম",
     "present_address":"123, Agrabad Commercial Area, Chittagong",
     "permanent_address":"Village: Agrabad, Upazila: Kotwali, District: Chittagong",
     "place_of_birth":"CHITTAGONG","district":"Chittagong","division":"Chittagong",
     "blood_group":"O+","gender":"M","religion":"Islam","occupation":"Service",
     "education":"Graduate","issue_date":"2018-03-20","nid_type":"SMART","status":"ACTIVE"},

    {"nid_number":"9876543210987","smart_card_number":"BGD9876543210987","pin":"9876543210987",
     "full_name_en":"FATEMA BEGUM","full_name_bn":"ফাতেমা বেগম","date_of_birth":"1985-06-20",
     "fathers_name_en":"MD IBRAHIM","fathers_name_bn":"মোঃ ইব্রাহিম",
     "mothers_name_en":"MST AMENA KHATUN","mothers_name_bn":"মোসাম্মাৎ আমেনা খাতুন",
     "spouse_name_en":"MD KARIM","spouse_name_bn":"মোঃ করিম",
     "present_address":"456, Dhanmondi R/A, Dhaka",
     "permanent_address":"Village: Madhabpur, Upazila: Habiganj Sadar, District: Habiganj",
     "place_of_birth":"HABIGANJ","district":"Dhaka","division":"Dhaka",
     "blood_group":"A+","gender":"F","religion":"Islam","occupation":"Housewife",
     "education":"SSC","issue_date":"2015-11-05","nid_type":"SMART","status":"ACTIVE"},

    {"nid_number":"1111111111111","smart_card_number":"BGD1111111111111","pin":"1111111111111",
     "full_name_en":"KARIM UDDIN AHMED","full_name_bn":"করিম উদ্দিন আহমেদ",
     "date_of_birth":"1975-03-10","fathers_name_en":"RAHIM UDDIN AHMED",
     "fathers_name_bn":"রহিম উদ্দিন আহমেদ","mothers_name_en":"SUFIA BEGUM",
     "mothers_name_bn":"সুফিয়া বেগম","spouse_name_en":"RAHELA BEGUM",
     "spouse_name_bn":"রাহেলা বেগম",
     "present_address":"789, Sylhet Sadar, Sylhet","permanent_address":"789, Sylhet Sadar, Sylhet",
     "place_of_birth":"SYLHET","district":"Sylhet","division":"Sylhet",
     "blood_group":"B+","gender":"M","religion":"Islam","occupation":"Farmer",
     "education":"Primary","issue_date":"2013-06-15","nid_type":"LAMINATED","status":"ACTIVE"},

    {"nid_number":"2222222222222","smart_card_number":"BGD2222222222222","pin":"2222222222222",
     "full_name_en":"NASRIN SULTANA","full_name_bn":"নাসরিন সুলতানা","date_of_birth":"1992-11-25",
     "fathers_name_en":"MD ANWAR HOSSAIN","fathers_name_bn":"মোঃ আনোয়ার হোসেন",
     "mothers_name_en":"HALIMA BEGUM","mothers_name_bn":"হালিমা বেগম",
     "present_address":"House 12, Road 4, Banani, Dhaka",
     "permanent_address":"Village: Karimpur, Upazila: Comilla Sadar, District: Comilla",
     "place_of_birth":"COMILLA","district":"Dhaka","division":"Dhaka",
     "blood_group":"AB+","gender":"F","religion":"Islam","occupation":"Teacher",
     "education":"Masters","issue_date":"2019-07-22","nid_type":"SMART","status":"ACTIVE"},

    {"nid_number":"3333333333333","smart_card_number":"BGD3333333333333","pin":"3333333333333",
     "full_name_en":"MOHAMMAD RAFIQUL ISLAM","full_name_bn":"মোহাম্মদ রফিকুল ইসলাম",
     "date_of_birth":"1980-07-04","fathers_name_en":"ABDUS SALAM",
     "fathers_name_bn":"আব্দুস সালাম","mothers_name_en":"MST KULSUM BEGUM",
     "mothers_name_bn":"মোসাম্মাৎ কুলসুম বেগম",
     "present_address":"Flat 5B, Bashundhara R/A, Dhaka-1229",
     "permanent_address":"Village: Char Fashon, Upazila: Bhola Sadar, District: Bhola",
     "place_of_birth":"BHOLA","district":"Dhaka","division":"Dhaka",
     "blood_group":"B-","gender":"M","religion":"Islam","occupation":"Doctor",
     "education":"MBBS","issue_date":"2017-09-12","nid_type":"SMART","status":"ACTIVE"},

    {"nid_number":"4444444444444","smart_card_number":"BGD4444444444444","pin":"4444444444444",
     "full_name_en":"SHIRIN AKTER","full_name_bn":"শিরিন আক্তার","date_of_birth":"1995-02-14",
     "fathers_name_en":"NURUL ISLAM","fathers_name_bn":"নুরুল ইসলাম",
     "mothers_name_en":"ROHIMA BEGUM","mothers_name_bn":"রহিমা বেগম",
     "present_address":"Road 7, Uttara Sector-3, Dhaka",
     "permanent_address":"Village: Sonargaon, Upazila: Sonargaon, District: Narayanganj",
     "place_of_birth":"NARAYANGANJ","district":"Dhaka","division":"Dhaka",
     "blood_group":"A-","gender":"F","religion":"Islam","occupation":"Engineer",
     "education":"BSc Engineering","issue_date":"2021-03-08","nid_type":"SMART","status":"ACTIVE"},

    # Blocked NID — tests 403 error path
    {"nid_number":"0000000000000","smart_card_number":None,"pin":"0000000000000",
     "full_name_en":"BLOCKED TEST CITIZEN","full_name_bn":"ব্লকড টেস্ট নাগরিক",
     "date_of_birth":"2000-01-01","fathers_name_en":"TEST FATHER","fathers_name_bn":"টেস্ট পিতা",
     "mothers_name_en":"TEST MOTHER","mothers_name_bn":"টেস্ট মাতা",
     "present_address":"Test Address, Dhaka","permanent_address":"Test Address, Dhaka",
     "place_of_birth":"DHAKA","district":"Dhaka","division":"Dhaka",
     "blood_group":None,"gender":"M","religion":"Islam","occupation":"Unknown",
     "education":"Unknown","issue_date":"2020-01-01","nid_type":"SMART","status":"BLOCKED"},
]

SEED_INSTITUTIONS = [
    {"client_id":"inst_xpert_001","client_secret":"sk_test_xpert_ekyc_secret_2026",
     "name":"Xpert Fintech Ltd.","status":"active","scope":"nid:verify nid:read"},
    {"client_id":"inst_test_bank","client_secret":"sk_test_bank_secret_2026",
     "name":"Test Bank Ltd.","status":"active","scope":"nid:verify nid:read"},
    {"client_id":"inst_suspended","client_secret":"sk_suspended_secret",
     "name":"Suspended Institution","status":"suspended","scope":"nid:verify"},
]

def seed(db):
    for rec in SEED_NIDS:
        if not db.query(NIDRecord).filter_by(nid_number=rec["nid_number"]).first():
            db.add(NIDRecord(**rec))
    for inst in SEED_INSTITUTIONS:
        if not db.query(Institution).filter_by(client_id=inst["client_id"]).first():
            db.add(Institution(**inst))
    db.commit()
