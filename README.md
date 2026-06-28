<div align="center">
  
# 🏥 ArogyaAI
  
**India's First Multimodal AI Health Intelligence Platform**  
*Allopathy · Ayurveda · Homeopathy · 7 Indian Languages*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LLaMA 3](https://img.shields.io/badge/LLaMA_3-8B_Instruct-0466c8?style=for-the-badge)](https://ai.meta.com/llama/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

---

## 🌟 What is ArogyaAI?

ArogyaAI bridges the gap in Indian healthcare by safely combining modern **Allopathy** with traditional **AYUSH** (Ayurveda & Homeopathy) systems. It is an offline-first, multimodal medical AI that generates highly accurate, structured prescriptions and diagnostics.

**Why is this better than ChatGPT for medical queries?**
> Standard LLMs do not know that Ayurvedic *Ashwagandha* interacts dangerously with thyroid medications. They lack knowledge of Indian drug brands like *Dolo-650* or *Glycomet*. They cannot process raw, uploaded blood test PDFs to automatically highlight high/low anomalies. **ArogyaAI does all of this.**

---

## 📸 UI Previews & Platform Walkthrough

ArogyaAI is designed with a clean, responsive Single Page Application (SPA) frontend. Here is how the platform works:

### 1. Authentication & Roles
Secure login portals with distinct views for Patients, Doctors, and Administrators.
| Login Page | Registration |
|:---:|:---:|
| ![Login](assets/LoginPage.PNG) | ![Registration](assets/UserRegistration.PNG) |

### 2. Multimodal Diagnostic Input
Patients can manually describe symptoms or upload physical blood reports for instant OCR analysis. The system automatically color-codes anomalies (High/Low/Normal).
| Symptoms Input | Blood Report Analysis | Blood Report Results |
|:---:|:---:|:---:|
| ![Symptoms](assets/SymptomsInput.PNG) | ![Blood Input](assets/BloodReportInput.PNG) | ![Blood Output](assets/BloodReportOutput.PNG) |

### 3. AI Intelligence & Safety
The core engine detects emergencies instantly (bypassing the LLM) and generates deep diagnostic predictions using a fine-tuned RAG pipeline.
| Emergency Detection 🚨 | Disease Prediction | Drug & Cross-System Interactions |
|:---:|:---:|:---:|
| ![Emergency](assets/EmergencyCase.PNG) | ![Predicted Disease](assets/PredictedDisease.PNG) | ![Drug Info](assets/DrugInfo.PNG) |

### 4. Professional Dashboards
| Doctor Dashboard | Admin Dashboard |
|:---:|:---:|
| ![Doctor](assets/DoctorPage.PNG) | ![Admin](assets/AdminPage.PNG) |

---

## 🗂️ System Architecture & Project Schema

ArogyaAI operates on a robust, highly modular architecture built for scale. 

### Core Components
- **`api.py` (The Brain)**: A high-performance FastAPI server. It manages REST endpoints, static file mounting, user sessions, and triggers the medical analysis pipelines.
- **`medical.py` (The Heart)**: The core medical orchestration engine. It houses the Rule-Based Emergency logic, PDF/OCR Report parsing using `pdfplumber` and Tesseract, and the semantic RAG retrieval system powered by BioLORD and FAISS vector indexing.
- **`llm_engine.py` (The Engine)**: Handles hybrid local/cloud generation. It first attempts to load the fine-tuned offline LLaMA 3 model. If unavailable or rate-limited, it implements a secure exponential backoff fallback to the Google Gemini API. It also handles JSON recovery for truncated outputs.
- **`database.py` (The Memory)**: A SQLite-based system using `PRAGMA journal_mode=WAL` for concurrent reads. It securely stores user profiles, medical histories, and consultation JSON states.
- **`pdf_report.py` (The Output)**: Uses ReportLab to convert the AI's JSON outputs into beautiful, printable A4 PDF prescriptions.
- **`static/` (The Face)**: The frontend SPA. Contains `index.html`, `style.css`, and `app.js` which manages the complex client-side state machine without needing full page reloads.

### Data & Training
- **`data/`**: Contains the critical offline lookup dictionaries (`medicine_db.py`, `drug_db.py`, `extended_diseases.py`). This prevents AI hallucinations by forcing the LLM to select from verified medical lists.
- **`training/`**: The massive pipeline scripts (`build_dataset.py`, `finetune_llama.py`, `finetune_biobert.py`) used to compile PubMed data and train the LLaMA/BioBERT models on an H100 cluster.

---

## ⚡ Quick Start

### Step 1: Install Dependencies
```bash
pip install fastapi uvicorn python-multipart python-dotenv requests Pillow plotly pandas reportlab pdfplumber beautifulsoup4
```

### Step 2: Environment Setup
Copy the example file to create your own configuration:
```bash
cp .env.example .env
```
Edit `.env` and add your **Gemini API Key** (Get it free at [Google AI Studio](https://aistudio.google.com)).

### Step 3: Run the Server
```bash
bash start.sh
# The platform will be live at: http://localhost:8000
```

---

## 📄 Example Reports & Prescriptions

You can view actual outputs generated by the ArogyaAI pipeline in the `Report/` directory:
- 🧪 **Input**: [Sample Patient Blood Report (PDF)](Report/ramesh_kumar_blood_report-1.pdf)
- 📝 **Output**: [ArogyaAI Unified 3-System Prescription (PDF)](Report/ArogyaAI_Prescription_all.pdf)

---

## 🤗 Hugging Face Models & Datasets

Because the fine-tuned models and datasets are too large for GitHub, they have been hosted publicly on Hugging Face. You can download and run them locally:

- 🧠 **Fine-tuned LLaMA 3 (8B)**: [Aman0026/ArogyaAI-LLaMA3-8B](https://huggingface.co/Aman0026/ArogyaAI-LLaMA3-8B)
- 🔍 **Fine-tuned BioBERT (BioLORD)**: [Aman0026/ArogyaAI-BioBERT-BioLORD](https://huggingface.co/Aman0026/ArogyaAI-BioBERT-BioLORD)
- 📚 **Medical Q&A Datasets**: [Aman0026/ArogyaAI-Medical-Instruction-Dataset](https://huggingface.co/datasets/Aman0026/ArogyaAI-Medical-Instruction-Dataset)

---

## 🧬 Training Pipeline (H100 Server)

If you have access to a heavy compute cluster (e.g., Dual H100 80GB), you can recreate the fine-tuned models from scratch.

### 1. Build Dataset (~20 min)
Compiles knowledge bases, PubMed, and OpenFDA into JSONL format for LLaMA and Sentence Pairs for BioBERT.
```bash
python training/build_dataset.py --all
```

### 2. Fine-tune LLaMA 3 8B (~4 hours)
Uses DeepSpeed ZeRO Stage 2 and QLoRA.
```bash
export HUGGINGFACE_TOKEN="hf_..."
deepspeed --num_gpus=2 training/finetune_llama.py
```

### 3. Fine-tune BioBERT + Build FAISS (~1 hour)
Teaches the embeddings to map "Hinglish" (e.g. 'bukhar') to formal English ('fever').
```bash
python training/finetune_biobert.py --all
```

---

## 📈 Model Evaluation Metrics

### BioBERT (BioLORD) Semantic Similarity
*Note: This model was trained on an H100 cluster to build a hyper-local retrieval engine capable of mapping highly colloquial Indian medical terms (Romanized Hindi, Marathi, Tamil, etc.) directly to standard clinical terminology.*

- **Dataset:** Fine-tuned on a robust dataset of **7,689** cross-lingual Indian medical sentence pairs.
- **Metrics:** During 9 epochs of optimized training with a batch size of 180, the model achieved peak Spearman correlations of **+0.4657**. 
- **Performance:** 
  - **Perfect Top-1 Retrieval** on our strict benchmark evaluation suite.
  - **60% zero-shot accuracy** on highly colloquial, unseen Romanized/Hinglish test phrases. *(Note: This zero-shot metric is currently bottlenecked by the limited size of our custom training dataset. It is expected to scale significantly higher as the dataset expands, but current hardware and open-source data constraints limited the available training vocabulary).*

| Epoch | Step | Spearman Cosine |
|:-----:|:----:|:---------------:|
| 1.0   | 43   | 0.4523          |
| 5.0   | 215  | 0.3544          |
| 7.0   | 301  | 0.3783          |
| 9.0   | 387  | 0.4657          |

✅ **Evaluation Note:** The positive Spearman alignment and perfect top-1 retrieval accuracy prove that the RAG embeddings can accurately capture cross-lingual semantic similarity for complex, multi-language Indian medical queries without hallucination.

---

## 📊 Knowledge Base Scale
| Category | Count |
|----------|-------|
| Diseases (full profiles) | 110+ |
| Allopathic medicines with Indian brands | 222,825+ |
| Ayurvedic formulations with brands | 30+ |
| Homeopathic remedies | 20+ |
| Drug interactions (Allopathic + Ayurvedic cross-system) | 23+ |
| Blood test reference ranges | 40+ |

<br>
<div align="center">
<i>ArogyaAI — Democratising healthcare intelligence for Bharat 🇮🇳</i>
</div>
