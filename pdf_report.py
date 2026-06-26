import io
import re
from datetime import datetime
from typing import Optional
import config


# Emoji → text replacements for PDF (Helvetica can't render emoji)
_EMOJI_MAP = {
    "🏥": "[+]", "🔬": "[Dx]", "💊": "[Rx]", "🌿": "[Ay]", "💧": "[Ho]",
    "📦": "[Dose]", "🕐": "[Freq]", "📅": "[Dur]", "⏱": "[Time]",
    "🎯": "[Purpose]", "⚠️": "[!]", "📌": "[Note]", "🔴": "[!]",
    "🧪": "[Test]", "❌": "[X]", "✅": "[OK]", "✓": "[OK]",
    "💰": "$", "₹": "Rs.", "🥗": "[Diet]", "💡": "[Tip]",
    "🩺": "[Dr]", "📄": "[PDF]", "🔄": "[New]", "⬇️": "[DL]",
    "🔍": "[Search]", "⚡": "[Fast]",
}

def _strip_emoji(text: str) -> str:
    """Replace emoji with text equivalents for PDF rendering."""
    if not text:
        return text
    for emoji, replacement in _EMOJI_MAP.items():
        text = text.replace(emoji, replacement)
    # Remove any remaining emoji/special chars that Helvetica can't render
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    return text.encode('latin-1', 'ignore').decode('latin-1')


def make_pdf(patient: Optional[dict], rx: dict,
             report: Optional[dict], session_id: str, target_system: str = "all") -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors as C
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=1.8*cm, leftMargin=1.8*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)

        def rgb(r, g, b): return C.Color(r/255, g/255, b/255)

        INK   = rgb(10,  15,  28)
        BLUE  = rgb(37,  99, 235)
        GREEN = rgb(5,  150,  89)
        RED   = rgb(220, 38,  38)
        AMBER = rgb(217,119,   6)
        BG    = rgb(240,242,248)
        WHITE = C.white
        MID   = rgb(100,116,139)

        # Style factory — no default fontName to avoid duplicate kwarg errors
        H1   = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15,
                               textColor=BLUE, leading=20, spaceBefore=6, spaceAfter=3)
        H2   = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11,
                               textColor=BLUE, leading=16, spaceBefore=8, spaceAfter=4)
        BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=9,
                               textColor=INK, leading=14, spaceAfter=3)
        SML  = ParagraphStyle("SML", fontName="Helvetica", fontSize=8,
                               textColor=MID, leading=12, spaceAfter=3)
        RED_S = ParagraphStyle("RED", fontName="Helvetica-Bold", fontSize=9,
                                textColor=RED, leading=14, spaceAfter=3)
        DISC = ParagraphStyle("DISC", fontName="Helvetica-Oblique", fontSize=8,
                               textColor=AMBER, leading=12, spaceAfter=3)
        HDR_L = ParagraphStyle("hL", fontName="Helvetica-Bold", fontSize=13,
                                textColor=WHITE, leading=18)
        HDR_R = ParagraphStyle("hR", fontName="Helvetica", fontSize=9,
                                textColor=WHITE, leading=14, alignment=2)

        story = []
        now   = datetime.now().strftime("%d %B %Y, %I:%M %p")

        # ── Header ──────────────────────────────────────────────────────────
        hdr = [[
            Paragraph("<font color='white' size='13'><b>ArogyaAI</b></font><br/>"
                      "<font color='white' size='8'>India's AI Health Intelligence Platform</font>",
                      HDR_L),
            Paragraph(f"<font color='white' size='9'><b>PRESCRIPTION</b></font><br/>"
                      f"<font color='white' size='8'>{now}</font><br/>"
                      f"<font color='white' size='7'>Session: {session_id[:16]}</font>",
                      HDR_R),
        ]]
        ht = Table(hdr, colWidths=[10*cm, 7.4*cm])
        ht.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), BLUE),
            ("TOPPADDING",   (0,0),(-1,-1), 14),
            ("BOTTOMPADDING",(0,0),(-1,-1), 14),
            ("LEFTPADDING",  (0,0),(0,-1),  16),
            ("RIGHTPADDING", (-1,0),(-1,-1),12),
        ]))
        story += [ht, Spacer(1,8)]

        story.append(Paragraph(
            "[!] AI-generated prescription. Must be verified by a licensed physician. "
            "Emergency: 112 | Medical Helpline: 104", DISC))
        story.append(HRFlowable(width="100%", thickness=1, color=AMBER, spaceAfter=8))

        # ── Patient ──────────────────────────────────────────────────────────
        if patient:
            story.append(Paragraph("Patient Details", H2))
            p = patient
            rows = [
                ["Name",        p.get("name","—"),
                 "Age / Gender",f"{p.get('age','—')} yr / {p.get('gender','—')}"],
                ["State / City",f"{p.get('state','—')} / {p.get('city','—')}",
                 "Blood Group", p.get("blood_group","—") or "—"],
                ["Conditions",  ", ".join(p.get("conditions",[]) or ["None"]),
                 "Allergies",   ", ".join(p.get("allergies",[]) or ["None"])],
                ["Current Meds","," .join(p.get("current_meds",[]) or ["None"]),
                 "Diet",        p.get("dietary_pref","—")],
            ]
            pt = Table(rows, colWidths=[2.8*cm, 6.0*cm, 2.6*cm, 5.8*cm])
            pt.setStyle(TableStyle([
                ("FONTNAME",     (0,0),(-1,-1), "Helvetica"),
                ("FONTNAME",     (0,0),(0,-1),  "Helvetica-Bold"),
                ("FONTNAME",     (2,0),(2,-1),  "Helvetica-Bold"),
                ("FONTSIZE",     (0,0),(-1,-1), 8.5),
                ("TEXTCOLOR",    (0,0),(0,-1),  MID),
                ("TEXTCOLOR",    (2,0),(2,-1),  MID),
                ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, BG]),
                ("GRID",         (0,0),(-1,-1), 0.5, rgb(200,210,225)),
                ("TOPPADDING",   (0,0),(-1,-1), 5),
                ("BOTTOMPADDING",(0,0),(-1,-1), 5),
                ("LEFTPADDING",  (0,0),(-1,-1), 7),
            ]))
            story += [pt, Spacer(1,10)]

        # ── Vital Alarms ─────────────────────────────────────────────────────
        if rx.get("vital_alarms"):
            story.append(Paragraph("Vital Alarms", H2))
            for alarm in rx["vital_alarms"]:
                story.append(Paragraph(f"[!] {alarm}", RED_S))
            story.append(Spacer(1,8))

        # ── Diagnosis ────────────────────────────────────────────────────────
        if rx.get("primary_diagnosis"):
            story.append(Paragraph("Diagnosis", H2))
            story.append(Paragraph(
                f"<b>{_strip_emoji(rx['primary_diagnosis'])}</b>"
                f" ({rx.get('icd10','')}) — "
                f"{rx.get('severity','')} | Confidence: {rx.get('confidence','?')}%", BODY))
            if rx.get("diagnosis_reasoning"):
                story.append(Paragraph(_strip_emoji(rx["diagnosis_reasoning"]), SML))
            for flag in rx.get("red_flags", []):
                story.append(Paragraph(f"[!] {_strip_emoji(flag)}", RED_S))
            story.append(Spacer(1,8))

        # ── Medicines ────────────────────────────────────────────────────────
        system_configs = [
            ("Allopathy (Rx)",  "allopathy",  GREEN),
            ("Ayurveda",        "ayurveda",   rgb(5,120,80)),
            ("Homeopathy",      "homeopathy", rgb(109,40,217)),
        ]
        
        if target_system != "all":
            system_configs = [s for s in system_configs if s[1] == target_system]

        for sys_name, sys_key, col in system_configs:
            meds = rx.get(sys_key, {}).get("medicines", [])
            if not meds:
                continue
            story.append(Paragraph(sys_name, H2))
            med_rows = [["Medicine / Brand", "Dose", "Frequency",
                          "Duration", "Timing", "MRP"]]
            for m in meds:
                brand  = m.get("brand","") or m.get("brand_india","")
                price  = f"Rs.{m.get('price_inr','?')}"
                freq = m.get("frequency","") or m.get("freq","—")
                dur  = m.get("duration","") or m.get("dur","—")
                med_rows.append([
                    Paragraph(f"<b>{_strip_emoji(m.get('name','—'))}</b><br/>{_strip_emoji(brand)}", SML),
                    Paragraph(_strip_emoji(m.get("dose","—")), SML),
                    Paragraph(_strip_emoji(freq), SML),
                    Paragraph(_strip_emoji(dur), SML),
                    Paragraph(_strip_emoji(m.get("timing","—")), SML),
                    Paragraph(_strip_emoji(price), SML),
                ])
            mt = Table(med_rows, colWidths=[4.8*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.9*cm])
            mt.setStyle(TableStyle([
                ("BACKGROUND",   (0,0),(-1,0), col),
                ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
                ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0),(-1,-1),7.5),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, BG]),
                ("GRID",         (0,0),(-1,-1),0.5, rgb(200,210,225)),
                ("TOPPADDING",   (0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",  (0,0),(-1,-1),4),
                ("VALIGN",       (0,0),(-1,-1),"TOP"),
            ]))
            story.append(mt)
            # Diet / avoid notes
            sd = rx.get(sys_key,{})
            diet  = sd.get("diet_recommendations",[]) or sd.get("dietary_advice",[])
            avoid = sd.get("avoid",[]) or sd.get("avoid_foods",[])
            if diet:
                story.append(Paragraph(f"Diet: {' | '.join(_strip_emoji(d) for d in diet[:3])}", SML))
            if avoid:
                story.append(Paragraph(f"Avoid: {' | '.join(_strip_emoji(a) for a in avoid[:3])}", SML))
            story.append(Spacer(1,8))

        # ── Precautionary Medical Tests ───────────────────────────────────────
        tests = rx.get("allopathy", {}).get("tests_to_order", [])
        if tests:
            story.append(Paragraph("Precautionary Medical Tests", H2))
            story.append(Paragraph("If symptoms persist, consider the following investigations:", SML))
            for t in tests:
                story.append(Paragraph(f"• {_strip_emoji(t)}", BODY))
            story.append(Spacer(1,8))



        # ── Report findings ───────────────────────────────────────────────────
        if report and report.get("findings"):
            story.append(Paragraph(f"Report: {_strip_emoji(report.get('report_type',''))}", H2))
            story.append(Paragraph(_strip_emoji(report.get("overall_impression","")), BODY))
            ab = [f for f in report["findings"]
                  if f.get("status","").lower() not in ("normal","")]
            for f in ab[:10]:
                story.append(Paragraph(
                    f"* {f.get('parameter','?')}: {f.get('value','?')}"
                    f"{f.get('unit','')} [{f.get('status','?')}] — "
                    f"{_strip_emoji(f.get('significance',''))}",
                    BODY))
            story.append(Spacer(1,8))

        # ── General advice ────────────────────────────────────────────────────
        adv = rx.get("general_advice",{})
        if adv:
            story.append(Paragraph("General Advice", H2))
            for k, v in adv.items():
                if v:
                    story.append(Paragraph(f"<b>{k.title()}:</b> {_strip_emoji(str(v))}", BODY))

        # ── Footer ────────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=10))
        story.append(Paragraph(
            f"ArogyaAI v{config.APP_VERSION} | {config.APP_NAME} | "
            f"Emergency: 112 | iCall Mental Health: 9152987821 | "
            f"Session: {session_id}", DISC))

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        return _text_fallback(patient, rx, session_id)
    except Exception as e:
        return f"PDF error: {e}\nInstall reportlab: pip install reportlab".encode()


def _text_fallback(patient, rx, sid, target_system="all") -> bytes:
    lines = ["="*60, "AROGYAAI PRESCRIPTION", "="*60, ""]
    if patient:
        lines += [f"Patient: {patient.get('name')} | {patient.get('age')}yr | {patient.get('gender')}",""]
    if rx.get("primary_diagnosis"):
        lines += [f"Diagnosis: {rx['primary_diagnosis']} ({rx.get('icd10','')})", ""]
        
    if rx.get("vital_alarms"):
        lines += ["VITAL ALARMS:"]
        for alarm in rx["vital_alarms"]:
            lines.append(f"  [!] {alarm}")
        lines.append("")
        
    system_configs = [("ALLOPATHY","allopathy"),("AYURVEDA","ayurveda"),("HOMEOPATHY","homeopathy")]
    if target_system != "all":
        system_configs = [s for s in system_configs if s[1] == target_system]
        
    for sn, sk in system_configs:
        meds = rx.get(sk,{}).get("medicines",[])
        if meds:
            lines.append(f"\n{sn}:")
            for m in meds:
                freq = m.get('frequency','') or m.get('freq','?')
                dur  = m.get('duration','') or m.get('dur','?')
                lines.append(f"  * {m.get('name','?')} — {m.get('dose','?')} {freq} for {dur}")
                
    tests = rx.get("allopathy", {}).get("tests_to_order", [])
    if tests:
        lines.append("\nPRECAUTIONARY TESTS:")
        for t in tests:
            lines.append(f"  * {t}")
            
    lines += ["","Emergency: 112 | ArogyaAI"]
    return "\n".join(lines).encode()

