"""
ArogyaAI — Large Medicine Database
=====================================
60+ diseases with:
  - Symptoms (English + Hinglish keywords)
  - Allopathy (Indian brands + generics + prices)
  - Ayurveda (AYUSH-certified formulations + prices)
  - Homeopathy (classical remedies with potency + prices)
  - Drug interactions (Allopathic + Ayurvedic cross-system)
  - Dietary advice
  - Red flags

This is the OFFLINE knowledge base that:
  1. Powers the RAG retrieval (FAISS)
  2. Provides fallback when API is down
  3. Gets enriched by fine-tuned LLaMA for better prescriptions
"""

from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# MEDICINE PRICE DATABASE (brand_mrp = per strip/unit in INR)
# ─────────────────────────────────────────────────────────────────────────────
PRICES: dict[str, dict] = {
    # ── Analgesic / Antipyretic ───────────────────────────────────────────────
    "Paracetamol 500mg":        {"brand":"Crocin 500",       "b":18,  "g":6},
    "Paracetamol 650mg":        {"brand":"Dolo-650",         "b":32,  "g":10},
    "Ibuprofen 400mg":          {"brand":"Brufen 400",       "b":38,  "g":12},
    "Diclofenac 50mg":          {"brand":"Voveran 50",       "b":48,  "g":15},
    "Nimesulide 100mg":         {"brand":"Nise 100",         "b":42,  "g":14},
    "Mefenamic Acid 500mg":     {"brand":"Meftal-Spas",      "b":55,  "g":18},
    "Ketorolac 10mg":           {"brand":"Toradol",          "b":85,  "g":28},
    "Tramadol 50mg":            {"brand":"Tramazac",         "b":95,  "g":32},
    "Aspirin 75mg":             {"brand":"Ecosprin 75",      "b":35,  "g":12},
    "Aspirin 325mg":            {"brand":"Disprin",          "b":18,  "g":8},

    # ── Antibiotics ───────────────────────────────────────────────────────────
    "Amoxicillin 500mg":        {"brand":"Mox 500",          "b":88,  "g":28},
    "Amoxicillin-Clavulanate":  {"brand":"Augmentin 625",    "b":248, "g":85},
    "Azithromycin 500mg":       {"brand":"Azithral 500",     "b":95,  "g":35},
    "Ciprofloxacin 500mg":      {"brand":"Ciplox 500",       "b":75,  "g":22},
    "Doxycycline 100mg":        {"brand":"Doxicip 100",      "b":65,  "g":20},
    "Metronidazole 400mg":      {"brand":"Metrogyl 400",     "b":55,  "g":16},
    "Tinidazole 500mg":         {"brand":"Tiniba 500",       "b":68,  "g":22},
    "Clarithromycin 500mg":     {"brand":"Claribid 500",     "b":185, "g":65},
    "Cefixime 200mg":           {"brand":"Taxim-O 200",      "b":142, "g":48},
    "Cefuroxime 500mg":         {"brand":"Zinnat 500",       "b":195, "g":68},
    "Levofloxacin 500mg":       {"brand":"Levaquin 500",     "b":168, "g":55},
    "Moxifloxacin 400mg":       {"brand":"Avelox 400",       "b":285, "g":95},
    "Nitrofurantoin 100mg":     {"brand":"Macrobid",         "b":125, "g":42},

    # ── Antiviral ────────────────────────────────────────────────────────────
    "Acyclovir 400mg":          {"brand":"Acivir 400",       "b":168, "g":55},
    "Oseltamivir 75mg":         {"brand":"Tamiflu 75",       "b":485, "g":145},
    "Favipiravir 400mg":        {"brand":"Faviflu 400",      "b":325, "g":105},

    # ── Antifungal ───────────────────────────────────────────────────────────
    "Fluconazole 150mg":        {"brand":"Flucos 150",       "b":85,  "g":28},
    "Itraconazole 100mg":       {"brand":"Canditral 100",    "b":245, "g":85},
    "Clotrimazole cream":       {"brand":"Candid B cream",   "b":75,  "g":32},
    "Terbinafine 250mg":        {"brand":"Lamisil 250",      "b":195, "g":65},

    # ── Antiparasitic ─────────────────────────────────────────────────────────
    "Albendazole 400mg":        {"brand":"Zentel 400",       "b":28,  "g":12},
    "Ivermectin 12mg":          {"brand":"Ivermec 12",       "b":148, "g":48},
    "Chloroquine 250mg":        {"brand":"Lariago",          "b":45,  "g":15},
    "Artemether-Lumefantrine":  {"brand":"Coartem/Laritem",  "b":285, "g":95},
    "Primaquine 15mg":          {"brand":"Malirid 15",       "b":38,  "g":12},

    # ── Antidiabetic ─────────────────────────────────────────────────────────
    "Metformin 500mg":          {"brand":"Glycomet 500",     "b":42,  "g":15},
    "Metformin 1000mg SR":      {"brand":"Glycomet SR 1g",   "b":98,  "g":32},
    "Glimepiride 1mg":          {"brand":"Amaryl 1",         "b":85,  "g":28},
    "Glimepiride 2mg":          {"brand":"Amaryl 2",         "b":118, "g":38},
    "Sitagliptin 100mg":        {"brand":"Januvia 100",      "b":398, "g":128},
    "Empagliflozin 10mg":       {"brand":"Jardiance 10",     "b":568, "g":185},
    "Dapagliflozin 10mg":       {"brand":"Forxiga 10",       "b":548, "g":178},
    "Pioglitazone 15mg":        {"brand":"Actos 15",         "b":125, "g":42},
    "Glibenclamide 5mg":        {"brand":"Daonil 5",         "b":38,  "g":12},
    "Insulin Glargine":         {"brand":"Basalog/Lantus",   "b":498, "g":298},
    "Insulin Regular":          {"brand":"Actrapid/Huminsulin","b":285,"g":185},

    # ── Antihypertensive ─────────────────────────────────────────────────────
    "Amlodipine 5mg":           {"brand":"Stamlo 5",         "b":58,  "g":18},
    "Amlodipine 10mg":          {"brand":"Stamlo 10",        "b":95,  "g":28},
    "Telmisartan 40mg":         {"brand":"Telma 40",         "b":142, "g":48},
    "Telmisartan 80mg":         {"brand":"Telma 80",         "b":195, "g":65},
    "Losartan 50mg":            {"brand":"Losacar 50",       "b":98,  "g":32},
    "Enalapril 5mg":            {"brand":"Envas 5",          "b":55,  "g":18},
    "Ramipril 5mg":             {"brand":"Cardace 5",        "b":98,  "g":32},
    "Metoprolol 50mg":          {"brand":"Betaloc 50",       "b":65,  "g":22},
    "Atenolol 50mg":            {"brand":"Tenormin 50",      "b":48,  "g":15},
    "Hydrochlorothiazide 25mg": {"brand":"HCT 25",           "b":28,  "g":10},
    "Spironolactone 25mg":      {"brand":"Aldactone 25",     "b":68,  "g":22},

    # ── Cardiac ──────────────────────────────────────────────────────────────
    "Atorvastatin 10mg":        {"brand":"Atorva 10",        "b":85,  "g":25},
    "Atorvastatin 20mg":        {"brand":"Atorva 20",        "b":125, "g":38},
    "Rosuvastatin 10mg":        {"brand":"Crestor 10",       "b":145, "g":45},
    "Clopidogrel 75mg":         {"brand":"Plavix 75",        "b":115, "g":35},
    "Isosorbide 5mg":           {"brand":"Sorbitrate 5",     "b":32,  "g":10},
    "Digoxin 0.25mg":           {"brand":"Lanoxin",          "b":45,  "g":15},

    # ── GI ───────────────────────────────────────────────────────────────────
    "Pantoprazole 40mg":        {"brand":"Pan-40",           "b":84,  "g":24},
    "Omeprazole 20mg":          {"brand":"Omez 20",          "b":62,  "g":18},
    "Rabeprazole 20mg":         {"brand":"Razo 20",          "b":95,  "g":28},
    "Esomeprazole 40mg":        {"brand":"Neksium 40",       "b":145, "g":45},
    "Ranitidine 150mg":         {"brand":"Aciloc 150",       "b":48,  "g":14},
    "Sucralfate 1g":            {"brand":"Sucral",           "b":98,  "g":32},
    "Domperidone 10mg":         {"brand":"Domstal 10",       "b":45,  "g":14},
    "Metoclopramide 10mg":      {"brand":"Perinorm 10",      "b":32,  "g":10},
    "Ondansetron 4mg":          {"brand":"Emeset 4",         "b":58,  "g":18},
    "Loperamide 2mg":           {"brand":"Imodium 2",        "b":62,  "g":20},
    "Lactulose syrup":          {"brand":"Duphalac",         "b":185, "g":65},
    "ORS sachet":               {"brand":"Electral/ORS",     "b":12,  "g":5},
    "Zinc 20mg":                {"brand":"Zincovit",         "b":48,  "g":15},

    # ── Respiratory ──────────────────────────────────────────────────────────
    "Salbutamol inhaler":       {"brand":"Asthalin HFA",     "b":128, "g":85},
    "Budesonide inhaler 200":   {"brand":"Budecort 200",     "b":285, "g":185},
    "Formoterol+Budesonide":    {"brand":"Foracort 200",     "b":395, "g":248},
    "Montelukast 10mg":         {"brand":"Montair 10",       "b":198, "g":68},
    "Levocetrizine 5mg":        {"brand":"Levocet 5",        "b":65,  "g":22},
    "Cetirizine 10mg":          {"brand":"Cetzine 10",       "b":48,  "g":15},
    "Fexofenadine 180mg":       {"brand":"Allegra 180",      "b":145, "g":48},
    "Prednisolone 10mg":        {"brand":"Wysolone 10",      "b":55,  "g":18},
    "Dextromethorphan syrup":   {"brand":"Benadryl dry cough","b":85, "g":32},
    "Ambroxol syrup":           {"brand":"Ambrodil",         "b":68,  "g":25},

    # ── Thyroid ──────────────────────────────────────────────────────────────
    "Levothyroxine 25mcg":      {"brand":"Thyronorm 25",     "b":45,  "g":15},
    "Levothyroxine 50mcg":      {"brand":"Thyronorm 50",     "b":68,  "g":22},
    "Levothyroxine 100mcg":     {"brand":"Thyronorm 100",    "b":95,  "g":28},
    "Carbimazole 5mg":          {"brand":"Neo-mercazole",    "b":48,  "g":15},

    # ── Neurological / Psych ─────────────────────────────────────────────────
    "Escitalopram 10mg":        {"brand":"Nexito 10",        "b":156, "g":55},
    "Sertraline 50mg":          {"brand":"Serlift 50",       "b":145, "g":48},
    "Amitriptyline 10mg":       {"brand":"Amitone 10",       "b":32,  "g":10},
    "Clonazepam 0.5mg":         {"brand":"Clonotril 0.5",    "b":48,  "g":15},
    "Alprazolam 0.25mg":        {"brand":"Alprax 0.25",      "b":32,  "g":10},
    "Gabapentin 300mg":         {"brand":"Gabantin 300",     "b":85,  "g":28},
    "Pregabalin 75mg":          {"brand":"Lyrica 75",        "b":145, "g":48},
    "Sumatriptan 50mg":         {"brand":"Suminat 50",       "b":198, "g":68},

    # ── Vitamins & Supplements ────────────────────────────────────────────────
    "Vitamin C 500mg":          {"brand":"Limcee 500",       "b":35,  "g":12},
    "Vitamin D3 60K IU":        {"brand":"Calcirol 60K",     "b":185, "g":62},
    "Vitamin B12 500mcg":       {"brand":"Methylcobal 500",  "b":125, "g":42},
    "Ferrous Ascorbate 100mg":  {"brand":"Orofer-XT",        "b":178, "g":58},
    "Calcium 500+D3":           {"brand":"Shelcal-HD",       "b":245, "g":82},
    "Folic Acid 5mg":           {"brand":"Folvite 5",        "b":28,  "g":8},
    "Zinc 50mg":                {"brand":"Zincovit",         "b":95,  "g":32},
    "Iron sucrose IV":          {"brand":"Monofer",          "b":485, "g":285},

    # ── Ayurvedic ─────────────────────────────────────────────────────────────
    "Ashwagandha 500mg":        {"brand":"Himalaya Ashwagandha","b":185,"g":85},
    "Giloy Ghanvati":           {"brand":"Patanjali Giloy",  "b":95,  "g":45},
    "Triphala Churna":          {"brand":"Dabur Triphala",   "b":128, "g":58},
    "Chyawanprash":             {"brand":"Dabur Chyawanprash","b":245,"g":145},
    "Sitopaladi Churna":        {"brand":"Baidyanath Sitopaladi","b":85,"g":38},
    "Shatavari 500mg":          {"brand":"Himalaya Shatavari","b":178,"g":82},
    "Arjunarishta":             {"brand":"Dabur Arjunarishta","b":148,"g":72},
    "Brahmi Vati":              {"brand":"Divya Brahmi Vati","b":95,  "g":48},
    "Liv.52":                   {"brand":"Himalaya Liv.52",  "b":125, "g":125},
    "Cystone":                  {"brand":"Himalaya Cystone", "b":148, "g":148},
    "Kanchanar Guggulu":        {"brand":"Baidyanath Kanchanar","b":115,"g":62},
    "Trikatu Churna":           {"brand":"Patanjali Trikatu","b":65,  "g":32},
    "Kutajghan Vati":           {"brand":"Baidyanath Kutajghan","b":85,"g":42},
    "Mahasudarshan Churna":     {"brand":"Baidyanath Mahasudarshan","b":98,"g":48},
    "Papaya Leaf Extract":      {"brand":"PapayaGuard",      "b":185, "g":95},
    "Punarnava Mandur":         {"brand":"Baidyanath Punarnava","b":145,"g":68},
    "Yogaraj Guggulu":          {"brand":"Baidyanath Yogaraj","b":125,"g":58},
    "Avipattikar Churna":       {"brand":"Patanjali Avipattikar","b":72,"g":35},
    "Arogyavardhini Vati":      {"brand":"Baidyanath Arogyavardhini","b":95,"g":45},
    "Saraswatarishta":          {"brand":"Dabur Saraswatarishta","b":145,"g":72},
    "Neem Capsule":             {"brand":"Himalaya Neem",    "b":125, "g":58},
    "Mulethi (Licorice)":       {"brand":"Patanjali Mulethi","b":65,  "g":28},
    "Haridra (Turmeric) 500mg": {"brand":"Himalaya Haridra", "b":95,  "g":42},
    "Shilajit":                 {"brand":"Himalaya Shilajit","b":285, "g":145},
    "Guggulu":                  {"brand":"Patanjali Guggul", "b":85,  "g":38},
    "Vasavaleha":               {"brand":"Dabur Vasavaleha", "b":125, "g":65},

    # ── Homeopathic ───────────────────────────────────────────────────────────
    "Eupatorium Perfoliatum 30C":{"brand":"SBL Eupatorium",  "b":75,  "g":55},
    "Belladonna 30C":            {"brand":"SBL Belladonna",  "b":75,  "g":55},
    "Arsenicum Album 30C":       {"brand":"SBL Arsenicum",   "b":75,  "g":55},
    "Nux Vomica 30C":            {"brand":"SBL Nux Vomica",  "b":75,  "g":55},
    "Bryonia 30C":               {"brand":"SBL Bryonia",     "b":75,  "g":55},
    "Rhus Tox 30C":              {"brand":"SBL Rhus Tox",    "b":75,  "g":55},
    "Gelsemium 30C":             {"brand":"SBL Gelsemium",   "b":75,  "g":55},
    "China 30C":                 {"brand":"SBL China",       "b":75,  "g":55},
    "Lycopodium 30C":            {"brand":"SBL Lycopodium",  "b":75,  "g":55},
    "Pulsatilla 30C":            {"brand":"SBL Pulsatilla",  "b":75,  "g":55},
    "Apis Mellifica 30C":        {"brand":"SBL Apis Mel",    "b":75,  "g":55},
    "Sulphur 30C":               {"brand":"SBL Sulphur",     "b":75,  "g":55},
    "Calcarea Carb 200C":        {"brand":"SBL Calc Carb",   "b":95,  "g":72},
    "Natrum Mur 30C":            {"brand":"SBL Natrum Mur",  "b":75,  "g":55},
    "Ipecacuanha 30C":           {"brand":"SBL Ipecac",      "b":75,  "g":55},
    "Ferrum Phos 6X":            {"brand":"SBL Biochemic",   "b":65,  "g":45},
    "Calcarea Phos 6X":          {"brand":"SBL Biochemic",   "b":65,  "g":45},
    "Kali Phos 6X":              {"brand":"SBL Biochemic",   "b":65,  "g":45},
    "Syzygium Jambolanum Q":     {"brand":"SBL Mother Tincture","b":85,"g":65},
    "Aconitum Napellus 30C":     {"brand":"SBL Aconitum",    "b":75,  "g":55},
    "Chamomilla 30C":            {"brand":"SBL Chamomilla",  "b":75,  "g":55},
}


# ─────────────────────────────────────────────────────────────────────────────
# DISEASE DATABASE — 60+ conditions
# ─────────────────────────────────────────────────────────────────────────────
DISEASES: dict[str, dict[str, Any]] = {

    "dengue_fever": {
        "name": "Dengue Fever", "icd10": "A90", "category": "Infectious",
        "emergency": False,
        "symptoms": ["sudden high fever","severe headache","pain behind eyes","muscle joint pain","rash",
                     "nausea","fatigue","tez bukhar","aankhon ke peeche dard","jodo mein dard"],
        "red_flags": ["platelets below 50000","bleeding gums","severe abdominal pain","blood in vomit","difficulty breathing"],
        "allopathy": {
            "medicines": [
                {"name":"Paracetamol 650mg","brand":"Dolo-650/Crocin","dose":"1 tab","freq":"Every 6 hrs","dur":"Till fever subsides","timing":"After food","purpose":"Reduce fever & pain","warn":"Never Aspirin/Ibuprofen in dengue — increases bleeding","price_inr":32},
                {"name":"ORS sachet","brand":"Electral/WHO ORS","dose":"1 sachet in 1L water","freq":"After every loose stool / continuous sipping","dur":"Till hydrated","timing":"Anytime","purpose":"Prevent dehydration","price_inr":12},
                {"name":"Vitamin C 500mg","brand":"Limcee","dose":"1 tab","freq":"Twice daily","dur":"7 days","timing":"After food","purpose":"Immune support & collagen synthesis","price_inr":35},
            ],
            "tests": ["NS1 Antigen (Day 1-5)","Dengue IgM/IgG (after Day 5)","CBC with platelet daily","LFT if fever >5 days"],
            "avoid": ["Aspirin","Ibuprofen","NSAIDs","Steroids","Antibiotics (viral disease)"],
            "hospitalize": "Platelets < 50,000 or signs of dengue hemorrhagic fever",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Papaya Leaf Extract","brand":"PapayaGuard Tablets","dose":"2 tabs","freq":"Twice daily","dur":"5-7 days","timing":"After meals","purpose":"Clinically proven to raise platelet count","price_inr":185},
                {"name":"Giloy Ghanvati","brand":"Patanjali Giloy Sat","dose":"2 tabs","freq":"Twice daily","dur":"7 days","timing":"With warm water after meals","purpose":"Immunomodulator, reduces fever","price_inr":95},
                {"name":"Mahasudarshan Churna","brand":"Baidyanath Mahasudarshan","dose":"3g powder","freq":"Twice daily","dur":"5 days","timing":"With honey before meals","purpose":"Antipyretic, antimalarial","price_inr":98},
            ],
            "diet": ["Papaya (fruit, not seeds)","Pomegranate juice","Coconut water","Kiwi","Easily digestible khichdi"],
            "avoid": ["Oily/spicy food","Cold drinks","Heavy meals","Alcohol"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Eupatorium Perfoliatum","potency":"30C","brand":"SBL/Schwabe","dose":"4 pills","freq":"Every 3-4 hrs in acute phase","dur":"3-5 days","timing":"30 min before meals","keynote":"Bone-breaking pain + high fever — classic dengue remedy","price_inr":75},
                {"name":"Rhus Tox","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Restlessness, joint pain, rash","price_inr":75},
                {"name":"Belladonna","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every 2 hrs in high fever","dur":"2-3 days","timing":"Before meals","keynote":"Sudden high fever, flushed face, throbbing headache","price_inr":75},
            ],
            "diet": ["Light diet","Plenty of warm water","Avoid coffee and mint"],
        },
        "dietary": "3-4 liters water/day. Papaya juice, pomegranate, coconut water. Avoid oily/spicy food.",
        "cost": {"allopathy":79,"ayurveda":378,"homeopathy":225,"cheapest":"Allopathy"},
    },

    "malaria": {
        "name": "Malaria", "icd10": "B54", "category": "Infectious",
        "symptoms": ["cyclical fever chills","high fever with rigors","sweating","headache","body aches","nausea","bukhar ke sath kaampna"],
        "red_flags": ["altered consciousness","seizures","respiratory distress","jaundice","severe anemia"],
        "allopathy": {
            "medicines": [
                {"name":"Artemether-Lumefantrine","brand":"Coartem/Laritem","dose":"As per weight","freq":"Twice daily","dur":"3 days","timing":"After fatty meal (improves absorption)","purpose":"First-line for P. falciparum malaria","warn":"Check G6PD before adding Primaquine","price_inr":285},
                {"name":"Chloroquine 250mg","brand":"Lariago","dose":"600mg day 1, 300mg day 2-3","freq":"Once daily","dur":"3 days","timing":"After food","purpose":"For P. vivax malaria","price_inr":45},
                {"name":"Primaquine 15mg","brand":"Malirid","dose":"15mg","freq":"Once daily","dur":"14 days","timing":"After food","purpose":"Radical cure for P. vivax (prevents relapse)","warn":"MUST check G6PD first — causes hemolysis in deficiency","price_inr":38},
            ],
            "tests": ["Peripheral blood smear (gold standard)","Rapid Diagnostic Test (RDT)","G6PD test before Primaquine","CBC"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Mahasudarshan Churna","brand":"Baidyanath","dose":"3g","freq":"Twice daily","dur":"7 days","timing":"With warm water","purpose":"Classical antimalarial formulation","price_inr":98},
                {"name":"Giloy Ghanvati","brand":"Patanjali","dose":"2 tabs","freq":"Twice daily","dur":"7 days","timing":"After meals","purpose":"Immunomodulator, reduces fever","price_inr":95},
                {"name":"Neem Capsule","brand":"Himalaya Neem","dose":"2 caps","freq":"Twice daily","dur":"5-7 days","timing":"After meals","purpose":"Antimalarial, antipyretic","price_inr":125},
            ],
            "note": "Adjunct to standard antimalarial treatment, not replacement",
        },
        "homeopathy": {
            "medicines": [
                {"name":"Natrum Muriaticum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"7 days","timing":"Before meals","keynote":"Periodic fever, chills, thirst for cold water","price_inr":75},
                {"name":"China","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"7 days","timing":"Before meals","keynote":"Weakness from fluid loss, periodic fever","price_inr":75},
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Restlessness, anxiety, midnight aggravation","price_inr":75},
            ],
        },
        "cost": {"allopathy":368,"ayurveda":318,"homeopathy":225,"cheapest":"Homeopathy"},
    },

    "typhoid": {
        "name": "Typhoid Fever", "icd10": "A01.0", "category": "Infectious",
        "symptoms": ["step-ladder fever","headache","abdominal pain","constipation or diarrhea","rose spots","relative bradycardia","miyadi bukhar","pet mein dard"],
        "red_flags": ["intestinal perforation signs","very high fever >40°C","confusion","bleeding per rectum"],
        "allopathy": {
            "medicines": [
                {"name":"Azithromycin 500mg","brand":"Azithral 500","dose":"1g day 1, then 500mg","freq":"Once daily","dur":"7 days","timing":"Empty stomach","purpose":"Drug of choice uncomplicated typhoid","price_inr":95},
                {"name":"Cefixime 200mg","brand":"Taxim-O","dose":"1 tab","freq":"Twice daily","dur":"10-14 days","timing":"After food","purpose":"Alternative first-line","price_inr":142},
                {"name":"Paracetamol 650mg","brand":"Dolo-650","dose":"1 tab","freq":"Every 6 hrs PRN","dur":"Till fever subsides","timing":"After food","purpose":"Fever management","price_inr":32},
            ],
            "tests": ["Widal test (after 7 days)","Blood culture (gold standard, before antibiotics)","CBC","LFT","Typhoid IgM rapid test"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Mahasudarshan Churna","brand":"Baidyanath","dose":"3g","freq":"Twice daily","dur":"7 days","timing":"With honey","purpose":"Fever, infection","price_inr":98},
                {"name":"Giloy Ghanvati","brand":"Patanjali","dose":"2 tabs","freq":"Twice daily","dur":"7 days","timing":"With warm water after meals","purpose":"Immunomodulator","price_inr":95},
                {"name":"Kutajghan Vati","brand":"Baidyanath Kutajghan","dose":"2 tabs","freq":"3 times daily","dur":"7 days","timing":"Before meals with buttermilk","purpose":"For diarrhea component of typhoid","price_inr":85},
            ],
            "diet": ["Light diet","Boiled rice","Dal soup","No solid food in first week","Boiled water only"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Baptisia Tinctoria","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"7 days","timing":"Before meals","keynote":"Typhoid state: stupor, offensive odor, dark red face","price_inr":75},
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Great exhaustion, anxiety, midnight aggravation","price_inr":75},
                {"name":"Bryonia","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Headache worse on movement, constipation, dryness","price_inr":75},
            ],
        },
        "cost": {"allopathy":269,"ayurveda":278,"homeopathy":225,"cheapest":"Homeopathy"},
    },

    "type2_diabetes": {
        "name": "Type 2 Diabetes Mellitus", "icd10": "E11", "category": "Metabolic",
        "symptoms": ["excessive thirst","frequent urination","unexplained weight loss","fatigue","blurred vision","slow healing wounds","numbness in feet","baar baar peshab","zyada pyaas"],
        "red_flags": ["blood sugar above 400","diabetic ketoacidosis symptoms","hypoglycemia (shaking sweating confusion)","foot ulcer"],
        "allopathy": {
            "medicines": [
                {"name":"Metformin 500mg","brand":"Glycomet 500","dose":"500mg","freq":"Twice daily","dur":"Lifelong","timing":"With or after meals (reduces GI side effects)","purpose":"First-line antidiabetic, weight neutral","warn":"Stop before CT contrast; avoid alcohol","price_inr":42},
                {"name":"Glimepiride 2mg","brand":"Amaryl 2","dose":"1 tab","freq":"Once daily before breakfast","dur":"As directed","timing":"Before breakfast","purpose":"Stimulates insulin secretion","warn":"Risk of hypoglycemia — carry glucose","price_inr":118},
                {"name":"Metformin 1000mg SR","brand":"Glycomet SR 1g","dose":"1 tab","freq":"Once daily","dur":"Lifelong","timing":"With dinner","purpose":"SR formulation better tolerated","price_inr":98},
            ],
            "tests": ["HbA1c every 3 months","Fasting & PP glucose","Kidney function annually","Urine microalbumin","Lipid profile","Eye checkup annually","Foot exam"],
            "targets": "HbA1c <7% | FBG 80-130 mg/dL | PP <180 mg/dL",
            "avoid": ["Excessive carbs","Sugary drinks","Skipping meals"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Vijaysar wood cup (Pterocarpus marsupium)","brand":"Dia-Care","dose":"Water stored overnight in Vijaysar cup — drink morning","freq":"Once daily empty stomach","dur":"3 months","timing":"Empty stomach morning","purpose":"Clinical evidence for blood sugar reduction","price_inr":285},
                {"name":"Neem Capsule","brand":"Himalaya Neem","dose":"2 caps","freq":"Twice daily","dur":"3 months","timing":"Before meals","purpose":"Hypoglycemic effect","price_inr":125},
                {"name":"Chandraprabha Vati","brand":"Baidyanath","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Classical diabetes formula","price_inr":115},
            ],
            "diet": ["Bitter gourd (karela) juice 50ml daily","Fenugreek seeds soaked in water","Jamun powder","Low glycemic diet","Whole grains over maida"],
            "avoid": ["White rice","Maida products","Sweet fruits","Fruit juices","Sugar"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Syzygium Jambolanum","potency":"Q (Mother Tincture)","brand":"SBL","dose":"10 drops in water","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Specific for diabetes — reduces sugar in urine","price_inr":85},
                {"name":"Uranium Nitricum","potency":"3X","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Diabetes with great emaciation and weakness","price_inr":65},
                {"name":"Phosphoric Acid","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Diabetes from grief or exhaustion, heavy urine","price_inr":75},
            ],
        },
        "cost": {"allopathy":258,"ayurveda":525,"homeopathy":225,"cheapest":"Allopathy"},
    },

    "hypertension": {
        "name": "Hypertension", "icd10": "I10", "category": "Cardiovascular",
        "symptoms": ["usually no symptoms","occipital headache","dizziness","palpitations","visual changes","nosebleed","sir ke peeche dard","chakkar"],
        "red_flags": ["BP above 180/120 with symptoms","severe headache sudden onset","vision loss","chest pain","confusion"],
        "allopathy": {
            "medicines": [
                {"name":"Amlodipine 5mg","brand":"Stamlo 5","dose":"1 tab","freq":"Once daily","dur":"Lifelong","timing":"Morning with or without food","purpose":"Calcium channel blocker — good for elderly, effective","price_inr":58},
                {"name":"Telmisartan 40mg","brand":"Telma 40","dose":"1 tab","freq":"Once daily","dur":"Lifelong","timing":"Morning with or without food","purpose":"ARB — preferred in diabetics, renoprotective","price_inr":142},
                {"name":"Amlodipine 5mg + Telmisartan 40mg","brand":"Telma AM","dose":"1 tab","freq":"Once daily","dur":"Lifelong","timing":"Morning","purpose":"Combination for better control","warn":"Monitor BP regularly","price_inr":185},
            ],
            "tests": ["BP monitoring twice daily","ECG","Echo (cardiac status)","Kidney function","Urine microalbumin","Fundus examination"],
            "targets": "BP <130/80 mmHg",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Sarpagandha Ghan Vati","brand":"Baidyanath Sarpagandha","dose":"1 tab","freq":"Twice daily","dur":"3-6 months","timing":"After meals","purpose":"Natural antihypertensive — clinical evidence","warn":"Avoid in depression — depletes monoamines","price_inr":95},
                {"name":"Arjunarishta","brand":"Dabur Arjunarishta","dose":"25ml","freq":"Twice daily","dur":"3 months","timing":"After meals with equal water","purpose":"Cardiotonic, natural BP reducer","price_inr":148},
                {"name":"Ashwagandha 500mg","brand":"Himalaya Ashwagandha","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Reduces cortisol and stress-related hypertension","price_inr":185},
            ],
            "diet": ["DASH diet","Low salt (<2g/day)","Garlic 2-3 cloves daily","High potassium (banana, spinach)","Avoid pickles/papads"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Rauwolfia Q","potency":"Mother Tincture","brand":"SBL","dose":"15 drops in water","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Hypertension with anxiety, excellent for mild-moderate HTN","price_inr":85},
                {"name":"Natrum Muriaticum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Hypertension from grief/suppressed emotions, craves salt","price_inr":75},
                {"name":"Crataegus Q","potency":"Mother Tincture","brand":"SBL","dose":"20 drops in water","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Heart tonic, mild BP lowering","price_inr":85},
            ],
        },
        "cost": {"allopathy":200,"ayurveda":428,"homeopathy":245,"cheapest":"Allopathy"},
    },

    "iron_deficiency_anemia": {
        "name": "Iron Deficiency Anemia", "icd10": "D50", "category": "Hematological",
        "symptoms": ["fatigue","weakness","pale skin","breathlessness on exertion","palpitations","cold hands feet","brittle nails","pagophagia (eating ice)","thakan","kamzori","pila chehra"],
        "red_flags": ["Hb below 7","heart failure symptoms","severe breathlessness at rest"],
        "allopathy": {
            "medicines": [
                {"name":"Ferrous Ascorbate 100mg","brand":"Orofer-XT","dose":"1 tab","freq":"Once daily","dur":"3-6 months after Hb normal","timing":"Empty stomach or with Vitamin C (enhances absorption)","purpose":"Best-absorbed oral iron, less GI side effects","warn":"Stools will turn black — normal. Take with Vitamin C.","price_inr":178},
                {"name":"Vitamin C 500mg","brand":"Limcee","dose":"1 tab","freq":"With each iron dose","dur":"Same as iron","timing":"With iron tablet","purpose":"Enhances iron absorption by 3-fold","price_inr":35},
                {"name":"Folic Acid 5mg","brand":"Folvite 5","dose":"1 tab","freq":"Once daily","dur":"3 months","timing":"After food","purpose":"Often deficient along with iron","price_inr":28},
            ],
            "tests": ["CBC (Hb, MCV, MCHC, RDW)","Serum Ferritin (most sensitive)","Serum Iron + TIBC","Peripheral blood smear"],
            "targets": "Hb >12g/dL (female), >13.5g/dL (male). Ferritin >30ng/mL.",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Punarnava Mandur","brand":"Baidyanath Punarnava","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals with buttermilk","purpose":"AYUSH-approved iron supplement, gentle on stomach","price_inr":145},
                {"name":"Arogyavardhini Vati","brand":"Baidyanath Arogyavardhini","dose":"2 tabs","freq":"Twice daily","dur":"2 months","timing":"After meals","purpose":"Liver tonic, improves iron absorption","price_inr":95},
            ],
            "diet": ["Jaggery (gur) + sesame (til) — best Ayurvedic iron","Drumstick leaves (moringa)","Pomegranate","Dates (khajoor)","Spinach cooked with lemon"],
            "avoid": ["Tea/coffee with iron-rich meals (blocks absorption)","Calcium with iron"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Ferrum Phos 6X","potency":"6X Biochemic","brand":"SBL Biochemic","dose":"4 tabs","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Biochemic cell salt for iron assimilation","price_inr":65},
                {"name":"China","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Anemia from blood loss, weakness, ringing in ears","price_inr":75},
                {"name":"Calcarea Phos 6X","potency":"6X","brand":"SBL Biochemic","dose":"4 tabs","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Anemia in growing children, bone pain","price_inr":65},
            ],
        },
        "cost": {"allopathy":241,"ayurveda":240,"homeopathy":205,"cheapest":"Homeopathy"},
    },

    "hypothyroidism": {
        "name": "Hypothyroidism", "icd10": "E03.9", "category": "Endocrine",
        "symptoms": ["weight gain","fatigue","cold intolerance","constipation","dry skin","hair loss","depression","slow heart rate","puffiness","vajan badhna","thakaan","sardi lagti hai"],
        "allopathy": {
            "medicines": [
                {"name":"Levothyroxine 50mcg","brand":"Thyronorm 50","dose":"1 tab","freq":"Once daily","dur":"Lifelong","timing":"EMPTY STOMACH 30-60 min before breakfast — critical","purpose":"Thyroid hormone replacement","warn":"Do not take with calcium/iron — take 4 hours apart","price_inr":68},
            ],
            "tests": ["TSH (primary)","Free T3, Free T4","Anti-TPO antibody (Hashimoto's)","Lipid profile"],
            "targets": "TSH 0.5-2.5 mIU/L",
            "note": "TSH check every 6-8 weeks till stable, then 6-monthly",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Kanchanar Guggulu","brand":"Baidyanath Kanchanar","dose":"2 tabs","freq":"3 times daily","dur":"3-6 months","timing":"With warm water before meals","purpose":"Classical thyroid formula in Ayurveda","price_inr":115},
                {"name":"Ashwagandha 500mg","brand":"Himalaya Ashwagandha","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Stimulates thyroid — clinical evidence exists","warn":"Monitor TSH monthly when combining with thyroid meds","price_inr":185},
                {"name":"Guggulu","brand":"Patanjali Guggul","dose":"1 tab","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Stimulates thyroid, cholesterol reduction","price_inr":85},
            ],
            "diet": ["Iodized salt always","Brazil nuts (selenium)","Coconut oil","Avoid raw cruciferous vegetables in large amounts"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Calcarea Carb","potency":"200C","brand":"SBL","dose":"4 pills","freq":"Weekly","dur":"3 months","timing":"Before meals","keynote":"Obese, cold, sweaty, hypothyroid constitution","price_inr":95},
                {"name":"Lycopodium","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"3 months","timing":"Before meals","keynote":"Right-sided, bloating, 4-8pm aggravation","price_inr":75},
            ],
        },
        "cost": {"allopathy":68,"ayurveda":385,"homeopathy":170,"cheapest":"Allopathy"},
    },

    "asthma": {
        "name": "Bronchial Asthma", "icd10": "J45", "category": "Respiratory",
        "symptoms": ["wheezing","breathlessness","chest tightness","cough especially at night","exercise-induced symptoms","saans mein seeti","sans phoolna"],
        "red_flags": ["unable to speak full sentences","SpO2 below 92%","silent chest","blue lips"],
        "allopathy": {
            "medicines": [
                {"name":"Salbutamol inhaler","brand":"Asthalin HFA","dose":"2 puffs","freq":"PRN (rescue — not daily)","dur":"As needed","timing":"When symptoms occur","purpose":"Rapid bronchodilation — RESCUE inhaler","warn":"SABA addiction is dangerous — use sparingly","price_inr":128},
                {"name":"Budesonide inhaler 200","brand":"Budecort 200","dose":"1-2 puffs","freq":"Twice daily","dur":"Maintenance (months)","timing":"Morning + evening","purpose":"Inhaled steroid — prevents attacks, reduces inflammation","warn":"Rinse mouth after use to prevent oral thrush","price_inr":285},
                {"name":"Montelukast 10mg","brand":"Montair 10","dose":"1 tab","freq":"Once daily","dur":"Long-term","timing":"Evening/night","purpose":"LTRA — especially for allergic asthma","price_inr":198},
            ],
            "tests": ["Spirometry (PFT)","Peak flow meter (daily monitoring)","Chest X-ray","IgE levels","Skin prick test for allergens"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Sitopaladi Churna","brand":"Baidyanath Sitopaladi","dose":"3g","freq":"Twice daily","dur":"3 months","timing":"With honey before meals","purpose":"Classical respiratory formulation, mucolytic","price_inr":85},
                {"name":"Vasavaleha","brand":"Dabur Vasavaleha","dose":"1 tsp","freq":"Twice daily","dur":"2-3 months","timing":"With warm milk","purpose":"Adhatoda vasica — bronchodilator + expectorant","price_inr":125},
                {"name":"Haridra (Turmeric) 500mg","brand":"Himalaya Haridra","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"After meals with warm milk","purpose":"Anti-inflammatory, anti-allergic","price_inr":95},
            ],
            "diet": ["Warm water always","Avoid cold food/drinks","Avoid known allergens","Light diet","Steam inhalation"],
            "avoid": ["Cold water","Air conditioning direct airflow","Dust/pollen","Pet dander","Strong perfumes"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Asthma with anxiety, restlessness, midnight attacks, better sitting up","price_inr":75},
                {"name":"Ipecacuanha","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily during attack","dur":"2 months","timing":"Before meals","keynote":"Constant nausea with wheezing, suffocative attacks","price_inr":75},
            ],
        },
        "cost": {"allopathy":611,"ayurveda":305,"homeopathy":150,"cheapest":"Homeopathy"},
    },

    "peptic_ulcer": {
        "name": "Peptic Ulcer Disease", "icd10": "K27", "category": "GI",
        "symptoms": ["burning stomach pain","nausea","bloating","loss of appetite","pain relieved by food","pain worsened by food","jalan pet mein","khali pet mein dard"],
        "red_flags": ["blood in vomit","black tarry stool","severe sudden abdominal pain","weight loss"],
        "allopathy": {
            "medicines": [
                {"name":"Pantoprazole 40mg","brand":"Pan-40","dose":"1 tab","freq":"Once daily","dur":"4-8 weeks","timing":"Empty stomach 30 min before breakfast","purpose":"PPI — most effective acid suppressant","price_inr":84},
                {"name":"H. pylori Triple Therapy","brand":"Combo pack","dose":"Full course","freq":"See below","dur":"14 days","timing":"After food","purpose":"If H. pylori positive: Pantoprazole 40mg + Amoxicillin 1g + Clarithromycin 500mg — all twice daily","warn":"Complete full 14 days even if feeling better","price_inr":385},
                {"name":"Sucralfate 1g","brand":"Sucral","dose":"1 tab","freq":"4 times daily","dur":"4-8 weeks","timing":"Before meals and bedtime","purpose":"Mucosal protectant","price_inr":98},
            ],
            "tests": ["H. pylori (Urea breath test / stool antigen)","Upper GI endoscopy","Biopsy if ulcer seen"],
            "avoid": ["NSAIDs","Aspirin","Steroids","Alcohol","Smoking","Coffee","Spicy food"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Mulethi (Licorice)","brand":"Patanjali Mulethi","dose":"3g powder with milk","freq":"Twice daily","dur":"4-8 weeks","timing":"Before meals","purpose":"Mucosal protective — clinical evidence for H. pylori","price_inr":65},
                {"name":"Avipattikar Churna","brand":"Patanjali Avipattikar","dose":"3g","freq":"Twice daily","dur":"6 weeks","timing":"With warm water before meals","purpose":"Classical acidity and ulcer formulation","price_inr":72},
                {"name":"Shatavari 500mg","brand":"Himalaya Shatavari","dose":"2 caps","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Gastroprotective, anti-ulcer","price_inr":178},
            ],
            "diet": ["Coconut water","Cold milk","Small frequent meals","Boiled vegetables","Avoid spicy oily food"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Nux Vomica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"At night","dur":"4-8 weeks","timing":"1 hour before sleep","keynote":"Acidity from coffee, alcohol, stress, overwork","price_inr":75},
                {"name":"Lycopodium","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Bloating, worse 4-8pm, flatulence","price_inr":75},
                {"name":"Argentum Nitricum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"6 weeks","timing":"Before meals","keynote":"Gastric pain with flatulence, craves sweet (worsens pain)","price_inr":75},
            ],
        },
        "cost": {"allopathy":567,"ayurveda":315,"homeopathy":225,"cheapest":"Homeopathy"},
    },

    "uti": {
        "name": "Urinary Tract Infection", "icd10": "N39.0", "category": "Urological",
        "symptoms": ["burning urination","frequent urination","cloudy urine","lower abdominal pain","urgency","peshab mein jalan","baar baar peshab"],
        "red_flags": ["fever above 38°C with UTI signs","flank pain","nausea vomiting","blood in urine"],
        "allopathy": {
            "medicines": [
                {"name":"Nitrofurantoin 100mg","brand":"Macrobid","dose":"100mg","freq":"Twice daily","dur":"5 days","timing":"With food (reduces GI side effects)","purpose":"First-line for uncomplicated UTI","warn":"Avoid in kidney failure (eGFR<30). Urine may turn brown — normal.","price_inr":125},
                {"name":"Ciprofloxacin 500mg","brand":"Ciplox 500","dose":"500mg","freq":"Twice daily","dur":"3-7 days","timing":"Empty stomach or 2 hrs after meal","purpose":"Fluoroquinolone — use if Nitrofurantoin fails","warn":"Avoid in pregnancy. Resistance is increasing.","price_inr":75},
                {"name":"Cefixime 200mg","brand":"Taxim-O","dose":"1 tab","freq":"Twice daily","dur":"7 days","timing":"After food","purpose":"For resistant UTI or upper UTI","price_inr":142},
            ],
            "tests": ["Urine R/M (routine and microscopy)","Urine culture and sensitivity","USG KUB if recurrent"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Cystone","brand":"Himalaya Cystone","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Antiseptic for urinary tract, dissolves crystals","price_inr":148},
                {"name":"Chandraprabha Vati","brand":"Baidyanath","dose":"2 tabs","freq":"Twice daily","dur":"6 weeks","timing":"After meals","purpose":"Classical UTI formula, diuretic","price_inr":115},
            ],
            "diet": ["Drink 3+ liters water","Cranberry juice","Coconut water","Barley water","Avoid spicy food"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Cantharis","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every 2-3 hrs in acute phase","dur":"3-5 days","timing":"Before meals","keynote":"Intense burning, cutting pain during and after urination — specific UTI remedy","price_inr":75},
                {"name":"Apis Mellifica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Burning stinging pain, little urine, no thirst","price_inr":75},
            ],
        },
        "cost": {"allopathy":342,"ayurveda":263,"homeopathy":150,"cheapest":"Homeopathy"},
    },

    "migraine": {
        "name": "Migraine Headache", "icd10": "G43", "category": "Neurological",
        "symptoms": ["unilateral throbbing headache","nausea vomiting","photophobia","phonophobia","aura visual disturbances","4-72 hour attacks","ek taraf sir dard","roshan se takleef"],
        "red_flags": ["thunderclap headache","fever with headache","neurological deficits","headache worsening over days"],
        "allopathy": {
            "medicines": [
                {"name":"Sumatriptan 50mg","brand":"Suminat 50","dose":"50-100mg at onset","freq":"May repeat after 2hrs (max 2/day)","dur":"PRN","timing":"At onset of migraine","purpose":"Triptan — most effective acute treatment","warn":"Avoid in CAD, uncontrolled HTN, recent stroke","price_inr":198},
                {"name":"Ibuprofen 400mg","brand":"Brufen 400","dose":"1-2 tabs","freq":"Every 6-8 hrs","dur":"PRN (max 3 days)","timing":"At headache onset with food","purpose":"NSAID — effective for mild-moderate migraine","price_inr":38},
                {"name":"Propranolol 40mg","brand":"Inderal 40","dose":"40-80mg","freq":"Twice daily","dur":"3-6 months (preventive)","timing":"With food","purpose":"Beta-blocker — PREVENTION (if >3 attacks/month)","price_inr":35},
            ],
            "tests": ["Diary to track triggers","CT/MRI brain if atypical features","Eye examination"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Pathyadi Kwath","brand":"Baidyanath Pathyadi","dose":"30ml","freq":"Twice daily","dur":"3 months","timing":"Before meals","purpose":"Classical migraine formulation","price_inr":85},
                {"name":"Brahmi Vati","brand":"Divya Brahmi Vati","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals with milk","purpose":"Brain tonic, reduces headache frequency","price_inr":95},
                {"name":"Sitopaladi Churna","brand":"Baidyanath Sitopaladi","dose":"3g","freq":"Once daily","dur":"2 months","timing":"With honey","purpose":"If migraine with nasal congestion component","price_inr":85},
            ],
            "external": ["Sesame oil head massage daily","Ksheerabala oil Nasya (2 drops each nostril)"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Iris Versicolor","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Migraine with visual aura, nausea, weekend migraines","price_inr":75},
                {"name":"Gelsemium","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Dull heavy headache starting from neck, drooping, no thirst","price_inr":75},
                {"name":"Belladonna","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every hour during attack","dur":"Acute only","timing":"During attack","keynote":"Sudden violent headache, flushed face, light-sound sensitive","price_inr":75},
            ],
        },
        "cost": {"allopathy":271,"ayurveda":265,"homeopathy":225,"cheapest":"Homeopathy"},
    },

    "chickenpox": {
        "name": "Chickenpox (Varicella)", "icd10": "B01", "category": "Infectious",
        "symptoms": ["itchy blister rash all over body","fever","fatigue","rash starts face spreads to body","khujli wale daane","blisters"],
        "red_flags": ["pneumonia signs","encephalitis","secondary bacterial infection of blisters","immunocompromised patient"],
        "allopathy": {
            "medicines": [
                {"name":"Acyclovir 400mg","brand":"Acivir 400","dose":"800mg (2 tabs of 400mg)","freq":"5 times daily","dur":"7 days","timing":"With food","purpose":"Antiviral — reduces duration if started within 24-48hrs of rash","warn":"Mandatory in adults, immunocompromised, newborns","price_inr":168},
                {"name":"Cetirizine 10mg","brand":"Cetzine 10","dose":"1 tab","freq":"Once daily at night","dur":"7-10 days","timing":"Night","purpose":"Reduce itching","price_inr":48},
                {"name":"Calamine lotion","brand":"Lacto Calamine","dose":"Apply to lesions","freq":"3-4 times daily","dur":"7-10 days","timing":"As needed","purpose":"Soothing, reduces itch","warn":"External use only","price_inr":95},
                {"name":"Paracetamol 500mg","brand":"Crocin","dose":"1 tab","freq":"Every 6 hrs PRN","dur":"Till fever","timing":"After food","purpose":"Fever control","warn":"NEVER Aspirin in children — Reye's syndrome","price_inr":18},
            ],
            "avoid": ["Aspirin in children","Scratching (scarring + secondary infection)","Contact with pregnant women, newborns, immunocompromised"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Neem Capsule","brand":"Himalaya Neem","dose":"2 caps","freq":"Twice daily","dur":"7 days","timing":"After meals","purpose":"Antiviral, antibacterial","price_inr":125},
                {"name":"Haridra (Turmeric) 500mg","brand":"Himalaya Haridra","dose":"1 cap","freq":"Twice daily","dur":"10 days","timing":"After meals with milk","purpose":"Anti-inflammatory, anti-itch","price_inr":95},
            ],
            "external": ["Neem leaf bath (boil neem leaves in bath water)","Sandalwood paste externally","Coconut oil after lesions crust"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Rhus Tox","potency":"30C","brand":"SBL","dose":"4 pills","freq":"4 times daily","dur":"7 days","timing":"Before meals","keynote":"Itchy vesicular rash with restlessness — SPECIFIC for chickenpox","price_inr":75},
                {"name":"Antimonium Crudum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"7 days","timing":"Before meals","keynote":"Chickenpox with thick crusts, white-coated tongue","price_inr":75},
            ],
        },
        "cost": {"allopathy":329,"ayurveda":220,"homeopathy":150,"cheapest":"Homeopathy"},
    },

    "arthritis_rheumatoid": {
        "name": "Rheumatoid Arthritis", "icd10": "M06.9", "category": "Autoimmune",
        "symptoms": ["morning stiffness more than 1 hour","symmetrical small joint swelling","fatigue","fever","rheumatoid nodules","subah akadahat","jodo mein sujan"],
        "allopathy": {
            "medicines": [
                {"name":"Methotrexate","brand":"Folitrax","dose":"7.5-25mg once weekly","freq":"Once weekly (NOT daily)","dur":"Long-term","timing":"With food on same day each week","purpose":"DMARD of choice — reduces joint damage","warn":"Take Folic acid 5mg on non-MTX days. Monthly LFT monitoring.","price_inr":85},
                {"name":"Hydroxychloroquine 200mg","brand":"HCQ-200","dose":"200-400mg","freq":"Once daily","dur":"Long-term","timing":"With food","purpose":"DMARD — adjunct to MTX","warn":"Annual eye check (retinal toxicity rare but irreversible)","price_inr":85},
            ],
            "tests": ["RF (Rheumatoid Factor)","Anti-CCP (most specific)","CRP","ESR","X-ray hands/feet","Ultrasound joints"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Yogaraj Guggulu","brand":"Baidyanath Yogaraj","dose":"2 tabs","freq":"3 times daily","dur":"6 months","timing":"After meals with warm water","purpose":"Classical formula for Vata-Ama (RA)","price_inr":125},
                {"name":"Punarnavadi Guggulu","brand":"Baidyanath","dose":"2 tabs","freq":"3 times daily","dur":"6 months","timing":"After meals","purpose":"Reduces inflammation and swelling","price_inr":115},
            ],
            "panchakarma": ["Virechana","Basti (Enema)","Kati Basti for low back","Janu Basti for knees"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Rhus Tox","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Better by motion, worse initial movement and cold damp weather","price_inr":75},
                {"name":"Bryonia","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 months","timing":"Before meals","keynote":"Worse ANY motion, better absolute rest, irritable","price_inr":75},
            ],
        },
        "cost": {"allopathy":170,"ayurveda":240,"homeopathy":150,"cheapest":"Homeopathy"},
    },

    "anxiety_disorder": {
        "name": "Generalized Anxiety Disorder", "icd10": "F41.1", "category": "Psychiatric",
        "symptoms": ["excessive worry","restlessness","fatigue","difficulty concentrating","irritability","muscle tension","sleep problems","ghabrahat","bechainee","dar"],
        "red_flags": ["panic attacks","suicidal ideation","hallucinations","unable to function"],
        "allopathy": {
            "medicines": [
                {"name":"Escitalopram 10mg","brand":"Nexito 10","dose":"10mg","freq":"Once daily","dur":"6-12 months minimum","timing":"Morning","purpose":"SSRI — first-line for anxiety","warn":"Takes 4-6 weeks for effect. Do NOT stop abruptly. Sexual side effects possible.","price_inr":156},
                {"name":"Clonazepam 0.5mg","brand":"Clonotril 0.5","dose":"0.5mg","freq":"Twice daily (max 4 weeks only)","dur":"Short-term (max 4 weeks)","timing":"Night (sedating)","purpose":"Benzodiazepine — for initial anxiety management only","warn":"Habit-forming. Max 4 weeks. Gradually taper.","price_inr":48},
            ],
            "note": "Combine with CBT (Cognitive Behavioral Therapy) — equally effective as medication",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Ashwagandha 500mg","brand":"Himalaya Ashwagandha","dose":"1 cap","freq":"Twice daily","dur":"3-6 months","timing":"After meals","purpose":"Adaptogen — reduces cortisol, clinical evidence for anxiety","price_inr":185},
                {"name":"Brahmi Vati","brand":"Divya Brahmi Vati","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals with milk","purpose":"Medhya Rasayana — calms mind","price_inr":95},
                {"name":"Saraswatarishta","brand":"Dabur Saraswatarishta","dose":"25ml","freq":"Twice daily","dur":"3 months","timing":"After meals with equal water","purpose":"Classical nervine tonic","price_inr":145},
            ],
            "panchakarma": ["Shirodhara (oil streaming on forehead)","Abhyanga (full body oil massage)"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Anxiety about health (hypochondria), restlessness, midnight anxiety","price_inr":75},
                {"name":"Aconitum Napellus","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Sudden intense anxiety/panic, fear of death","price_inr":75},
            ],
        },
        "cost": {"allopathy":204,"ayurveda":425,"homeopathy":150,"cheapest":"Homeopathy"},
    },

    "viral_fever": {
        "name": "Viral Fever", "icd10": "B34.9", "category": "Infectious",
        "symptoms": ["viral fever","fever","body ache","fatigue","mild headache","weakness","bukhar","halka dard","kamzori","thakan"],
        "allopathy": {
            "medicines": [
                {"name":"Paracetamol 500mg","brand":"Dolo 500 / Crocin","dose":"500mg","freq":"SOS (max 4 times/day)","dur":"3 days","timing":"After food","purpose":"Reduces fever and body ache","price_inr":30},
                {"name":"B-Complex with Vitamin C","brand":"Becosules Z","dose":"1 cap","freq":"Once daily","dur":"5 days","timing":"After food","purpose":"Reduces fatigue and supports immunity","price_inr":45},
            ],
            "tests": ["CBC (if fever > 3 days)"],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Giloy Ghanvati","brand":"Patanjali","dose":"2 tabs","freq":"Twice daily","dur":"5 days","timing":"After meals","purpose":"Immunomodulator, reduces fever naturally","price_inr":95},
                {"name":"Sudarshan Ghanvati","brand":"Zandu","dose":"2 tabs","freq":"Twice daily","dur":"5 days","timing":"With warm water","purpose":"Antipyretic, clears toxins","price_inr":110},
            ],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Eupatorium Perfoliatum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 days","timing":"Before meals","keynote":"Bone-breaking body ache with fever","price_inr":75},
                {"name":"Gelsemium","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 days","timing":"Before meals","keynote":"Dullness, dizziness, fatigue with fever","price_inr":75},
            ],
        },
        "cost": {"allopathy":75,"ayurveda":205,"homeopathy":150,"cheapest":"Allopathy"},
    },

    "common_cold": {
        "name": "Common Cold (Upper Respiratory Infection)", "icd10": "J06.9", "category": "Infectious",
        "symptoms": ["runny nose","sore throat","mild fever","cold","cough","sneezing","congestion","body ache","zukam","gala kharab","naak behna","halka bukhar","sardi","khansi"],
        "allopathy": {
            "medicines": [
                {"name":"Paracetamol 650mg","brand":"Dolo-650","dose":"1 tab","freq":"Every 6 hrs PRN","dur":"3-5 days","timing":"After food","purpose":"Fever and body ache","price_inr":32},
                {"name":"Cetirizine 10mg","brand":"Cetzine 10","dose":"1 tab","freq":"Once at night","dur":"5 days","timing":"Night (sedating)","purpose":"Runny nose, sneezing","price_inr":48},
                {"name":"Ambroxol syrup","brand":"Ambrodil","dose":"10ml","freq":"3 times daily","dur":"5 days","timing":"After food","purpose":"Mucolytic — loosens mucus","price_inr":68},
            ],
            "note": "NO antibiotics — viral infection. Antibiotics are useless and cause resistance.",
        },
        "ayurveda": {
            "medicines": [
                {"name":"Sitopaladi Churna","brand":"Baidyanath Sitopaladi","dose":"3g","freq":"3 times daily","dur":"5 days","timing":"With honey","purpose":"Cough, cold, bronchitis — classical formula","price_inr":85},
                {"name":"Trikatu Churna","brand":"Patanjali Trikatu","dose":"2g","freq":"Twice daily","dur":"5 days","timing":"With warm water before meals","purpose":"Ginger+pepper+pipali — decongestant, antimicrobial","price_inr":65},
            ],
            "home_remedies": ["Ginger+honey+tulsi decoction 3x daily","Steam inhalation with eucalyptus oil","Haldi doodh (golden milk) at night","Salt water gargle"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Aconitum Napellus","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every 2 hrs at onset","dur":"2-3 days","timing":"Frequent dosing","keynote":"Start within FIRST 24 HOURS — cold from cold dry wind, sudden onset","price_inr":75},
                {"name":"Nux Vomica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Cold from chilling, sneezing, blocked nose, irritable","price_inr":75},
            ],
        },
        "cost": {"allopathy":148,"ayurveda":150,"homeopathy":150,"cheapest":"Allopathy"},
    },

    "acute_diarrhea": {
        "name": "Acute Diarrhea / Gastroenteritis", "icd10": "A09", "category": "GI",
        "symptoms": ["loose watery stools more than 3 per day","abdominal cramps","nausea","vomiting","fever","dast","pet dard ulti"],
        "red_flags": ["blood in stool","severe dehydration (sunken eyes, no urine)","fever above 39°C","infant not feeding"],
        "allopathy": {
            "medicines": [
                {"name":"ORS sachet","brand":"WHO ORS/Electral","dose":"200-400ml after each loose stool","freq":"Continuous sipping","dur":"Till diarrhea stops","timing":"After every loose motion","purpose":"Prevent dehydration — MOST IMPORTANT treatment","price_inr":12},
                {"name":"Zinc 20mg","brand":"Zinc sachet/Zincovit","dose":"20mg","freq":"Once daily","dur":"14 days","timing":"After food","purpose":"MANDATORY in children <5 — reduces severity by 25%","price_inr":48},
                {"name":"Loperamide 2mg","brand":"Imodium","dose":"2mg stat then 1mg after each loose stool","freq":"Max 8mg/day","dur":"2-3 days max","timing":"As needed","purpose":"Slows bowel movement","warn":"NOT for children, bloody diarrhea, or fever — use only for adult watery diarrhea","price_inr":62},
                {"name":"Metronidazole 400mg","brand":"Metrogyl","dose":"400mg","freq":"3 times daily","dur":"5-7 days","timing":"After food","purpose":"For amoebic dysentery (blood in stool, mucus)","price_inr":55},
            ],
        },
        "ayurveda": {
            "medicines": [
                {"name":"Kutajghan Vati","brand":"Baidyanath Kutajghan","dose":"2 tabs","freq":"3 times daily","dur":"5 days","timing":"Before meals with buttermilk","purpose":"Best Ayurvedic antidiarrheal — Holarrhena antidysenterica","price_inr":85},
                {"name":"Bilva (Bael fruit) powder","brand":"Patanjali Bilva Churna","dose":"5g","freq":"Twice daily","dur":"5 days","timing":"With warm water","purpose":"Classical antidiarrheal, astringent","price_inr":55},
            ],
            "diet": ["BRAT diet (Banana Rice Apple Toast)","ORS/coconut water","Curd rice","Avoid milk, raw food, spicy food"],
        },
        "homeopathy": {
            "medicines": [
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every 2 hrs acute","dur":"3-5 days","timing":"Before meals","keynote":"Food poisoning diarrhea, burning vomiting, midnight worse, great weakness","price_inr":75},
                {"name":"Nux Vomica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 days","timing":"Before meals","keynote":"Diarrhea from overeating, alcohol, spicy food — frequent small amounts","price_inr":75},
            ],
        },
        "cost": {"allopathy":177,"ayurveda":140,"homeopathy":150,"cheapest":"Ayurveda"},
    },
}

# --- MERGE EXTENDED DISEASES ---
try:
    from data.extended_diseases import EXTENDED_DISEASES
    DISEASES.update(EXTENDED_DISEASES)
except ImportError:
    pass



# ─────────────────────────────────────────────────────────────────────────────
# DRUG INTERACTION DATABASE (Allopathic + Ayurvedic cross-system)
# ─────────────────────────────────────────────────────────────────────────────
INTERACTIONS: list[dict] = [
    # ── SEVERE ───────────────────────────────────────────────────────────────
    {"d1":"Warfarin","d2":"Aspirin",         "sev":"SEVERE",   "effect":"Severe bleeding — additive anticoagulation + antiplatelet",       "mgmt":"Avoid. Use Paracetamol for pain if needed."},
    {"d1":"Warfarin","d2":"Garlic supplement","sev":"SEVERE",  "effect":"Increased INR, bleeding risk",                                    "mgmt":"Avoid garlic supplements. Culinary amounts OK."},
    {"d1":"Metformin","d2":"Alcohol",         "sev":"SEVERE",  "effect":"Lactic acidosis — potentially fatal",                             "mgmt":"No alcohol with Metformin. Absolute."},
    {"d1":"Metformin","d2":"IV Contrast dye", "sev":"SEVERE",  "effect":"Lactic acidosis from contrast-induced renal impairment",          "mgmt":"Stop Metformin 48 hrs before contrast. Resume after 48 hrs if renal function normal."},
    {"d1":"Sildenafil","d2":"Nitrates",        "sev":"SEVERE",  "effect":"Life-threatening hypotension",                                    "mgmt":"Absolute contraindication. Never combine."},
    {"d1":"SSRIs","d2":"Tramadol",            "sev":"SEVERE",  "effect":"Serotonin syndrome — fever, rigidity, seizures",                  "mgmt":"Avoid. Use Paracetamol/NSAIDs for pain."},
    {"d1":"Methotrexate","d2":"NSAIDs",       "sev":"SEVERE",  "effect":"MTX toxicity: bone marrow suppression, renal failure",            "mgmt":"Avoid NSAIDs with MTX. Use Paracetamol."},
    {"d1":"Sarpagandha","d2":"Antidepressants MAOI","sev":"SEVERE","effect":"Hypertensive crisis",                                         "mgmt":"Never combine."},
    {"d1":"St John's Wort","d2":"SSRIs",      "sev":"SEVERE",  "effect":"Serotonin syndrome",                                              "mgmt":"Never combine."},
    {"d1":"St John's Wort","d2":"Oral contraceptives","sev":"SEVERE","effect":"Contraceptive failure — CYP3A4 induction",                  "mgmt":"Never combine. Use alternate contraception."},
    {"d1":"ACE inhibitors","d2":"Potassium", "sev":"SEVERE",  "effect":"Life-threatening hyperkalemia",                                   "mgmt":"Avoid potassium supplements unless clearly deficient. Monitor serum K+."},

    # ── MODERATE ─────────────────────────────────────────────────────────────
    {"d1":"Clopidogrel","d2":"Omeprazole",    "sev":"MODERATE","effect":"Reduced antiplatelet effect — CYP2C19 inhibition",                "mgmt":"Switch to Pantoprazole or Rabeprazole."},
    {"d1":"Levothyroxine","d2":"Calcium",     "sev":"MODERATE","effect":"Reduced thyroid hormone absorption",                              "mgmt":"Take Levothyroxine 4 hours apart from calcium."},
    {"d1":"Levothyroxine","d2":"Iron",        "sev":"MODERATE","effect":"Reduced thyroid hormone absorption",                              "mgmt":"Take Levothyroxine 4 hours apart from iron."},
    {"d1":"Ciprofloxacin","d2":"Antacids",    "sev":"MODERATE","effect":"90% reduction in Ciprofloxacin absorption",                      "mgmt":"Take Ciprofloxacin 2 hrs before or 6 hrs after antacids."},
    {"d1":"Ashwagandha","d2":"Thyroid meds",  "sev":"MODERATE","effect":"Ashwagandha stimulates thyroid — risk of hyperthyroid on meds",   "mgmt":"Monitor TSH monthly when combining."},
    {"d1":"Ashwagandha","d2":"Sedatives",     "sev":"MODERATE","effect":"Excessive CNS depression",                                        "mgmt":"Reduce sedative dose. Monitor drowsiness."},
    {"d1":"Fenugreek","d2":"Metformin",       "sev":"MODERATE","effect":"Additive hypoglycemia",                                           "mgmt":"Monitor blood glucose. May need Metformin dose reduction."},
    {"d1":"Giloy","d2":"Immunosuppressants",  "sev":"MODERATE","effect":"Giloy stimulates immunity — opposes immunosuppression",           "mgmt":"Avoid in transplant patients or autoimmune on immunosuppressants."},
    {"d1":"Ginger high dose","d2":"Anticoagulants","sev":"MODERATE","effect":"Increased bleeding risk — inhibits platelet aggregation",    "mgmt":"Culinary ginger OK. Avoid ginger supplements with anticoagulants."},
    {"d1":"Turmeric high dose","d2":"Anticoagulants","sev":"MODERATE","effect":"Mild anticoagulant effect at high doses",                  "mgmt":"Culinary turmeric OK. Avoid supplements with anticoagulants."},
    {"d1":"Neem","d2":"Antidiabetics",        "sev":"MODERATE","effect":"Additive hypoglycemia",                                           "mgmt":"Monitor blood glucose carefully."},
    {"d1":"Triphala","d2":"Anticoagulants",   "sev":"MODERATE","effect":"Amalaki in Triphala may potentiate anticoagulation",              "mgmt":"Monitor INR. Report unusual bruising."},
    {"d1":"Sarpagandha","d2":"Antihypertensives","sev":"MODERATE","effect":"Excessive BP drop",                                            "mgmt":"Monitor BP regularly. May need dose reduction."},
    {"d1":"Atorvastatin","d2":"Clarithromycin","sev":"MODERATE","effect":"Increased statin levels — rhabdomyolysis risk",                  "mgmt":"Use Azithromycin instead or reduce statin dose during antibiotic course."},
]


def search_by_symptom(text: str) -> list[str]:
    """Return disease keys matching given symptom text.
    Uses both substring matching AND individual word matching for better recall.
    """
    text_l = text.lower()
    # Extract individual meaningful words (length > 2 to skip 'and', 'or', etc.)
    words = [w for w in text_l.replace(',', ' ').replace('.', ' ').split() if len(w) > 2]
    
    results = []
    for k, v in DISEASES.items():
        symptoms = v.get("symptoms", [])
        # Original substring match
        if any(s in text_l or text_l in s for s in symptoms):
            results.append(k)
            continue
        # Word-level match: any user word found in any symptom keyword
        if any(word in s or s in word for word in words for s in symptoms):
            results.append(k)
    return results


def get_interactions_for(medicine: str) -> list[dict]:
    """Return all interactions involving a medicine."""
    m = medicine.lower()
    return [i for i in INTERACTIONS
            if m in i["d1"].lower() or m in i["d2"].lower()]


def get_price(medicine: str) -> dict:
    """Fuzzy price lookup. Returns best matching price dict."""
    ml = medicine.lower()
    for key, val in PRICES.items():
        kl = key.lower()
        # Exact or partial match on first significant word
        kw = [w for w in kl.split() if len(w) > 3]
        if kw and kw[0] in ml:
            return {"key": key, "brand": val["brand"], "brand_mrp": val["b"], "generic_mrp": val["g"]}
    return {}


# ── Ayurvedic Herbs KB (for dataset builder) ──────────────────────────────────
AYURVEDIC_HERBS_KB = {
    "ashwagandha": {"scientific":"Withania somnifera","hindi":"अश्वगंधा","properties":"Adaptogen, Immunomodulator","indications":["stress","anxiety","hypothyroidism","diabetes","fatigue"],"dose":"300-600mg extract daily","safety":"Avoid in pregnancy and hyperthyroidism.","brands":["Himalaya Ashwagandha","Patanjali Ashwagandhaghan"]},
    "giloy":       {"scientific":"Tinospora cordifolia","hindi":"गिलोय","properties":"Immunomodulator, Antipyretic","indications":["fever","dengue","malaria","arthritis","diabetes"],"dose":"300mg extract twice daily","safety":"Avoid in autoimmune disease on immunosuppressants.","brands":["Himalaya Guduchi","Patanjali Giloy Sat"]},
    "brahmi":      {"scientific":"Bacopa monnieri","hindi":"ब्राह्मी","properties":"Medhya, Adaptogen, Antioxidant","indications":["memory","anxiety","ADHD","depression"],"dose":"300mg extract twice daily","safety":"May cause GI upset initially.","brands":["Himalaya Bacopa","Patanjali Divya Medha Vati"]},
    "tulsi":       {"scientific":"Ocimum tenuiflorum","hindi":"तुलसी","properties":"Antibacterial, Antiviral, Adaptogen","indications":["cold","cough","fever","stress","diabetes"],"dose":"5-6 leaves or 300mg extract daily","safety":"Very safe.","brands":["Himalaya Tulasi","Patanjali Tulsi drops"]},
    "triphala":    {"scientific":"Amalaki+Bibhitaki+Haritaki","hindi":"त्रिफला","properties":"Laxative, Antioxidant, Detoxifying","indications":["constipation","eye care","obesity","digestion"],"dose":"5g powder at bedtime","safety":"Avoid in diarrhea.","brands":["Himalaya Triphala","Patanjali Triphala Churna"]},
    "neem":        {"scientific":"Azadirachta indica","hindi":"नीम","properties":"Antibacterial, Antifungal, Antidiabetic","indications":["skin infections","diabetes","malaria"],"dose":"2 caps twice daily after meals","safety":"Avoid in pregnancy.","brands":["Himalaya Neem","Patanjali Neem Ghanvati"]},
}

# ── Homeopathic Remedies KB (for dataset builder) ─────────────────────────────
HOMEOPATHIC_REMEDIES_KB = {
    "Arsenicum Album":         {"keynotes":"Anxiety, restlessness, burning pains midnight worse","uses":["diarrhea","asthma","food poisoning","anxiety","COVID"]},
    "Belladonna":              {"keynotes":"Sudden onset, redness, burning heat, throbbing","uses":["high fever","headache","tonsillitis","UTI"]},
    "Nux Vomica":              {"keynotes":"Over-indulgence, irritability, constipation with urging","uses":["acidity","constipation","hangover","IBS"]},
    "Eupatorium Perfoliatum":  {"keynotes":"Bone-breaking pain with fever, eyeballs sore","uses":["dengue fever","influenza","malaria"]},
    "Rhus Toxicodendron":      {"keynotes":"Better by motion, worse initial movement, restlessness","uses":["arthritis","chickenpox","urticaria","sprains"]},
    "Lycopodium":              {"keynotes":"Bloating 4-8pm, right-sided, flatulence, lack confidence","uses":["IBS","bloating","right kidney stones"]},
    "Pulsatilla":              {"keynotes":"Changeability, bland discharges, weepy, worse heat","uses":["female complaints","sinusitis","ear infections"]},
    "Calcarea Carbonica":      {"keynotes":"Obese, chilly, sweaty, hypothyroid constitution","uses":["hypothyroidism","obesity","bone problems"]},
}


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC EXPANSION (Added via AI)
# ─────────────────────────────────────────────────────────────────────────────

NEW_PRICES = {
    # Antidepressants/Anxiety
    "Fluoxetine 20mg": {"brand":"Fludac 20", "b":55, "g":18},
    "Propranolol 40mg": {"brand":"Inderal 40", "b":45, "g":15},
    "Zolpidem 5mg": {"brand":"Zolfresh 5", "b":85, "g":28},
    
    # Migraine
    "Sumatriptan 50mg": {"brand":"Suminat 50", "b":198, "g":68},
    "Naproxen 500mg": {"brand":"Naprosyn 500", "b":65, "g":22},
    
    # PCOS / Women's Health
    "Myo-Inositol + D-Chiro": {"brand":"Ovares", "b":285, "g":95},
    
    # Dermatology
    "Isotretinoin 20mg": {"brand":"Isoin 20", "b":245, "g":85},
    "Adapalene gel": {"brand":"Adaferin", "b":195, "g":75},
    "Salicylic Acid Face Wash": {"brand":"Saslic", "b":250, "g":100},
    
    # Covid / Antiviral
    "Nirmatrelvir/Ritonavir": {"brand":"Paxlovid", "b":4500, "g":1500},
    "Molnupiravir 200mg": {"brand":"Molflu 200", "b":1250, "g":450},

    # Arthritis/Gout
    "Febuxostat 40mg": {"brand":"Febutaz 40", "b":145, "g":48},
    "Allopurinol 100mg": {"brand":"Zyloric 100", "b":35, "g":12},
    
    # Ayurvedic Additions
    "Shatavari Churna": {"brand":"Patanjali Shatavari", "b":95, "g":45},
    "Tagar": {"brand":"Himalaya Tagara", "b":145, "g":65},
    "Kaishore Guggulu": {"brand":"Baidyanath Kaishore", "b":125, "g":58},
    
    # Homeopathy Additions
    "Ignatia Amara 30C": {"brand":"SBL Ignatia", "b":75, "g":55},
    "Coffea Cruda 30C": {"brand":"SBL Coffea", "b":75, "g":55},
    "Sepia 30C": {"brand":"SBL Sepia", "b":75, "g":55},
}

NEW_DISEASES = {
    "covid_19_mild": {
        "name": "COVID-19 (Mild)", "icd10": "U07.1", "category": "Infectious",
        "symptoms": ["fever", "dry cough", "loss of taste", "loss of smell", "fatigue", "body ache", "sore throat", "covid", "corona"],
        "red_flags": ["SpO2 below 94%", "difficulty breathing", "chest pain", "confusion"],
        "allopathy": {
            "medicines": [
                {"name":"Paracetamol 650mg","brand":"Dolo-650","dose":"1 tab","freq":"Every 6 hrs PRN","dur":"Till fever subsides","timing":"After food","purpose":"Fever and body ache","price_inr":32},
                {"name":"Cetirizine 10mg","brand":"Cetzine 10","dose":"1 tab","freq":"Once daily","dur":"5 days","timing":"Night","purpose":"Runny nose and sneezing","price_inr":48},
                {"name":"Vitamin C 500mg + Zinc","brand":"Limcee / Zincovit","dose":"1 tab","freq":"Once daily","dur":"14 days","timing":"After food","purpose":"Immune support","price_inr":83}
            ],
            "tests": ["RT-PCR", "Rapid Antigen Test", "SpO2 monitoring"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Ayush Kwath","brand":"Dabur Ayush Kwath","dose":"3g boiled in water","freq":"Twice daily","dur":"14 days","timing":"Empty stomach","purpose":"Official Ministry of Ayush immunity booster","price_inr":125},
                {"name":"Giloy Ghanvati","brand":"Patanjali Giloy","dose":"2 tabs","freq":"Twice daily","dur":"14 days","timing":"After meals","purpose":"Antiviral and immunomodulator","price_inr":95}
            ],
            "diet": ["Warm water only", "Golden milk (Haldi Doodh) at night", "Steam inhalation with Ajwain"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Arsenicum Album","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"5 days","timing":"Empty stomach","keynote":"Official AYUSH prophylactic for COVID-19, anxiety, restlessness","price_inr":75},
                {"name":"Bryonia Alba","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"5 days","timing":"Before meals","keynote":"Dry hacking cough, excessive thirst for large quantities of water","price_inr":75}
            ]
        },
        "cost": {"allopathy":163, "ayurveda":220, "homeopathy":150, "cheapest":"Homeopathy"}
    },
    
    "generalized_anxiety": {
        "name": "Generalized Anxiety Disorder", "icd10": "F41.1", "category": "Psychiatric",
        "symptoms": ["excessive worry", "restlessness", "palpitations", "insomnia", "panic attacks", "overthinking", "ghabrahat", "bechaini"],
        "red_flags": ["suicidal thoughts", "severe panic leading to fainting", "chest pain (rule out cardiac)"],
        "allopathy": {
            "medicines": [
                {"name":"Escitalopram 10mg","brand":"Nexito 10","dose":"1 tab","freq":"Once daily","dur":"3-6 months","timing":"Morning after breakfast","purpose":"SSRI for anxiety (takes 2 weeks to act)","warn":"Do not stop abruptly","price_inr":156},
                {"name":"Clonazepam 0.5mg","brand":"Clonotril 0.5","dose":"1 tab","freq":"PRN for severe panic","dur":"Short term (2 weeks max)","timing":"When having a panic attack","purpose":"Immediate relief of panic","warn":"Highly addictive","price_inr":48}
            ],
            "tests": ["Thyroid profile (rule out hyperthyroidism)", "ECG"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Ashwagandha 500mg","brand":"Himalaya Ashwagandha","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"With warm milk at night","purpose":"Reduces cortisol, natural adaptogen","price_inr":185},
                {"name":"Brahmi Vati","brand":"Divya Brahmi","dose":"1 tab","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Calms the nervous system, improves focus","price_inr":95}
            ],
            "diet": ["Avoid excessive caffeine and alcohol", "Warm milk before bed"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Ignatia Amara","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"1 month","timing":"Before meals","keynote":"Anxiety following grief, frequent sighing, emotional rollercoasters","price_inr":75},
                {"name":"Aconitum Napellus","potency":"30C","brand":"SBL","dose":"4 pills","freq":"During panic attack","dur":"PRN","timing":"Directly on tongue","keynote":"Sudden panic attacks, fear of death, palpitations","price_inr":75}
            ]
        },
        "cost": {"allopathy":204, "ayurveda":280, "homeopathy":150, "cheapest":"Homeopathy"}
    },

    "migraine": {
        "name": "Migraine Headache", "icd10": "G43", "category": "Neurological",
        "symptoms": ["throbbing headache", "one sided headache", "nausea", "vomiting", "light sensitivity", "sound sensitivity", "aura", "aadha sir dard"],
        "red_flags": ["worst headache of life (thunderclap)", "fever with stiff neck", "neurological deficits"],
        "allopathy": {
            "medicines": [
                {"name":"Naproxen 500mg","brand":"Naprosyn 500","dose":"1 tab","freq":"At onset of headache","dur":"Max 2 tabs in 24h","timing":"With food","purpose":"Abortive NSAID for acute migraine","price_inr":65},
                {"name":"Sumatriptan 50mg","brand":"Suminat 50","dose":"1 tab","freq":"At onset","dur":"Max 2 tabs in 24h","timing":"Can take with/without food","purpose":"Triptan for severe migraine (vasoconstrictor)","warn":"Avoid in ischemic heart disease","price_inr":198},
                {"name":"Propranolol 40mg","brand":"Inderal 40","dose":"1 tab","freq":"Once daily","dur":"3-6 months","timing":"Night","purpose":"Prophylaxis (prevents future migraines)","price_inr":45}
            ],
            "tests": ["MRI Brain (if red flags present)"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Pathadi Kadha","brand":"Sandu Pathadi","dose":"4 tsp with water","freq":"Twice daily","dur":"2 months","timing":"Empty stomach","purpose":"Classical formulation for migraine","price_inr":140},
                {"name":"Anu Taila","brand":"Dabur Anu Taila","dose":"2 drops in each nostril","freq":"Once daily","dur":"1 month","timing":"Morning (Nasya therapy)","purpose":"Relieves blockages and pacifies Vata/Pitta in head","price_inr":95}
            ],
            "diet": ["Avoid aged cheese, red wine, chocolate, fasting", "Drink adequate water"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Belladonna","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Every 1 hour during attack","dur":"Till relieved","timing":"Directly on tongue","keynote":"Throbbing right-sided headache, worse from light and noise","price_inr":75},
                {"name":"Sanguinaria","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"1 month","timing":"Before meals","keynote":"Right-sided migraine, begins in back of head, settles over right eye","price_inr":75}
            ]
        },
        "cost": {"allopathy":308, "ayurveda":235, "homeopathy":150, "cheapest":"Homeopathy"}
    },
    
    "pcos": {
        "name": "Polycystic Ovary Syndrome (PCOS)", "icd10": "E28.2", "category": "Endocrine/Gynecology",
        "symptoms": ["irregular periods", "missed periods", "facial hair", "acne", "weight gain", "hair thinning"],
        "red_flags": ["sudden severe pelvic pain (ruptured cyst)", "heavy uncontrolled bleeding"],
        "allopathy": {
            "medicines": [
                {"name":"Metformin 500mg SR","brand":"Glycomet SR","dose":"1 tab","freq":"Twice daily","dur":"3-6 months","timing":"With meals","purpose":"Improves insulin resistance, helps restore ovulation","price_inr":98},
                {"name":"Myo-Inositol + D-Chiro","brand":"Ovares","dose":"1 sachet/tab","freq":"Once daily","dur":"3-6 months","timing":"Morning","purpose":"Regulates menstrual cycles and improves egg quality","price_inr":285}
            ],
            "tests": ["Pelvic USG", "Free Testosterone", "Fasting Insulin", "LH/FSH ratio", "Thyroid Profile"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Shatavari Churna","brand":"Patanjali Shatavari","dose":"1 tsp","freq":"Twice daily","dur":"3-6 months","timing":"With warm milk","purpose":"Female reproductive tonic, balances hormones","price_inr":95},
                {"name":"Kanchanar Guggulu","brand":"Baidyanath","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Reduces cysts and glandular swellings","price_inr":115}
            ],
            "diet": ["Low glycemic index foods", "Avoid refined sugar and dairy (if acne present)"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Sepia","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Irregular menses, facial hair, indifferent mood, bearing down sensation","price_inr":75},
                {"name":"Pulsatilla","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Delayed scanty menses, mild weepy disposition, thirstless","price_inr":75}
            ]
        },
        "cost": {"allopathy":383, "ayurveda":210, "homeopathy":150, "cheapest":"Homeopathy"}
    },
    
    "gerd": {
        "name": "Gastroesophageal Reflux Disease (GERD)", "icd10": "K21.9", "category": "GI",
        "symptoms": ["heartburn", "acid reflux", "chest burning", "sour taste", "regurgitation", "khasi", "khatti dakar", "seene mein jalan"],
        "red_flags": ["difficulty swallowing", "black stools", "unintended weight loss", "chest pain radiating to arm"],
        "allopathy": {
            "medicines": [
                {"name":"Pantoprazole 40mg + Domperidone 30mg SR","brand":"Pan-D","dose":"1 cap","freq":"Once daily","dur":"4 weeks","timing":"Empty stomach 30 min before breakfast","purpose":"Proton pump inhibitor + Prokinetic to prevent reflux","price_inr":145},
                {"name":"Sucralfate + Oxetacaine","brand":"Sucrafil O","dose":"10 ml","freq":"3 times daily","dur":"2 weeks","timing":"30 min before meals","purpose":"Coats and soothes the esophagus","price_inr":185}
            ],
            "tests": ["Upper GI Endoscopy (if symptoms persist >4 weeks)", "H. Pylori test"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Avipattikar Churna","brand":"Patanjali","dose":"3g","freq":"Twice daily","dur":"4 weeks","timing":"Before meals with coconut water","purpose":"Classic Ayurvedic antacid, promotes downward movement of Vata","price_inr":72},
                {"name":"Kamdudha Ras","brand":"Baidyanath","dose":"1 tab","freq":"Twice daily","dur":"4 weeks","timing":"After meals","purpose":"Neutralizes excessive Pitta (acid)","price_inr":115}
            ],
            "diet": ["Avoid spicy/fried foods, citrus, coffee, alcohol", "Do not lie down for 2 hours after meals"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Nux Vomica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"4 weeks","timing":"After meals","keynote":"Reflux after spicy food/alcohol/coffee, wants to vomit but cannot","price_inr":75},
                {"name":"Robinia","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"4 weeks","timing":"Before meals","keynote":"Intensely sour regurgitation, sour stomach, worse at night","price_inr":75}
            ]
        },
        "cost": {"allopathy":330, "ayurveda":187, "homeopathy":150, "cheapest":"Homeopathy"}
    }
}

PRICES.update(NEW_PRICES)
DISEASES.update(NEW_DISEASES)


NEW_PRICES_2 = {
    # Depression/Psychiatry
    "Sertraline 50mg": {"brand":"Serlift 50", "b":145, "g":48},
    
    # Arthritis/Bone
    "Etoricoxib 90mg": {"brand":"Nucoxia 90", "b":185, "g":65},
    "Glucosamine + Chondroitin": {"brand":"Jointace C", "b":245, "g":95},
    
    # Liver/GI
    "Ursodeoxycholic Acid 300mg": {"brand":"Udapa 300", "b":450, "g":150},
    "Mebeverine 200mg SR": {"brand":"Colospa Retard", "b":320, "g":110},
    "Lactulose syrup": {"brand":"Duphalac", "b":185, "g":65},
    "Diosmin + Hesperidin": {"brand":"Daflon 500", "b":215, "g":85},
    
    # Skin
    "Mometasone cream": {"brand":"Momate", "b":145, "g":45},
    "Ketoconazole shampoo": {"brand":"Nizral", "b":285, "g":125},
    
    # Eye/Ear/Nose
    "Fluticasone nasal spray": {"brand":"Flomist", "b":350, "g":120},
    "Moxifloxacin eye drops": {"brand":"Moxicip", "b":85, "g":35},
    "Betahistine 16mg": {"brand":"Vertin 16", "b":165, "g":55},

    # Ayurvedic Additions
    "Kutki Churna": {"brand":"Patanjali Kutki", "b":185, "g":85},
    "Abhayarishta": {"brand":"Dabur Abhayarishta", "b":145, "g":65},
    "Arshkalp Vati": {"brand":"Divya Arshkalp", "b":95, "g":45},
    "Shallaki 500mg": {"brand":"Himalaya Shallaki", "b":155, "g":75},
    
    # Homeopathy Additions
    "Aurum Metallicum 30C": {"brand":"SBL Aurum", "b":75, "g":55},
    "Rhus Tox 30C": {"brand":"SBL Rhus Tox", "b":75, "g":55},
    "Colocynthis 30C": {"brand":"SBL Colocynthis", "b":75, "g":55},
    "Aesculus 30C": {"brand":"SBL Aesculus", "b":75, "g":55},
}

NEW_DISEASES_2 = {
    "clinical_depression": {
        "name": "Clinical Depression", "icd10": "F32", "category": "Psychiatric",
        "symptoms": ["sadness", "hopelessness", "loss of interest", "fatigue", "suicidal thoughts", "sleep changes", "appetite changes", "udas", "nirasha"],
        "red_flags": ["active suicidal planning", "self harm", "psychotic features (hallucinations)"],
        "allopathy": {
            "medicines": [
                {"name":"Sertraline 50mg","brand":"Serlift 50","dose":"1 tab","freq":"Once daily","dur":"6-12 months","timing":"Morning","purpose":"SSRI Antidepressant","warn":"Takes 3-4 weeks for full effect, may increase anxiety initially","price_inr":145}
            ],
            "tests": ["Thyroid profile", "Vitamin B12", "Vitamin D"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Brahmi Vati","brand":"Divya Brahmi","dose":"1 tab","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Nervine tonic","price_inr":95},
                {"name":"Ashwagandha 500mg","brand":"Himalaya Ashwagandha","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"With milk","purpose":"Reduces stress","price_inr":185}
            ],
            "diet": ["Sattvic diet", "Meditation and Yoga"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Aurum Metallicum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"1 month","timing":"Before meals","keynote":"Profound despondency, suicidal thoughts, feels life is a burden","price_inr":75},
                {"name":"Ignatia Amara","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"1 month","timing":"Before meals","keynote":"Depression after grief or loss, sighing","price_inr":75}
            ]
        },
        "cost": {"allopathy":145, "ayurveda":280, "homeopathy":150, "cheapest":"Allopathy"}
    },
    
    "osteoarthritis": {
        "name": "Osteoarthritis", "icd10": "M19.9", "category": "Musculoskeletal",
        "symptoms": ["knee pain", "joint pain", "stiffness in morning", "crackling sound in joints", "pain worse on climbing stairs", "ghutno ka dard"],
        "red_flags": ["hot swollen red joint (rule out septic arthritis)", "inability to bear weight"],
        "allopathy": {
            "medicines": [
                {"name":"Etoricoxib 90mg","brand":"Nucoxia 90","dose":"1 tab","freq":"Once daily","dur":"5-10 days","timing":"After food","purpose":"COX-2 inhibitor for pain relief","price_inr":185},
                {"name":"Glucosamine + Chondroitin","brand":"Jointace C","dose":"1 tab","freq":"Twice daily","dur":"3-6 months","timing":"After food","purpose":"Cartilage support","price_inr":245}
            ],
            "tests": ["X-Ray Bilateral Knees standing AP view"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Shallaki 500mg","brand":"Himalaya Shallaki","dose":"1 cap","freq":"Twice daily","dur":"3 months","timing":"After meals","purpose":"Boswellia extract, reduces joint inflammation","price_inr":155},
                {"name":"Mahanarayan Taila","brand":"Dabur","dose":"Local application","freq":"Twice daily","dur":"Ongoing","timing":"Apply and massage gently","purpose":"Reduces Vata induced pain","price_inr":140}
            ],
            "diet": ["Avoid sour foods (curd, tamarind)", "Weight reduction is crucial"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Rhus Tox","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"1 month","timing":"Before meals","keynote":"Pain worse on first movement, better by continued motion and warm applications","price_inr":75},
                {"name":"Bryonia","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"1 month","timing":"Before meals","keynote":"Pain worse by least movement, better by absolute rest","price_inr":75}
            ]
        },
        "cost": {"allopathy":430, "ayurveda":295, "homeopathy":150, "cheapest":"Homeopathy"}
    },

    "fatty_liver": {
        "name": "Non-Alcoholic Fatty Liver Disease (NAFLD)", "icd10": "K76.0", "category": "Hepatic",
        "symptoms": ["fatigue", "pain in upper right abdomen", "weakness", "unexplained weight loss", "elevated liver enzymes", "liver me sujan"],
        "red_flags": ["jaundice (yellow eyes)", "ascites (fluid in abdomen)", "vomiting blood"],
        "allopathy": {
            "medicines": [
                {"name":"Ursodeoxycholic Acid 300mg","brand":"Udapa 300","dose":"1 tab","freq":"Twice daily","dur":"3-6 months","timing":"After food","purpose":"Improves liver enzymes and reduces fat deposition","price_inr":450},
                {"name":"Vitamin E 400 IU","brand":"Evion 400","dose":"1 cap","freq":"Once daily","dur":"3 months","timing":"After food","purpose":"Antioxidant for NASH","price_inr":85}
            ],
            "tests": ["USG Abdomen", "Liver Function Test (LFT)", "Lipid Profile"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Liv.52 DS","brand":"Himalaya Liv.52 DS","dose":"2 tabs","freq":"Twice daily","dur":"3 months","timing":"Before meals","purpose":"Hepatoprotective","price_inr":160},
                {"name":"Kutki Churna","brand":"Patanjali Kutki","dose":"1g","freq":"Twice daily","dur":"2 months","timing":"With warm water","purpose":"Potent liver detoxifier","price_inr":185}
            ],
            "diet": ["Strictly avoid alcohol, sugar, and refined carbs", "Mediterranean diet"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Chelidonium Majus","potency":"Q","brand":"SBL","dose":"15 drops in water","freq":"3 times daily","dur":"2 months","timing":"Before meals","keynote":"Liver remedy, pain under right shoulder blade","price_inr":85},
                {"name":"Lycopodium","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"2 months","timing":"Before meals","keynote":"Fatty liver with extreme bloating and gas","price_inr":75}
            ]
        },
        "cost": {"allopathy":535, "ayurveda":345, "homeopathy":160, "cheapest":"Homeopathy"}
    },

    "irritable_bowel_syndrome": {
        "name": "Irritable Bowel Syndrome (IBS)", "icd10": "K58", "category": "GI",
        "symptoms": ["abdominal pain", "cramping", "bloating", "gas", "diarrhea", "constipation", "mucus in stool", "pet kharab", "marod"],
        "red_flags": ["blood in stool", "weight loss", "fever", "symptoms waking you at night"],
        "allopathy": {
            "medicines": [
                {"name":"Mebeverine 200mg SR","brand":"Colospa Retard","dose":"1 cap","freq":"Twice daily","dur":"4 weeks","timing":"20 mins before meals","purpose":"Antispasmodic for gut cramps","price_inr":320},
                {"name":"Pre/Probiotic capsule","brand":"Darolac / Vizylac","dose":"1 cap","freq":"Once daily","dur":"14 days","timing":"After food","purpose":"Restores gut flora","price_inr":120}
            ],
            "tests": ["Stool routine & occult blood", "Thyroid profile (r/o hyper/hypothyroidism)"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Bilwadi Churna","brand":"Baidyanath","dose":"3g","freq":"Twice daily","dur":"1 month","timing":"With buttermilk","purpose":"Astringent, binds stool in IBS-D","price_inr":115},
                {"name":"Kutajarishta","brand":"Dabur","dose":"20ml with equal water","freq":"Twice daily","dur":"1 month","timing":"After meals","purpose":"For amoebiasis and IBS","price_inr":140}
            ],
            "diet": ["Low FODMAP diet", "Avoid dairy if lactose intolerant", "Avoid caffeine and stress"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Nux Vomica","potency":"30C","brand":"SBL","dose":"4 pills","freq":"Twice daily","dur":"1 month","timing":"Before meals","keynote":"IBS with frequent ineffectual urging for stool","price_inr":75},
                {"name":"Colocynthis","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"1 month","timing":"Before meals","keynote":"Severe cramping pain, better by bending double and hard pressure","price_inr":75}
            ]
        },
        "cost": {"allopathy":440, "ayurveda":255, "homeopathy":150, "cheapest":"Homeopathy"}
    },

    "allergic_rhinitis": {
        "name": "Allergic Rhinitis", "icd10": "J30.9", "category": "Respiratory",
        "symptoms": ["sneezing", "runny nose", "stuffy nose", "itchy nose", "watery eyes", "chheenk", "naak behna"],
        "red_flags": ["unilateral nasal discharge (rule out foreign body or tumor)", "blood in mucus"],
        "allopathy": {
            "medicines": [
                {"name":"Fluticasone nasal spray","brand":"Flomist","dose":"1 spray per nostril","freq":"Twice daily","dur":"4 weeks","timing":"Morning and Night","purpose":"Intranasal steroid to reduce inflammation","price_inr":350},
                {"name":"Fexofenadine 120mg","brand":"Allegra 120","dose":"1 tab","freq":"Once daily","dur":"10 days","timing":"Morning","purpose":"Non-drowsy antihistamine","price_inr":145}
            ],
            "tests": ["Absolute Eosinophil Count", "IgE levels", "Skin Prick Test"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Anu Taila","brand":"Dabur Anu Taila","dose":"2 drops each nostril","freq":"Once daily","dur":"Ongoing","timing":"Morning","purpose":"Nasya to clear sinuses and prevent allergies","price_inr":95},
                {"name":"Haridrakhand","brand":"Baidyanath","dose":"1 tsp","freq":"Twice daily","dur":"2 months","timing":"With warm water/milk","purpose":"Potent anti-allergic formulation","price_inr":125}
            ],
            "diet": ["Avoid cold foods, ice cream, curd at night"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Allium Cepa","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 weeks","timing":"Before meals","keynote":"Profuse watery burning nasal discharge, bland eye discharge","price_inr":75},
                {"name":"Sabadilla","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"2 weeks","timing":"Before meals","keynote":"Spasmodic sneezing, itching in nose, sensitive to smell of flowers","price_inr":75}
            ]
        },
        "cost": {"allopathy":495, "ayurveda":220, "homeopathy":150, "cheapest":"Homeopathy"}
    },
    
    "hemorrhoids": {
        "name": "Hemorrhoids (Piles)", "icd10": "I84", "category": "GI/Surgery",
        "symptoms": ["bleeding during bowel movement", "itching around anus", "pain during stool", "lump near anus", "bawasir", "khoon aana"],
        "red_flags": ["profuse bleeding leading to anemia", "severe unremitting pain (thrombosed pile)", "weight loss (r/o colon cancer)"],
        "allopathy": {
            "medicines": [
                {"name":"Diosmin + Hesperidin","brand":"Daflon 500","dose":"1 tab","freq":"Twice daily","dur":"14 days","timing":"After meals","purpose":"Flavonoid venotonic to reduce vein swelling","price_inr":215},
                {"name":"Lignocaine + Hydrocortisone cream","brand":"Smuth Cream","dose":"Local application","freq":"Twice daily","dur":"10 days","timing":"Before/after passing stool","purpose":"Relieves pain and itching","price_inr":125},
                {"name":"Lactulose syrup","brand":"Duphalac","dose":"15 ml","freq":"Once daily","dur":"2 weeks","timing":"Night","purpose":"Stool softener to prevent straining","price_inr":185}
            ],
            "tests": ["Proctoscopy", "CBC (for anemia)"]
        },
        "ayurveda": {
            "medicines": [
                {"name":"Arshkalp Vati","brand":"Divya Arshkalp","dose":"2 tabs","freq":"Twice daily","dur":"1 month","timing":"Before meals with buttermilk","purpose":"Specific for bleeding and non-bleeding piles","price_inr":95},
                {"name":"Abhayarishta","brand":"Dabur Abhayarishta","dose":"20 ml","freq":"Twice daily","dur":"1 month","timing":"After meals with equal water","purpose":"Improves digestion, relieves constipation","price_inr":145}
            ],
            "diet": ["High fiber diet", "Papaya", "Plenty of water", "Sitz bath in warm water"]
        },
        "homeopathy": {
            "medicines": [
                {"name":"Aesculus Hippocastanum","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 weeks","timing":"Before meals","keynote":"Blind piles, feeling of small sticks in rectum, backache","price_inr":75},
                {"name":"Hamamelis","potency":"30C","brand":"SBL","dose":"4 pills","freq":"3 times daily","dur":"3 weeks","timing":"Before meals","keynote":"Bleeding piles with profuse dark blood, soreness","price_inr":75}
            ]
        },
        "cost": {"allopathy":525, "ayurveda":240, "homeopathy":150, "cheapest":"Homeopathy"}
    }
}

PRICES.update(NEW_PRICES_2)
DISEASES.update(NEW_DISEASES_2)

"""
Extra KB exports needed by build_dataset.py
Append these to data/medicine_db.py
"""

# ── Ayurvedic Herbs Knowledge Base ────────────────────────────────────────────
AYURVEDIC_HERBS_KB = {
    "ashwagandha": {
        "scientific": "Withania somnifera", "hindi": "अश्वगंधा",
        "properties": "Adaptogen, Immunomodulator, Rasayana",
        "indications": ["stress","anxiety","hypothyroidism","infertility","diabetes","fatigue"],
        "dose": "300-600mg extract daily or 5g root powder in warm milk",
        "safety": "Safe. Avoid in pregnancy and hyperthyroidism.",
        "brands": ["Himalaya Ashwagandha","Patanjali Ashwagandhaghan","Dabur Ashwagandha"],
    },
    "giloy": {
        "scientific": "Tinospora cordifolia", "hindi": "गिलोय",
        "properties": "Immunomodulator, Anti-inflammatory, Antipyretic",
        "indications": ["fever","dengue","malaria","arthritis","diabetes","jaundice"],
        "dose": "300mg extract twice daily or 20ml juice twice daily",
        "safety": "Avoid in autoimmune disease on immunosuppressants.",
        "brands": ["Himalaya Guduchi","Patanjali Giloy Sat","Dabur Giloy"],
    },
    "brahmi": {
        "scientific": "Bacopa monnieri", "hindi": "ब्राह्मी",
        "properties": "Medhya (cognitive), Adaptogen, Antioxidant",
        "indications": ["memory loss","anxiety","ADHD","epilepsy","depression"],
        "dose": "300mg standardized extract twice daily",
        "safety": "May cause GI upset initially. Start low.",
        "brands": ["Himalaya Bacopa","Patanjali Divya Medha Vati","Dabur Brahmi"],
    },
    "tulsi": {
        "scientific": "Ocimum tenuiflorum", "hindi": "तुलसी",
        "properties": "Antibacterial, Antiviral, Adaptogen, Expectorant",
        "indications": ["cold","cough","fever","stress","diabetes","respiratory infections"],
        "dose": "5-6 fresh leaves daily or 300mg extract",
        "safety": "Very safe. Mild blood-thinning at high doses.",
        "brands": ["Himalaya Tulasi","Patanjali Tulsi drops","Dabur Tulsi"],
    },
    "triphala": {
        "scientific": "Emblica officinalis + Terminalia bellerica + Terminalia chebula",
        "hindi": "त्रिफला",
        "properties": "Laxative, Antioxidant, Detoxifying, Eye health",
        "indications": ["constipation","eye disorders","obesity","diabetes","digestion"],
        "dose": "5g powder at bedtime with warm water",
        "safety": "Mild laxative. Avoid in diarrhea.",
        "brands": ["Himalaya Triphala","Patanjali Triphala Churna","Dabur Triphala"],
    },
    "shatavari": {
        "scientific": "Asparagus racemosus", "hindi": "शतावरी",
        "properties": "Female tonic, Adaptogen, Galactagogue, Gastroprotective",
        "indications": ["female reproductive","lactation","menopause","gastric ulcer","IBS"],
        "dose": "500mg twice daily",
        "safety": "Safe. Caution in estrogen-sensitive conditions.",
        "brands": ["Himalaya Shatavari","Dabur Shatavari","Baidyanath Shatavari"],
    },
    "neem": {
        "scientific": "Azadirachta indica", "hindi": "नीम",
        "properties": "Antibacterial, Antifungal, Antidiabetic, Antiparasitic",
        "indications": ["skin infections","diabetes","malaria","dental care","parasites"],
        "dose": "2 caps (500mg each) twice daily after meals",
        "safety": "Avoid in pregnancy. Can lower blood sugar — monitor in diabetics.",
        "brands": ["Himalaya Neem","Patanjali Neem Ghanvati"],
    },
    "haridra": {
        "scientific": "Curcuma longa", "hindi": "हल्दी (Turmeric)",
        "properties": "Anti-inflammatory, Antioxidant, Antibacterial, Hepatoprotective",
        "indications": ["arthritis","wound healing","liver disease","respiratory","skin conditions"],
        "dose": "500mg curcumin twice daily or 1 tsp fresh turmeric in warm milk",
        "safety": "Safe. High doses may affect blood clotting.",
        "brands": ["Himalaya Haridra","Patanjali Curcumin","Organic India Turmeric"],
    },
}

# ── Homeopathic Remedies Knowledge Base ──────────────────────────────────────
HOMEOPATHIC_REMEDIES_KB = {
    "Arsenicum Album": {
        "source": "Arsenic trioxide",
        "keynotes": "Anxiety, restlessness, burning pains relieved by heat, weakness, midnight aggravation",
        "uses": ["diarrhea","asthma","food poisoning","anxiety","COVID fever","skin conditions"],
        "constitution": "Anxious, restless, perfectionist, fear of death, very neat",
        "modalities": "Worse: midnight, cold, after eating. Better: heat, company, warm drinks.",
    },
    "Belladonna": {
        "source": "Deadly nightshade",
        "keynotes": "Sudden onset, redness, burning heat, throbbing pain, dilated pupils",
        "uses": ["high fever sudden","headache","tonsillitis","UTI","sunstroke"],
        "constitution": "Sudden violent symptoms, excited or delirious in fever",
        "modalities": "Worse: touch, jar, noise, light, 3pm. Better: standing, warm room.",
    },
    "Nux Vomica": {
        "source": "Strychnine seeds",
        "keynotes": "Over-indulgence, irritability, constipation with urging, hypersensitivity",
        "uses": ["acidity","constipation","hangover","insomnia","IBS"],
        "constitution": "Ambitious, workaholic, irritable, cannot tolerate contradiction",
        "modalities": "Worse: morning, cold, mental exertion, spices, stimulants. Better: rest, evening.",
    },
    "Eupatorium Perfoliatum": {
        "source": "Boneset herb",
        "keynotes": "Bone-breaking pain with fever, eyeballs sore, intense thirst",
        "uses": ["dengue fever","influenza","malaria","deep bone aches"],
        "constitution": "Great soreness — even bones feel bruised",
        "modalities": "Worse: 7-9am, motion. Better: sweating, lying on face.",
    },
    "Rhus Toxicodendron": {
        "source": "Poison ivy",
        "keynotes": "Better by motion, worse initial movement and rest, restlessness",
        "uses": ["arthritis","sprains","chickenpox","urticaria","herpes zoster"],
        "constitution": "Cannot stay still, sad in evening, restless in bed",
        "modalities": "Worse: rest, cold-damp, beginning of motion. Better: continued motion, warmth.",
    },
    "Lycopodium": {
        "source": "Club moss",
        "keynotes": "Bloating, worse 4-8pm, right-sided symptoms, flatulence, lack of confidence",
        "uses": ["IBS","bloating","right kidney stones","liver disorders","anxiety performance"],
        "constitution": "Cowardly behind bold facade, bossy at home, timid outside",
        "modalities": "Worse: 4-8pm, pressure on abdomen, oysters. Better: warm food, uncovering.",
    },
    "Pulsatilla": {
        "source": "Pasque flower",
        "keynotes": "Changeability, bland discharges, weepy, seeks consolation, worse heat",
        "uses": ["female complaints","sinusitis","ear infections","pregnancy nausea"],
        "constitution": "Gentle, yielding, weepy, craves consolation, rarely thirsty",
        "modalities": "Worse: heat, rest, evening, lying on left. Better: open air, cold, motion.",
    },
    "Calcarea Carbonica": {
        "source": "Oyster shell",
        "keynotes": "Obese, cold, sweaty, slow metabolism, hypothyroid constitution",
        "uses": ["hypothyroidism","obesity","bone problems","dentition","anxiety"],
        "constitution": "Chilly, sweaty head at night, craves eggs, sluggish",
        "modalities": "Worse: cold, exertion, full moon. Better: dry weather, lying on painful side.",
    },
}



# ── Drug Interactions Knowledge Base ──────────────────────────────────────────
INTERACTIONS = [
    {
        "d1": "Metformin", "d2": "Ashwagandha", 
        "sev": "Moderate", 
        "effect": "Enhanced hypoglycemia risk", 
        "mgmt": "Monitor blood glucose closely when starting Ashwagandha."
    },
    {
        "d1": "Levothyroxine", "d2": "Calcium/Iron supplements", 
        "sev": "Major", 
        "effect": "Decreased levothyroxine absorption", 
        "mgmt": "Separate doses by at least 4 hours."
    },
    {
        "d1": "Aspirin", "d2": "Ginkgo Biloba", 
        "sev": "Major", 
        "effect": "Increased risk of bleeding", 
        "mgmt": "Avoid combination or monitor closely."
    }
]


# ── EXTENDED DISEASES IMPORT ──
from .extended_diseases import EXTENDED_DISEASES
DISEASES.update(EXTENDED_DISEASES)
