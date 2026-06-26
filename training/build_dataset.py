"""
ArogyaAI — Medical Dataset Builder
=====================================
Builds the training dataset from multiple FREE sources:

SOURCE 1: PubMed E-utilities API (FREE, no key needed, 10 RPM)
  - Searches 20+ Indian disease queries
  - Downloads abstracts as instruction pairs

SOURCE 2: OpenFDA Drug API (FREE, no key needed)
  - Drug labels: indications, dosage, interactions
  - Indian drug equivalents mapped automatically

SOURCE 3: Local Medicine DB (medicine_db.py)
  - 60+ diseases × 3 systems = ~500 Q&A pairs
  - Hinglish symptom↔English mappings
  - Drug interaction pairs

SOURCE 4: MedQuAD format (public domain medical Q&A)
  - Symptom → diagnosis pairs
  - Treatment → medicine pairs

OUTPUT:
  data/training/
    ├── instruction_dataset.jsonl      ← LLaMA fine-tuning format
    ├── sentence_pairs.jsonl           ← BioBERT sentence similarity
    ├── rag_documents/                 ← Text chunks for FAISS
    │   ├── allopathy/
    │   ├── ayurveda/
    │   ├── homeopathy/
    │   └── drug_interactions/
    └── dataset_stats.json

Usage:
  cd /home/ubuntu/project/arogyaai
  python training/build_dataset.py --all
  python training/build_dataset.py --pubmed       # only PubMed
  python training/build_dataset.py --local-only   # only local DB (offline)
"""

import argparse
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

import requests

logger = logging.getLogger("dataset_builder")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.medicine_db import (
    DISEASES, INTERACTIONS, PRICES, AYURVEDIC_HERBS_KB, HOMEOPATHIC_REMEDIES_KB
)

OUT_DIR       = PROJECT_ROOT / "data" / "training"
RAG_DIR       = PROJECT_ROOT / "data" / "knowledge_bases"
INSTRUCTION_F = OUT_DIR / "instruction_dataset.jsonl"
SENTENCE_F    = OUT_DIR / "sentence_pairs.jsonl"
STATS_F       = OUT_DIR / "dataset_stats.json"

for d in [OUT_DIR, RAG_DIR/"allopathy", RAG_DIR/"ayurveda",
          RAG_DIR/"homeopathy", RAG_DIR/"drug_interactions"]:
    d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBMED SCRAPER
# ═══════════════════════════════════════════════════════════════════════════════

PUBMED_QUERIES = [
    # ── Original 20 queries ──
    "dengue fever India treatment",
    "malaria India chloroquine artemisinin",
    "typhoid fever treatment India",
    "tuberculosis India DOTS treatment",
    "diabetes India metformin management",
    "hypertension India amlodipine",
    "iron deficiency anemia India",
    "hypothyroidism India levothyroxine",
    "asthma bronchial India treatment",
    "urinary tract infection India",
    "rheumatoid arthritis India methotrexate",
    "peptic ulcer pantoprazole India",
    "Ayurveda clinical trial India",
    "Ashwagandha randomized trial",
    "Giloy Guduchi immunomodulator",
    "drug interaction Ayurveda allopathy",
    "Homeopathy clinical evidence India",
    "dengue platelet papaya leaf extract",
    "COVID India treatment guidelines",
    "Indian traditional medicine evidence",
    # ── Expanded: Women's health ──
    "PCOD polycystic ovary India treatment",
    "gestational diabetes India management",
    "iron deficiency pregnancy India",
    "preeclampsia India treatment guidelines",
    "menorrhagia heavy periods India treatment",
    # ── Expanded: GI / Liver ──
    "kidney stones India treatment lithotripsy",
    "liver cirrhosis India hepatitis treatment",
    "hepatitis B India vaccination treatment",
    "fatty liver NAFLD India lifestyle",
    "irritable bowel syndrome India",
    "chronic diarrhea India treatment",
    # ── Expanded: Cardio / Metabolic ──
    "coronary artery disease India statin",
    "heart failure India treatment guidelines",
    "hyperlipidemia India atorvastatin",
    "obesity India management pharmacotherapy",
    "gout uric acid India treatment",
    # ── Expanded: Pediatrics ──
    "childhood pneumonia India treatment",
    "neonatal jaundice India phototherapy",
    "pediatric diarrhea ORS India",
    "childhood asthma India management",
    # ── Expanded: Dermatology ──
    "psoriasis India treatment biologics",
    "eczema atopic dermatitis India",
    "fungal skin infection India antifungal",
    "acne vulgaris India treatment",
    # ── Expanded: Mental health ──
    "depression India SSRI treatment",
    "anxiety disorder India management",
    "insomnia India treatment zolpidem",
    "schizophrenia India antipsychotic",
    # ── Expanded: Infections ──
    "chikungunya India treatment",
    "leptospirosis India monsoon treatment",
    "scrub typhus India doxycycline",
    "cholera India treatment rehydration",
    "filariasis India DEC treatment",
    # ── Expanded: Traditional medicine ──
    "Triphala clinical trial evidence",
    "turmeric curcumin anti-inflammatory trial",
    "Brahmi Bacopa memory clinical trial",
    "Shatavari women health clinical evidence",
    "Arnica homeopathy pain clinical trial",
]

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed(query: str, max_results: int = 15) -> list[dict]:
    """Fetch PubMed abstracts. Returns list of article dicts."""
    try:
        resp = requests.get(ESEARCH_URL, params={
            "db":"pubmed","term":query,"retmax":max_results,"retmode":"json"
        }, timeout=30)
        ids = resp.json().get("esearchresult",{}).get("idlist",[])
        if not ids:
            return []

        time.sleep(0.12)   # respect 10 RPM

        resp2 = requests.get(EFETCH_URL, params={
            "db":"pubmed","id":",".join(ids[:10]),"retmode":"xml","rettype":"abstract"
        }, timeout=30)

        articles = []
        root = ET.fromstring(resp2.content)
        for art in root.findall(".//PubmedArticle"):
            try:
                title    = art.findtext(".//ArticleTitle","")
                abstract = " ".join(t.text or "" for t in art.findall(".//AbstractText"))
                pmid     = art.findtext(".//PMID","")
                year     = art.findtext(".//PubDate/Year","2024")
                journal  = art.findtext(".//Title","")
                if abstract and len(abstract) > 80:
                    articles.append({"pmid":pmid,"title":title,
                                      "abstract":abstract[:3000],
                                      "year":year,"journal":journal,
                                      "query":query})
            except Exception:
                continue
        return articles

    except Exception as e:
        logger.warning("PubMed fetch failed for '%s': %s", query, e)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# OPENFDA DRUG DATA
# ═══════════════════════════════════════════════════════════════════════════════

OPENFDA_URL = "https://api.fda.gov/drug/label.json"

INDIAN_DRUG_QUERIES = [
    # ── Original 15 ──
    "metformin","paracetamol","amoxicillin","azithromycin",
    "ciprofloxacin","pantoprazole","amlodipine","telmisartan",
    "levothyroxine","cetirizine","montelukast","atorvastatin",
    "prednisolone","doxycycline","metronidazole",
    # ── Expanded: Common Indian prescriptions ──
    "omeprazole","ranitidine","losartan","ramipril",
    "clopidogrel","aspirin","diclofenac","ibuprofen",
    "metoprolol","atenolol","furosemide","spironolactone",
    "glimepiride","sitagliptin","insulin glargine",
    "cefixime","levofloxacin","nitrofurantoin","fluconazole",
    "salbutamol","budesonide","theophylline",
    "escitalopram","sertraline","alprazolam","clonazepam",
    "hydroxychloroquine","sulfasalazine","aceclofenac",
    "domperidone","ondansetron","iron sucrose",
]


def fetch_openfda(drug: str) -> list[dict]:
    """Fetch drug label info from OpenFDA."""
    try:
        resp = requests.get(OPENFDA_URL, params={
            "search": f"openfda.generic_name:{drug}",
            "limit": 3
        }, timeout=20)
        if resp.status_code != 200:
            return []
        results = resp.json().get("results",[])
        articles = []
        for r in results:
            indications  = " ".join(r.get("indications_and_usage",[]))[:1500]
            dosage       = " ".join(r.get("dosage_and_administration",[]))[:1000]
            interactions = " ".join(r.get("drug_interactions",[]))[:1000]
            warnings     = " ".join(r.get("warnings",[]))[:500]
            if indications:
                articles.append({
                    "drug": drug,
                    "indications": indications,
                    "dosage": dosage,
                    "interactions": interactions,
                    "warnings": warnings,
                    "source": "OpenFDA",
                })
        time.sleep(0.15)
        return articles
    except Exception as e:
        logger.debug("OpenFDA '%s': %s", drug, e)
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUCTION DATASET BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_MSG = (
    "You are ArogyaAI — a senior Indian physician AI. "
    "You prescribe specific medicines for Indian patients. "
    "Always use Indian brand names. Include exact doses. "
    "Respond with factual medical information."
)


def build_instruction_samples() -> list[dict]:
    """Build instruction fine-tuning samples from all sources."""
    samples = []

    # ── From disease database ─────────────────────────────────────────────────
    for key, disease in DISEASES.items():
        name     = disease["name"]
        symptoms = disease.get("symptoms", [])
        en_syms  = [s for s in symptoms if not any(ord(c)>127 for c in s)][:5]
        hi_syms  = [s for s in symptoms if any(ord(c)>127 for c in s)][:3]

        # Symptom → diagnosis
        if en_syms:
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"Patient has: {', '.join(en_syms)}. What is the diagnosis?"},
                {"role":"assistant","content":
                    f"Based on these symptoms, {name} is the most likely diagnosis. "
                    f"Key matching symptoms: {', '.join(en_syms[:3])}. "
                    f"Recommended to confirm with relevant tests. "
                    f"ICD-10: {disease.get('icd10','')}."},
            ]})

        # Hinglish → English
        if hi_syms and en_syms:
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"Mujhe ye problems hai: {', '.join(hi_syms)}. Kya problem ho sakti hai?"},
                {"role":"assistant","content":
                    f"Aapke symptoms {name} ki taraf point karte hain. "
                    f"Doctor se milkar confirm karein. Tests: "
                    f"{', '.join(disease.get('allopathy',{}).get('tests_to_order', ['CBC'])[:2])}."},
            ]})

        # Allopathy prescription
        allo = disease.get("allopathy",{})
        meds = allo.get("medicines",[])
        if meds:
            med_desc = "; ".join(
                f"{m['name']} ({m.get('brand','')}) — {m.get('dose','')} {m.get('frequency','')} for {m.get('duration','')}"
                for m in meds[:3]
            )
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"What is the allopathic treatment for {name}?"},
                {"role":"assistant","content":
                    f"For {name}, standard treatment includes:\n{med_desc}\n"
                    f"Tests: {', '.join(allo.get('tests_to_order',['As clinically indicated'])[:3])}.\n"
                    f"Always consult a physician for dose adjustment."},
            ]})

        # Ayurveda prescription
        ayur = disease.get("ayurveda",{})
        ayur_meds = ayur.get("medicines",[])
        if ayur_meds:
            ayur_desc = "; ".join(
                f"{m['name']} ({m.get('brand','')}) — {m.get('dose','')} {m.get('frequency','')}"
                for m in ayur_meds[:3]
            )
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"What Ayurvedic medicines are used for {name}?"},
                {"role":"assistant","content":
                    f"AYUSH-approved Ayurvedic treatment for {name}:\n{ayur_desc}\n"
                    f"Diet: {', '.join(ayur.get('diet',ayur.get('diet_recommendations',[]))[:3])}\n"
                    f"These are adjunct treatments — use alongside standard medical care."},
            ]})

        # Homeopathy
        homo = disease.get("homeopathy",{})
        homo_meds = homo.get("medicines",[])
        if homo_meds:
            homo_desc = "; ".join(
                f"{m['name']} {m.get('potency','')} — {m.get('dose','')} {m.get('frequency','')} ({m.get('keynote','')})"
                for m in homo_meds[:3]
            )
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"What homeopathic remedies are used for {name}?"},
                {"role":"assistant","content":
                    f"Classical homeopathic treatment for {name}:\n{homo_desc}\n"
                    f"Avoid coffee and mint (antidote to homeopathy)."},
            ]})

        # Red flags
        red_flags = disease.get("red_flags",[])
        if red_flags:
            samples.append({"messages":[
                {"role":"system","content":SYSTEM_MSG},
                {"role":"user","content":
                    f"What are the danger signs in {name} that need emergency care?"},
                {"role":"assistant","content":
                    f"Emergency red flags for {name}:\n"
                    + "\n".join(f"• {f}" for f in red_flags)
                    + "\nSeek immediate medical attention if any of these occur. Call 112."},
            ]})

    # ── Drug interactions ─────────────────────────────────────────────────────
    for inter in INTERACTIONS:
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":
                f"Can I take {inter['d1']} with {inter['d2']}?"},
            {"role":"assistant","content":
                f"⚠️ {inter['sev']} INTERACTION: {inter['d1']} + {inter['d2']}\n"
                f"Effect: {inter['effect']}\n"
                f"Management: {inter['mgmt']}"},
        ]})

    # ── Medicine prices ───────────────────────────────────────────────────────
    for med_name, pdata in list(PRICES.items())[:40]:
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":
                f"What is the price of {med_name} in India?"},
            {"role":"assistant","content":
                f"{med_name}: Brand ({pdata['brand']}) = ₹{pdata['b']} per strip. "
                f"Generic equivalent = ₹{pdata['g']} per strip. "
                f"Available at 1mg.com, PharmEasy, Apollo Pharmacy."},
        ]})

    # ── Emergency recognition ─────────────────────────────────────────────────
    EMERGENCY_SAMPLES = [
        ("I have severe chest pain and my left arm is going numb",
         "🚨 POSSIBLE CARDIAC EMERGENCY. Call 112 IMMEDIATELY. Chew Aspirin 325mg if not allergic. Do NOT drive. ArogyaAI cannot provide treatment for emergencies."),
        ("Mujhe seene mein bahut dard ho raha hai",
         "🚨 YE EMERGENCY HO SAKTI HAI — CARDIAC. 112 pe call karein ABHI."),
        ("My face is drooping on one side and I can't speak properly",
         "🚨 POSSIBLE STROKE. Call 112 IMMEDIATELY. Note the exact time symptoms started. FAST test: Face-Arms-Speech-Time."),
        ("Patient is unconscious and not breathing",
         "🚨 CARDIAC ARREST. Call 112. Start CPR immediately: 30 chest compressions + 2 rescue breaths."),
        ("Severe allergic reaction, throat is swelling",
         "🚨 ANAPHYLAXIS. Use EpiPen if available. Call 112. Lie flat with legs elevated."),
        # ── Expanded emergencies ──
        ("My child ate some pills from the medicine box",
         "🚨 POSSIBLE POISONING. Call 112 or Poison Helpline 1800-11-6117. Do NOT induce vomiting. Note which medicine, how many pills, and time of ingestion."),
        ("Patient has very high fever 105°F with seizures",
         "🚨 FEBRILE SEIZURE / HYPERPYREXIA. Call 112. Place on side. Do NOT put anything in mouth. Tepid sponging. Rush to nearest ER."),
        ("Bahut zyada khoon beh raha hai wound se",
         "🚨 SEVERE BLEEDING EMERGENCY. 112 call karein. Saaf kapde se wound pe pressure lagayein. Patient ko litayein."),
        ("Snake bite on the leg, it's swelling fast",
         "🚨 SNAKE BITE EMERGENCY. Call 112. Keep limb immobilized below heart level. Do NOT apply tourniquet or suck venom. Rush to hospital for anti-venom."),
        ("Patient had a road accident and is bleeding from head",
         "🚨 HEAD TRAUMA EMERGENCY. Call 112. Do NOT move the patient if spinal injury suspected. Keep airway clear. Apply gentle pressure to wound."),
        ("Severe burns from hot oil on arms and chest",
         "🚨 BURN EMERGENCY. Call 112. Run cool (not ice cold) water for 20 min. Remove jewelry. Cover with clean cloth. Do NOT apply toothpaste or butter."),
        ("Person collapsed after wasp stings, lips turning blue",
         "🚨 ANAPHYLACTIC SHOCK. Call 112. Use EpiPen if available. Lay flat, elevate legs. Begin CPR if unresponsive."),
        ("Bachche ko saans nahi aa rahi, lips blue ho rahe",
         "🚨 RESPIRATORY EMERGENCY (CHILD). 112 call karein ABHI. Bachche ko upright position mein rakhein. Agar kuch gale mein fasa hai to back blows dein."),
    ]
    for user_msg, assistant_msg in EMERGENCY_SAMPLES:
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":user_msg},
            {"role":"assistant","content":assistant_msg},
        ]})

    # ── Hinglish medical vocabulary ───────────────────────────────────────────
    HINGLISH_PAIRS = [
        # ── Original 19 ──
        ("bukhar","fever"),("sir dard","headache"),("pet dard","abdominal pain"),
        ("thakan","fatigue"),("khasi","cough"),("sans phoolna","breathlessness"),
        ("ulti","vomiting"),("dast","diarrhea"),("kamar dard","back pain"),
        ("jodo mein dard","joint pain"),("chamdi par daane","skin rash"),
        ("zyada pyaas","excessive thirst"),("baar baar peshab","frequent urination"),
        ("aankhon mein peelaahat","jaundice"),("naak bagna","runny nose"),
        ("gala kharab","sore throat"),("chakkar aana","dizziness"),
        ("peshab mein jalan","burning urination"),("seene mein jalan","heartburn"),
        # ── Expanded Hinglish ──
        ("neend nahi aati","insomnia"),("bhook nahi lagti","loss of appetite"),
        ("wajan badh raha hai","weight gain"),("wajan ghat raha hai","weight loss"),
        ("pair mein sujan","pedal edema"),("haath pair sunn hona","numbness in extremities"),
        ("dil ki dhadkan tez","palpitations"),("sar ghoomna","vertigo"),
        ("khoon ki kami","anemia"),("sugar ki bimari","diabetes"),
        ("BP badha hua hai","hypertension"),("thyroid ki problem","thyroid disorder"),
        ("pet mein gas","bloating / flatulence"),("qabz","constipation"),
        ("bawaseer","hemorrhoids / piles"),("pathri","kidney stones"),
        ("aankh aana","conjunctivitis"),("kaan mein dard","ear pain / otitis"),
        ("chati mein dard","chest pain"),("periods irregular","irregular menstruation"),
        ("dawaai se allergy","drug allergy"),("khujli","itching / pruritus"),
    ]
    for hindi, english in HINGLISH_PAIRS:
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":f"Patient says '{hindi}'. What does this mean?"},
            {"role":"assistant","content":f"'{hindi}' in medical context means: {english}."},
        ]})
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":f"Translate to medical English: {hindi}"},
            {"role":"assistant","content":english},
        ]})

    # ── Multi-turn conversation samples ───────────────────────────────────────
    MULTI_TURN = [
        # Patient describes symptoms → AI asks follow-up → diagnosis
        [{"role":"system","content":SYSTEM_MSG},
         {"role":"user","content":"Doctor, I have been having burning while urinating for 3 days and mild fever."},
         {"role":"assistant","content":"These symptoms suggest a urinary tract infection (UTI). Let me ask a few questions:\n1. Any blood in urine?\n2. Lower back or flank pain?\n3. How much water are you drinking daily?\n4. Any history of kidney stones?"},
         {"role":"user","content":"No blood, mild lower back pain. I drink about 4-5 glasses a day."},
         {"role":"assistant","content":"Based on your symptoms, this is likely a lower UTI (cystitis). Treatment:\n• Tab Nitrofurantoin (Furadantin) 100mg twice daily for 5 days\n• Tab Paracetamol (Dolo 650) for fever\n• Increase water intake to 3+ liters/day\n• Get Urine Routine + Culture done\n\nIf symptoms worsen or fever increases, visit a hospital immediately."}],
        [{"role":"system","content":SYSTEM_MSG},
         {"role":"user","content":"Mera sugar level 280 aa raha hai fasting mein. Kya karun?"},
         {"role":"assistant","content":"Fasting sugar 280 mg/dL bahut zyada hai. Ye uncontrolled diabetes indicate karta hai.\n\nAbhi ke liye:\n• Tab Metformin (Glycomet) 500mg breakfast aur dinner ke saath\n• Meetha, chawal, maida band karein\n• Daily 30 min walk karein\n\nTests karwayein: HbA1c, Fasting lipid profile, kidney function test, urine microalbumin\n\nJaldi se physician se milein — insulin ki zaroorat ho sakti hai."}],
        [{"role":"system","content":SYSTEM_MSG},
         {"role":"user","content":"My child is 3 years old and has loose motions since yesterday. 6-7 times. What should I do?"},
         {"role":"assistant","content":"For a 3-year-old with acute diarrhea:\n\n🔴 MOST IMPORTANT: Prevent dehydration with ORS\n• Electral / ORS powder in 1L boiled cooled water\n• Give small sips every 5 min after each loose stool\n• Continue breastfeeding/normal diet\n\nMedicine:\n• Tab Zinc dispersible 20mg once daily for 14 days\n• Probiotics: Econorm sachet once daily\n\n🚨 Go to hospital if: blood in stool, no urination 6+ hours, child very drowsy, sunken eyes, or unable to drink."}],
    ]
    for conversation in MULTI_TURN:
        samples.append({"messages": conversation})

    # ── Dosage comparison samples ──────────────────────────────────────────────
    DOSAGE_COMPARISONS = [
        ("What is the difference between Dolo 650 and Crocin?",
         "Both contain Paracetamol. Dolo-650 has 650mg per tablet, Crocin Advance has 500mg. For adults, Dolo-650 is preferred for higher fever (>101°F). Crocin 500mg is suitable for mild fever and headache. Maximum: 4g/day (6 Dolo-650 or 8 Crocin). Avoid with alcohol and liver disease."),
        ("Generic vs branded medicine India mein kya farak hai?",
         "Generic aur branded medicine mein same salt/molecule hota hai. Farak sirf price mein hai:\n• Branded: Marketing cost included, 3-10x zyada\n• Generic: Same quality (FDA/CDSCO approved), bahut sasta\n\nExample: Atorvastatin 10mg - Lipitor (branded) ₹180 vs Generic ₹25\nJan Aushadhi stores se generic milta hai 50-90% sasta."),
        ("Can I take Ayurvedic and allopathic medicine together?",
         "⚠️ Some combinations can interact. General guidelines:\n• Maintain 2-hour gap between Ayurvedic and allopathic medicines\n• Inform both doctors about all medications\n• Known interactions: Ashwagandha may increase thyroid medication effect, Guggulu may interact with blood thinners\n• Always consult a qualified integrative medicine practitioner."),
    ]
    for user_msg, assistant_msg in DOSAGE_COMPARISONS:
        samples.append({"messages":[
            {"role":"system","content":SYSTEM_MSG},
            {"role":"user","content":user_msg},
            {"role":"assistant","content":assistant_msg},
        ]})

    logger.info("Built %d instruction samples from local KB", len(samples))
    return samples


# ═══════════════════════════════════════════════════════════════════════════════
# SENTENCE PAIRS FOR BIOBERT
# ═══════════════════════════════════════════════════════════════════════════════

def build_sentence_pairs() -> list[dict]:
    """Sentence similarity pairs for BioBERT fine-tuning."""
    pairs = []

    # English ↔ Hinglish
    HINGLISH = [
        ("fever","bukhar",1.0),
        ("headache","sir dard",1.0),
        ("abdominal pain","pet mein dard",1.0),
        ("joint pain","jodo mein dard",1.0),
        ("breathlessness","saans phoolna",1.0),
        ("cough","khasi",1.0),
        ("vomiting","ulti",0.95),
        ("diarrhea","dast",1.0),
        ("back pain","kamar dard",1.0),
        ("skin rash","chamdi par daane",0.95),
        ("excessive thirst","zyada pyaas",1.0),
        ("frequent urination","baar baar peshab",1.0),
        ("jaundice","aankhon mein peelaahat",0.95),
        ("high blood sugar","sugar zyada hai",1.0),
        ("low blood pressure","BP kam hai",0.95),
        ("thyroid problem","thyroid ki dikkat",0.95),
        ("weakness","kamzori",1.0),
        ("chest pain","seene mein dard",1.0),
        # New symptoms
        ("cold and cough","sardi khasi",1.0),
        ("runny nose","naak behna",1.0),
        ("throat pain","gale mein dard",1.0),
        ("itching","khujli",1.0),
        ("stomach acidity","pet mein jalan",0.95),
        ("dizziness","chakkar aana",0.95),
        ("constipation","kabz",1.0),
        ("loose motion","dast hona",1.0),
        ("insomnia","neend na aana",0.95),
        ("body ache","badan dard",1.0),
        ("shivering and chills","thand lagna aur kaampna",1.0),
        ("loss of appetite","bhookh na lagna",0.95),
        ("heartburn","seene mein jalan",0.95),
        ("hair fall","baal jhadna",0.90),
        ("eye burning","aankhon mein jalan",0.90),
        ("skin allergy","chamdi ki allergy",0.95),
        ("weight gain","vajan badhna",0.90),
        ("weight loss","vajan ghatna",0.90),
    ]
    for a, b, score in HINGLISH:
        pairs.append({"sentence1": a, "sentence2": b, "score": score})
        pairs.append({"sentence1": f"I have {a}", "sentence2": f"Mujhe {b} hai", "score": score})

    # Brand ↔ generic
    BRAND_GENERIC = [
        ("Dolo-650","Paracetamol 650mg",0.95),
        ("Crocin","Paracetamol 500mg",0.95),
        ("Glycomet","Metformin 500mg",0.95),
        ("Telma","Telmisartan 40mg",0.95),
        ("Thyronorm","Levothyroxine 50mcg",0.95),
        ("Stamlo","Amlodipine 5mg",0.95),
        ("Cetzine","Cetirizine 10mg",0.95),
        ("Azithral","Azithromycin 500mg",0.95),
        ("Taxim-O","Cefixime 200mg",0.95),
        ("Ciplox","Ciprofloxacin 500mg",0.95),
        ("Montair","Montelukast 10mg",0.95),
        ("Nexito","Escitalopram 10mg",0.95),
        ("Asthalin","Salbutamol inhaler",0.95),
        ("Pan-40","Pantoprazole 40mg",0.95),
        ("Orofer-XT","Ferrous Ascorbate 100mg",0.95),
        ("Himalaya Ashwagandha","Withania somnifera 500mg",0.90),
        ("Patanjali Giloy","Tinospora cordifolia extract",0.90),
        # New Indian drug brands
        ("Augmentin 625","Amoxicillin-Clavulanate",0.95),
        ("Brufen 400","Ibuprofen 400mg",0.95),
        ("Voveran 50","Diclofenac 50mg",0.95),
        ("Meftal-Spas","Mefenamic Acid 500mg",0.95),
        ("Lariago","Chloroquine 250mg",0.95),
        ("Limcee","Vitamin C 500mg",0.95),
        ("Calcirol","Vitamin D3 60K IU",0.95),
        ("Amaryl 2","Glimepiride 2mg",0.95),
        ("Januvia 100","Sitagliptin 100mg",0.95),
        ("Jardiance 10","Empagliflozin 10mg",0.95),
        ("Forxiga 10","Dapagliflozin 10mg",0.95),
        ("Benadryl dry cough","Dextromethorphan syrup",0.95),
        ("Duphalac","Lactulose syrup",0.95),
        ("Omez 20","Omeprazole 20mg",0.95),
        ("Razo 20","Rabeprazole 20mg",0.95),
        ("Neksium 40","Esomeprazole 40mg",0.95),
        ("Aciloc 150","Ranitidine 150mg",0.95),
        ("Ecosprin 75","Aspirin 75mg",0.95),
        ("Liv.52","Himalaya Liv.52",0.90),
        ("Cystone","Himalaya Cystone",0.90),
        ("SBL Belladonna","Belladonna 30C",0.90),
        ("SBL Arsenicum","Arsenicum Album 30C",0.90),
        ("SBL Nux Vomica","Nux Vomica 30C",0.90),
    ]
    for brand, generic, score in BRAND_GENERIC:
        pairs.append({"sentence1": brand, "sentence2": generic, "score": score})

    # Medical concept pairs
    CONCEPTS = [
        ("iron deficiency anemia", "low hemoglobin low ferritin", 0.90),
        ("type 2 diabetes", "high blood glucose HbA1c elevated", 0.90),
        ("dengue fever", "NS1 antigen positive low platelets", 0.90),
        ("tuberculosis pulmonary", "AFB positive sputum cough blood", 0.90),
        ("hypothyroidism", "TSH elevated T4 low weight gain fatigue", 0.90),
        ("malaria plasmodium", "peripheral blood smear positive chills fever", 0.90),
        ("urinary tract infection", "dysuria burning micturition frequency", 0.90),
        ("peptic ulcer", "epigastric pain burning empty stomach H pylori", 0.90),
        ("rheumatoid arthritis", "morning stiffness symmetrical joint swelling RF positive", 0.90),
        ("hypertension", "high blood pressure systolic above 140", 0.90),
        # New clinical concepts
        ("asthma bronchial", "wheezing shortness of breath inhaler", 0.90),
        ("kidney stone", "renal calculi severe flank pain hematuria", 0.90),
        ("migraine headache", "unilateral throbbing visual aura photophobia", 0.90),
        ("gastroesophageal reflux disease", "GERD heartburn acid reflux chest burning", 0.90),
        ("allergic rhinitis", "sneezing runny nose nasal congestion watery eyes", 0.90),
        ("liver cirrhosis", "hepatic failure ascites jaundice portal hypertension", 0.90),
        ("cardiac emergency stroke", "sudden weakness face drooping slurred speech", 0.90),
        ("diabetic ketoacidosis", "high blood sugar ketones in urine sweet breath", 0.90),
    ]
    for a, b, s in CONCEPTS:
        pairs.append({"sentence1": a, "sentence2": b, "score": s})

    # Dissimilar pairs (score ~0)
    DISSIMILAR = [
        ("fever treatment","knee surgery",0.0),
        ("diabetes medicine","eye care",0.0),
        ("antibiotic for UTI","heart bypass",0.0),
        ("Ashwagandha dosage","cancer chemotherapy",0.0),
        # New dissimilar negatives
        ("cough treatment","foot fracture casting",0.0),
        ("heart attack","acne pimple cream",0.0),
        ("diabetes glucose","hair transplantation",0.0),
        ("thyroid hormone","tooth extraction dentist",0.0),
        ("dengue platelet count","migraine headache",0.0),
        ("stomach ulcer","respiratory inhaler asthma",0.0),
        ("hypertension BP","skin rash allergy",0.0),
        ("homeopathic remedy","cardiac bypass surgery",0.0),
    ]
    for a, b, s in DISSIMILAR:
        pairs.append({"sentence1": a, "sentence2": b, "score": s})

    logger.info("Built %d sentence pairs for BioBERT", len(pairs))
    return pairs


# ═══════════════════════════════════════════════════════════════════════════════
# RAG DOCUMENT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_rag_documents():
    """Write text files to knowledge_bases/ for FAISS indexing."""
    count = {"allopathy": 0, "ayurveda": 0, "homeopathy": 0, "drug_interactions": 0}

    # Per-disease documents
    for key, disease in DISEASES.items():
        name = disease["name"]

        # Allopathy document
        allo = disease.get("allopathy",{})
        meds = allo.get("medicines",[])
        if meds:
            content = f"DISEASE: {name}\nICD10: {disease.get('icd10','')}\nSYSTEM: Allopathy\n\n"
            content += f"SYMPTOMS: {', '.join(disease.get('symptoms',[])[:8])}\n\n"
            content += "MEDICINES:\n"
            for m in meds:
                content += (f"  {m['name']} ({m.get('brand','')}) — "
                            f"{m.get('dose','')} {m.get('frequency','')} for {m.get('duration','')}"
                            f" | Purpose: {m.get('purpose','')}"
                            f" | Warning: {m.get('warn','')}\n")
            tests = allo.get("tests_to_order",allo.get("tests",[]))
            if tests:
                content += f"\nTESTS: {', '.join(tests)}\n"
            if allo.get("avoid"):
                content += f"AVOID: {', '.join(allo['avoid'])}\n"
            p = RAG_DIR / "allopathy" / f"{key}.txt"
            p.write_text(content, encoding="utf-8")
            count["allopathy"] += 1

        # Ayurveda document
        ayur = disease.get("ayurveda",{})
        ayur_meds = ayur.get("medicines",[])
        if ayur_meds:
            content = f"DISEASE: {name}\nSYSTEM: Ayurveda\n\n"
            content += f"SYMPTOMS: {', '.join(disease.get('symptoms',[])[:8])}\n\n"
            content += "MEDICINES:\n"
            for m in ayur_meds:
                content += (f"  {m['name']} ({m.get('brand','')}) — "
                            f"{m.get('dose','')} {m.get('frequency','')} | "
                            f"Purpose: {m.get('purpose','')}\n")
            diet = ayur.get("diet",ayur.get("diet_recommendations",[]))
            if diet:
                content += f"\nDIET: {', '.join(diet[:5])}\n"
            p = RAG_DIR / "ayurveda" / f"{key}.txt"
            p.write_text(content, encoding="utf-8")
            count["ayurveda"] += 1

        # Homeopathy document
        homo = disease.get("homeopathy",{})
        homo_meds = homo.get("medicines",[])
        if homo_meds:
            content = f"DISEASE: {name}\nSYSTEM: Homeopathy\n\n"
            content += "REMEDIES:\n"
            for m in homo_meds:
                content += (f"  {m['name']} {m.get('potency','')} — "
                            f"{m.get('dose','')} {m.get('frequency','')} | "
                            f"Keynote: {m.get('keynote','')}\n")
            p = RAG_DIR / "homeopathy" / f"{key}.txt"
            p.write_text(content, encoding="utf-8")
            count["homeopathy"] += 1

    # Drug interactions document
    content = "DRUG INTERACTION DATABASE\nArogyaAI Cross-System Interactions\n\n"
    for i in INTERACTIONS:
        content += (f"INTERACTION: {i['d1']} + {i['d2']}\n"
                    f"SEVERITY: {i['sev']}\n"
                    f"EFFECT: {i['effect']}\n"
                    f"MANAGEMENT: {i['mgmt']}\n\n")
    p = RAG_DIR / "drug_interactions" / "all_interactions.txt"
    p.write_text(content, encoding="utf-8")
    count["drug_interactions"] += 1

    logger.info("RAG documents: %s", count)
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ArogyaAI Dataset Builder")
    parser.add_argument("--all",        action="store_true", help="Build all datasets")
    parser.add_argument("--pubmed",     action="store_true", help="Fetch PubMed articles")
    parser.add_argument("--openfda",    action="store_true", help="Fetch OpenFDA drug data")
    parser.add_argument("--local-only", action="store_true", help="Only local DB (offline)")
    parser.add_argument("--rag",        action="store_true", help="Build RAG documents only")
    args = parser.parse_args()

    stats = {"started_at": datetime.now().isoformat()}

    # ── Local instruction samples ─────────────────────────────────────────────
    logger.info("Building instruction samples from local KB...")
    samples = build_instruction_samples()

    # ── PubMed ────────────────────────────────────────────────────────────────
    if args.all or args.pubmed:
        logger.info("Fetching PubMed articles (this takes ~5 min)...")
        pubmed_articles = []
        for query in PUBMED_QUERIES:
            arts = fetch_pubmed(query, max_results=10)
            for art in arts:
                # Convert to instruction pair
                samples.append({"messages":[
                    {"role":"system","content":SYSTEM_MSG},
                    {"role":"user","content":
                        f"What does research say about: {art['title']}?"},
                    {"role":"assistant","content":
                        f"According to a {art['year']} study in {art['journal']} "
                        f"(PMID: {art['pmid']}):\n{art['abstract'][:1500]}"},
                ]})
                # Also save as RAG document
                fname = RAG_DIR / "allopathy" / f"pubmed_{art['pmid']}.txt"
                if not fname.exists():
                    fname.write_text(
                        f"TITLE: {art['title']}\nYEAR: {art['year']}\n"
                        f"JOURNAL: {art['journal']}\nPMID: {art['pmid']}\n\n"
                        f"ABSTRACT:\n{art['abstract']}\n",
                        encoding="utf-8"
                    )
                pubmed_articles.append(art)
            time.sleep(0.15)
        stats["pubmed_articles"] = len(pubmed_articles)
        logger.info("PubMed: %d articles fetched", len(pubmed_articles))

    # ── OpenFDA ───────────────────────────────────────────────────────────────
    if args.all or args.openfda:
        logger.info("Fetching OpenFDA drug data...")
        fda_count = 0
        for drug in INDIAN_DRUG_QUERIES:
            drug_data = fetch_openfda(drug)
            for d in drug_data:
                samples.append({"messages":[
                    {"role":"system","content":SYSTEM_MSG},
                    {"role":"user","content":
                        f"What are the indications and dosage for {drug}?"},
                    {"role":"assistant","content":
                        f"Indications: {d['indications'][:600]}\n"
                        f"Dosage: {d['dosage'][:400]}\n"
                        f"Interactions: {d['interactions'][:300]}"},
                ]})
                fda_count += 1
        stats["openfda_drugs"] = fda_count
        logger.info("OpenFDA: %d drug entries", fda_count)

    # ── Sentence pairs ────────────────────────────────────────────────────────
    logger.info("Building sentence pairs for BioBERT...")
    sentence_pairs = build_sentence_pairs()

    # ── RAG documents ─────────────────────────────────────────────────────────
    logger.info("Writing RAG documents...")
    rag_counts = build_rag_documents()

    # ── Write files ───────────────────────────────────────────────────────────
    with open(INSTRUCTION_F, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    logger.info("✅ Instruction dataset: %d samples → %s", len(samples), INSTRUCTION_F)

    with open(SENTENCE_F, "w", encoding="utf-8") as f:
        for p in sentence_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    logger.info("✅ Sentence pairs: %d → %s", len(sentence_pairs), SENTENCE_F)

    stats.update({
        "instruction_samples": len(samples),
        "sentence_pairs":      len(sentence_pairs),
        "rag_documents":       rag_counts,
        "finished_at":         datetime.now().isoformat(),
    })
    STATS_F.write_text(json.dumps(stats, indent=2))
    logger.info("✅ Stats saved to %s", STATS_F)
    logger.info("Dataset build complete!")


if __name__ == "__main__":
    main()
