"""M104 -- Real Adverse Media Tests -- BFIU Circular No. 29 s5.3"""
import os, pytest
from unittest.mock import patch, MagicMock
os.environ.setdefault("DATABASE_URL", "sqlite:///./ekyc.db")

from app.services.adverse_media_service import (
    screen_adverse_media_live, _fetch_rss, _name_in_text, _is_adverse,
    ADVERSE_KEYWORDS,
)
from app.services.screening_service import screen_adverse_media


def test_T01_importable():
    assert screen_adverse_media_live is not None


def test_T02_returns_required_fields():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media_live("Test Person")
    for f in ["verdict","name","hits","hit_count","edd_required","sources","screened_at","bfiu_ref"]:
        assert f in r, f"Missing field: {f}"


def test_T03_clear_on_no_hits():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media_live("Nobody Special")
    assert r["verdict"] == "CLEAR"
    assert r["hit_count"] == 0
    assert r["edd_required"] == False


def test_T04_flagged_on_3_plus_hits():
    items = [
        {"title": "John Doe convicted of fraud", "description": "criminal case", "link": "", "pub_date": ""},
        {"title": "John Doe money laundering",  "description": "corruption",    "link": "", "pub_date": ""},
        {"title": "John Doe arrested bribery",  "description": "embezzlement",  "link": "", "pub_date": ""},
    ]
    with patch("app.services.adverse_media_service._fetch_rss", return_value=items):
        r = screen_adverse_media_live("John Doe")
    assert r["verdict"] == "FLAGGED"
    assert r["edd_required"] == True


def test_T05_review_on_1_hit():
    items = [
        {"title": "Jane Smith arrested", "description": "criminal", "link": "", "pub_date": ""},
    ]
    with patch("app.services.adverse_media_service._fetch_rss", return_value=items):
        r = screen_adverse_media_live("Jane Smith")
    assert r["verdict"] in ("REVIEW", "FLAGGED")


def test_T06_name_in_text_full_name():
    assert _name_in_text("John Doe", "John Doe was arrested for fraud") == True


def test_T07_name_in_text_no_match():
    assert _name_in_text("John Doe", "Completely unrelated article") == False


def test_T08_name_in_text_partial():
    assert _name_in_text("Rahman", "Mr Rahman convicted of corruption") == True


def test_T09_is_adverse_fraud():
    assert _is_adverse("Convicted of fraud and money laundering") == True


def test_T10_is_adverse_clear():
    assert _is_adverse("Won award for community service") == False


def test_T11_adverse_keywords_present():
    assert "fraud" in ADVERSE_KEYWORDS
    assert "money laundering" in ADVERSE_KEYWORDS
    assert "terrorist" in ADVERSE_KEYWORDS
    assert "corruption" in ADVERSE_KEYWORDS


def test_T12_empty_name_returns_clear():
    r = screen_adverse_media_live("")
    assert r["verdict"] == "CLEAR"


def test_T13_short_name_returns_clear():
    r = screen_adverse_media_live("AB")
    assert r["verdict"] == "CLEAR"


def test_T14_fetch_rss_handles_error():
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
        result = _fetch_rss("http://fake")
    assert result == []


def test_T15_deduplicates_hits():
    items = [
        {"title": "John Doe fraud case", "description": "criminal", "link": "", "pub_date": ""},
        {"title": "John Doe fraud case", "description": "criminal", "link": "", "pub_date": ""},
        {"title": "John Doe fraud case", "description": "criminal", "link": "", "pub_date": ""},
    ]
    with patch("app.services.adverse_media_service._fetch_rss", return_value=items):
        r = screen_adverse_media_live("John Doe")
    assert r["hit_count"] == 1


def test_T16_bfiu_ref_present():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media_live("Test")
    assert "BFIU" in r["bfiu_ref"]
    assert "5.3" in r["bfiu_ref"]


def test_T17_screening_service_uses_live():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media("Test Person")
    assert "sources" in r


def test_T18_fallback_on_network_error():
    with patch("app.services.adverse_media_service.screen_adverse_media_live",
               side_effect=Exception("network down")):
        r = screen_adverse_media("Test Person")
    assert r["verdict"] in ("CLEAR", "FLAGGED")
    assert "fallback" in str(r.get("sources", ""))


def test_T19_bangladeshi_name():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media_live("Mohammad Rahimuddin")
    assert r["verdict"] == "CLEAR"


def test_T20_result_has_screened_at():
    with patch("app.services.adverse_media_service._fetch_rss", return_value=[]):
        r = screen_adverse_media_live("Test")
    assert r["screened_at"] is not None
    assert len(r["screened_at"]) > 0
