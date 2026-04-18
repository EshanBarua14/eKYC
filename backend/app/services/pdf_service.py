"""
KYC PDF Generator Service - M15
Generates BFIU-compliant digital KYC profile documents.
Contains: match score, timestamp, EC data, risk grade,
          screening result, liveness checks, agent/institution info.
"""
import io
import base64
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Brand colours ───────────────────────────────────────────────────────────
ACCENT   = colors.HexColor("#6358ff")
GREEN    = colors.HexColor("#00b87a")
RED      = colors.HexColor("#f03d5f")
YELLOW   = colors.HexColor("#f0a500")
BLUE     = colors.HexColor("#2d7ef0")
BG_LIGHT = colors.HexColor("#f4f4f8")
BORDER   = colors.HexColor("#e2e2ea")
TEXT     = colors.HexColor("#1a1a2e")
TEXT2    = colors.HexColor("#6b6b8a")

def _styles():
    base = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("title",    fontSize=18, textColor=ACCENT,  fontName="Helvetica-Bold",  spaceAfter=2,  alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontSize=9,  textColor=TEXT2,   fontName="Helvetica",       spaceAfter=0,  alignment=TA_CENTER),
        "h2":       ParagraphStyle("h2",       fontSize=10, textColor=ACCENT,  fontName="Helvetica-Bold",  spaceBefore=10, spaceAfter=4),
        "body":     ParagraphStyle("body",     fontSize=8,  textColor=TEXT,    fontName="Helvetica",       spaceAfter=2),
        "mono":     ParagraphStyle("mono",     fontSize=8,  textColor=TEXT,    fontName="Courier",         spaceAfter=2),
        "caption":  ParagraphStyle("caption",  fontSize=7,  textColor=TEXT2,   fontName="Helvetica",       spaceAfter=2),
        "verdict_matched": ParagraphStyle("vm", fontSize=13, textColor=GREEN,  fontName="Helvetica-Bold",  alignment=TA_CENTER),
        "verdict_review":  ParagraphStyle("vr", fontSize=13, textColor=YELLOW, fontName="Helvetica-Bold",  alignment=TA_CENTER),
        "verdict_failed":  ParagraphStyle("vf", fontSize=13, textColor=RED,    fontName="Helvetica-Bold",  alignment=TA_CENTER),
    }

def _table(data, col_widths, row_colors=None):
    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TEXTCOLOR",   (0,0), (-1,-1), TEXT),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [BG_LIGHT, colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.3, BORDER),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0,0), (0,-1), TEXT2),
    ]
    if row_colors:
        style.extend(row_colors)
    t.setStyle(TableStyle(style))
    return t

def generate_kyc_pdf(
    # Verification result
    session_id:     str,
    verdict:        str,
    confidence:     float,
    timestamp:      str,
    processing_ms:  int             = 0,
    bfiu_ref:       str             = "BFIU Circular No. 29",
    # Personal info
    full_name:      str             = "N/A",
    date_of_birth:  str             = "N/A",
    mobile:         str             = "N/A",
    fathers_name:   Optional[str]   = None,
    mothers_name:   Optional[str]   = None,
    spouse_name:    Optional[str]   = None,
    gender:         Optional[str]   = None,
    nationality:    str             = "Bangladeshi",
    profession:     Optional[str]   = None,
    present_address: Optional[str]  = None,
    permanent_address: Optional[str]= None,
    # KYC classification
    kyc_type:       str             = "SIMPLIFIED",
    institution_type: str           = "INSURANCE",
    product_type:   Optional[str]   = None,
    risk_grade:     str             = "LOW",
    risk_score:     int             = 0,
    edd_required:   bool            = False,
    status:         str             = "PENDING",
    # Compliance
    pep_flag:       bool            = False,
    unscr_checked:  bool            = False,
    screening_result: str           = "CLEAR",
    # Liveness
    liveness_passed: bool           = True,
    liveness_score:  int            = 0,
    liveness_max:    int            = 5,
    # Scores
    ssim_score:     float           = 0,
    orb_score:      float           = 0,
    histogram_score: float          = 0,
    pixel_score:    float           = 0,
    # Agent / institution
    agent_id:       str             = "N/A",
    institution_id: str             = "N/A",
    geolocation:    str             = "N/A",
    # Face images (base64)
    nid_face_b64:   Optional[str]   = None,
    live_face_b64:  Optional[str]   = None,
) -> bytes:
    """Generate a BFIU-compliant KYC PDF and return raw bytes."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
    )
    S = _styles()
    W = A4[0] - 3.6*cm   # usable width
    story = []

    # ── Header ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("Xpert eKYC", S["title"]),
        Paragraph("DIGITAL KYC VERIFICATION CERTIFICATE", S["subtitle"]),
        Paragraph(bfiu_ref, S["caption"]),
    ]]
    ht = Table([
        [Paragraph("<b>Xpert eKYC</b><br/>Digital KYC Certificate", S["title"])],
    ], colWidths=[W])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ACCENT),
        ("TEXTCOLOR",  (0,0), (-1,-1), colors.white),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Document Reference: {session_id}  ·  Generated: {timestamp[:19].replace('T',' ')} UTC  ·  {bfiu_ref}", S["caption"]))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=6))

    # ── Verdict banner ────────────────────────────────────────────────────
    v_color = GREEN if verdict=="MATCHED" else (YELLOW if verdict=="REVIEW" else RED)
    v_label = "✓ IDENTITY VERIFIED" if verdict=="MATCHED" else ("⚠ MANUAL REVIEW REQUIRED" if verdict=="REVIEW" else "✗ VERIFICATION FAILED")
    vt = Table([[
        Paragraph(v_label, S[f"verdict_{'matched' if verdict=='MATCHED' else 'review' if verdict=='REVIEW' else 'failed'}"]),
        Paragraph(f"<b>{confidence}%</b><br/><font size=7>Confidence Score</font>", ParagraphStyle("cs", fontSize=11, textColor=v_color, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
    ]], colWidths=[W*0.7, W*0.3])
    bg = colors.HexColor("#e8fdf4") if verdict=="MATCHED" else (colors.HexColor("#fffbe6") if verdict=="REVIEW" else colors.HexColor("#fdeaee"))
    vt.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), bg),
        ("BOX",        (0,0),(-1,-1), 1, v_color),
        ("TOPPADDING", (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1),12),
        ("VALIGN",     (0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(vt)
    story.append(Spacer(1, 0.3*cm))

    # ── Personal Information ──────────────────────────────────────────────
    story.append(Paragraph("1. Personal Information (EC Verified)", S["h2"]))
    personal = [
        ["Full Name",         full_name,           "Date of Birth",   date_of_birth],
        ["Mobile",            mobile,               "Gender",          gender or "N/A"],
        ["Nationality",       nationality,          "Profession",      profession or "N/A"],
        ["Father's Name",    fathers_name or "N/A","Mother's Name",  mothers_name or "N/A"],
        ["Spouse Name",       spouse_name  or "N/A","PEP/IP Flag",     "YES ⚠" if pep_flag else "No"],
        ["Present Address",   present_address  or "N/A", "Permanent Address", permanent_address or "N/A"],
    ]
    story.append(_table(personal, [W*0.15, W*0.35, W*0.15, W*0.35]))

    # ── KYC Classification ────────────────────────────────────────────────
    story.append(Paragraph("2. KYC Classification & Risk Grade", S["h2"]))
    risk_color_map = {"HIGH": RED, "MEDIUM": YELLOW, "LOW": GREEN}
    rc = risk_color_map.get(risk_grade, TEXT)
    kyc_data = [
        ["KYC Type",        kyc_type,             "Institution Type", institution_type],
        ["Product Type",    product_type or "N/A","Status",           status],
        ["Risk Grade",      risk_grade,            "Risk Score",       str(risk_score)],
        ["EDD Required",    "YES ⚠" if edd_required else "No", "UNSCR Checked", "Yes" if unscr_checked else "No"],
        ["Screening Result",screening_result,      "BFIU Reference",  bfiu_ref],
    ]
    ct = _table(kyc_data, [W*0.15, W*0.35, W*0.15, W*0.35],
        row_colors=[("TEXTCOLOR",(1,2),(1,2), rc), ("FONTNAME",(1,2),(1,2),"Helvetica-Bold")])
    story.append(ct)

    # ── Biometric Verification Scores ─────────────────────────────────────
    story.append(Paragraph("3. Biometric Verification Scores", S["h2"]))
    scores_data = [
        ["Method",                  "Score",       "Weight", "Description"],
        ["Overall Confidence",      f"{confidence}%", "—",   "Weighted composite score"],
        ["SSIM Structural",         f"{ssim_score:.1f}%",  "35%", "Structural similarity index"],
        ["Histogram Correlation",   f"{histogram_score:.1f}%","30%","Colour histogram comparison"],
        ["ORB Feature Points",      f"{orb_score:.1f}%",   "25%", "Keypoint descriptor matching"],
        ["Pixel Difference",        f"{pixel_score:.1f}%", "10%", "Raw pixel-level comparison"],
    ]
    bt = Table(scores_data, colWidths=[W*0.3, W*0.15, W*0.1, W*0.45])
    bt.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,0), ACCENT),
        ("TEXTCOLOR",   (0,0),(-1,0), colors.white),
        ("FONTNAME",    (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[BG_LIGHT, colors.white]),
        ("GRID",        (0,0),(-1,-1), 0.3, BORDER),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
        ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("TOPPADDING",  (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("ALIGN",       (1,0),(2,-1), "CENTER"),
    ]))
    story.append(bt)

    # ── Liveness Check ────────────────────────────────────────────────────
    story.append(Paragraph("4. Liveness Detection (BFIU Annexure-2)", S["h2"]))
    liveness_color = GREEN if liveness_passed else RED
    liveness_label = "PASSED" if liveness_passed else "FAILED"
    lt = Table([[
        Paragraph(f"Liveness: <b>{liveness_label}</b>", ParagraphStyle("lv", fontSize=9, textColor=liveness_color, fontName="Helvetica-Bold")),
        Paragraph(f"Score: <b>{liveness_score}/{liveness_max}</b> challenges passed", S["body"]),
        Paragraph("Active liveness — 5-challenge protocol (BFIU Annexure-2)", S["caption"]),
    ]], colWidths=[W*0.2, W*0.3, W*0.5])
    lt.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#e8fdf4") if liveness_passed else colors.HexColor("#fdeaee")),
        ("BOX",        (0,0),(-1,-1), 0.5, liveness_color),
        ("TOPPADDING", (0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1), 8), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(lt)

    # ── Session & Audit ───────────────────────────────────────────────────
    story.append(Paragraph("5. Session & Audit Information", S["h2"]))
    session_data = [
        ["Session ID",      session_id,        "Timestamp (UTC)",  timestamp[:19].replace("T"," ")],
        ["Agent ID",        agent_id,           "Institution ID",   institution_id],
        ["Geolocation",     geolocation,        "Processing Time",  f"{processing_ms} ms"],
        ["Document Status", "FINAL — IMMUTABLE","Retention Policy", "5 years (BFIU §5.1)"],
    ]
    story.append(_table(session_data, [W*0.15, W*0.35, W*0.15, W*0.35]))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.2*cm))
    footer_text = (
        f"This document is an electronically generated KYC verification certificate issued by Xpert Fintech Ltd. "
        f"It is compliant with {bfiu_ref} and contains a legally binding biometric verification record. "
        f"Retention period: {5} years from relationship end. "
        f"Generated: {timestamp[:19].replace('T',' ')} UTC."
    )
    story.append(Paragraph(footer_text, S["caption"]))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        "Xpert Fintech Ltd.  ·  BFIU-Registered eKYC Platform  ·  Circular No. 29 Compliant  ·  Deadline: 31 Dec 2026",
        ParagraphStyle("footer2", fontSize=7, textColor=ACCENT, fontName="Helvetica-Bold", alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()


def generate_kyc_pdf_b64(kwargs: dict) -> str:
    """Return PDF as base64 string for API response."""
    return base64.b64encode(generate_kyc_pdf(**kwargs)).decode()
