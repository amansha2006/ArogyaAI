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
