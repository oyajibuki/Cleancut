from fastapi import FastAPI, File, UploadFile, Form, Request, Header
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from rembg import remove, new_session
import io
import os

# Load .env if exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import init_db
from license import can_use, record_usage, verify_license, create_license

app = FastAPI()

sk = os.getenv("STRIPE_SECRET_KEY", "NOT_FOUND")
print(f"DEBUG APP LOAD - SK: {sk[:10]}...")

# Initialize DB on startup
init_db()

# Pre-load default lightweight model to save memory
session = new_session("u2netp")


@app.get("/", response_class=HTMLResponse)
async def main():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ClearCut</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            *, *::before, *::after {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                font-family: 'Noto Sans JP', sans-serif;
                background: #f5f5f5;
                color: #3a3a3a;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 30px 16px 60px;
            }

            h1 {
                font-size: 2.4rem;
                font-weight: 700;
                color: #2d2d2d;
                margin-bottom: 6px;
                letter-spacing: -0.5px;
            }

            .subtitle {
                font-size: 0.9rem;
                color: #6b6b6b;
                margin-bottom: 28px;
            }

            /* Upload Area */
            .upload-area {
                background: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 16px;
                padding: 36px 40px;
                text-align: center;
                max-width: 500px;
                width: 100%;
                transition: border-color 0.3s, background 0.3s;
                cursor: pointer;
            }
            .upload-area:hover, .upload-area.drag-over {
                border-color: #2563eb;
                background: #eff6ff;
            }
            .upload-area input[type="file"] {
                display: none;
            }
            .upload-icon {
                font-size: 2.4rem;
                margin-bottom: 10px;
            }
            .upload-text {
                font-size: 0.95rem;
                color: #6b7280;
            }
            .upload-text strong {
                color: #2563eb;
            }

            /* Model selector */
            .model-selector {
                margin-top: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                font-size: 0.85rem;
                color: #6b7280;
            }
            .model-selector select {
                background: #f1f5f9;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 12px;
                font-family: inherit;
                font-size: 0.85rem;
                cursor: pointer;
            }

            /* Buttons */
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 28px;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.15s, box-shadow 0.3s, opacity 0.3s;
                font-family: inherit;
            }
            .btn:hover { transform: translateY(-2px); }
            .btn:active { transform: translateY(0); }
            .btn-primary {
                background: linear-gradient(135deg, #2563eb, #7c3aed);
                color: #fff;
                box-shadow: 0 4px 15px rgba(37,99,235,0.3);
            }
            .btn-primary:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            .btn-download {
                background: linear-gradient(135deg, #059669, #10b981);
                color: #fff;
                box-shadow: 0 4px 15px rgba(16,185,129,0.3);
            }
            .btn-erase {
                background: linear-gradient(135deg, #ef4444, #f97316);
                color: #fff;
                box-shadow: 0 4px 15px rgba(239,68,68,0.25);
            }
            .btn-erase.active-mode {
                outline: 3px solid #ef4444;
                outline-offset: 2px;
            }
            .btn-restore {
                background: linear-gradient(135deg, #8b5cf6, #a855f7);
                color: #fff;
                box-shadow: 0 4px 15px rgba(139,92,246,0.25);
            }
            .btn-restore.active-mode {
                outline: 3px solid #8b5cf6;
                outline-offset: 2px;
            }
            .btn-secondary {
                background: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
            }
            .btn-secondary:hover {
                background: #e2e8f0;
            }

            .action-bar {
                margin-top: 20px;
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }

            /* Image container */
            .container {
                display: flex;
                gap: 30px;
                margin-top: 30px;
                width: 100%;
                max-width: 960px;
                flex-wrap: wrap;
                justify-content: center;
            }
            .box {
                flex: 1;
                min-width: 280px;
                max-width: 450px;
                background: #ffffff;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #e2e8f0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }
            .box h3 {
                font-size: 0.95rem;
                color: #6b7280;
                margin-bottom: 14px;
                font-weight: 600;
            }
            .image-wrapper {
                position: relative;
                background: repeating-conic-gradient(#f3f4f6 0% 25%, #ffffff 0% 50%) 50% / 20px 20px;
                border-radius: 10px;
                overflow: hidden;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid #e5e7eb;
            }
            .image-wrapper img {
                max-width: 100%;
                max-height: 400px;
                display: block;
            }

            /* Canvas overlay */
            .canvas-wrapper {
                position: relative;
                display: inline-block;
            }
            .canvas-wrapper canvas {
                position: absolute;
                top: 0;
                left: 0;
            }

            /* Brush toolbar */
            .brush-toolbar {
                display: none;
                flex-direction: column;
                gap: 12px;
                margin-top: 16px;
                padding: 16px;
                background: #f8fafc;
                border-radius: 12px;
            }
            .brush-toolbar.active {
                display: flex;
            }
            .btn-icon {
                width: 16px;
                height: 16px;
                vertical-align: -2px;
            }

            .brush-row {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 0.85rem;
            }
            .brush-row label {
                min-width: 90px;
                color: #6b7280;
            }
            .brush-row input[type="range"] {
                flex: 1;
                accent-color: #2563eb;
            }
            .brush-row .value {
                min-width: 36px;
                text-align: right;
                color: #2563eb;
                font-weight: 600;
            }
            .brush-actions {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
            }
            .brush-actions .btn {
                font-size: 0.85rem;
                padding: 8px 18px;
            }
            .mode-badge {
                font-size: 0.8rem;
                padding: 4px 14px;
                border-radius: 20px;
                font-weight: 600;
                margin-left: auto;
            }
            .mode-badge.erase {
                background: #fef2f2;
                color: #ef4444;
                border: 1px solid #fecaca;
            }
            .mode-badge.restore {
                background: #f5f3ff;
                color: #8b5cf6;
                border: 1px solid #ddd6fe;
            }

            /* Full-screen loading overlay */
            .loading-fullscreen {
                position: fixed;
                inset: 0;
                background: rgba(255,255,255,0.92);
                backdrop-filter: blur(6px);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s;
            }
            .loading-fullscreen.active {
                opacity: 1;
                pointer-events: all;
            }
            .loading-spinner {
                width: 56px;
                height: 56px;
                border: 4px solid #e2e8f0;
                border-top-color: #2563eb;
                border-right-color: #7c3aed;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
            .loading-label {
                margin-top: 20px;
                font-size: 1.1rem;
                color: #1e293b;
                font-weight: 600;
            }
            .loading-sub {
                margin-top: 8px;
                font-size: 0.85rem;
                color: #6b7280;
            }

            .hidden { display: none !important; }

            /* Usage bar */
            .usage-bar {
                margin-top: 18px;
                text-align: center;
                font-size: 0.88rem;
                color: #6b7280;
            }
            .usage-bar .uses-left {
                font-weight: 600;
                color: #3a3a3a;
            }
            .usage-bar.pro {
                color: #059669;
                font-weight: 600;
            }
            .upgrade-link {
                display: inline-block;
                margin-top: 8px;
                padding: 10px 28px;
                background: linear-gradient(135deg, #2563eb, #7c3aed);
                color: #fff;
                border: none;
                border-radius: 10px;
                font-size: 0.95rem;
                font-weight: 600;
                cursor: pointer;
                font-family: inherit;
                transition: transform 0.15s, box-shadow 0.3s;
                box-shadow: 0 4px 15px rgba(37,99,235,0.3);
            }
            .upgrade-link:hover { transform: translateY(-2px); }
            .license-link {
                display: block;
                margin-top: 8px;
                font-size: 0.82rem;
                color: #6b7280;
                cursor: pointer;
                text-decoration: underline;
                background: none;
                border: none;
                font-family: inherit;
            }

            /* License modal */
            .modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0,0,0,0.4);
                backdrop-filter: blur(4px);
                z-index: 9998;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.25s;
            }
            .modal-overlay.active {
                opacity: 1;
                pointer-events: all;
            }
            .modal-box {
                background: #fff;
                border-radius: 16px;
                padding: 32px;
                max-width: 420px;
                width: 90%;
                box-shadow: 0 8px 30px rgba(0,0,0,0.12);
            }
            .modal-box h2 {
                font-size: 1.2rem;
                color: #2d2d2d;
                margin-bottom: 12px;
            }
            .modal-box p {
                font-size: 0.88rem;
                color: #6b7280;
                margin-bottom: 16px;
            }
            .modal-box input {
                width: 100%;
                padding: 10px 14px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: 1rem;
                font-family: monospace;
                letter-spacing: 1px;
                text-align: center;
                margin-bottom: 12px;
            }
            .modal-box input:focus {
                outline: none;
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
            }
            .modal-actions {
                display: flex;
                gap: 10px;
                justify-content: flex-end;
            }
            .modal-msg {
                font-size: 0.82rem;
                margin-top: 8px;
                text-align: center;
            }
            .modal-msg.error { color: #ef4444; }
            .modal-msg.success { color: #059669; }

            @media (max-width: 640px) {
                h1 { font-size: 1.5rem; }
                .container { flex-direction: column; align-items: center; }
                .box { max-width: 100%; }
                .upload-area { padding: 24px 20px; }
            }
        </style>
    </head>
    <body>

        <!-- Full-screen loading overlay -->
        <div class="loading-fullscreen" id="loadingFullscreen">
            <div class="loading-spinner"></div>
            <div class="loading-label">Removing background…</div>
            <div class="loading-sub">This may take a few seconds</div>
        </div>

        <h1>ClearCut</h1>
        <p class="subtitle">Simple. Fast. Just works.</p>

        <!-- Upload area -->
        <div class="upload-area" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <p class="upload-text">Drop image here or <strong>click to upload</strong></p>
            <input type="file" id="fileInput" accept="image/*">
        </div>

        <!-- Model selector -->
        <div class="model-selector">
            <label for="modelSelect">Model:</label>
            <select id="modelSelect">
                <option value="u2netp" selected>U2NetP (Fast/Light - Default)</option>
                <option value="isnet-general-use">ISNet (High Quality - Requires Pro Server)</option>
                <option value="u2net">U2Net (Standard)</option>
                <option value="u2net_human_seg">U2Net (Portrait)</option>
                <option value="silueta">Silueta (Fast)</option>
            </select>
        </div>

        <div class="action-bar">
            <button class="btn btn-primary" id="removeBgBtn" disabled>Remove Background</button>
        </div>

        <!-- Usage bar -->
        <div class="usage-bar" id="usageBar"></div>
        <div style="text-align:center;">
            <button class="upgrade-link hidden" id="upgradeBtn">Upgrade to Pro</button>
            <button class="license-link" id="licenseLink">Already have a license? Enter here.</button>
        </div>

        <!-- License modal -->
        <div class="modal-overlay" id="licenseModal">
            <div class="modal-box">
                <h2>Enter License Key</h2>
                <p>Paste the key you received after purchase.</p>
                <input type="text" id="licenseInput" placeholder="CC-XXXX-XXXX-XXXX-XXXX" maxlength="24">
                <div class="modal-msg hidden" id="licenseMsg"></div>
                <div class="modal-actions">
                    <button class="btn btn-secondary" id="licenseCancel">Cancel</button>
                    <button class="btn btn-primary" id="licenseSubmit">Activate</button>
                </div>
            </div>
        </div>

        <div class="container hidden" id="resultContainer">
            <!-- Original -->
            <div class="box">
                <h3>Original</h3>
                <div class="image-wrapper" style="background: #fff;">
                    <img id="preview" />
                </div>
            </div>

            <!-- Result -->
            <div class="box">
                <h3>Result</h3>
                <div class="image-wrapper" id="resultWrapper">
                    <div class="canvas-wrapper" id="canvasWrapper">
                        <img id="resultImg" />
                        <canvas id="eraserCanvas"></canvas>
                    </div>
                </div>

                <!-- Brush toolbar -->
                <div class="brush-toolbar" id="brushToolbar">
                    <div class="brush-row">
                        <label>Brush Size</label>
                        <input type="range" id="brushSize" min="3" max="80" value="20">
                        <span class="value" id="brushSizeVal">20</span>
                    </div>
                    <div class="brush-actions">
                        <button class="btn btn-erase active-mode" id="eraseBtn"><svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="8" y1="8" x2="16" y2="16"/><line x1="16" y1="8" x2="8" y2="16"/></svg> Erase</button>
                        <button class="btn btn-restore" id="restoreBtn"><svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4l-1 1 4 4 1-1a2.83 2.83 0 0 0-4-4Z"/><path d="M13.5 6.5 5 15v4h4l8.5-8.5"/><line x1="2" y1="2" x2="5" y2="5"/><line x1="18" y1="13" x2="21" y2="10"/><line x1="3" y1="8" x2="1" y2="6"/></svg> Restore</button>
                        <button class="btn btn-secondary" id="undoBtn">Undo</button>
                        <span class="mode-badge erase" id="modeBadge">Erase</span>
                    </div>
                </div>

                <!-- Download button -->
                <div class="action-bar" id="resultActions" style="display:none;">
                    <button class="btn btn-download" id="downloadBtn">Download</button>
                </div>
            </div>
        </div>

        <script>
        (() => {
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            const removeBgBtn = document.getElementById('removeBgBtn');
            const preview = document.getElementById('preview');
            const resultImg = document.getElementById('resultImg');
            const resultContainer = document.getElementById('resultContainer');
            const resultActions = document.getElementById('resultActions');
            const loadingFullscreen = document.getElementById('loadingFullscreen');
            const downloadBtn = document.getElementById('downloadBtn');
            const brushToolbar = document.getElementById('brushToolbar');
            const brushSizeInput = document.getElementById('brushSize');
            const brushSizeVal = document.getElementById('brushSizeVal');
            const undoBtn = document.getElementById('undoBtn');
            const eraseBtn = document.getElementById('eraseBtn');
            const restoreBtn = document.getElementById('restoreBtn');
            const modeBadge = document.getElementById('modeBadge');
            const eraserCanvas = document.getElementById('eraserCanvas');
            const canvasWrapper = document.getElementById('canvasWrapper');
            const modelSelect = document.getElementById('modelSelect');
            const ctx = eraserCanvas.getContext('2d');

            // License & usage UI
            const usageBar = document.getElementById('usageBar');
            const upgradeBtn = document.getElementById('upgradeBtn');
            const licenseLink = document.getElementById('licenseLink');
            const licenseModal = document.getElementById('licenseModal');
            const licenseInput = document.getElementById('licenseInput');
            const licenseMsg = document.getElementById('licenseMsg');
            const licenseCancel = document.getElementById('licenseCancel');
            const licenseSubmit = document.getElementById('licenseSubmit');

            let currentFile = null;
            let resultBlobUrl = null;
            let originalSourceImage = null;
            let originalSourceCanvas = null;
            let bgRemovedImageData = null;
            let brushMode = 'erase';
            let isDrawing = false;
            let lastPos = null;
            let history = [];

            // --- License key from LocalStorage ---
            function getSavedLicense() {
                return localStorage.getItem('clearcut_license') || '';
            }
            function saveLicense(key) {
                localStorage.setItem('clearcut_license', key);
            }
            function getLicenseHeaders() {
                const key = getSavedLicense();
                return key ? { 'X-License-Key': key } : {};
            }

            // --- Usage status ---
            async function updateUsageUI() {
                try {
                    const resp = await fetch('/usage-status', { headers: getLicenseHeaders() });
                    const data = await resp.json();
                    if (data.is_pro) {
                        usageBar.innerHTML = '\u2713 Pro \u2014 Unlimited access';
                        usageBar.className = 'usage-bar pro';
                        upgradeBtn.classList.add('hidden');
                        licenseLink.classList.add('hidden');
                    } else {
                        const left = data.limit - data.used;
                        usageBar.innerHTML = `Free: <span class="uses-left">${left} / ${data.limit}</span> uses left today`;
                        usageBar.className = 'usage-bar';
                        upgradeBtn.classList.remove('hidden');
                        licenseLink.classList.remove('hidden');
                    }
                } catch(e) {}
            }
            updateUsageUI();

            // --- Upgrade button ---
            upgradeBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch('/create-checkout', { method: 'POST' });
                    const data = await resp.json();
                    if (data.url) {
                        window.location.href = data.url;
                    } else {
                        alert('Stripe is not configured yet.');
                    }
                } catch(e) {
                    alert('Stripe is not configured yet.');
                }
            });

            // --- License modal ---
            licenseLink.addEventListener('click', () => {
                licenseModal.classList.add('active');
                licenseInput.value = '';
                licenseMsg.classList.add('hidden');
                licenseInput.focus();
            });
            licenseCancel.addEventListener('click', () => {
                licenseModal.classList.remove('active');
            });
            licenseModal.addEventListener('click', (e) => {
                if (e.target === licenseModal) licenseModal.classList.remove('active');
            });
            licenseSubmit.addEventListener('click', async () => {
                const key = licenseInput.value.trim().toUpperCase();
                if (!key) return;
                licenseMsg.classList.add('hidden');
                try {
                    const resp = await fetch('/verify-license', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ license_key: key })
                    });
                    const data = await resp.json();
                    if (data.valid) {
                        saveLicense(key);
                        licenseMsg.textContent = 'License activated! Unlimited access unlocked.';
                        licenseMsg.className = 'modal-msg success';
                        licenseMsg.classList.remove('hidden');
                        setTimeout(() => {
                            licenseModal.classList.remove('active');
                            updateUsageUI();
                        }, 1500);
                    } else {
                        licenseMsg.textContent = 'Invalid or expired license key.';
                        licenseMsg.className = 'modal-msg error';
                        licenseMsg.classList.remove('hidden');
                    }
                } catch(e) {
                    licenseMsg.textContent = 'Verification failed. Try again.';
                    licenseMsg.className = 'modal-msg error';
                    licenseMsg.classList.remove('hidden');
                }
            });

            // --- Custom cursors via SVG data URIs ---
            function makeBrushCursor(size) {
                const displaySize = Math.max(size, 12);
                const half = displaySize / 2;
                const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${displaySize}" height="${displaySize}" viewBox="0 0 ${displaySize} ${displaySize}">
                    <circle cx="${half}" cy="${half}" r="${half - 1}" fill="rgba(239,68,68,0.25)" stroke="#ef4444" stroke-width="1.5"/>
                </svg>`;
                return `url('data:image/svg+xml;utf8,${encodeURIComponent(svg)}') ${half} ${half}, crosshair`;
            }

            function makeWandCursor() {
                const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
                    <line x1="4" y1="28" x2="20" y2="12" stroke="#8b5cf6" stroke-width="2.5" stroke-linecap="round"/>
                    <polygon points="20,12 24,8 28,4 26,10 22,14" fill="#a855f7"/>
                    <circle cx="26" cy="4" r="2" fill="#fbbf24"/>
                    <line x1="24" y1="1" x2="24" y2="7" stroke="#fbbf24" stroke-width="1"/>
                    <line x1="21" y1="4" x2="27" y2="4" stroke="#fbbf24" stroke-width="1"/>
                    <line x1="29" y1="7" x2="30" y2="10" stroke="#fbbf24" stroke-width="0.8"/>
                    <line x1="22" y1="1" x2="21" y2="3" stroke="#fbbf24" stroke-width="0.8"/>
                </svg>`;
                return `url('data:image/svg+xml;utf8,${encodeURIComponent(svg)}') 4 28, crosshair`;
            }

            function updateCursor() {
                if (!brushToolbar.classList.contains('active')) {
                    eraserCanvas.style.cursor = 'default';
                    return;
                }
                if (brushMode === 'erase') {
                    const displaySize = Math.min(parseInt(brushSizeInput.value), 40);
                    eraserCanvas.style.cursor = makeBrushCursor(displaySize);
                } else {
                    eraserCanvas.style.cursor = makeWandCursor();
                }
            }

            // --- Drag & drop ---
            dropZone.addEventListener('dragover', e => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });
            dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
            dropZone.addEventListener('drop', e => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                if (e.dataTransfer.files.length) {
                    fileInput.files = e.dataTransfer.files;
                    handleFile(e.dataTransfer.files[0]);
                }
            });

            fileInput.addEventListener('change', () => {
                if (fileInput.files[0]) handleFile(fileInput.files[0]);
            });

            function handleFile(file) {
                currentFile = file;
                const url = URL.createObjectURL(file);
                preview.src = url;

                // Load original image into an HTMLImageElement for restore brush
                const img = new Image();
                img.onload = () => { originalSourceImage = img; };
                img.src = url;

                resultContainer.classList.remove('hidden');
                resultImg.src = '';
                eraserCanvas.width = 0;
                eraserCanvas.height = 0;
                resultActions.style.display = 'none';
                brushToolbar.classList.remove('active');
                brushMode = 'erase';
                removeBgBtn.disabled = false;
                history = [];
                bgRemovedImageData = null;
            }

            // --- Remove BG ---
            removeBgBtn.addEventListener('click', async () => {
                if (!currentFile) return;
                removeBgBtn.disabled = true;
                loadingFullscreen.classList.add('active');

                try {
                    const formData = new FormData();
                    formData.append('file', currentFile);
                    formData.append('model', modelSelect.value);

                    const resp = await fetch('/remove-bg', {
                        method: 'POST',
                        body: formData,
                        headers: getLicenseHeaders()
                    });

                    if (resp.status === 429) {
                        const data = await resp.json();
                        alert(data.error || 'Daily limit reached. Upgrade to Pro!');
                        return;
                    }
                    if (!resp.ok) throw new Error('Error');

                    const blob = await resp.blob();
                    if (resultBlobUrl) URL.revokeObjectURL(resultBlobUrl);
                    resultBlobUrl = URL.createObjectURL(blob);
                    resultImg.src = resultBlobUrl;

                    resultImg.onload = () => {
                        setupCanvas();
                        resultActions.style.display = 'flex';
                    };

                    updateUsageUI();
                } catch (err) {
                    alert('Failed to remove background. Please try again.');
                } finally {
                    loadingFullscreen.classList.remove('active');
                    removeBgBtn.disabled = false;
                }
            });

            // --- Canvas Setup ---
            function setupCanvas() {
                const img = resultImg;
                const w = img.naturalWidth;
                const h = img.naturalHeight;
                eraserCanvas.width = w;
                eraserCanvas.height = h;
                eraserCanvas.style.width = img.width + 'px';
                eraserCanvas.style.height = img.height + 'px';
                ctx.clearRect(0, 0, w, h);
                ctx.drawImage(img, 0, 0, w, h);

                // Save BG-removed result for reference
                bgRemovedImageData = ctx.getImageData(0, 0, w, h);

                // Cache original source image at result size for fast restore
                if (originalSourceImage) {
                    originalSourceCanvas = document.createElement('canvas');
                    originalSourceCanvas.width = w;
                    originalSourceCanvas.height = h;
                    const tmpCtx = originalSourceCanvas.getContext('2d');
                    tmpCtx.drawImage(originalSourceImage, 0, 0, w, h);
                }

                // Show brush toolbar
                brushToolbar.classList.add('active');
                eraserCanvas.style.cursor = 'crosshair';
                updateCursor();

                history = [];
                saveHistory();
                resultImg.style.visibility = 'hidden';
            }



            // --- Erase / Restore mode toggle ---
            eraseBtn.addEventListener('click', () => {
                brushMode = 'erase';
                eraseBtn.classList.add('active-mode');
                restoreBtn.classList.remove('active-mode');
                modeBadge.textContent = 'Erase';
                modeBadge.className = 'mode-badge erase';
                updateCursor();
            });

            restoreBtn.addEventListener('click', () => {
                brushMode = 'restore';
                restoreBtn.classList.add('active-mode');
                eraseBtn.classList.remove('active-mode');
                modeBadge.textContent = 'Restore';
                modeBadge.className = 'mode-badge restore';
                updateCursor();
            });

            brushSizeInput.addEventListener('input', () => {
                brushSizeVal.textContent = brushSizeInput.value;
                updateCursor();
            });

            // --- Drawing ---
            function getCanvasPos(e) {
                const rect = eraserCanvas.getBoundingClientRect();
                const scaleX = eraserCanvas.width / rect.width;
                const scaleY = eraserCanvas.height / rect.height;
                const clientX = e.touches ? e.touches[0].clientX : e.clientX;
                const clientY = e.touches ? e.touches[0].clientY : e.clientY;
                return {
                    x: (clientX - rect.left) * scaleX,
                    y: (clientY - rect.top) * scaleY
                };
            }

            function isBrushActive() {
                return brushToolbar.classList.contains('active');
            }

            // Interpolate points for smooth strokes
            function interpolatePoints(p1, p2, spacing) {
                const points = [];
                const dx = p2.x - p1.x;
                const dy = p2.y - p1.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const steps = Math.max(Math.floor(dist / spacing), 1);
                for (let i = 0; i <= steps; i++) {
                    const t = i / steps;
                    points.push({ x: p1.x + dx * t, y: p1.y + dy * t });
                }
                return points;
            }

            function brushStroke(pos) {
                const radius = parseInt(brushSizeInput.value);
                const spacing = Math.max(radius * 0.3, 2);

                // Get points to draw (interpolated for smoothness)
                let points;
                if (lastPos) {
                    points = interpolatePoints(lastPos, pos, spacing);
                } else {
                    points = [pos];
                }
                lastPos = pos;

                if (brushMode === 'erase') {
                    ctx.globalCompositeOperation = 'destination-out';
                    ctx.lineWidth = radius * 2;
                    ctx.lineCap = 'round';
                    ctx.lineJoin = 'round';
                    ctx.beginPath();
                    ctx.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        ctx.lineTo(points[i].x, points[i].y);
                    }
                    ctx.stroke();
                    ctx.globalCompositeOperation = 'source-over';

                } else if (brushMode === 'restore' && originalSourceCanvas) {
                    // Use clip + drawImage for fast restore
                    ctx.save();
                    ctx.beginPath();
                    for (const p of points) {
                        ctx.moveTo(p.x + radius, p.y);
                        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
                    }
                    ctx.clip();
                    ctx.drawImage(originalSourceCanvas, 0, 0);
                    ctx.restore();
                }
            }

            function startDraw(e) {
                if (!isBrushActive()) return;
                e.preventDefault();
                isDrawing = true;
                lastPos = null;
                brushStroke(getCanvasPos(e));
            }

            function draw(e) {
                if (!isDrawing || !isBrushActive()) return;
                e.preventDefault();
                brushStroke(getCanvasPos(e));
            }

            function endDraw() {
                if (!isDrawing) return;
                isDrawing = false;
                lastPos = null;
                saveHistory();
            }

            eraserCanvas.addEventListener('mousedown', startDraw);
            eraserCanvas.addEventListener('mousemove', draw);
            eraserCanvas.addEventListener('mouseup', endDraw);
            eraserCanvas.addEventListener('mouseleave', endDraw);
            eraserCanvas.addEventListener('touchstart', startDraw, { passive: false });
            eraserCanvas.addEventListener('touchmove', draw, { passive: false });
            eraserCanvas.addEventListener('touchend', endDraw);

            // --- Undo ---
            function saveHistory() {
                if (history.length > 30) history.shift();
                history.push(ctx.getImageData(0, 0, eraserCanvas.width, eraserCanvas.height));
            }

            undoBtn.addEventListener('click', () => {
                if (history.length <= 1) return;
                history.pop();
                const prev = history[history.length - 1];
                ctx.putImageData(prev, 0, 0);
            });

            // --- Download ---
            downloadBtn.addEventListener('click', () => {
                const link = document.createElement('a');
                if (eraserCanvas.width > 0 && eraserCanvas.height > 0) {
                    link.href = eraserCanvas.toDataURL('image/png');
                } else {
                    link.href = resultBlobUrl;
                }
                link.download = 'removed_bg.png';
                link.click();
            });

            // Resize observer
            const resizeObserver = new ResizeObserver(() => {
                if (resultImg.width > 0) {
                    eraserCanvas.style.width = resultImg.width + 'px';
                    eraserCanvas.style.height = resultImg.height + 'px';
                }
            });
            resizeObserver.observe(resultImg);
        })();
        </script>
    </body>
    </html>
    """


@app.post("/remove-bg")
async def remove_bg(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form("isnet-general-use"),
    x_license_key: str = Header(None, alias="X-License-Key"),
):
    ip = request.client.host

    # Check usage limits
    status = can_use(ip, x_license_key)
    if not status["allowed"]:
        return JSONResponse(
            status_code=429,
            content={"error": "Daily limit reached. Upgrade to Pro for unlimited access."}
        )

    input_data = await file.read()

    allowed_models = ["u2netp", "isnet-general-use", "u2net", "u2net_human_seg", "silueta"]
    if model not in allowed_models:
        model = "u2netp"

    sess = new_session(model)
    output_data = remove(input_data, session=sess)

    # Record usage for free users
    if not status["is_pro"]:
        record_usage(ip)

    return StreamingResponse(
        io.BytesIO(output_data),
        media_type="image/png"
    )


@app.get("/usage-status")
async def usage_status(
    request: Request,
    x_license_key: str = Header(None, alias="X-License-Key"),
):
    ip = request.client.host
    status = can_use(ip, x_license_key)
    return status


@app.post("/verify-license")
async def verify_license_endpoint(request: Request):
    body = await request.json()
    key = body.get("license_key", "")
    valid = verify_license(key)
    return {"valid": valid, "license_key": key}


@app.post("/create-checkout")
async def create_checkout(request: Request):
    try:
        from stripe_handler import create_checkout_session
        base_url = str(request.base_url).rstrip("/")
        url = create_checkout_session(
            success_url=f"{base_url}/?checkout=success",
            cancel_url=f"{base_url}/?checkout=cancel",
        )
        return {"url": url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    try:
        from stripe_handler import handle_webhook
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        result = handle_webhook(payload, sig)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# Dev/test helper: manually generate a license
@app.post("/generate-test-license")
async def generate_test_license(request: Request):
    body = await request.json()
    email = body.get("email", "test@example.com")
    key = create_license(email)
    print(f"[ClearCut] Test license generated: {key} for {email}")
    return {"license_key": key, "email": email}