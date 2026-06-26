import base64
import json
import logging
import os
import re
import time
from typing import Optional

import requests

import config

logger = logging.getLogger("llm_engine")

# ── Module-level globals (In-memory state) ────────────────────────────────────
_gemini_key: str = ""
_last_api_call_time: float = 0.0   # epoch seconds of last Gemini call
_MIN_CALL_GAP: float = 6.0         # enforce ≥ 6s gap (15 RPM free tier = 4s min, use 6s for safety)
_health_checked: bool = False      # True once per process lifecycle
_health_ok: bool = False
_health_msg: str = ""
_rate_limit_until: float = 0.0     # epoch time until which all calls are blocked (cooldown after 429)

_local_model = None
_local_tokenizer = None
_local_loaded: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def set_gemini_key(key: str):
    """Store key globally. Call when user saves key in Settings tab."""
    global _gemini_key, _health_checked
    stripped = key.strip()
    if stripped and stripped != _gemini_key:
        _gemini_key     = stripped
        _health_checked = False   # allow one fresh health check after new key
        logger.info("Gemini API key updated (%d chars)", len(stripped))


def get_gemini_key() -> str:
    """Returns key: module global → config.py hardcoded → env var."""
    global _gemini_key
    if _gemini_key:
        return _gemini_key
    cfg = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if cfg:
        _gemini_key = cfg
    return _gemini_key


def reset_health_cache():
    """Allow a fresh health check (e.g. after key change)."""
    global _health_checked
    _health_checked = False


# ═══════════════════════════════════════════════════════════════════════════════
# THROTTLE — minimum gap between API calls prevents cascade 429s
# ═══════════════════════════════════════════════════════════════════════════════

def _throttle():
    global _last_api_call_time
    now     = time.time()
    elapsed = now - _last_api_call_time
    if elapsed < _MIN_CALL_GAP and _last_api_call_time > 0:
        wait = _MIN_CALL_GAP - elapsed
        logger.debug("Throttle: sleeping %.2fs", wait)
        time.sleep(wait)
    _last_api_call_time = time.time()


def _is_rate_limited() -> bool:
    """Check if we're in a cooldown period after a 429."""
    if _rate_limit_until > 0:
        remaining = _rate_limit_until - time.time()
        if remaining > 0:
            logger.warning("Rate limit cooldown active. Wait %ds before retrying.", int(remaining))
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# GEMINI REST CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

def _gemini_post(payload: dict, model: str = None, retries: int = 2) -> Optional[dict]:
    """
    POST to Gemini with throttle + exponential backoff.
    On 429: waits 60s on first attempt, fails fast on second.
    Global cooldown prevents other calls from piling up.
    """
    global _rate_limit_until

    key = get_gemini_key()
    if not key:
        logger.error("No Gemini key. Set it in ⚙ Settings tab.")
        return None

    # If we're in cooldown from a recent 429, fail immediately
    if _is_rate_limited():
        return None

    model   = model or config.GEMINI_MODEL
    url     = f"{config.GEMINI_BASE_URL}/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}

    for attempt in range(retries):
        _throttle()   # always enforce gap before each attempt
        try:
            r = requests.post(url, headers=headers, json=payload,
                              timeout=config.GEMINI_TIMEOUT)

            if r.status_code == 200:
                _rate_limit_until = 0.0   # clear any cooldown on success
                return r.json()

            if r.status_code == 429:
                # Set global cooldown — block ALL calls for 60s
                _rate_limit_until = time.time() + 60.0
                if attempt == 0:
                    logger.warning("Gemini 429 rate limit. Cooling down 60s (attempt %d/%d). "
                                   "Free tier: 15 RPM. Wait and retry.",
                                   attempt + 1, retries)
                    time.sleep(60)
                    _last_api_call_time = time.time()
                    continue
                else:
                    # Second 429 — give up, don't burn more quota
                    logger.error("Gemini 429 again. Quota exhausted. Wait 1-2 minutes "
                                 "or get a new API key at aistudio.google.com")
                    return None

            if r.status_code == 401:
                logger.error("Gemini 401 — INVALID API KEY. Update in ⚙ Settings.")
                return None

            if r.status_code == 404:
                logger.error("Gemini 404 — model '%s' not found. Check config.GEMINI_MODEL", model)
                return None

            if r.status_code in (500, 503):
                wait = 10 * (attempt + 1)
                logger.warning("Gemini %d server error. Waiting %ds.", r.status_code, wait)
                time.sleep(wait)
                continue

            logger.error("Gemini HTTP %d: %s", r.status_code, r.text[:400])
            return None

        except requests.Timeout:
            wait = 15 * (attempt + 1)
            logger.warning("Gemini timeout (attempt %d/%d). Waiting %ds.",
                           attempt + 1, retries, wait)
            time.sleep(wait)

        except Exception as e:
            logger.error("Gemini request exception: %s", e)
            return None

    logger.error("Gemini: all %d retries exhausted.", retries)
    return None


def _extract(data: dict) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error("Gemini response parse error: %s | %s", e, str(data)[:300])
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL LLAMA ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _load_local():
    global _local_model, _local_tokenizer, _local_loaded
    if _local_loaded:
        return _local_model is not None
    _local_loaded = True

    if not config.LOCAL_LLM_ENABLED:
        logger.info("Local LLM not found — using Gemini API")
        return False
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
        logger.info("Loading local LLaMA from %s ...", config.LOCAL_LLM_PATH)
        bnb = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        _local_tokenizer = AutoTokenizer.from_pretrained(
            config.LOCAL_LLM_PATH, trust_remote_code=True)
        if _local_tokenizer.pad_token is None:
            _local_tokenizer.pad_token = _local_tokenizer.eos_token
        _local_model = AutoModelForCausalLM.from_pretrained(
            config.LOCAL_LLM_PATH, quantization_config=bnb,
            device_map="auto", trust_remote_code=True)
        _local_model.eval()
        logger.info("✅ Local LLaMA loaded — unlimited FREE inference")
        return True
    except Exception as e:
        logger.error("Local model load failed: %s", e)
        _local_model = None
        return False


def _infer_local(prompt: str) -> str:
    import torch
    try:
        messages = [
            {"role": "system", "content": (
                "You are ArogyaAI — a senior Indian physician AI. "
                "Prescribe specific medicines. Use Indian brand names. "
                "Include exact doses. Respond only with valid JSON.")},
            {"role": "user", "content": prompt},
        ]
        if hasattr(_local_tokenizer, "apply_chat_template"):
            result_ids = _local_tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
            if hasattr(result_ids, "keys"):
                inputs = result_ids
            else:
                inputs = {"input_ids": result_ids}
        else:
            txt = "\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)
            inputs = _local_tokenizer(txt, return_tensors="pt")
            
        device = next(_local_model.parameters()).device
        if hasattr(inputs, "to"):
            inputs = inputs.to(device)
        else:
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            input_ids = inputs["input_ids"]
            attention_mask = inputs.get("attention_mask", None) if hasattr(inputs, "get") else None
            out = _local_model.generate(
                input_ids, attention_mask=attention_mask, max_new_tokens=3072, temperature=0.1, do_sample=True,
                top_p=0.9, pad_token_id=_local_tokenizer.eos_token_id)
        return _local_tokenizer.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True)
    except Exception as e:
        import traceback
        logger.error("Local inference error:\n%s", traceback.format_exc())
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_text(prompt: str, system: str = "", is_json: bool = False) -> str:
    if _load_local():
        result = _infer_local(f"{system}\n\n{prompt}" if system else prompt)
        if result.strip():
            # For JSON calls, don't accept the local model's output blindly —
            # if it's not actually parseable JSON, fall through to Gemini
            # instead of shipping garbage to the caller.
            if not is_json:
                return result
            if _parse_json(result) is not None:
                return result
            logger.warning("Local model returned unparseable JSON (%d chars) — falling back to Gemini.", len(result))
    key = get_gemini_key()
    if not key:
        return "ERROR: No API key. Add your Gemini key in ⚙ Settings tab."
    full = f"{system}\n\n{prompt}" if system else prompt
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full}]}],
        "generationConfig": {
            "temperature":     config.GEMINI_TEMP,
            "maxOutputTokens": config.GEMINI_MAX_TOKENS,
            "topP": 0.9,
        },
    }
    if is_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        
    data = _gemini_post(payload)
    if not data:
        return "ERROR: Gemini API failed. Check key and internet connection."
    return _extract(data) or "ERROR: Empty response from Gemini."


def generate_json(prompt: str, system: str = "") -> Optional[dict]:
    suffix = "\n\nRespond with ONLY valid JSON. No markdown, no backticks, no text."
    raw = generate_text(prompt + suffix, system, is_json=True)
    if raw.startswith("ERROR:"):
        logger.error("generate_json: %s", raw)
        return None
    parsed = _parse_json(raw)
    if not parsed:
        logger.error("generate_json: JSON parse error. Raw: %s", raw[:300])
        return None
    return parsed


def analyze_image(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    key = get_gemini_key()
    if not key:
        return "ERROR: Gemini API key required for image analysis."
    if not image_bytes:
        return "ERROR: No image data received. File may have been read already."
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime_type, "data": b64}},
        ]}],
        "generationConfig": {"temperature": 0.05, "maxOutputTokens": config.GEMINI_MAX_TOKENS},
    }
    # Vision MUST use gemini-2.0-flash (not lite — lite may not support multimodal)
    vision_model = "gemini-2.0-flash"
    data = _gemini_post(payload, model=vision_model)
    if not data:
        return "ERROR: Image analysis failed. Check API key."
    return _extract(data) or "ERROR: No analysis returned."


def analyze_image_json(prompt: str, image_bytes: bytes, mime_type: str) -> Optional[dict]:
    raw = analyze_image(prompt + "\n\nReturn ONLY valid JSON. No markdown.", image_bytes, mime_type)
    if raw.startswith("ERROR:"):
        return None
    return _parse_json(raw)


def check_health(force: bool = False) -> tuple[bool, str]:
    """
    Check AI engine. Cached result returned unless force=True.
    When force=False: only checks if key/model exists — NO API call.
    When force=True:  actually pings Gemini (use only on user click).
    This prevents the app from consuming API quota on page loads.
    """
    global _health_checked, _health_ok, _health_msg

    if _health_checked and not force:
        return _health_ok, _health_msg

    if _load_local():
        _health_ok = True; _health_msg = "⚡ Local LLaMA active — unlimited free inference"
        _health_checked = True
        return True, _health_msg

    key = get_gemini_key()
    if not key:
        _health_ok = False; _health_msg = "No API key set. Enter it in ⚙ Settings."
        _health_checked = True
        return False, _health_msg

    # If not forced, just trust the key exists — skip API call to save quota
    if not force:
        _health_ok  = True
        _health_msg = f"✓ Gemini key set ({len(key)} chars) — ready"
        _health_checked = True
        return True, _health_msg

    # Only do a live API ping when user explicitly clicks "Test Connection"
    logger.info("Running Gemini connection test (user-requested)...")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Reply exactly: OK"}]}],
        "generationConfig": {"maxOutputTokens": 5, "temperature": 0},
    }
    data = _gemini_post(payload, retries=2)
    if data and _extract(data):
        _health_ok  = True
        _health_msg = f"✓ Gemini {config.GEMINI_MODEL} connected and verified"
    else:
        _health_ok  = False
        _health_msg = "Gemini API unreachable. Check key/internet. You may be rate-limited — wait 60s and retry."

    _health_checked = True
    return _health_ok, _health_msg


def _try_close_truncated_json(text: str) -> Optional[str]:
    """
    Best-effort repair for JSON cut off mid-generation (e.g. local model hit
    max_new_tokens before finishing the homeopathy/ayurveda section). Walks
    the string tracking open brackets/strings and appends whatever closing
    characters are needed to make it syntactically valid again.
    Returns the repaired string, or None if there's nothing to repair.
    """
    stack = []
    in_string = False
    escape = False

    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()

    if not stack and not in_string:
        return None  # nothing unbalanced — the original parse failure was something else

    repaired = text
    if in_string:
        repaired += '"'
    repaired = re.sub(r',\s*$', '', repaired.rstrip())  # drop a dangling trailing comma
    closers = {'{': '}', '[': ']'}
    for opener in reversed(stack):
        repaired += closers[opener]
    return repaired


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    text = raw.strip()
    for fence in ["```json", "```JSON", "```"]:
        if text.startswith(fence):
            text = text[len(fence):]
            break
    text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    stripped_start = text.lstrip()[:1]
    if stripped_start == '{':
        s, e = text.find('{'), text.rfind('}')
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
    elif stripped_start == '[':
        s, e = text.find('['), text.rfind(']')
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
    s = text.find("{")
    if s != -1:
        repaired = _try_close_truncated_json(text[s:])
        if repaired:
            try:
                result = json.loads(repaired)
                logger.warning("JSON response was truncated — repaired by closing open brackets.")
                return result
            except json.JSONDecodeError:
                pass
    logger.error("JSON parse failed. Raw: %s", text[:400])
    return None