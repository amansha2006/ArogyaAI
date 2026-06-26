import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
import llm_engine

logger = logging.getLogger("medical")

# ── RAG SEMANTIC RETRIEVAL (BioLORD + FAISS) ──────────────────────────────────
_embed_model = None
_faiss_indexes = {}
_faiss_metadata = {}

def get_embedding_model():
    """Lazily load sentence-transformers model (fine-tuned BioLORD first, then base)."""
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    try:
        from sentence_transformers import SentenceTransformer
        model_path = config.BIOBERT_PATH
        if Path(model_path).exists() and any(Path(model_path).iterdir()):
            logger.info("RAG: Loading fine-tuned BioLORD model on CPU from %s", model_path)
            _embed_model = SentenceTransformer(model_path, device="cpu")
        else:
            logger.info("RAG: Fine-tuned model not found, loading base model on CPU: %s", config.BIOBERT_BASE)
            _embed_model = SentenceTransformer(config.BIOBERT_BASE, device="cpu")
        return _embed_model
    except Exception as e:
        logger.warning("RAG: Failed to load sentence-transformers model: %s", e)
        return None

def load_faiss_index(category: str):
    """Lazily load FAISS index and metadata for a category."""
    global _faiss_indexes, _faiss_metadata
    if category in _faiss_indexes:
        return _faiss_indexes[category], _faiss_metadata[category]
    
    try:
        import faiss
        import json
        idx_path = Path(config.FAISS_INDEX_DIR) / f"{category}.index"
        meta_path = Path(config.FAISS_INDEX_DIR) / f"{category}_meta.json"
        
        if idx_path.exists() and meta_path.exists():
            logger.info("RAG: Loading FAISS index and metadata for %s", category)
            index = faiss.read_index(str(idx_path))
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            _faiss_indexes[category] = index
            _faiss_metadata[category] = meta
            return index, meta
    except Exception as e:
        logger.warning("RAG: Failed to load FAISS index for %s: %s", category, e)
    return None, None

def retrieve_rag_context(query: str, top_k: int = 10) -> str:
    """Retrieve relevant text chunks from FAISS knowledge bases based on semantic similarity."""
    faiss_dir = Path(config.FAISS_INDEX_DIR)
    if not faiss_dir.exists() or not any(faiss_dir.glob("*.index")):
        logger.info("RAG: ⏭️  No FAISS indexes found in %s — skipping semantic search entirely", faiss_dir)
        return ""

    embed_model = get_embedding_model()
    if not embed_model:
        logger.info("RAG: ❌ No embedding model loaded — skipping semantic search")
        return ""
        
    try:
        import numpy as np
        # Encode and normalize query vector
        query_vector = embed_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        
        context_parts = []
        categories = ["allopathy", "ayurveda", "homeopathy", "drug_interactions"]
        
        logger.info("RAG: 🔍 Searching for: '%s'", query)
        
        for cat in categories:
            index, meta = load_faiss_index(cat)
            if not index or not meta:
                continue
                
            # FAISS index query
            D, I = index.search(query_vector.astype("float32"), top_k)
            
            cat_results = []
            for dist, idx in zip(D[0], I[0]):
                if idx == -1:
                    continue
                source_file = meta["metadata"][idx].get("file", "unknown")
                # Higher threshold (0.35) to avoid pulling irrelevant diseases
                if dist < 0.35:
                    continue
                text = meta["texts"][idx]
                logger.info("RAG:    [%s] ✓ %s (similarity %.2f)", cat, source_file, dist)
                cat_results.append(f"- [{source_file} (similarity: {dist:.2f})]: {text.strip()}")
                
            if cat_results:
                context_parts.append(f"\n--- Category: {cat.upper()} ---")
                context_parts.extend(cat_results)
                
        if context_parts:
            result = "RELEVANT KNOWLEDGE BASE CONTEXT:\n" + "\n".join(context_parts)
            logger.info("RAG: ✅ Retrieved %d context chunks", len([p for p in context_parts if p.startswith("- ")]))
            return result
        else:
            logger.info("RAG: ℹ️  No chunks above similarity threshold — falling back to keyword search")
    except Exception as e:
        logger.warning("RAG: ❌ Search execution failed: %s", e)
    return ""


# Import medicine DB
try:
    from data.medicine_db import DISEASES, INTERACTIONS, PRICES, search_by_symptom, get_price
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from data.medicine_db import DISEASES, INTERACTIONS, PRICES, search_by_symptom, get_price
    except ImportError:
        logger.warning("medicine_db not found — using empty fallbacks")
        DISEASES = {}; INTERACTIONS = []; PRICES = {}
        def search_by_symptom(t): return []
        def get_price(m): return {}


# ─────────────────────────────────────────────────────────────────────────────
# 1. EMERGENCY DETECTION (no API, instant)
# ─────────────────────────────────────────────────────────────────────────────

def detect_emergency(text: str) -> Optional[dict]:
    tl = text.lower()
    for name, info in config.EMERGENCY.items():
        hits = [kw for kw in info["kw"] if kw in tl]
        if hits:
            return {"condition": name, "icon": info["icon"],
                    "action": info["action"], "hits": hits}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. REPORT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyse_report(file_bytes: bytes, filename: str, mime_type: str,
                   patient: dict = None, extra: str = "") -> dict:
    is_pdf = mime_type == "application/pdf" or filename.lower().endswith(".pdf")
    pctx   = _profile_ctx(patient)

    if is_pdf:
        text = _pdf_text(file_bytes)
        if text.strip():
            return _text_to_report(text, pctx, extra)
        return _image_to_report(file_bytes, "application/pdf", pctx, extra)
    return _image_to_report(file_bytes, mime_type, pctx, extra)


def analyse_manual_values(values_text: str, gender: str = "unknown") -> dict:
    prompt = f"""
Patient (gender: {gender}) blood values: {values_text}

Parse every value. Return JSON:
{{
  "report_type": "Blood Test (Manual Entry)",
  "overall_impression": "Main finding",
  "findings": [
    {{
      "parameter": "Hemoglobin",
      "value": "8.2", "unit": "g/dL",
      "reference_range": "12.0-15.5 (female)",
      "status": "Low",
      "significance": "Moderate anemia — fatigue and breathlessness"
    }}
  ],
  "abnormal_findings": [], "critical_values": [],
  "likely_conditions": [], "recommended_tests": [],
  "urgency": "Routine",
  "patient_summary": "Simple explanation"
}}
Use Indian/WHO reference ranges. Flag critical values.
"""
    result = llm_engine.generate_json(prompt)
    if result and "error" not in result:
        result["source"] = "manual_entry"
        return result
    
    err_msg = result.get("error", "LLM unavailable") if result else "LLM unavailable"
    return {"report_type": "Blood Test", "overall_impression": f"Error: {err_msg}",
            "findings": [], "urgency": "Routine", "error": err_msg}


def _pdf_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber, io
        parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: parts.append(t)
        extracted_text = "\n".join(parts).strip()
        
        # If standard text extraction works, return it
        if extracted_text:
            return extracted_text
            
        # If no text found (Scanned PDF), fallback to Local OCR
        logger.info("PDF has no text (likely scanned). Attempting Local OCR...")
        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_bytes)
            ocr_parts = []
            for img in images:
                text = pytesseract.image_to_string(img)
                ocr_parts.append(text)
            return "\n".join(ocr_parts).strip()
        except ImportError:
            logger.warning("pytesseract or pdf2image not installed. Skipping local OCR.")
            return ""
            
    except Exception as e:
        logger.warning("PDF extraction error: %s", e)
        return ""


def _text_to_report(text: str, pctx: str, extra: str) -> dict:
    prompt = f"""
{pctx}
{f"Patient notes: {extra}" if extra else ""}

MEDICAL REPORT TEXT:
{text[:5000]}

Analyse and return JSON:
{{
  "report_type": "Blood Test|Pathology|Radiology",
  "lab_name": "lab name if visible",
  "report_date": "date if visible",
  "overall_impression": "Most important finding",
  "findings": [
    {{"parameter":"name","value":"value","unit":"unit",
     "reference_range":"normal range",
     "status":"Normal|High|Low|Critical High|Critical Low",
     "significance":"plain language meaning"}}
  ],
  "abnormal_findings": [], "critical_values": [],
  "likely_conditions": [], "recommended_tests": [],
  "urgency": "Routine|Soon|Urgent|Emergency",
  "patient_summary": "simple explanation"
}}
"""
    result = llm_engine.generate_json(prompt)
    if result and "error" not in result:
        result["source"] = "pdfplumber+llm"
        return result
    
    err_msg = result.get("error", "LLM unavailable.") if result else "LLM unavailable."
    return {"report_type": "Report", "overall_impression": f"Error: {err_msg}",
            "raw_text": text[:1500], "findings": [], "urgency": "Routine",
            "source": "raw_text"}


def _image_to_report(fb: bytes, mime: str, pctx: str, extra: str) -> dict:
    # 1. ATTEMPT LOCAL OCR (100% Free & Private)
    try:
        import pytesseract
        import io
        from PIL import Image
        
        logger.info("Attempting Local OCR on image...")
        img = Image.open(io.BytesIO(fb))
        ocr_text = pytesseract.image_to_string(img).strip()
        
        if len(ocr_text) > 30:  # If we got meaningful text out of the image
            logger.info("Local OCR successful! Passing text to local LLaMA.")
            return _text_to_report(ocr_text, pctx, extra)
    except ImportError:
        logger.warning("pytesseract not installed. Skipping local Image OCR.")
    except Exception as e:
        logger.warning("Local Image OCR failed: %s", e)

    # 2. FALLBACK TO GEMINI VISION
    logger.info("Local OCR failed or unavailable. Falling back to Gemini Vision API.")
    prompt = f"""
{pctx}
{f"Notes: {extra}" if extra else ""}

Analyse this medical image. Return JSON:
{{
  "report_type": "Chest X-ray|Blood Test|MRI|CT|ECG|Ultrasound",
  "overall_impression": "main finding",
  "findings": [
    {{"parameter":"name","value":"observed","unit":"",
     "reference_range":"normal","status":"Normal|Abnormal|High|Low|Critical",
     "significance":"meaning"}}
  ],
  "abnormal_findings": [], "critical_values": [],
  "likely_conditions": [], "recommended_tests": [],
  "urgency": "Routine|Soon|Urgent|Emergency",
  "patient_summary": "simple explanation"
}}
"""
    raw = llm_engine.analyze_image(prompt, fb, mime)
    if raw.startswith("ERROR:"):
        return {"report_type": "Report", "overall_impression": raw,
                "findings": [], "urgency": "Routine", "error": raw}
    result = llm_engine._parse_json(raw)
    if result:
        result["source"] = "gemini_vision"
        return result
    return {"report_type": "Report", "overall_impression": raw[:200],
            "raw_analysis": raw, "findings": [], "urgency": "Routine",
            "source": "vision_raw"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. PRESCRIPTION GENERATION (symptoms → all 3 systems, ONE call)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are ArogyaAI — a senior Indian physician and integrative medicine specialist.
You must prescribe SPECIFIC medicines based on the user's symptoms. If symptoms are very brief (e.g., "cough and cold"), you MUST assume standard associated symptoms for that condition to provide a full treatment plan.

DIAGNOSIS ACCURACY RULES (READ CAREFULLY):
1. Diagnose what the symptoms indicate.
2. Common cold ≠ COVID. Headache ≠ migraine (unless throbbing + one-sided + nausea).
3. Fever alone ≠ dengue. Dengue requires: high fever + severe joint/muscle pain + headache + rash.
4. Stomach pain alone ≠ ulcer. UTI requires: burning urination + frequency + suprapubic pain.
5. Fatigue alone ≠ anemia. Anemia requires: pallor + fatigue + breathlessness + lab values.
6. If symptoms are vague or mild: diagnose as "Viral Upper Respiratory Tract Infection" or "Non-specific Febrile Illness" — not a serious disease.
7. Confidence must reflect match quality: if only 1-2 symptoms match, confidence ≤ 55%.
8. Use differential diagnosis when symptoms are ambiguous.

PRESCRIPTION RULES:
9. Real drug names only — never "antibiotic" or "pain reliever" — name it specifically
10. Indian brand names: Dolo-650, Crocin, Glycomet, Himalaya, Patanjali, SBL, Dabur
11. Exact dose + frequency + duration + timing for every medicine
12. CRITICAL: You MUST output ALL 3 sections: "allopathy", "ayurveda", and "homeopathy" in your JSON. NEVER omit Ayurveda or Homeopathy. 
13. CRITICAL: The "medicines" array for EACH of allopathy, ayurveda, and homeopathy MUST contain AT LEAST 2 DISTINCT medicines (2-3 is ideal). An array with exactly 1 medicine is INVALID output. Even for brief inputs like "cough and cold", provide a COMPLETE REGIMEN (e.g. Paracetamol + Cough Syrup + Antihistamine).
14. Include INR prices from Indian market
15. Check allergies — NEVER prescribe known allergens
16. Vegetarian patients: no animal-derived Ayurvedic ingredients
17. Use ICMR, WHO India, and AYUSH guidelines
18. If abnormal lab/report findings are provided, explicitly mention them in 'diagnosis_reasoning' and 'vitals_interpretation'.
19. CRITICAL: Every medicine — especially Ayurvedic and Homeopathic — MUST be selected specifically for the diagnosis you just made, not copied from a generic template. Two different diagnoses must NOT receive the same Ayurvedic/Homeopathic combination unless that remedy is genuinely indicated for both conditions.
20. The JSON schema below is a STRUCTURE EXAMPLE ONLY, illustrated with a hypothetical fever case. Its specific drug names (Paracetamol, Levocetirizine, Giloy Ghanvati, Eupatorium Perfoliatum, etc.) are NOT default answers. Reuse them only if fever/cold is the actual diagnosis — otherwise replace every single one.

COMMON CORRECT DIAGNOSES (EXACT MATCHING):
- sudden high fever + severe headache + pain behind eyes + muscle joint pain = Dengue Fever
- cyclical fever chills + high fever with rigors + sweating + headache = Malaria
- step-ladder fever + headache + abdominal pain + constipation or diarrhea = Typhoid Fever
- excessive thirst + frequent urination + unexplained weight loss + fatigue = Type 2 Diabetes Mellitus
- usually no symptoms + occipital headache + dizziness + palpitations = Hypertension
- fatigue + weakness + pale skin + breathlessness on exertion = Iron Deficiency Anemia
- weight gain + fatigue + cold intolerance + constipation = Hypothyroidism
- wheezing + breathlessness + chest tightness + cough especially at night = Bronchial Asthma
- burning stomach pain + nausea + bloating + loss of appetite = Peptic Ulcer Disease
- burning urination + frequent urination + cloudy urine + lower abdominal pain = Urinary Tract Infection
- throbbing headache + one sided headache + nausea + vomiting = Migraine Headache
- itchy blister rash all over body + fever + fatigue + rash starts face spreads to body = Chickenpox (Varicella)
- morning stiffness more than 1 hour + symmetrical small joint swelling + fatigue + fever = Rheumatoid Arthritis
- excessive worry + restlessness + fatigue + difficulty concentrating = Generalized Anxiety Disorder
- runny nose + sore throat + mild fever = Common Cold (Upper Respiratory Infection)
- loose watery stools more than 3 per day + abdominal cramps + nausea + vomiting = Acute Diarrhea / Gastroenteritis
- dry itchy skin + red patches + crusted skin + flaky skin = Eczema
- silvery scales + thick red skin patches + joint pain + dry cracked skin = Psoriasis
- severe itching at night + pimple-like rash + burrows on skin + itching between fingers = Scabies
- pimples + blackheads + whiteheads + oily skin = Acne Vulgaris
- white skin patches + loss of skin color + premature graying + safed daag = Vitiligo
- hives + red itchy welts + swelling + sudden rash = Urticaria
- chronic cough > 2 weeks + blood in sputum + evening fever + night sweats = Pulmonary Tuberculosis
- chronic cough + shortness of breath + wheezing + tight chest = COPD
- cough with mucus + chest discomfort + mild fever + fatigue = Acute Bronchitis
- high fever with chills + cough with yellow/green mucus + chest pain when breathing + fast breathing = Pneumonia
- facial pain + headache + stuffy nose + thick nasal discharge = Sinusitis
- sore throat + difficulty swallowing + swollen tonsils + fever = Tonsillitis
- sudden severe upper right abdomen pain + pain radiating to back + nausea + vomiting = Gallstones (Cholelithiasis)
- sudden pain on right side of lower abdomen + nausea + vomiting + fever = Appendicitis
- yellow eyes + dark urine + extreme fatigue + abdominal pain = Hepatitis B
- diarrhea + abdominal pain + cramping + blood in stool = Crohns Disease
- bloody diarrhea + abdominal pain + cramping + rectal bleeding = Ulcerative Colitis
- gnawing stomach pain + nausea + vomiting + feeling full after eating = Gastritis
- chest pain + pressure in chest + pain radiating to arm + shortness of breath = Angina Pectoris
- shortness of breath on lying down + swelling in legs + fatigue + rapid heartbeat = Heart Failure
- no symptoms + xanthomas + high cholesterol on report + cholesterol badhna = Dyslipidemia
- dull aching head pain + pressure across forehead + tightness around head + neck pain = Tension Headache
- dizziness + feeling of spinning + loss of balance + nausea = Vertigo
- seizures + convulsions + loss of consciousness + staring spells = Epilepsy
- tremors + slow movement + stiff muscles + loss of balance = Parkinsons Disease
- lower back pain radiating to leg + numbness in leg + tingling in foot + shooting leg pain = Sciatica
- severe pelvic pain + painful periods + pain during intercourse + heavy bleeding = Endometriosis
- lower abdominal pain + vaginal discharge + fever + painful urination = Pelvic Inflammatory Disease
- hot flashes + night sweats + mood swings + vaginal dryness = Menopause Syndrome
- vaginal itching + thick white discharge + burning sensation + guptang mein khujli = Vaginal Candidiasis
- high fever + cough + runny nose + koplik spots = Measles
- swollen salivary glands + pain on chewing + fever + fatigue = Mumps
- fever + mouth sores + red rash on hands and feet + loss of appetite = Hand Foot Mouth Disease
- severe watery diarrhea + vomiting + fever + abdominal pain = Rotavirus Diarrhea
- sudden severe joint pain + swollen big toe + red hot joint + limited movement = Gout
- weight loss + rapid heartbeat + increased appetite + nervousness = Hyperthyroidism
- bone pain + muscle weakness + fatigue + depression = Vitamin D Deficiency
- fatigue + weakness + numbness in hands + tingling in feet = B12 Deficiency
- sudden fever + severe joint pain + muscle pain + headache = Chikungunya
- fever + headache + muscle pain + dark eschar at bite site = Scrub Typhus
- prolonged fever + weight loss + enlarged spleen + enlarged liver = Kala-azar
- red eyes + itchy eyes + tearing + discharge from eyes = Conjunctivitis
- dog bite + animal scratch + kutta katna = Rabies Prophylaxis
- mood swings + manic episodes + depressive episodes + high energy = Bipolar Disorder
- hallucinations + delusions + disorganized thinking + lack of emotion = Schizophrenia
- difficulty falling asleep + waking up during night + waking up early + feeling tired = Insomnia
- fever + dry cough + loss of taste + loss of smell = COVID-19 (Mild)
- excessive worry + restlessness + palpitations + insomnia = Generalized Anxiety Disorder
- irregular periods + missed periods + facial hair + acne = Polycystic Ovary Syndrome (PCOS)
- heartburn + acid reflux + chest burning + sour taste = Gastroesophageal Reflux Disease (GERD)
- sadness + hopelessness + loss of interest + fatigue = Clinical Depression
- knee pain + joint pain + stiffness in morning + crackling sound in joints = Osteoarthritis
- fatigue + pain in upper right abdomen + weakness + unexplained weight loss = Non-Alcoholic Fatty Liver Disease (NAFLD)
- abdominal pain + cramping + bloating + gas = Irritable Bowel Syndrome (IBS)
- sneezing + runny nose + stuffy nose + itchy nose = Allergic Rhinitis
- bleeding during bowel movement + itching around anus + pain during stool + lump near anus = Hemorrhoids (Piles)
"""


def check_vital_alarms(patient: dict) -> list:
    if not patient:
        return []
    alarms = []
    if sys := patient.get('bp_systolic'):
        try:
            if float(sys) > 140: alarms.append(f"High Systolic BP ({sys})")
            if float(sys) < 90: alarms.append(f"Low Systolic BP ({sys})")
        except (ValueError, TypeError): pass
    if dia := patient.get('bp_diastolic'):
        try:
            if float(dia) > 90: alarms.append(f"High Diastolic BP ({dia})")
            if float(dia) < 60: alarms.append(f"Low Diastolic BP ({dia})")
        except (ValueError, TypeError): pass
    if temp := patient.get('temperature_f'):
        try:
            if float(temp) > 99.5: alarms.append(f"Fever ({temp}°F)")
            if float(temp) < 95.0: alarms.append(f"Hypothermia ({temp}°F)")
        except (ValueError, TypeError): pass
    return alarms


def _validate_prescription(result: dict) -> list:
    """
    Catch the exact failure mode reported in production: a system collapsing
    to a single medicine, or a missing system entirely. Returns a list of
    human-readable issues (empty list = valid).
    """
    issues = []
    if not isinstance(result, dict):
        return ["result is not a dict"]
    for sys_name in ("allopathy", "ayurveda", "homeopathy"):
        sys_block = result.get(sys_name)
        if not isinstance(sys_block, dict):
            issues.append(f"{sys_name}: section missing entirely")
            continue
        meds = sys_block.get("medicines", [])
        if not isinstance(meds, list) or len(meds) < 2:
            issues.append(f"{sys_name}: only {len(meds) if isinstance(meds, list) else 0} medicine(s) (need >= 2)")
    return issues


def generate_prescription(symptoms: str, patient: dict = None,
                           report: dict = None) -> dict:
    """
    symptoms + optional vitals + optional report → full prescription (all 3 systems).
    ONE LLM call only.
    """
    emr = detect_emergency(symptoms)
    if emr:
        return {"emergency": emr, "abort": True}

    pctx       = _profile_ctx(patient)
    vitals_ctx = _vitals_ctx(patient)
    report_ctx = _report_context(report)
    regional   = _regional_alert(patient)
    allergies  = ", ".join((patient or {}).get("allergies", []) or ["None"])
    is_veg     = (patient or {}).get("dietary_pref", "") in ("Vegetarian", "Vegan")

    # Try semantic search first with increased top_k to fetch more medicine variations
    rag_context = retrieve_rag_context(symptoms, top_k=10)
    
    # ALWAYS run keyword symptom match — use as additional signal alongside RAG
    matched = search_by_symptom(symptoms)
    kb_hint = ""
    if matched:
        # Rank by number of matching symptoms (best match first)
        symptoms_lower = symptoms.lower()
        words = [w for w in symptoms_lower.replace(',', ' ').replace('.', ' ').split() if len(w) > 2]
        scored = []
        for key in matched:
            d = DISEASES.get(key, {})
            d_symptoms = d.get("symptoms", [])
            # Calculate score using both substring and word matching
            match_count = 0
            for s in d_symptoms:
                if s == symptoms_lower:
                    match_count += 10 # very high weight for exact match
                elif s in symptoms_lower or symptoms_lower in s:
                    match_count += 2  # higher weight for full phrase match
                elif any(w == s for w in words):
                    match_count += 2  # exact single word match
                elif any(w in s or s in w for w in words):
                    match_count += 1  # lower weight for partial word match
            
            if match_count > 0:
                scored.append((match_count, key, d.get("name", key)))
        scored.sort(key=lambda x: -x[0])  # highest match count first
        matched = [key for _, key, _ in scored]  # reorder matched by score for fallback
        
        top_matches = [f"{name} ({cnt} symptoms matched)" for cnt, key, name in scored[:3]]
        kb_hint = f"\nKB symptom matches (ranked by match count): {', '.join(top_matches)}"
        
        if scored:
            best_key = scored[0][1]
            best_disease = DISEASES.get(best_key, {})
            kb_hint += f"\n\n=== VERIFIED MEDICINES FOR '{best_disease.get('name', best_key)}' ==="
            kb_hint += "\nYou MUST use these exact medicines (not the JSON schema examples) in your response:\n"
            for sys_name in ["allopathy", "ayurveda", "homeopathy"]:
                meds = best_disease.get(sys_name, {}).get("medicines", [])
                if meds:
                    kb_hint += f"\n{sys_name.upper()} MEDICINES:\n"
                    for i, m in enumerate(meds, 1):
                        kb_hint += f"  {i}. {m.get('name', '?')}"
                        if m.get('brand'):  kb_hint += f" (Brand: {m['brand']})"
                        if m.get('dose'):   kb_hint += f" | Dose: {m['dose']}"
                        if m.get('freq') or m.get('frequency'):  kb_hint += f" | Freq: {m.get('freq') or m.get('frequency')}"
                        if m.get('dur') or m.get('duration'):    kb_hint += f" | Duration: {m.get('dur') or m.get('duration')}"
                        if m.get('timing'): kb_hint += f" | Timing: {m['timing']}"
                        if m.get('purpose') or m.get('keynote'): kb_hint += f" | Purpose: {m.get('purpose') or m.get('keynote')}"
                        if m.get('price_inr'): kb_hint += f" | ₹{m['price_inr']}"
                        kb_hint += "\n"
                # Also include diet if available
                diet = best_disease.get(sys_name, {}).get("diet", []) or best_disease.get(sys_name, {}).get("home_remedies", []) or best_disease.get(sys_name, {}).get("diet_recommendations", [])
                if diet:
                    kb_hint += f"  Diet: {', '.join(diet[:4])}\n"
                    
        logger.info("KB MATCH: %s", kb_hint.strip())

    prompt = f"""
{pctx}
{vitals_ctx}
{report_ctx}
{f"Regional: {regional}" if regional else ""}
{rag_context}
{kb_hint}

PATIENT SYMPTOMS: {symptoms}

Return this EXACT JSON:
{{
  "vital_alarms": [],
  "primary_diagnosis": "Disease name",
  "icd10": "ICD-10 code",
  "confidence": 82,
  "diagnosis_reasoning": "Why this fits symptoms + vitals",
  "severity": "Mild|Moderate|Severe",
  "differential": [
    {{"diagnosis": "Second", "likelihood": "Low|Medium", "reason": "brief"}}
  ],
  "red_flags": ["See doctor immediately if..."],
  "allopathy": {{
    "medicines": [
      {{
        "name": "[Primary drug from VERIFIED MEDICINES above]",
        "brand": "[Indian brand]",
        "category": "[Drug class]",
        "dose": "[exact dose]",
        "frequency": "[how often]",
        "duration": "[how long]",
        "timing": "[before/after food]",
        "purpose": "[why this drug]",
        "price_inr": 0,
        "generic_mrp": 0,
        "warnings": "[key warning]",
        "is_otc": true
      }},
      {{
        "name": "[Secondary/supportive drug from VERIFIED MEDICINES]",
        "brand": "[Indian brand]",
        "category": "[Drug class]",
        "dose": "[exact dose]",
        "frequency": "[how often]",
        "duration": "[how long]",
        "timing": "[when to take]",
        "purpose": "[why this drug]",
        "price_inr": 0,
        "generic_mrp": 0,
        "warnings": "[key warning]",
        "is_otc": true
      }}
    ],
    "tests_to_order": ["[relevant test 1]", "[relevant test 2]"],
    "avoid": ["[contraindicated drug 1]"],
    "total_cost_inr": 0
  }},
  "ayurveda": {{
    "dosha": "Pitta|Vata|Kapha",
    "medicines": [
      {{
        "name": "[Use AYURVEDA MEDICINE 1 from VERIFIED MEDICINES above — NOT Giloy Ghanvati unless genuinely indicated]",
        "brand": "[Exact brand from VERIFIED MEDICINES]",
        "category": "[category]",
        "dose": "[dose from VERIFIED MEDICINES]",
        "frequency": "[freq from VERIFIED MEDICINES]",
        "duration": "[duration from VERIFIED MEDICINES]",
        "timing": "[timing from VERIFIED MEDICINES]",
        "purpose": "[purpose from VERIFIED MEDICINES]",
        "preparation": "[how to prepare]",
        "price_inr": 0,
        "vegetarian": true
      }},
      {{
        "name": "[Use AYURVEDA MEDICINE 2 from VERIFIED MEDICINES above]",
        "brand": "[brand]",
        "category": "[category]",
        "dose": "[dose]",
        "frequency": "[freq]",
        "duration": "[duration]",
        "timing": "[timing]",
        "purpose": "[purpose]",
        "preparation": "[how to prepare]",
        "price_inr": 0,
        "vegetarian": true
      }}
    ],
    "diet_recommendations": ["[diet tip 1]", "[diet tip 2]"],
    "foods_to_avoid": ["[avoid 1]", "[avoid 2]"],
    "total_cost_inr": 0
  }},
  "homeopathy": {{
    "medicines": [
      {{
        "name": "[Use HOMEOPATHY MEDICINE 1 from VERIFIED MEDICINES above — NOT Eupatorium unless genuinely indicated]",
        "potency": "[potency from VERIFIED MEDICINES]",
        "brand": "[brand from VERIFIED MEDICINES]",
        "dose": "[dose from VERIFIED MEDICINES]",
        "frequency": "[freq from VERIFIED MEDICINES]",
        "duration": "[duration from VERIFIED MEDICINES]",
        "timing": "[timing]",
        "purpose": "[purpose from VERIFIED MEDICINES]",
        "keynote": "[keynote from VERIFIED MEDICINES]",
        "price_inr": 0
      }},
      {{
        "name": "[Use HOMEOPATHY MEDICINE 2 from VERIFIED MEDICINES above]",
        "potency": "[potency]",
        "brand": "[brand]",
        "dose": "[dose]",
        "frequency": "[freq]",
        "duration": "[duration]",
        "timing": "[timing]",
        "purpose": "[purpose]",
        "keynote": "[keynote]",
        "price_inr": 0
      }}
    ],
    "diet_recommendations": ["[diet tip 1]", "[diet tip 2]"],
    "avoid": ["Coffee", "Camphor", "Mint"],
    "total_cost_inr": 0
  }},
  "vitals_interpretation": "Brief clinical note on BP/temperature if abnormal",
  "general_advice": {{
    "diet": "Specific diet",
    "hydration": "Fluids required",
    "rest": "Rest needed",
    "follow_up": "When to see doctor"
  }},
  "disclaimer": "AI-generated. Verify with a qualified physician."
}}

CRITICAL ACCURACY RULES:
- Leave "vital_alarms" empty [] unless the patient's vitals provided in the context are actually abnormal. Do NOT hallucinate alerts.
- Allergies to exclude: {allergies}
- Vegetarian (Ayurveda): {is_veg}
- CRITICAL: Copy the medicine names, doses, brands, and details DIRECTLY from the "VERIFIED MEDICINES" section above into the JSON fields. Do NOT invent or substitute different Ayurvedic/Homeopathic medicines — the verified list is your prescribing source.
- When treating fever, use Paracetamol 650mg. NEVER use Aspirin/Ibuprofen due to dengue hemorrhage risk.
- For bacterial infection (pus, productive cough, high fever >3 days): specific antibiotic.
- For viral fever (most fevers) or common cold: NO antibiotics. ALWAYS prescribe Paracetamol for fever/body ache ALONGSIDE other supportive medicines (like Cetirizine/Ambroxol/syrups) for cold and cough symptoms.
- For high BP: note Amlodipine/Telmisartan in general_advice, do NOT add cardiac meds unless HTN is confirmed.
- For fever > 38.5°C: mark severity as Moderate minimum.
- Set confidence = 85+ only if 4+ symptoms clearly match the diagnosis.
- Set confidence = 60-80 if 2-3 symptoms match.
- Set confidence = 40-60 if symptoms are vague or only 1-2 match.
"""

    result = llm_engine.generate_json(prompt, SYSTEM_PROMPT)
    if not result:
        result = _kb_fallback(symptoms, matched, patient)
    else:
        issues = _validate_prescription(result)
        if issues and matched:
            logger.warning("Prescription validation issues: %s — patching from local KB", "; ".join(issues))
            fallback_disease = DISEASES.get(matched[0], {})
            for sys_name in ("allopathy", "ayurveda", "homeopathy"):
                sys_block = result.get(sys_name)
                meds = sys_block.get("medicines", []) if isinstance(sys_block, dict) else []
                if not isinstance(sys_block, dict) or len(meds) < 2:
                    fb_sys = fallback_disease.get(sys_name, {})
                    if fb_sys and fb_sys.get("medicines"):
                        # Normalize short keys
                        fb_meds = []
                        for m in fb_sys["medicines"]:
                            nm = dict(m)
                            if "freq" in nm and "frequency" not in nm: nm["frequency"] = nm.pop("freq")
                            if "dur" in nm and "duration" not in nm: nm["duration"] = nm.pop("dur")
                            if "warn" in nm and "warnings" not in nm: nm["warnings"] = nm.pop("warn")
                            fb_meds.append(nm)
                        if not isinstance(sys_block, dict):
                            result[sys_name] = {"medicines": fb_meds}
                        else:
                            result[sys_name]["medicines"] = fb_meds
                        logger.info("Patched %s with %d medicines from local KB", sys_name, len(fb_meds))

        result = _enrich_prices(result)
        result["symptoms_input"] = symptoms
        result["generated_at"]   = datetime.now().isoformat()
        result["source"]         = "llm"

    # Inject Deterministic Vital Alarms
    if patient:
        alarms = check_vital_alarms(patient)
        if alarms:
            # Merge with LLM generated alarms if any, ensuring uniqueness
            existing_alarms = result.get("vital_alarms", [])
            result["vital_alarms"] = list(set(existing_alarms + alarms))

    return result


def _kb_fallback(symptoms: str, matched: list, patient: dict) -> dict:
    """Build prescription from local knowledge base when LLM is unavailable."""
    if not matched:
        return {"error": "AI unavailable and no local match.",
                "primary_diagnosis": "Unknown",
                "allopathy": {"medicines": []},
                "ayurveda":  {"medicines": []},
                "homeopathy":{"medicines": []},
                "symptoms_input": symptoms}

    disease = DISEASES[matched[0]]

    def _normalize_meds(meds_list: list) -> list:
        """Map KB short keys (freq, dur) to full keys (frequency, duration)."""
        normalized = []
        for m in meds_list:
            nm = dict(m)  # copy
            # Map short keys → full keys expected by app.py and pdf_report.py
            if "freq" in nm and "frequency" not in nm:
                nm["frequency"] = nm.pop("freq")
            if "dur" in nm and "duration" not in nm:
                nm["duration"] = nm.pop("dur")
            if "warn" in nm and "warnings" not in nm:
                nm["warnings"] = nm.pop("warn")
            normalized.append(nm)
        return normalized

    def _normalize_system(sys_data: dict) -> dict:
        """Normalize an entire system (allopathy/ayurveda/homeopathy) block."""
        if not sys_data:
            return {"medicines": []}
        result = dict(sys_data)
        result["medicines"] = _normalize_meds(result.get("medicines", []))
        # Map KB field names → what app.py and pdf_report.py expect
        if "home_remedies" in result and "diet_recommendations" not in result:
            result["diet_recommendations"] = result["home_remedies"]
        if "diet" in result and "diet_recommendations" not in result:
            result["diet_recommendations"] = result["diet"]
        if "tests" in result and "tests_to_order" not in result:
            result["tests_to_order"] = result["tests"]
        return result


    def _calculate_confidence(syms_input: str, dis: dict) -> int:
        us = [s.strip().lower() for s in syms_input.replace(',', ' ').split() if len(s) > 2]
        ds = [s.lower() for s in dis.get("symptoms", [])]
        matches = 0
        for u in us:
            if any(u in d or d in u for d in ds):
                matches += 1
        if matches >= 4: return 85
        if matches >= 2: return 75
        if matches == 1: return 60
        return 50

    return {
        "primary_diagnosis": disease["name"],
        "icd10": disease.get("icd10", ""),
        "confidence": _calculate_confidence(symptoms, disease),
        "diagnosis_reasoning": f"Matched from local knowledge base (offline mode). "
                               f"AI was unavailable — this prescription uses verified ICMR/AYUSH data.",
        "severity": "Moderate",
        "allopathy":  _normalize_system(disease.get("allopathy",  {})),
        "ayurveda":   _normalize_system(disease.get("ayurveda",   {})),
        "homeopathy": _normalize_system(disease.get("homeopathy", {})),
        "red_flags": disease.get("red_flags", []),
        "general_advice": {"diet": disease.get("dietary", ""),
                           "follow_up": "See doctor if no improvement in 3 days"},
        "source": "local_kb",
        "symptoms_input": symptoms,
        "generated_at": datetime.now().isoformat(),
    }


def _enrich_prices(result: dict) -> dict:
    for sys in ("allopathy", "ayurveda", "homeopathy"):
        for med in result.get(sys, {}).get("medicines", []):
            if med.get("price_inr"):
                continue
            pdata = get_price(med.get("name", ""))
            if pdata:
                med["price_inr"]   = pdata.get("brand_mrp")
                med["generic_mrp"] = pdata.get("generic_mrp")
                if not med.get("brand"):
                    med["brand"] = pdata.get("brand", "")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. DRUG INTERACTION CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_interactions(medicines: list) -> list:
    """Check drug interactions using LOCAL database only (no API call)."""
    found = []
    ml = [m.lower() for m in medicines]
    for inter in INTERACTIONS:
        d1l, d2l = inter["d1"].lower(), inter["d2"].lower()
        if any(d1l in m for m in ml) and any(d2l in m for m in ml):
            found.append(inter)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# 5. PRICE SCRAPING
# ─────────────────────────────────────────────────────────────────────────────

def scrape_price(medicine: str) -> list:
    import requests as req, re, time
    from bs4 import BeautifulSoup
    HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36"}
    results = []
    try:
        url = f"https://www.1mg.com/search/all?name={req.utils.quote(medicine)}"
        r = req.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for sel in ["[class*='price-tag']", "[class*='Price']", "[class*='price']"]:
                for el in soup.select(sel)[:3]:
                    price = _parse_price(el.get_text())
                    if price:
                        results.append({"platform":"1mg","price":price,"url":url,"type":"brand"})
                if results: break
    except Exception as e:
        logger.debug("1mg scrape: %s", e)

    time.sleep(0.8)
    try:
        url = f"https://pharmeasy.in/search/all?name={req.utils.quote(medicine)}"
        r = req.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for sel in ["[class*='discountedPrice']", "[class*='price']"]:
                for el in soup.select(sel)[:3]:
                    price = _parse_price(el.get_text())
                    if price:
                        results.append({"platform":"PharmEasy","price":price,"url":url,"type":"brand"})
                if results: break
    except Exception as e:
        logger.debug("PharmEasy: %s", e)

    if not results:
        pdata = get_price(medicine)
        if pdata:
            results.append({"platform": pdata.get("brand","Brand"),
                             "price": pdata.get("brand_mrp",0), "url":"", "type":"brand"})
            results.append({"platform":"Generic",
                             "price": pdata.get("generic_mrp",0), "url":"", "type":"generic"})

    results.sort(key=lambda x: x.get("price",9999))
    return [r for r in results if r.get("price",0) > 0]


def _parse_price(text: str):
    import re
    text = text.replace(",", "")
    m = re.search(r'[\₹Rs\s]*(\d+(?:\.\d{1,2})?)', text)
    if m:
        try:
            p = float(m.group(1))
            if 1 < p < 5000: return p
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _profile_ctx(p: dict) -> str:
    if not p:
        return "Patient: profile not provided."
    bmi = ""
    try:
        h = float(p.get("height_cm") or 0)
        w = float(p.get("weight_kg") or 0)
        if h > 0 and w > 0:
            bmi = f", BMI {w / (h/100)**2:.1f}"
    except Exception:
        pass
    return (
        f"Patient: {p.get('name','?')}, {p.get('age','?')}yr, "
        f"{p.get('gender','?')}, {p.get('weight_kg','?')}kg{bmi}. "
        f"Conditions: {', '.join(p.get('conditions',[]) or ['None'])}. "
        f"Allergies: {', '.join(p.get('allergies',[]) or ['None'])}. "
        f"Meds: {', '.join(p.get('current_meds',[]) or ['None'])}. "
        f"Diet: {p.get('dietary_pref','unknown')}."
    )


def _vitals_ctx(p: dict) -> str:
    """Format current vitals as clinical context."""
    if not p:
        return ""
    parts = []
    sys_bp  = p.get("bp_systolic")
    dia_bp  = p.get("bp_diastolic")
    temp    = p.get("temperature_c")

    if sys_bp and dia_bp:
        bp_str = f"BP: {sys_bp}/{dia_bp} mmHg"
        if sys_bp >= 180 or dia_bp >= 110:
            bp_str += " ⚠️ HYPERTENSIVE CRISIS"
        elif sys_bp >= 140 or dia_bp >= 90:
            bp_str += " (Stage 2 Hypertension)"
        elif sys_bp >= 130 or dia_bp >= 80:
            bp_str += " (Stage 1 Hypertension)"
        elif sys_bp < 90 or dia_bp < 60:
            bp_str += " ⚠️ HYPOTENSION"
        parts.append(bp_str)

    if temp:
        temp_str = f"Temperature: {temp}°C"
        if temp >= 40.0:
            temp_str += " ⚠️ HYPERPYREXIA"
        elif temp >= 38.5:
            temp_str += " (High Fever)"
        elif temp >= 37.5:
            temp_str += " (Low-grade Fever)"
        elif temp < 36.0:
            temp_str += " ⚠️ HYPOTHERMIA"
        parts.append(temp_str)

    if not parts:
        return ""
    return "Current Vitals: " + " | ".join(parts)


def _report_context(report: dict) -> str:
    if not report or not report.get("findings"):
        return ""
    abnormal = [f for f in report["findings"]
                if f.get("status", "").lower() not in ("normal", "")]
    conditions = report.get("likely_conditions", [])
    parts = []
    if abnormal:
        parts.append(f"Report abnormal: {json.dumps(abnormal[:5])}")
    if conditions:
        parts.append(f"Report suggests: {', '.join(conditions[:3])}")
    return "\n".join(parts)


def _regional_alert(p: dict) -> str:
    if not p or not p.get("state"):
        return ""
    month    = datetime.now().month
    diseases = config.SEASONAL.get(p["state"], {}).get(month, [])
    if diseases:
        return f"{', '.join(diseases)} season in {p['state']} ({datetime.now().strftime('%B')})"
    return ""


def get_medicine_details(drug_name: str) -> dict:
    """Fetch structured pharmacological details from the offline database."""
    try:
        from data.drug_db import DRUGS
    except ImportError:
        DRUGS = {}

    query = drug_name.lower().strip()
    
    # 1. Direct Salt Match
    if query in DRUGS:
        res = dict(DRUGS[query])
        res["query"] = drug_name
        return res
        
    # 2. Search inside Brands and partial salt names
    for salt_key, data in DRUGS.items():
        # Check if query matches a known brand
        brands = [b.lower() for b in data.get("popular_indian_brands", [])]
        if any(query in b or b in query for b in brands):
            res = dict(data)
            res["query"] = drug_name
            return res
            
        # Check if query is a partial match to the long generic salt name
        if query in data.get("generic_salt", "").lower():
            res = dict(data)
            res["query"] = drug_name
            return res

    # 3. Search in SQLite Database
    import database as db
    db_result = db.search_medicines(drug_name)
    if db_result:
        db_result["query"] = drug_name
        return db_result

    # 4. Fallback if not found (Strict Offline Mode)
    return {
        "query": drug_name,
        "generic_salt": "Unknown / Not in Local DB",
        "drug_class": "N/A",
        "primary_uses": ["Information not available offline."],
        "mechanism_of_action": "The requested medicine is not present in the current offline database. Please update the local database.",
        "common_side_effects": ["N/A"],
        "contraindications": ["N/A"],
        "popular_indian_brands": [],
        "safety_advice": "Consult your doctor or check physical drug packaging for details.",
        "error": "Not found in local offline database."
    }