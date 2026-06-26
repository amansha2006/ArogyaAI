import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
Path(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(PROJECT_ROOT / "logs" / "arogyaai.log"), encoding="utf-8"),
    ],
)

# ── API KEYS ──────────────────────────────────────────────────────────────────
# PASTE YOUR GEMINI KEY HERE OR USE .env FILE (get free at aistudio.google.com)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
HF_TOKEN:       str = os.getenv("HUGGINGFACE_TOKEN", "")

# ── Gemini Settings ───────────────────────────────────────────────────────────
# gemini-2.0-flash: FREE — 15 RPM, 1M tokens/day
# gemini-2.0-flash-lite: FREE — 30 RPM (faster, less rate-limited)
GEMINI_MODEL      = "gemini-2.0-flash-lite"        # 30 RPM vs 15 RPM for flash
GEMINI_BASE_URL   = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_TIMEOUT    = 120
GEMINI_MAX_TOKENS = 8192                           # 3-system prescriptions need room
GEMINI_TEMP       = 0.1

# ── Local LLM ────────────────────────────────────────────────────────────────
LOCAL_LLM_PATH    = str(PROJECT_ROOT / "models" / "llama3_finetuned")
LOCAL_LLM_BASE    = "meta-llama/Meta-Llama-3-8B-Instruct"
LOCAL_LLM_ENABLED = Path(LOCAL_LLM_PATH).exists() and any(Path(LOCAL_LLM_PATH).iterdir()) if Path(LOCAL_LLM_PATH).exists() else False
BIOBERT_PATH      = str(PROJECT_ROOT / "models" / "biobert_finetuned")
BIOBERT_BASE      = "FremyCompany/BioLORD-2023-M"
FAISS_INDEX_DIR   = str(PROJECT_ROOT / "data" / "faiss_indexes")

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = str(PROJECT_ROOT / "data" / "arogyaai.db")

# ── Auth ──────────────────────────────────────────────────────────────────────
DOCTOR_USER = "doctor"
DOCTOR_PASS = os.getenv("DOCTOR_PASS", "change_this_doctor_password")

ROOT_USER = "root"
ROOT_PASS = os.getenv("ROOT_PASS", "change_this_admin_password")

# ── App ───────────────────────────────────────────────────────────────────────
APP_NAME    = "ArogyaAI"
APP_VERSION = "4.0.0"

LANGUAGES = ["English","Hindi","Tamil","Telugu","Bengali","Marathi","Kannada"]

INDIAN_STATES = sorted([
    "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Delhi","Goa","Gujarat",
    "Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala",
    "Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland",
    "Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura",
    "Uttar Pradesh","Uttarakhand","West Bengal","Jammu & Kashmir","Puducherry",
])

# ── Emergency ─────────────────────────────────────────────────────────────────
EMERGENCY = {
    "Cardiac Emergency": {
        "kw": ["chest pain","left arm pain","jaw pain","crushing chest","heart attack",
               "seene mein dard","cardiac arrest","crushing pressure"],
        "action": "Call 112 NOW. Chew Aspirin 325mg if not allergic.",
        "icon": "🚨",
    },
    "Stroke": {
        "kw": ["face drooping","sudden arm weakness","speech difficulty","sudden severe headache",
               "vision loss sudden","face numb","achanak laqwa"],
        "action": "Call 112 NOW. Note exact time. FAST test.",
        "icon": "🧠",
    },
    "Breathing Emergency": {
        "kw": ["cannot breathe","blue lips","choking","suffocating","saans nahi","severe asthma attack"],
        "action": "Call 112. Sit upright. Use rescue inhaler.",
        "icon": "🫁",
    },
    "Anaphylaxis": {
        "kw": ["throat swelling","hives difficulty breathing","allergic shock","gale mein sujan"],
        "action": "EpiPen if available. Call 112. Lie flat legs elevated.",
        "icon": "🚨",
    },
    "Diabetic Emergency": {
        "kw": ["very low blood sugar","severe hypoglycemia","diabetic coma","sugar bahut kam"],
        "action": "Give sugar/juice if conscious. Call 112 if unconscious.",
        "icon": "🩸",
    },
}

# ── Blood test reference ranges (Indian/WHO) ──────────────────────────────────
BLOOD_RANGES = {
    "Hemoglobin":         {"unit":"g/dL",   "male":(13.5,17.5),"female":(12.0,15.5)},
    "WBC":                {"unit":"K/µL",   "both":(4.0,11.0)},
    "Platelets":          {"unit":"K/µL",   "both":(150.0,400.0)},
    "RBC":                {"unit":"M/µL",   "male":(4.5,5.9),"female":(4.0,5.2)},
    "Hematocrit":         {"unit":"%",      "male":(41.0,53.0),"female":(36.0,46.0)},
    "MCV":                {"unit":"fL",     "both":(80.0,100.0)},
    "MCH":                {"unit":"pg",     "both":(27.0,33.0)},
    "MCHC":               {"unit":"g/dL",   "both":(32.0,36.0)},
    "Neutrophils":        {"unit":"%",      "both":(50.0,70.0)},
    "Lymphocytes":        {"unit":"%",      "both":(20.0,40.0)},
    "Blood Glucose (F)":  {"unit":"mg/dL",  "both":(70.0,100.0)},
    "Blood Glucose (PP)": {"unit":"mg/dL",  "both":(70.0,140.0)},
    "HbA1c":              {"unit":"%",      "both":(4.0,5.6)},
    "Total Cholesterol":  {"unit":"mg/dL",  "both":(0.0,200.0)},
    "HDL":                {"unit":"mg/dL",  "male":(40.0,60.0),"female":(50.0,60.0)},
    "LDL":                {"unit":"mg/dL",  "both":(0.0,100.0)},
    "Triglycerides":      {"unit":"mg/dL",  "both":(0.0,150.0)},
    "Creatinine":         {"unit":"mg/dL",  "male":(0.7,1.2),"female":(0.5,1.0)},
    "BUN":                {"unit":"mg/dL",  "both":(7.0,20.0)},
    "Uric Acid":          {"unit":"mg/dL",  "male":(3.5,7.2),"female":(2.5,6.0)},
    "SGOT/AST":           {"unit":"U/L",    "both":(10.0,40.0)},
    "SGPT/ALT":           {"unit":"U/L",    "both":(10.0,40.0)},
    "Total Bilirubin":    {"unit":"mg/dL",  "both":(0.1,1.2)},
    "Direct Bilirubin":   {"unit":"mg/dL",  "both":(0.0,0.3)},
    "Sodium":             {"unit":"mEq/L",  "both":(136.0,145.0)},
    "Potassium":          {"unit":"mEq/L",  "both":(3.5,5.0)},
    "Calcium":            {"unit":"mg/dL",  "both":(8.5,10.2)},
    "TSH":                {"unit":"µIU/mL", "both":(0.4,4.0)},
    "Free T3":            {"unit":"pg/mL",  "both":(2.3,4.2)},
    "Free T4":            {"unit":"ng/dL",  "both":(0.8,1.8)},
    "Vitamin D":          {"unit":"ng/mL",  "both":(30.0,100.0)},
    "Vitamin B12":        {"unit":"pg/mL",  "both":(200.0,900.0)},
    "Ferritin":           {"unit":"ng/mL",  "male":(24.0,336.0),"female":(11.0,307.0)},
    "Iron":               {"unit":"µg/dL",  "male":(65.0,175.0),"female":(50.0,170.0)},
    "TIBC":               {"unit":"µg/dL",  "both":(250.0,370.0)},
    "CRP":                {"unit":"mg/L",   "both":(0.0,5.0)},
    "ESR":                {"unit":"mm/hr",  "male":(0.0,15.0),"female":(0.0,20.0)},
    "INR":                {"unit":"",       "both":(0.8,1.1)},
    "PSA":                {"unit":"ng/mL",  "male":(0.0,4.0)},
}

# ── Seasonal Disease Map ──────────────────────────────────────────────────────
SEASONAL = {
    "Andhra Pradesh": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Assam": {6:["Dengue","Malaria","Japanese Encephalitis"],7:["Dengue","Malaria","Japanese Encephalitis"],8:["Dengue","Malaria"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Bihar": {6:["Dengue","Malaria"],7:["Dengue","Malaria","Kala-azar"],8:["Dengue","Malaria","Cholera"],9:["Dengue","Kala-azar"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Chhattisgarh": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Delhi": {6:["Dengue"],7:["Dengue"],8:["Dengue"],9:["Dengue","Chikungunya"],10:["Dengue"],11:["Flu","Pneumonia"],12:["Flu","Pneumonia"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Goa": {6:["Dengue","Malaria","Leptospirosis"],7:["Dengue","Malaria","Leptospirosis"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Gujarat": {6:["Dengue","Malaria","Cholera"],7:["Dengue","Malaria","Cholera"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu","Swine Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Haryana": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue","Chikungunya"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Himachal Pradesh": {6:["Scrub Typhus"],7:["Scrub Typhus","Dengue"],8:["Scrub Typhus","Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu","Pneumonia"],12:["Flu","Pneumonia"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Jharkhand": {6:["Dengue","Malaria"],7:["Dengue","Malaria","Kala-azar"],8:["Dengue","Malaria"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Karnataka": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue","Chikungunya"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Kerala": {6:["Dengue","Leptospirosis","Nipah Virus"],7:["Dengue","Leptospirosis"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Madhya Pradesh": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Maharashtra": {6:["Dengue","Malaria","Leptospirosis"],7:["Dengue","Malaria","Cholera"],8:["Dengue","Malaria"],9:["Dengue"],10:["Dengue"],11:["Swine Flu"],12:["Swine Flu","Flu"],1:["Swine Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Odisha": {6:["Dengue","Malaria","Filaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Punjab": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Rajasthan": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu","Swine Flu"],12:["Flu","Swine Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Tamil Nadu": {6:["Dengue"],7:["Dengue"],8:["Dengue"],9:["Dengue","Malaria"],10:["Dengue","Malaria","Cholera","Chikungunya"],11:["Dengue","Cholera"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Telangana": {6:["Dengue","Malaria"],7:["Dengue","Malaria"],8:["Dengue"],9:["Dengue","Chikungunya"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Uttar Pradesh": {6:["Dengue","Malaria"],7:["Dengue","Malaria","Japanese Encephalitis"],8:["Dengue","Malaria","Cholera"],9:["Dengue","Kala-azar"],10:["Dengue"],11:["Flu","Pneumonia"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "Uttarakhand": {6:["Scrub Typhus"],7:["Scrub Typhus","Dengue"],8:["Scrub Typhus","Dengue"],9:["Dengue"],10:["Dengue"],11:["Flu","Pneumonia"],12:["Flu","Pneumonia"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
    "West Bengal": {6:["Dengue","Malaria"],7:["Dengue","Malaria","Kala-azar"],8:["Dengue","Malaria","Cholera"],9:["Dengue"],10:["Dengue"],11:["Flu"],12:["Flu"],1:["Flu"],2:["Measles"],3:["Chickenpox"],4:["Heat Stroke"],5:["Heat Stroke"]},
}
