import os
import json
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import database as db
import llm_engine
import medical
from pdf_report import make_pdf

# Setup Logging
logger = logging.getLogger("api")

app = FastAPI(title="ArogyaAI API", version="4.0")

# Serve frontend static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class ProfileUpdate(BaseModel):
    user_id: int
    name: str
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    blood_group: Optional[str] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    temperature_f: Optional[float] = None
    state: str
    city: str
    language: str
    dietary_pref: str
    conditions: List[str]
    allergies: List[str]
    current_meds: List[str]
    emergency_contact: str

class AnalyzeManualRequest(BaseModel):
    values_text: str
    gender: str = "unknown"

class GenerateRxRequest(BaseModel):
    user_id: Optional[int] = None
    symptoms: str
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    temperature_f: Optional[float] = None
    report: Optional[Dict[str, Any]] = None

class MedicineInfoRequest(BaseModel):
    drug_name: str

class SettingsUpdate(BaseModel):
    gemini_key: str

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: HEALTH / STATUS CHECK
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    """Check status of all ML/AI components."""
    from pathlib import Path
    
    faiss_dir = Path(config.FAISS_INDEX_DIR)
    faiss_indexes = list(faiss_dir.glob("*.index")) if faiss_dir.exists() else []
    faiss_metas = list(faiss_dir.glob("*_meta.json")) if faiss_dir.exists() else []
    
    # Check BioLORD / sentence-transformers model
    biobert_loaded = medical._embed_model is not None
    biobert_path_exists = Path(config.BIOBERT_PATH).exists()
    
    # Check local LLM
    local_llm_loaded = config.LOCAL_LLM_ENABLED
    
    # Check Gemini
    gemini_key_set = bool(config.GEMINI_API_KEY and len(config.GEMINI_API_KEY) > 5)
    
    return {
        "status": "ok",
        "version": config.APP_VERSION,
        "components": {
            "gemini": {
                "model": config.GEMINI_MODEL,
                "api_key_configured": gemini_key_set,
            },
            "local_llm": {
                "enabled": local_llm_loaded,
                "path": config.LOCAL_LLM_PATH,
            },
            "rag_embeddings": {
                "model_loaded": biobert_loaded,
                "model_name": config.BIOBERT_BASE,
                "fine_tuned_path": config.BIOBERT_PATH,
                "fine_tuned_exists": biobert_path_exists,
            },
            "faiss_indexes": {
                "index_files": [f.name for f in faiss_indexes],
                "metadata_files": [f.name for f in faiss_metas],
                "warning": "Missing metadata" if len(faiss_indexes) != len(faiss_metas) else None,
            },
            "knowledge_base": {
                "diseases_count": len(medical.DISEASES),
                "interactions_count": len(medical.INTERACTIONS),
            },
        },
    }

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/login")
def login(req: LoginRequest):
    user = db.login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    patient = None
    if user["role"] == "patient":
        patient = db.get_patient(user["id"])
    
    return {
        "success": True,
        "user": user,
        "patient": patient
    }

@app.post("/api/register")
def register(req: RegisterRequest):
    ok, msg = db.register(req.username, req.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: PROFILE & HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/profile")
def update_profile(req: ProfileUpdate):
    try:
        db.upsert_patient(
            req.user_id,
            name=req.name, age=req.age, gender=req.gender,
            weight_kg=req.weight_kg, height_cm=req.height_cm,
            blood_group=req.blood_group,
            bp_systolic=req.bp_systolic, bp_diastolic=req.bp_diastolic,
            temperature_f=req.temperature_f,
            state=req.state, city=req.city, language=req.language,
            conditions=req.conditions, allergies=req.allergies,
            current_meds=req.current_meds, dietary_pref=req.dietary_pref,
            emergency_contact=req.emergency_contact
        )
        patient = db.get_patient(req.user_id)
        return {"success": True, "patient": patient}
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{user_id}")
def get_history(user_id: int):
    patient = db.get_patient(user_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    sessions = db.get_sessions(patient["id"], limit=20)
    return {"success": True, "sessions": sessions}

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: MEDICAL ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/analyze-report")
async def analyze_report(
    file: UploadFile = File(...),
    patient_json: Optional[str] = Form(None),
    notes: Optional[str] = Form("")
):
    try:
        if not llm_engine.check_health()[0]:
            raise HTTPException(status_code=503, detail="AI Engine not configured or unavailable.")

        patient = json.loads(patient_json) if patient_json else None
        contents = await file.read()
        
        report = medical.analyse_report(
            contents, file.filename, file.content_type, patient, notes
        )
        return {"success": True, "report": report}
    except Exception as e:
        logger.error(f"Analyze report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-manual")
def analyze_manual(req: AnalyzeManualRequest):
    if not llm_engine.check_health()[0]:
        raise HTTPException(status_code=503, detail="AI Engine not configured or unavailable.")
        
    report = medical.analyse_manual_values(req.values_text, req.gender)
    return {"success": True, "report": report}

@app.post("/api/medicine-info")
def get_medicine_info(req: MedicineInfoRequest):
    if not llm_engine.check_health()[0]:
        raise HTTPException(status_code=503, detail="AI Engine not configured or unavailable.")
    
    info = medical.get_medicine_details(req.drug_name)
    return {"success": True, "info": info}

@app.post("/api/generate-prescription")
def generate_prescription(req: GenerateRxRequest):
    if not llm_engine.check_health()[0]:
        raise HTTPException(status_code=503, detail="AI Engine not configured or unavailable.")

    patient = db.get_patient(req.user_id) if req.user_id else None
    
    # Check Emergency First
    emr = medical.detect_emergency(req.symptoms)
    if emr:
        rx = {"abort": True, "emergency": emr}
        sid = str(uuid.uuid4())
        if patient:
            db.save_session(sid, patient["id"], req.symptoms, True, {})
        return {"success": True, "prescription": rx, "session_id": sid}

    # Generate Rx
    patient_with_vitals = dict(patient or {})
    if req.bp_systolic: patient_with_vitals["bp_systolic"] = req.bp_systolic
    if req.bp_diastolic: patient_with_vitals["bp_diastolic"] = req.bp_diastolic
    if req.temperature_f: patient_with_vitals["temperature_f"] = req.temperature_f

    rx = medical.generate_prescription(req.symptoms, patient_with_vitals, req.report)
    sid = str(uuid.uuid4())
    
    if not rx.get("error") and not rx.get("abort"):
        try:
            # Generate PDF secretly and store to disk or return bytes logic
            # For FastAPI, we might just store it in memory or file
            pdf_bytes = make_pdf(patient_with_vitals, rx, req.report, sid)
            pdf_path = f"static/reports/{sid}.pdf"
            os.makedirs("static/reports", exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            rx["pdf_url"] = f"/{pdf_path}"
        except Exception as e:
            logger.warning(f"PDF pre-gen error: {e}")

    if patient:
        db.save_session(sid, patient["id"], req.symptoms, False, rx, req.report or {})

    return {"success": True, "prescription": rx, "session_id": sid}

@app.get("/api/download-prescription/{session_id}")
def download_prescription(session_id: str, system: str = "all"):
    session = db.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found in history")
        
    rx = session.get("prescription", {})
    report = session.get("report_data", {})
    patient = db.get_patient(session["patient_id"]) if session.get("patient_id") else None
    
    pdf_bytes = make_pdf(patient, rx, report, session_id, target_system=system)
    
    headers = {
        'Content-Disposition': f'attachment; filename="ArogyaAI_Prescription_{system}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS: SYSTEM & DOCTOR
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/doctor-stats")
def doctor_stats():
    # In a real app, verify doctor role from token
    return {
        "success": True,
        "stats": db.stats(),
        "sessions": db.all_sessions(50),
        "patients": db.list_patients()
    }

@app.get("/api/admin-data")
def admin_data():
    return {
        "success": True,
        "data": db.admin_get_all_data()
    }
@app.get("/api/config")
def get_config():
    """Return application config useful for frontend (e.g. state list)"""
    return {
        "success": True,
        "indian_states": config.INDIAN_STATES
    }

@app.get("/api/llm-health")
def llm_health_check(force: bool = False):
    ok, msg = llm_engine.check_health(force=force)
    return {"ok": ok, "msg": msg}

@app.post("/api/settings")
def update_settings(req: SettingsUpdate):
    llm_engine.set_gemini_key(req.gemini_key)
    return {"success": True, "message": "Key updated"}

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    """Serve the single page application."""
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse("static/index.html")
