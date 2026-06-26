/* ==========================================================================
   ArogyaAI — Frontend Logic (SPA)
   ========================================================================== */

const API_BASE = '/api';

// --- State Management ---
const appState = {
    user: null,
    patient: null,
    role: null, // 'patient' or 'doctor'
    currentView: 'landing',
    prescriptionResult: null
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already in localStorage (simple session persistence)
    const savedUser = localStorage.getItem('arogya_user');
    const savedPatient = localStorage.getItem('arogya_patient');
    if (savedUser) {
        appState.user = JSON.parse(savedUser);
        if (savedPatient) appState.patient = JSON.parse(savedPatient);
        
        if (appState.user.role === 'admin') navigate('admin');
        else if (appState.user.role === 'patient') navigate('consult');
        else navigate('doctor');
    } else {
        navigate('landing');
    }
});

// --- Navigation & Routing ---
function navigate(view) {
    appState.currentView = view;
    
    // Hide all views
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active-view'));
    
    // Show target view
    const target = document.getElementById(`view-${view}`);
    if (target) target.classList.add('active-view');
    
    // Top Nav visibility
    const nav = document.getElementById('navbar');
    if (view === 'landing' || view === 'login') {
        nav.style.display = 'none';
    } else {
        nav.style.display = 'block';
        renderNavLinks();
    }

    // View specific initialization
    if (view === 'consult') initConsultView();
    if (view === 'profile') initProfileView();
    if (view === 'history') loadHistory();
    if (view === 'doctor') loadDoctorData();
    if (view === 'admin') initAdminView();
    if (view === 'druginfo') initDrugInfoView();
}

function renderNavLinks() {
    const container = document.getElementById('navLinks');
    container.innerHTML = '';
    
    if (appState.user.role === 'patient') {
        const links = [
            { id: 'consult', icon: '🏠', label: 'Consult' },
            { id: 'profile', icon: '👤', label: 'Profile' },
            { id: 'history', icon: '📈', label: 'History' },
            { id: 'druginfo', icon: '💊', label: 'Drug Info' }
        ];
        
        links.forEach(l => {
            const btn = document.createElement('button');
            btn.className = `nav-btn ${appState.currentView === l.id ? 'active' : ''}`;
            btn.innerHTML = `${l.icon} ${l.label}`;
            btn.onclick = () => navigate(l.id);
            container.appendChild(btn);
        });
    } else if (appState.user.role === 'admin') {
        const btn = document.createElement('button');
        btn.className = `nav-btn ${appState.currentView === 'admin' ? 'active' : ''}`;
        btn.innerHTML = `👑 Admin Dashboard`;
        btn.onclick = () => navigate('admin');
        container.appendChild(btn);
    }
}

// --- Auth (Login / Register) ---
function renderLogin() {
    navigate('login');
    document.getElementById('loginTitle').innerText = appState.role === 'patient' ? 'Patient Portal' : 'Doctor Portal';
    document.getElementById('loginIcon').innerText = appState.role === 'patient' ? '👤' : '🩺';
    
    if (appState.role === 'doctor') {
        document.getElementById('tabRegister').style.display = 'none';
        switchLoginTab('login');
    } else {
        document.getElementById('tabRegister').style.display = 'block';
        switchLoginTab('login');
    }
}

function switchLoginTab(tab) {
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.form-section').forEach(el => el.classList.remove('active-form'));
    
    if (tab === 'login') {
        document.querySelector('.tab:nth-child(1)').classList.add('active');
        document.getElementById('loginForm').classList.add('active-form');
    } else {
        document.querySelector('.tab:nth-child(2)').classList.add('active');
        document.getElementById('registerForm').classList.add('active-form');
    }
}

async function doLogin() {
    const u = document.getElementById('l_username').value;
    const p = document.getElementById('l_password').value;
    const err = document.getElementById('loginError');
    
    if (!u || !p) { err.innerText = "Fill both fields"; return; }
    
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        
        if (res.ok) {
            if (data.user.role !== appState.role && data.user.role !== 'admin') {
                err.innerText = `This is a ${data.user.role} account. Use correct portal.`;
                return;
            }
            appState.user = data.user;
            appState.patient = data.patient;
            localStorage.setItem('arogya_user', JSON.stringify(data.user));
            if (data.patient) localStorage.setItem('arogya_patient', JSON.stringify(data.patient));
            
            if (data.user.role === 'admin') navigate('admin');
            else navigate(appState.role === 'patient' ? 'consult' : 'doctor');
        } else {
            err.innerText = data.detail || "Login failed";
        }
    } catch (e) {
        err.innerText = "Network error";
    }
}

async function doRegister() {
    const u = document.getElementById('r_username').value;
    const p = document.getElementById('r_password').value;
    const msg = document.getElementById('registerMsg');
    
    try {
        const res = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (res.ok) {
            msg.style.color = "var(--secondary)";
            msg.innerText = "Account created! Please login.";
            setTimeout(() => switchLoginTab('login'), 1500);
        } else {
            msg.style.color = "var(--danger)";
            msg.innerText = data.detail;
        }
    } catch (e) {
        msg.innerText = "Network error";
    }
}

function logout() {
    localStorage.removeItem('arogya_user');
    localStorage.removeItem('arogya_patient');
    appState.user = null;
    appState.patient = null;
    navigate('landing');
}

// --- Profile View ---
async function initProfileView() {
    if (!appState.patient) return;

    // Fetch config and populate states
    try {
        const configRes = await fetch(`${API_BASE}/config`);
        if (configRes.ok) {
            const configData = await configRes.json();
            if (configData.success && configData.indian_states) {
                const stateSelect = document.getElementById('p_state');
                stateSelect.innerHTML = configData.indian_states.map(state => `<option value="${state}">${state}</option>`).join('');
            }
        }
    } catch (e) {
        console.error("Failed to load config for states", e);
    }

    const p = appState.patient;
    document.getElementById('p_name').value = p.name || '';
    document.getElementById('p_age').value = p.age || '';
    document.getElementById('p_gender').value = p.gender || 'Male';
    document.getElementById('p_weight').value = p.weight_kg || '';
    document.getElementById('p_height').value = p.height_cm || '';
    document.getElementById('p_blood').value = p.blood_group || '—';
    document.getElementById('p_sys').value = p.bp_systolic || '';
    document.getElementById('p_dia').value = p.bp_diastolic || '';
    document.getElementById('p_temp').value = p.temperature_f || '';
    
    // Set the state after it's been populated
    if (p.state) {
        document.getElementById('p_state').value = p.state;
    } else {
        document.getElementById('p_state').value = 'Tamil Nadu';
    }

    document.getElementById('p_city').value = p.city || '';
    document.getElementById('p_diet').value = p.dietary_pref || 'Non-Vegetarian';
    
    document.getElementById('p_cond').value = (p.conditions || []).join(', ');
    document.getElementById('p_aller').value = (p.allergies || []).join(', ');
    document.getElementById('p_meds').value = (p.current_meds || []).join(', ');
}

async function saveProfile() {
    const payload = {
        user_id: appState.user.id,
        name: document.getElementById('p_name').value,
        age: parseInt(document.getElementById('p_age').value) || 25,
        gender: document.getElementById('p_gender').value,
        weight_kg: parseFloat(document.getElementById('p_weight').value) || 65.0,
        height_cm: parseFloat(document.getElementById('p_height').value) || 165.0,
        blood_group: document.getElementById('p_blood').value,
        bp_systolic: parseInt(document.getElementById('p_sys').value) || null,
        bp_diastolic: parseInt(document.getElementById('p_dia').value) || null,
        temperature_f: parseFloat(document.getElementById('p_temp').value) || null,
        state: document.getElementById('p_state').value,
        city: document.getElementById('p_city').value,
        language: "English",
        dietary_pref: document.getElementById('p_diet').value,
        conditions: document.getElementById('p_cond').value.split(',').map(s=>s.trim()).filter(s=>s),
        allergies: document.getElementById('p_aller').value.split(',').map(s=>s.trim()).filter(s=>s),
        current_meds: document.getElementById('p_meds').value.split(',').map(s=>s.trim()).filter(s=>s),
        emergency_contact: ""
    };
    
    if (!payload.name) { alert("Name is required"); return; }
    
    try {
        const res = await fetch(`${API_BASE}/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            appState.patient = data.patient;
            localStorage.setItem('arogya_patient', JSON.stringify(data.patient));
            alert("Profile Saved!");
            navigate('consult');
        } else alert("Error saving profile");
    } catch (e) {
        alert("Network error");
    }
}

// --- Consult View ---
function initConsultView() {
    document.getElementById('profileAlert').style.display = appState.patient ? 'none' : 'flex';
    if (appState.patient) {
        document.getElementById('iv_sys').value = appState.patient.bp_systolic || 120;
        document.getElementById('iv_dia').value = appState.patient.bp_diastolic || 80;
        document.getElementById('iv_temp').value = appState.patient.temperature_f || 98.6;
    }
}

async function analyzeReport() {
    const fileInput = document.getElementById('reportFile');
    const manualInput = document.getElementById('reportManual').value;
    
    document.getElementById('loaderState').style.display = 'block';
    document.getElementById('reportResult').style.display = 'none';
    
    try {
        let res, data;
        if (manualInput.trim()) {
            res = await fetch(`${API_BASE}/analyze-manual`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ values_text: manualInput, gender: appState.patient?.gender || 'unknown' })
            });
        } else if (fileInput.files.length > 0) {
            const fd = new FormData();
            fd.append('file', fileInput.files[0]);
            if (appState.patient) fd.append('patient_json', JSON.stringify(appState.patient));
            res = await fetch(`${API_BASE}/analyze-report`, { method: 'POST', body: fd });
        } else {
            alert("Please upload a file or paste values.");
            document.getElementById('loaderState').style.display = 'none';
            return;
        }
        
        data = await res.json();
        if (res.ok) {
            appState.currentReport = data.report;
            renderReport(data.report);
        } else {
            alert(data.detail);
        }
    } catch (e) {
        alert("Error analyzing report: " + e);
    }
    document.getElementById('loaderState').style.display = 'none';
}

function renderReport(report) {
    const div = document.getElementById('reportResult');
    div.style.display = 'block';
    
    let findingsHtml = '';
    if (report.findings && report.findings.length > 0) {
        findingsHtml = `<div style="margin-top:1rem; overflow-x:auto;">
            <table class="report-table" style="width:100%; border-collapse:collapse; font-size:0.9rem;">
                <tr style="background:var(--border); text-align:left;">
                    <th style="padding:8px;">Parameter</th>
                    <th style="padding:8px;">Value</th>
                    <th style="padding:8px;">Range</th>
                    <th style="padding:8px;">Status</th>
                </tr>`;
        report.findings.forEach(f => {
            let statusColor = 'var(--text)';
            let s = (f.status || '').toLowerCase();
            if (s.includes('high') || s.includes('critical')) statusColor = 'var(--danger)';
            else if (s.includes('low')) statusColor = '#d97706'; // amber
            
            findingsHtml += `
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:8px; font-weight:500;">${f.parameter}</td>
                    <td style="padding:8px; color:${statusColor}; font-weight:bold;">${f.value} ${f.unit || ''}</td>
                    <td style="padding:8px; color:var(--text-muted);">${f.reference_range}</td>
                    <td style="padding:8px; color:${statusColor}; font-weight:bold;">${f.status}</td>
                </tr>
            `;
        });
        findingsHtml += `</table></div>`;
    }

    div.innerHTML = `
        <h3 style="color:var(--primary); margin-bottom: 0.5rem;">📊 ${report.report_type || 'Report'}</h3>
        <p style="font-weight:700;">${report.overall_impression || ''}</p>
        <p style="font-size:0.85rem; margin-top:0.5rem; color:var(--text-muted);">${report.patient_summary || ''}</p>
        ${findingsHtml}
    `;
}

// --- Drug Info View ---
function initDrugInfoView() {
    document.getElementById('drugInput').value = '';
    document.getElementById('drugResult').innerHTML = '';
}

async function lookupMedicine() {
    const q = document.getElementById('drugInput').value;
    if (!q.trim()) return;
    
    document.getElementById('drugLoader').style.display = 'block';
    document.getElementById('drugResult').innerHTML = '';
    
    try {
        const res = await fetch(`${API_BASE}/medicine-info`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ drug_name: q })
        });
        const data = await res.json();
        if (res.ok && data.info && !data.info.error) {
            const info = data.info;
            document.getElementById('drugResult').innerHTML = `
                <div class="glass-card" style="margin-top:1rem;">
                    <h3 style="color:var(--primary); font-size:1.5rem;">💊 ${info.query}</h3>
                    <p style="color:var(--text-muted); margin-bottom:1rem;">Generic / Salt: <b>${info.generic_salt}</b> <span style="badge">${info.drug_class || ''}</span></p>
                    
                    <h4>🎯 Primary Uses</h4>
                    <ul style="margin-bottom:1rem; padding-left:1.2rem;">
                        ${(info.primary_uses||[]).map(u=>`<li>${u}</li>`).join('')}
                    </ul>
                    
                    <h4>⚙️ How it Works</h4>
                    <p style="margin-bottom:1rem; font-size:0.95rem; line-height:1.5;">${info.mechanism_of_action}</p>
                    
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
                        <div style="background:var(--bg); padding:1rem; border-radius:8px;">
                            <h4 style="color:#d97706;">⚠️ Side Effects</h4>
                            <ul style="padding-left:1.2rem; font-size:0.9rem;">
                                ${(info.common_side_effects||[]).map(u=>`<li>${u}</li>`).join('')}
                            </ul>
                        </div>
                        <div style="background:var(--bg); padding:1rem; border-radius:8px;">
                            <h4 style="color:var(--danger);">❌ Contraindications</h4>
                            <ul style="padding-left:1.2rem; font-size:0.9rem;">
                                ${(info.contraindications||[]).map(u=>`<li>${u}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    
                    <h4>🛍️ Popular Indian Brands</h4>
                    <p style="font-size:0.95rem;">${(info.popular_indian_brands||[]).join(', ')}</p>
                    
                    <div class="alert-box" style="margin-top:1rem;">
                        💡 <b>Safety Tip:</b> ${info.safety_advice}
                    </div>
                </div>
            `;
        } else {
            document.getElementById('drugResult').innerHTML = `<p style="color:var(--danger);">Error finding details: ${data.info?.error || 'Unknown'}</p>`;
        }
    } catch(e) {
        document.getElementById('drugResult').innerHTML = `<p style="color:var(--danger);">Network Error</p>`;
    }
    document.getElementById('drugLoader').style.display = 'none';
}

async function generatePrescription() {
    const sym = document.getElementById('symptomsText').value;
    if (!sym.trim()) { alert("Please describe your symptoms."); return; }
    
    document.getElementById('loaderState').style.display = 'block';
    document.getElementById('prescriptionResult').style.display = 'none';
    
    const payload = {
        user_id: appState.user.id,
        symptoms: sym + ` (Severity: ${document.getElementById('symSeverity').value}/10. Duration: ${document.getElementById('symDuration').value})`,
        bp_systolic: parseInt(document.getElementById('iv_sys').value),
        bp_diastolic: parseInt(document.getElementById('iv_dia').value),
        temperature_f: parseFloat(document.getElementById('iv_temp').value),
        report: appState.currentReport || null
    };
    
    appState.prefSystem = document.getElementById('prefSystem') ? document.getElementById('prefSystem').value : 'all';
    
    try {
        const res = await fetch(`${API_BASE}/generate-prescription`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        document.getElementById('loaderState').style.display = 'none';

        if (res.ok) {
            appState.prescriptionResult = data.prescription;
            renderPrescription(data.prescription, data.session_id);
            navigate('prescription'); // Redirect to new page
        } else {
            alert(data.detail);
        }
    } catch (e) {
        document.getElementById('loaderState').style.display = 'none';
        alert("Error generating prescription.");
    }
}

function renderPrescription(rx, sid) {
    const div = document.getElementById('prescriptionResult');
    const recBanner = document.getElementById('rxRecommendation');
    div.style.display = 'block';
    
    if (rx.abort) {
        recBanner.style.display = 'none';
        div.innerHTML = `
            <div style="background:var(--danger-bg); padding:1.5rem; border-radius:var(--radius-md); border:1px solid var(--danger);">
                <h2 style="color:var(--danger);">🚨 EMERGENCY DETECTED</h2>
                <h3 style="margin-top:0.5rem;">${rx.emergency.condition}</h3>
                <p style="font-weight:700; margin-top:1rem; font-size:1.1rem;">⚡ Action: ${rx.emergency.action}</p>
            </div>
        `;
        return;
    }

    if (rx.error) {
        recBanner.style.display = 'none';
        div.innerHTML = `
            <div style="background:var(--warning-bg); padding:1.5rem; border-radius:var(--radius-md); border:1px solid var(--warning);">
                <h3 style="color:var(--warning); margin-bottom: 0.5rem;">⚠️ AI Engine Unavailable</h3>
                <p style="font-weight:600;">The system encountered an error:</p>
                <p style="margin-top:0.5rem;">${rx.error}</p>
                <p style="margin-top:1rem; font-size:0.85rem; color:var(--text-muted);">Please wait a minute and try again, or check your API key.</p>
                <button class="btn btn-secondary" style="margin-top:1rem;" onclick="navigate('consult')">← Back to Consult</button>
            </div>
        `;
        return;
    }

    const pref = appState.prefSystem || 'all';

    // Render Recommendation Banner
    recBanner.style.display = 'none';
    
    let html = `
        <div class="rx-header">
            <div>
                <div class="dx-title">${rx.primary_diagnosis || '—'}</div>
                <div style="color:var(--text-muted); font-size:0.85rem; margin-top:4px;">
                    ${rx.severity || ''} | ICD-10: ${rx.icd10 || '—'}
                </div>
            </div>
            <div style="text-align:right;">
                <div class="conf-label">Confidence</div>
                <div class="dx-conf">${rx.confidence || '?'}%</div>
            </div>
        </div>
        <p style="font-size:0.95rem; margin-bottom: 1.5rem; color:var(--text-main);">${rx.diagnosis_reasoning || ''}</p>
    `;
    
    // --- Render Vital Alarms ---
    if (rx.vital_alarms && rx.vital_alarms.length > 0) {
        html += `<div id="vitalAlarmsContainer">
            <h3 style="color: var(--danger); font-size: 1.1rem; margin-bottom: 0.5rem;">⚠️ Vital Alerts</h3>
        `;
        rx.vital_alarms.forEach(alarm => {
            html += `<div class="alarm-item">🚨 ${alarm}</div>`;
        });
        html += `</div>`;
    }

    
    if (pref === 'all') {
        html += `
            <div class="sys-tabs">
                <div class="sys-tab active" onclick="switchSys('allo')">💊 Allopathy</div>
                <div class="sys-tab" onclick="switchSys('ayur')">🌿 Ayurveda</div>
                <div class="sys-tab" onclick="switchSys('home')">💧 Homeopathy</div>
            </div>
        `;
    } else {
        let title = '';
        if (pref === 'allo') title = `💊 Allopathy`;
        if (pref === 'ayur') title = `🌿 Ayurveda`;
        if (pref === 'home') title = `💧 Homeopathy`;
        html += `
            <div class="sys-tabs">
                <div class="sys-tab active">${title}</div>
            </div>
        `;
    }
    
    let systems = [
        { id: 'allo', data: rx.allopathy },
        { id: 'ayur', data: rx.ayurveda },
        { id: 'home', data: rx.homeopathy }
    ];
    
    if (pref !== 'all') {
        systems = systems.filter(s => s.id === pref);
    }
    
    systems.forEach((sys, i) => {
        html += `<div id="tab-${sys.id}" class="sys-content ${i===0 ? 'active' : ''}">
            <div class="med-grid">`;
        
        (sys.data?.medicines || []).forEach(m => {
            const searchQuery = encodeURIComponent(m.brand || m.name);
            const ecomLink = `https://www.1mg.com/search/all?name=${searchQuery}`;

            html += `<div class="med-card">
                <div class="med-name">${m.name} ${m.potency ? `(${m.potency})` : ''}</div>
                <div class="med-brand">${m.brand || ''}</div>
                <div class="med-info">
                    📦 ${m.dose || '—'} · 🕐 ${m.frequency || '—'} · 📅 ${m.duration || '—'}<br>
                    ${m.purpose ? `🎯 ${m.purpose}` : ''}
                </div>
                <a href="${ecomLink}" target="_blank" class="ecom-btn">🛒 Buy Online (1mg)</a>
            </div>`;
        });
        
        html += `</div></div>`;
    });
    
    // --- Render Precautionary Tests ---
    const tests = rx.allopathy?.tests_to_order || [];
    if (tests.length > 0) {
        html += `<div class="tests-container">
            <h3>🔬 Precautionary Medical Tests</h3>
            <p style="font-size: 0.85rem; margin-bottom: 1rem; color: #b36b00;">If symptoms persist, please consider the following investigations:</p>
            <div>
        `;
        tests.forEach(test => {
            html += `<span class="test-item">${test}</span>`;
        });
        html += `</div></div>`;
    }
    
    // --- Render Modular PDF Download Buttons ---
    html += `
        <div class="download-actions">
    `;
    
    if (pref === 'all' || pref === 'allo') {
        html += `<button class="btn btn-primary" onclick="window.open('/api/download-prescription/${sid}?system=allopathy', '_blank')">📄 Download Allopathy Rx</button>`;
    }
    if (pref === 'all' || pref === 'ayur') {
        html += `<button class="btn" style="background:#00875a; color:white;" onclick="window.open('/api/download-prescription/${sid}?system=ayurveda', '_blank')">🌿 Download Ayurveda Rx</button>`;
    }
    if (pref === 'all' || pref === 'home') {
        html += `<button class="btn" style="background:#5243aa; color:white;" onclick="window.open('/api/download-prescription/${sid}?system=homeopathy', '_blank')">💧 Download Homeopathy Rx</button>`;
    }
    
    if (pref === 'all') {
        html += `<button class="btn btn-secondary full-width mt-2" onclick="window.open('/api/download-prescription/${sid}?system=all', '_blank')">🏥 Download Full Prescription (All Systems)</button>`;
    }
    
    html += `</div>`;

    
    div.innerHTML = html;
}

window.switchSys = function(id) {
    document.querySelectorAll('.sys-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.sys-content').forEach(el => el.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`tab-${id}`).classList.add('active');
}

// --- History View ---
let patientHistoryCache = null;

async function loadHistory() {
    if (!appState.user) return;
    document.getElementById('historyLoader').style.display = 'block';
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '';
    document.getElementById('historyEmpty').style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/history/${appState.user.id}`);
        const data = await res.json();
        document.getElementById('historyLoader').style.display = 'none';
        
        if (res.ok) {
            patientHistoryCache = data.sessions;
            if (data.sessions.length === 0) {
                document.getElementById('historyEmpty').style.display = 'block';
                return;
            }
            let rows = '';
            data.sessions.forEach(s => {
                let dx = '—';
                if (s.prescription && s.prescription.primary_diagnosis) dx = s.prescription.primary_diagnosis;
                if (s.emergency) dx = '🚨 Emergency';
                rows += `<tr>
                    <td>${s.ts.substring(0,16).replace('T', ' ')}</td>
                    <td>${s.symptoms ? s.symptoms.substring(0, 45) + '...' : '—'}</td>
                    <td style="font-weight:600;">${dx}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary" onclick="viewPatientSession('${s.id}')">View</button>
                        ${s.prescription ? `<button class="btn btn-sm btn-primary" onclick="window.open('/api/download-prescription/${s.id}?system=all', '_blank')">PDF</button>` : ''}
                    </td>
                </tr>`;
            });
            tbody.innerHTML = rows;
        } else {
            document.getElementById('historyEmpty').style.display = 'block';
            document.getElementById('historyEmpty').innerText = "Failed to load history.";
        }
    } catch (e) {
        document.getElementById('historyLoader').style.display = 'none';
        document.getElementById('historyEmpty').style.display = 'block';
        document.getElementById('historyEmpty').innerText = "Network error.";
    }
}

window.viewPatientSession = function(sid) {
    const session = (patientHistoryCache || []).find(s => s.id === sid);
    if (!session) return;
    
    document.getElementById('patientSessionModal').style.display = 'flex';
    document.getElementById('pModalTitle').innerText = `Session Details: ${session.ts.substring(0,10)}`;
    
    const rx = session.prescription;
    let rxHtml = `<p><strong>Symptoms:</strong> ${session.symptoms}</p>`;
    
    if (session.emergency) {
        rxHtml += `<div class="badge badge-danger" style="margin-top:1rem; font-size:1rem; padding:0.5rem 1rem;">🚨 Emergency Triggered</div>`;
    } else if (rx && rx.primary_diagnosis) {
        rxHtml += `
            <div style="margin-top:1rem; border:1px solid var(--border); padding:1.5rem; border-radius:var(--radius-md); background:var(--bg-color);">
                <h4 style="color:var(--primary); margin-bottom:0.5rem; font-size:1.2rem;">Diagnosis: ${rx.primary_diagnosis}</h4>
                <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:1rem;">${rx.diagnosis_reasoning || ''}</p>
                
                <h5 style="margin-bottom:0.5rem;">Allopathy Prescription</h5>
                <ul style="font-size:0.9rem; padding-left:1.5rem; margin-bottom:1rem; color:var(--text-main);">
                    ${(rx.allopathy?.medicines || []).map(m => `<li><strong>${m.name}</strong> - ${m.dose} (${m.duration})</li>`).join('') || '<li>None</li>'}
                </ul>

                <h5 style="margin-bottom:0.5rem;">Ayurveda Alternatives</h5>
                <ul style="font-size:0.9rem; padding-left:1.5rem; color:var(--text-main);">
                    ${(rx.ayurveda?.medicines || []).map(m => `<li><strong>${m.name}</strong> - ${m.dose}</li>`).join('') || '<li>None</li>'}
                </ul>
            </div>
        `;
    } else {
        rxHtml += `<p style="margin-top:1rem; color:var(--text-muted);">No detailed prescription data recorded.</p>`;
    }
    
    document.getElementById('pModalBody').innerHTML = rxHtml;
}

window.closePatientSessionModal = function() {
    document.getElementById('patientSessionModal').style.display = 'none';
}

// --- Doctor Dashboard ---
let docDataCache = null;

window.switchDocTab = function(tab) {
    document.getElementById('tabDocSessions').classList.remove('active');
    document.getElementById('tabDocPatients').classList.remove('active');
    document.getElementById('docSessionsView').classList.remove('active-form');
    document.getElementById('docPatientsView').classList.remove('active-form');

    if (tab === 'sessions') {
        document.getElementById('tabDocSessions').classList.add('active');
        document.getElementById('docSessionsView').classList.add('active-form');
    } else {
        document.getElementById('tabDocPatients').classList.add('active');
        document.getElementById('docPatientsView').classList.add('active-form');
    }
}

window.viewSessionDetails = function(sid) {
    const session = docDataCache.sessions.find(s => s.id === sid);
    if (!session) return;
    
    document.getElementById('sessionModal').style.display = 'flex';
    document.getElementById('modalTitle').innerText = `Session Details: ${session.pname || 'Patient'} - ${session.ts.substring(0,10)}`;
    
    const rx = session.prescription;
    let rxHtml = `<p><strong>Symptoms:</strong> ${session.symptoms}</p>`;
    
    if (session.emergency) {
        rxHtml += `<div class="badge badge-danger" style="margin-top:1rem; font-size:1rem; padding:0.5rem 1rem;">🚨 Emergency Triggered</div>`;
    } else if (rx && rx.primary_diagnosis) {
        rxHtml += `
            <div style="margin-top:1rem; border:1px solid var(--border); padding:1.5rem; border-radius:var(--radius-md); background:var(--bg-color);">
                <h4 style="color:var(--primary); margin-bottom:0.5rem; font-size:1.2rem;">Diagnosis: ${rx.primary_diagnosis}</h4>
                <p style="font-size:0.9rem; color:var(--text-muted); margin-bottom:1rem;">${rx.diagnosis_reasoning || ''}</p>
                
                <h5 style="margin-bottom:0.5rem;">Allopathy Prescription</h5>
                <ul style="font-size:0.9rem; padding-left:1.5rem; margin-bottom:1rem; color:var(--text-main);">
                    ${(rx.allopathy?.medicines || []).map(m => `<li><strong>${m.name}</strong> - ${m.dose} (${m.duration})</li>`).join('') || '<li>None</li>'}
                </ul>

                <h5 style="margin-bottom:0.5rem;">Ayurveda Alternatives</h5>
                <ul style="font-size:0.9rem; padding-left:1.5rem; color:var(--text-main);">
                    ${(rx.ayurveda?.medicines || []).map(m => `<li><strong>${m.name}</strong> - ${m.dose}</li>`).join('') || '<li>None</li>'}
                </ul>
            </div>
        `;
    } else {
        rxHtml += `<p style="margin-top:1rem; color:var(--text-muted);">No detailed prescription data recorded for this session.</p>`;
    }
    
    document.getElementById('modalBody').innerHTML = rxHtml;
}

window.closeSessionModal = function() {
    document.getElementById('sessionModal').style.display = 'none';
}

async function loadDoctorData() {
    try {
        const res = await fetch(`${API_BASE}/doctor-stats`);
        const data = await res.json();
        if (res.ok) {
            docDataCache = data;
            const statsDiv = document.getElementById('docStats');
            statsDiv.innerHTML = `
                <div class="stat-card"><div class="stat-val">${data.stats.patients}</div><div class="stat-lbl">Total Patients</div></div>
                <div class="stat-card"><div class="stat-val">${data.stats.sessions}</div><div class="stat-lbl">Total Consults</div></div>
                <div class="stat-card"><div class="stat-val">${data.stats.today}</div><div class="stat-lbl">Today's Consults</div></div>
                <div class="stat-card"><div class="stat-val" style="color:var(--danger);">${data.stats.emergency}</div><div class="stat-lbl">Emergencies</div></div>
            `;
            
            // Sessions Table
            const sTbody = document.getElementById('docSessionsTable');
            let sRows = '';
            data.sessions.slice(0, 20).forEach(s => {
                const badge = s.emergency ? `<span class="badge badge-danger">🚨 Emergency</span>` : `<span class="badge badge-success">✓ Processed</span>`;
                sRows += `<tr>
                    <td>${s.ts.substring(0,16).replace('T', ' ')}</td>
                    <td style="font-weight:600;">${s.pname || 'Patient'}</td>
                    <td>${s.symptoms ? s.symptoms.substring(0, 45) + '...' : ''}</td>
                    <td>${badge}</td>
                    <td><button class="btn btn-sm btn-secondary" onclick="viewSessionDetails('${s.id}')">View Rx</button></td>
                </tr>`;
            });
            sTbody.innerHTML = sRows;

            // Patients Table
            const pTbody = document.getElementById('docPatientsTable');
            let pRows = '';
            data.patients.forEach(p => {
                pRows += `<tr>
                    <td>#${p.id}</td>
                    <td style="font-weight:600;">${p.name || p.username}</td>
                    <td>${p.age ? p.age + 'y / ' + (p.gender||'') : '—'}</td>
                    <td>${p.city || '—'}</td>
                    <td>${(p.conditions || []).join(', ') || 'None'}</td>
                </tr>`;
            });
            pTbody.innerHTML = pRows;
        }
    } catch (e) {
        console.error("Failed to load doctor data", e);
    }
}

// --- Admin Dashboard Logic ---
function switchAdminTab(tab) {
    document.getElementById('tabAdminUsers').classList.remove('active');
    document.getElementById('tabAdminSessions').classList.remove('active');
    document.getElementById('adminUsersView').classList.remove('active-form');
    document.getElementById('adminSessionsView').classList.remove('active-form');
    
    if (tab === 'users') {
        document.getElementById('tabAdminUsers').classList.add('active');
        document.getElementById('adminUsersView').classList.add('active-form');
    } else {
        document.getElementById('tabAdminSessions').classList.add('active');
        document.getElementById('adminSessionsView').classList.add('active-form');
    }
}

async function initAdminView() {
    try {
        const res = await fetch(`${API_BASE}/admin-data`);
        const result = await res.json();
        if (res.ok) {
            const usersTable = document.getElementById('adminUsersTable');
            let uHtml = '';
            result.data.users.forEach(u => {
                uHtml += `<tr>
                    <td>${u.id}</td>
                    <td>${u.username}</td>
                    <td><span class="badge ${u.role === 'admin' ? 'badge-danger' : (u.role === 'doctor' ? 'badge-primary' : 'badge-success')}">${u.role}</span></td>
                    <td style="font-family: monospace; font-size: 0.8rem; color: #888;">${u.password.substring(0, 16)}...</td>
                    <td>${u.created_at ? u.created_at.substring(0, 10) : '—'}</td>
                </tr>`;
            });
            usersTable.innerHTML = uHtml;

            const sessionsTable = document.getElementById('adminSessionsTable');
            let sHtml = '';
            result.data.session_stats.forEach(s => {
                sHtml += `<tr>
                    <td>Patient #${s.patient_id}</td>
                    <td>${s.visit_count}</td>
                    <td>${s.last_visit ? s.last_visit.substring(0, 16).replace('T', ' ') : '—'}</td>
                    <td>${s.latest_session_id ? `<a href="/api/download-prescription/${s.latest_session_id}?system=all" target="_blank" class="btn" style="padding:0.2rem 0.5rem; font-size:0.8rem;">📄 View PDF</a>` : '—'}</td>
                </tr>`;
            });
            sessionsTable.innerHTML = sHtml;
        }
    } catch (e) {
        console.error("Admin data fetch error", e);
    }
}
