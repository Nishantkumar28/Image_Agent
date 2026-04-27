const API_BASE = "http://localhost:8000";
let currentJobId = null;
let selectedFile = null;

// ── Tab Switching ──────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`tab-${tab}`).setAttribute('aria-selected', 'true');
  document.getElementById(`panel-${tab}`).classList.add('active');
}

// ── File Handling ──────────────────────────────────────────
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function handleDragLeave(e) {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    selectedFile = file;
    showFilePreview(file);
  }
}
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) {
    selectedFile = file;
    showFilePreview(file);
  }
}
function showFilePreview(file) {
  document.getElementById('file-name').textContent = file.name;
  document.getElementById('drop-zone').classList.add('hidden');
  document.getElementById('file-preview').classList.remove('hidden');
}
function clearFile() {
  selectedFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('drop-zone').classList.remove('hidden');
  document.getElementById('file-preview').classList.add('hidden');
}

// ── Processing Steps UI ───────────────────────────────────
const STEPS = ['fetch', 'analyse', 'segment', 'enhance'];

function showProcessing() {
  document.getElementById('processing-section').classList.remove('hidden');
  document.getElementById('error-section').classList.add('hidden');
  document.getElementById('results-section').classList.add('hidden');
  // Reset all steps
  STEPS.forEach(s => {
    const el = document.getElementById(`step-${s}`);
    el.className = 'step-item';
    el.querySelector('.step-dot').className = 'step-dot pending';
  });
  // Mark fetch as active immediately
  activateStep('fetch');
}

function activateStep(stepId) {
  const el = document.getElementById(`step-${stepId}`);
  if (!el) return;
  el.classList.add('active');
  el.querySelector('.step-dot').className = 'step-dot active';
}
function completeStep(stepId) {
  const el = document.getElementById(`step-${stepId}`);
  if (!el) return;
  el.classList.remove('active');
  el.classList.add('done');
  el.querySelector('.step-dot').className = 'step-dot done';
}

function animateSteps(completedSteps) {
  // completedSteps is an array of step names from the result
  STEPS.forEach((s, i) => {
    setTimeout(() => {
      activateStep(s);
      const isDone = completedSteps.includes(s);
      if (isDone) {
        setTimeout(() => completeStep(s), 400);
      }
    }, i * 300);
  });
}

// ── Process URL ───────────────────────────────────────────
async function processURL() {
  const url = document.getElementById('url-input').value.trim();
  if (!url) {
    document.getElementById('url-input').focus();
    return;
  }
  showProcessing();
  setButtonLoading('url-submit-btn', true);

  try {
    const response = await fetch(`${API_BASE}/process/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const result = await response.json();
    handleResult(result);
  } catch (err) {
    showError(err.message || 'Network error. Is the server running?');
  } finally {
    setButtonLoading('url-submit-btn', false);
  }
}

// ── Process Upload ────────────────────────────────────────
async function processUpload() {
  if (!selectedFile) return;
  showProcessing();
  setButtonLoading('upload-submit-btn', true);

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const response = await fetch(`${API_BASE}/process/upload`, {
      method: 'POST',
      body: formData,
    });
    const result = await response.json();
    handleResult(result);
  } catch (err) {
    showError(err.message || 'Network error. Is the server running?');
  } finally {
    setButtonLoading('upload-submit-btn', false);
  }
}

// ── Handle API Result ─────────────────────────────────────
function handleResult(result) {
  document.getElementById('processing-section').classList.add('hidden');

  if (result.status === 'failed' || result.error) {
    showError(result.error || 'Processing failed.');
    return;
  }

  // Animate steps derived from completed steps
  const completedNames = (result.steps || []).map(s => s.step);
  animateSteps(completedNames);

  if (result.status === 'completed') {
    currentJobId = result.job_id;
    setTimeout(() => showResults(result), STEPS.length * 300 + 600);
  }
}

// ── Show Results ──────────────────────────────────────────
function showResults(result) {
  document.getElementById('processing-section').classList.add('hidden');
  const section = document.getElementById('results-section');
  section.classList.remove('hidden');

  const cutouts = result.cutouts || [];
  const subtitle = document.getElementById('results-subtitle');

  if (cutouts.length === 0) {
    subtitle.textContent = result.message || 'No cuttable objects found.';
    document.getElementById('results-grid').innerHTML = '';
    document.getElementById('download-zip-btn').classList.add('hidden');
    return;
  }

  subtitle.textContent = `${cutouts.length} cutout${cutouts.length > 1 ? 's' : ''} extracted — job #${result.job_id}`;
  document.getElementById('download-zip-btn').classList.remove('hidden');

  const grid = document.getElementById('results-grid');
  grid.innerHTML = '';
  cutouts.forEach(cutout => {
    const card = buildCutoutCard(cutout, result.job_id);
    grid.appendChild(card);
  });

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildCutoutCard(cutout, jobId) {
  // Derive file URL: /files/{job_id}/{filename}
  const filename = cutout.file_path.replace(/\\/g, '/').split('/').pop();
  const fileUrl = `${API_BASE}/files/${jobId}/${filename}`;
  const confidence = Math.round((cutout.confidence || 1) * 100);

  const card = document.createElement('div');
  card.className = 'cutout-card';
  card.innerHTML = `
    <div class="cutout-thumb">
      <img src="${fileUrl}" alt="${escapeHtml(cutout.label)}" loading="lazy" />
    </div>
    <div class="cutout-info">
      <div class="cutout-label">
        ${escapeHtml(cutout.label)}
        <span class="cutout-label-confidence">${confidence}%</span>
      </div>
      <button class="cutout-download" onclick="downloadFile('${fileUrl}', '${escapeHtml(filename)}')">
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 1.5v7m0 0l-2.5-2.5m2.5 2.5l2.5-2.5M2 11h9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Download PNG
      </button>
    </div>
  `;
  return card;
}

// ── Download ──────────────────────────────────────────────
async function downloadFile(url, filename) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function downloadZip() {
  if (!currentJobId) return;
  window.location.href = `${API_BASE}/download/${currentJobId}`;
}

// ── Error / Reset ─────────────────────────────────────────
function showError(msg) {
  document.getElementById('processing-section').classList.add('hidden');
  document.getElementById('results-section').classList.add('hidden');
  const section = document.getElementById('error-section');
  section.classList.remove('hidden');
  document.getElementById('error-message').textContent = msg;
}

function resetUI() {
  document.getElementById('processing-section').classList.add('hidden');
  document.getElementById('error-section').classList.add('hidden');
  document.getElementById('results-section').classList.add('hidden');
  document.getElementById('url-input').value = '';
  clearFile();
  currentJobId = null;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Helpers ───────────────────────────────────────────────
function setButtonLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.style.opacity = loading ? '0.6' : '1';
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── Enter key submit ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('url-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') processURL();
  });
});
