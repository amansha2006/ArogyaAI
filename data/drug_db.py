"""
Offline Drug Database for ArogyaAI
A highly detailed, 100% local pharmacology dictionary.
This avoids API rate limits and provides instant responses.
Keys are lowercase generic names or core ingredients.
"""

DRUGS = {
    # ─── PAIN & FEVER ────────────────────────────────────────────────────────
    "paracetamol": {
        "generic_salt": "Paracetamol (Acetaminophen)",
        "drug_class": "Analgesic & Antipyretic",
        "primary_uses": ["Fever", "Mild to moderate pain", "Headache", "Body ache"],
        "mechanism_of_action": "Inhibits prostaglandin synthesis in the central nervous system and acts on the hypothalamic heat-regulating center to reduce fever.",
        "common_side_effects": ["Nausea (rare)", "Liver damage (only in severe overdose or chronic alcohol use)"],
        "contraindications": ["Severe liver disease", "Alcoholism"],
        "popular_indian_brands": ["Dolo 650", "Crocin", "Calpol", "P-250", "Sumo L"],
        "safety_advice": "Do not exceed 4000 mg (4 grams) in 24 hours to prevent liver toxicity."
    },
    "ibuprofen": {
        "generic_salt": "Ibuprofen",
        "drug_class": "NSAID (Non-Steroidal Anti-Inflammatory Drug)",
        "primary_uses": ["Pain relief", "Inflammation", "Menstrual cramps", "Toothache"],
        "mechanism_of_action": "Reversibly inhibits COX-1 and COX-2 enzymes, decreasing the production of inflammatory prostaglandins.",
        "common_side_effects": ["Stomach upset", "Heartburn", "Dizziness", "Ulcers (long term use)"],
        "contraindications": ["Dengue Fever (risk of bleeding)", "Active stomach ulcers", "Severe kidney disease"],
        "popular_indian_brands": ["Brufen", "Combiflam (with Paracetamol)", "Ibugesic"],
        "safety_advice": "Always take after meals to prevent stomach irritation."
    },
    "diclofenac": {
        "generic_salt": "Diclofenac Sodium/Potassium",
        "drug_class": "NSAID",
        "primary_uses": ["Joint pain", "Arthritis", "Severe muscle pain", "Post-surgical pain"],
        "mechanism_of_action": "Potent inhibitor of cyclooxygenase (COX), reducing prostaglandins that cause pain and inflammation.",
        "common_side_effects": ["Gastric irritation", "Nausea", "Elevated liver enzymes (rare)"],
        "contraindications": ["Asthma triggered by NSAIDs", "Gastric ulcers", "Severe heart failure"],
        "popular_indian_brands": ["Voveran", "Dynapar", "Reactin", "Dicloran"],
        "safety_advice": "Avoid long-term continuous use due to cardiovascular and renal risks."
    },

    # ─── ANTIBIOTICS ─────────────────────────────────────────────────────────
    "amoxicillin": {
        "generic_salt": "Amoxicillin",
        "drug_class": "Penicillin Antibiotic",
        "primary_uses": ["Ear infections", "Throat infections", "Pneumonia", "Dental infections"],
        "mechanism_of_action": "Binds to penicillin-binding proteins inside the bacterial cell wall, causing the bacteria to lyse (burst) and die.",
        "common_side_effects": ["Diarrhea", "Nausea", "Skin rash (if allergic)"],
        "contraindications": ["Penicillin allergy", "Cephalosporin allergy (cross-reactivity)"],
        "popular_indian_brands": ["Novamox", "Mox", "Augmentin (with Clavulanic Acid)", "Advent"],
        "safety_advice": "Always complete the full prescribed course even if you feel better."
    },
    "azithromycin": {
        "generic_salt": "Azithromycin",
        "drug_class": "Macrolide Antibiotic",
        "primary_uses": ["Respiratory tract infections", "Typhoid", "Chlamydia", "Skin infections"],
        "mechanism_of_action": "Inhibits bacterial protein synthesis by binding to the 50S ribosomal subunit.",
        "common_side_effects": ["Stomach pain", "Diarrhea", "Nausea", "QT prolongation (heart rhythm change)"],
        "contraindications": ["Liver dysfunction", "Known QT prolongation (heart issues)"],
        "popular_indian_brands": ["Azee", "Azithral", "Zithrox"],
        "safety_advice": "Take 1 hour before or 2 hours after meals for best absorption."
    },
    "cefixime": {
        "generic_salt": "Cefixime",
        "drug_class": "Cephalosporin Antibiotic (3rd Gen)",
        "primary_uses": ["Typhoid fever", "Urinary tract infections (UTI)", "Ear infections", "Bronchitis"],
        "mechanism_of_action": "Inhibits bacterial cell wall synthesis, leading to cell death. Highly stable against beta-lactamase enzymes.",
        "common_side_effects": ["Diarrhea", "Stomach upset", "Gas"],
        "contraindications": ["Severe penicillin/cephalosporin allergy"],
        "popular_indian_brands": ["Zifi", "Taxim-O", "Mahacef", "Omnicef"],
        "safety_advice": "Finish the entire course. Can be taken with or without food."
    },

    # ─── GASTROINTESTINAL (GI) ───────────────────────────────────────────────
    "pantoprazole": {
        "generic_salt": "Pantoprazole",
        "drug_class": "Proton Pump Inhibitor (PPI)",
        "primary_uses": ["Acid reflux (GERD)", "Stomach ulcers", "Acidity", "Heartburn"],
        "mechanism_of_action": "Irreversibly binds to the H+/K+ ATPase pump in the stomach parietal cells, drastically reducing stomach acid production.",
        "common_side_effects": ["Headache", "Diarrhea", "Vitamin B12 deficiency (long term use)", "Bone fractures (long term use)"],
        "contraindications": ["Severe liver impairment (use with caution)"],
        "popular_indian_brands": ["Pan", "Pantocid", "Pan-D (with Domperidone)", "Pantodac"],
        "safety_advice": "Take exactly 30-40 minutes before breakfast on an empty stomach."
    },
    "rabeprazole": {
        "generic_salt": "Rabeprazole",
        "drug_class": "Proton Pump Inhibitor (PPI)",
        "primary_uses": ["Severe acidity", "GERD", "Zollinger-Ellison syndrome"],
        "mechanism_of_action": "Blocks the gastric acid pump. Works faster than older PPIs like Omeprazole.",
        "common_side_effects": ["Headache", "Nausea", "Sore throat"],
        "contraindications": ["Pregnancy (unless advised by doctor)"],
        "popular_indian_brands": ["Rablet", "Rabium", "Cyra", "Happi"],
        "safety_advice": "Take on an empty stomach. Do not crush or chew the tablet."
    },
    "ondansetron": {
        "generic_salt": "Ondansetron",
        "drug_class": "Antiemetic (Serotonin 5-HT3 receptor antagonist)",
        "primary_uses": ["Nausea", "Vomiting", "Chemotherapy-induced vomiting"],
        "mechanism_of_action": "Blocks serotonin both peripherally on vagal nerve terminals and centrally in the chemoreceptor trigger zone, preventing vomiting.",
        "common_side_effects": ["Headache", "Constipation", "Fatigue"],
        "contraindications": ["Use with apomorphine (causes severe BP drop)"],
        "popular_indian_brands": ["Emeset", "Ondem", "Vomikind"],
        "safety_advice": "Can be taken as a mouth-dissolving tablet (MD) for faster relief."
    },

    # ─── CARDIOLOGY & HYPERTENSION ───────────────────────────────────────────
    "telmisartan": {
        "generic_salt": "Telmisartan",
        "drug_class": "Angiotensin II Receptor Blocker (ARB)",
        "primary_uses": ["High blood pressure (Hypertension)", "Heart attack prevention", "Diabetic nephropathy"],
        "mechanism_of_action": "Blocks the binding of angiotensin II to its receptor, causing blood vessels to relax and lowering blood pressure.",
        "common_side_effects": ["Back pain", "Sinus pain", "Dizziness", "High potassium levels"],
        "contraindications": ["Pregnancy", "Severe liver disease"],
        "popular_indian_brands": ["Telma", "Telmikind", "Tazloc", "Cresar"],
        "safety_advice": "Do not stop suddenly. Requires regular monitoring of potassium levels."
    },
    "amlodipine": {
        "generic_salt": "Amlodipine",
        "drug_class": "Calcium Channel Blocker",
        "primary_uses": ["Hypertension", "Angina (chest pain)"],
        "mechanism_of_action": "Prevents calcium from entering the cells of the heart and blood vessel walls, widening blood vessels.",
        "common_side_effects": ["Swelling in ankles/feet (Edema)", "Flushing", "Palpitations"],
        "contraindications": ["Severe aortic stenosis", "Cardiogenic shock"],
        "popular_indian_brands": ["Amlokind", "Stamlo", "Amlovas"],
        "safety_advice": "If ankle swelling occurs, consult your doctor. Do not stop abruptly."
    },
    "rosuvastatin": {
        "generic_salt": "Rosuvastatin",
        "drug_class": "Statin (Lipid-lowering agent)",
        "primary_uses": ["High cholesterol", "Triglycerides", "Prevention of cardiovascular disease"],
        "mechanism_of_action": "Inhibits HMG-CoA reductase, the enzyme responsible for cholesterol production in the liver.",
        "common_side_effects": ["Muscle pain", "Weakness", "Headache"],
        "contraindications": ["Active liver disease", "Pregnancy & Lactation"],
        "popular_indian_brands": ["Rosuvas", "Rozavel", "Novastat", "Crevast"],
        "safety_advice": "Take at the same time every day. Report any unexplained muscle pain immediately."
    },

    # ─── DIABETES ────────────────────────────────────────────────────────────
    "metformin": {
        "generic_salt": "Metformin Hydrochloride",
        "drug_class": "Biguanide Antidiabetic",
        "primary_uses": ["Type 2 Diabetes Mellitus", "PCOS (Polycystic Ovary Syndrome)"],
        "mechanism_of_action": "Decreases hepatic glucose production and improves insulin sensitivity by increasing peripheral glucose uptake.",
        "common_side_effects": ["Diarrhea", "Nausea", "Metallic taste", "Vitamin B12 deficiency (long term)"],
        "contraindications": ["Severe kidney dysfunction", "Diabetic ketoacidosis"],
        "popular_indian_brands": ["Glycomet", "Glucophage", "Cetapin", "Obimet"],
        "safety_advice": "Take with meals to reduce stomach/bowel side effects."
    },
    "glimepiride": {
        "generic_salt": "Glimepiride",
        "drug_class": "Sulfonylurea Antidiabetic",
        "primary_uses": ["Type 2 Diabetes Mellitus"],
        "mechanism_of_action": "Stimulates the release of insulin from the functioning pancreatic beta cells.",
        "common_side_effects": ["Low blood sugar (Hypoglycemia)", "Weight gain", "Dizziness"],
        "contraindications": ["Type 1 Diabetes", "Severe kidney/liver disease"],
        "popular_indian_brands": ["Amaryl", "Glimy", "Zoryl"],
        "safety_advice": "Take immediately before or during breakfast. Keep a sugar source handy for hypoglycemia."
    },

    # ─── RESPIRATORY & ANTIHISTAMINES ────────────────────────────────────────
    "levocetirizine": {
        "generic_salt": "Levocetirizine",
        "drug_class": "Antihistamine (Non-sedating)",
        "primary_uses": ["Allergies", "Runny nose", "Sneezing", "Hives/Itching"],
        "mechanism_of_action": "Selectively blocks peripheral H1 receptors, preventing histamine from causing allergic symptoms.",
        "common_side_effects": ["Mild drowsiness", "Dry mouth", "Fatigue"],
        "contraindications": ["Severe kidney impairment"],
        "popular_indian_brands": ["Levocet", "1-AL", "L-Hist", "Teczine"],
        "safety_advice": "Though non-sedating, it can cause mild drowsiness in some. Avoid driving if affected."
    },
    "montelukast": {
        "generic_salt": "Montelukast",
        "drug_class": "Leukotriene Receptor Antagonist",
        "primary_uses": ["Asthma prevention", "Severe allergic rhinitis"],
        "mechanism_of_action": "Blocks the action of leukotrienes, reducing inflammation and keeping airways open.",
        "common_side_effects": ["Headache", "Stomach pain", "Mood changes (rare)"],
        "contraindications": ["Acute asthma attacks (it is for prevention, not immediate relief)"],
        "popular_indian_brands": ["Montair", "Telekast", "Romilast"],
        "safety_advice": "Take regularly in the evening for asthma, even when symptom-free."
    },

    # ─── NEURO & PSYCHIATRY ──────────────────────────────────────────────────
    "escitalopram": {
        "generic_salt": "Escitalopram",
        "drug_class": "SSRI Antidepressant",
        "primary_uses": ["Depression", "Generalized Anxiety Disorder (GAD)", "Panic attacks"],
        "mechanism_of_action": "Selectively inhibits the reuptake of serotonin in the brain, increasing its availability to improve mood.",
        "common_side_effects": ["Nausea", "Insomnia or sleepiness", "Sexual dysfunction", "Weight changes"],
        "contraindications": ["Use with MAO inhibitors", "Bipolar disorder (without mood stabilizer)"],
        "popular_indian_brands": ["Nexito", "Cilentra", "Stalopam", "Szetalo"],
        "safety_advice": "Do not stop abruptly. May take 2-4 weeks to show full therapeutic effect."
    },
    "clonazepam": {
        "generic_salt": "Clonazepam",
        "drug_class": "Benzodiazepine",
        "primary_uses": ["Seizures", "Panic attacks", "Severe anxiety"],
        "mechanism_of_action": "Enhances the activity of GABA, a calming neurotransmitter in the brain, reducing abnormal electrical activity.",
        "common_side_effects": ["Drowsiness", "Poor coordination", "Memory issues", "Addiction/Dependence"],
        "contraindications": ["Severe liver disease", "Narrow-angle glaucoma"],
        "popular_indian_brands": ["Clonotril", "Petril", "Lonazep", "Zapiz"],
        "safety_advice": "Highly habit-forming. Use strictly as prescribed. Do not mix with alcohol."
    },

    # ─── AYURVEDIC HERBS / MEDICINES ─────────────────────────────────────────
    "ashwagandha": {
        "generic_salt": "Ashwagandha (Withania somnifera)",
        "drug_class": "Ayurvedic Adaptogen",
        "primary_uses": ["Stress reduction", "Anxiety", "Insomnia", "Fatigue", "Immunity building"],
        "mechanism_of_action": "Regulates the HPA axis to lower cortisol (stress hormone) levels and mimics GABA to promote calmness.",
        "common_side_effects": ["Mild stomach upset (if taken on empty stomach)", "Drowsiness"],
        "contraindications": ["Hyperthyroidism (can increase thyroid hormone)", "Pregnancy"],
        "popular_indian_brands": ["Himalaya Ashwagandha", "Patanjali Ashwagandha", "Baidyanath Ashwagandha"],
        "safety_advice": "Best taken with warm milk at night for sleep issues."
    },
    "triphala": {
        "generic_salt": "Triphala (Amla, Haritaki, Bibhitaki)",
        "drug_class": "Ayurvedic Rasayana & Mild Laxative",
        "primary_uses": ["Constipation", "Digestion issues", "Detoxification", "Eye health"],
        "mechanism_of_action": "Contains tannins and vitamin C that tone the intestinal walls, promote peristalsis, and act as a powerful antioxidant.",
        "common_side_effects": ["Loose stools (if taken in excess)", "Dehydration"],
        "contraindications": ["Diarrhea", "Dysentery"],
        "popular_indian_brands": ["Himalaya Triphala", "Dabur Triphala Churna", "Zandu Triphala"],
        "safety_advice": "Take with warm water at bedtime for best bowel regulating results."
    },
    "giloy": {
        "generic_salt": "Giloy (Tinospora cordifolia)",
        "drug_class": "Ayurvedic Immunomodulator",
        "primary_uses": ["Fever (especially Dengue/Malaria recovery)", "Immunity boosting", "Gout"],
        "mechanism_of_action": "Stimulates the phagocytic activity of macrophages, boosting the immune system's ability to fight infections.",
        "common_side_effects": ["Constipation (rare)"],
        "contraindications": ["Autoimmune diseases (may overstimulate the immune system)"],
        "popular_indian_brands": ["Patanjali Giloy Ghan Vati", "Himalaya Guduchi", "Dabur Giloy"],
        "safety_advice": "Excellent for post-viral fatigue. Diabetics should monitor blood sugar as it lowers glucose."
    },

    # ─── HOMEOPATHIC REMEDIES ────────────────────────────────────────────────
    "arnica": {
        "generic_salt": "Arnica Montana",
        "drug_class": "Homeopathic Anti-inflammatory",
        "primary_uses": ["Bruises", "Muscle soreness", "Sprains", "Post-surgical trauma"],
        "mechanism_of_action": "Believed to stimulate healing pathways and reduce capillary bleeding in micro-traumas.",
        "common_side_effects": ["None (highly diluted)"],
        "contraindications": ["Do not apply raw tincture to broken skin"],
        "popular_indian_brands": ["SBL Arnica 30CH", "Dr. Reckeweg Arnica 200", "Schwabe Arnica Ointment"],
        "safety_advice": "Use immediately after blunt trauma or falls to prevent severe bruising."
    },
    "nux vomica": {
        "generic_salt": "Nux Vomica",
        "drug_class": "Homeopathic Digestive",
        "primary_uses": ["Indigestion", "Hangover", "Constipation with ineffectual urge", "Irritability"],
        "mechanism_of_action": "Acts on the digestive and nervous systems to relieve spasms and overstimulation.",
        "common_side_effects": ["None (highly diluted)"],
        "contraindications": ["None"],
        "popular_indian_brands": ["SBL Nux Vomica 30CH", "Dr. Reckeweg Nux Vomica 200"],
        "safety_advice": "Often given to individuals with sedentary lifestyles who consume excess coffee, alcohol, or rich food."
    }
}
