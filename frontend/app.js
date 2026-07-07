/* ============================================================
   app.js — ResumeX SPA Logic (Mode C ATS Ranker)
   ============================================================ */

'use strict';

// ----------------------------------------------------------------
// Lucide-style SVG Icon Library
// ----------------------------------------------------------------
const IC = {
  fileChart:   `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 18v-2"/><path d="M12 18v-5"/><path d="M16 18v-8"/></svg>`,
  checkCircle: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  thumbsUp:    `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/></svg>`,
  thumbsDown:  `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z"/></svg>`,
  tag:         `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/></svg>`,
  briefcase:   `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
  graduation:  `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 10v6"/><path d="M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>`,
  user:        `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  alertTri:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
  circleX:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  helpCircle:  `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
};

// ----------------------------------------------------------------
// State
// ----------------------------------------------------------------
const state = {
  classifyFile: null,
  rankFiles: [],
  extractedSkills: [],
  jdParsed: false,
};

// ----------------------------------------------------------------
// Health check
// ----------------------------------------------------------------
async function checkHealth() {
  const badge = document.getElementById('status-badge');
  const text  = document.getElementById('status-text');
  try {
    const res  = await fetch('/health');
    const data = await res.json();
    badge.className = data.models_loaded ? 'status-badge' : 'status-badge loading';
    text.textContent = data.models_loaded
      ? 'Models loaded · API ready'
      : 'API up · Models loading…';
    if (!data.models_loaded) setTimeout(checkHealth, 5000);
  } catch {
    badge.className = 'status-badge error';
    text.textContent = 'API unreachable';
  }
}

// ----------------------------------------------------------------
// Dark Mode
// ----------------------------------------------------------------
function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next   = isDark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('resumex-theme', next); } catch(e) {}
  updateThemeIcons(next);
}

function updateThemeIcons(theme) {
  const moon = document.getElementById('icon-moon');
  const sun  = document.getElementById('icon-sun');
  if (!moon || !sun) return;
  moon.style.display = theme === 'dark' ? 'none'  : 'block';
  sun.style.display  = theme === 'dark' ? 'block' : 'none';
}

// ----------------------------------------------------------------
// Tab switching
// ----------------------------------------------------------------
function switchTab(name) {
  ['classify', 'rank'].forEach(t => {
    const btn   = document.getElementById(`tab-${t}-btn`);
    const panel = document.getElementById(`panel-${t}`);
    btn.classList.toggle('active', t === name);
    btn.setAttribute('aria-selected', t === name);
    panel.classList.toggle('active', t === name);
  });
}

// ----------------------------------------------------------------
// Drag-and-drop
// ----------------------------------------------------------------
function handleDragOver(e, el) { e.preventDefault(); el.classList.add('dragover'); }
function handleDragLeave(el)   { el.classList.remove('dragover'); }

function handleDrop(e, ctx) {
  e.preventDefault();
  document.getElementById(`${ctx}-drop-zone`).classList.remove('dragover');
  const files = Array.from(e.dataTransfer.files).filter(isValidFile);
  if (ctx === 'classify') { if (files.length) setClassifyFile(files[0]); }
  else addRankFiles(files);
}

function handleFileSelect(e, ctx) {
  const files = Array.from(e.target.files).filter(isValidFile);
  if (ctx === 'classify') { if (files.length) setClassifyFile(files[0]); }
  else addRankFiles(files);
  e.target.value = '';
}

function isValidFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf','docx','doc','txt'].includes(ext)) {
    alert(`".${ext}" is not supported. Use PDF, DOCX, or TXT.`);
    return false;
  }
  if (file.size > 10 * 1024 * 1024) {
    alert(`"${file.name}" exceeds the 10 MB limit.`);
    return false;
  }
  return true;
}

// ----------------------------------------------------------------
// Classify file management
// ----------------------------------------------------------------
function setClassifyFile(file) {
  state.classifyFile = file;
  renderPills('classify', [file]);
  document.getElementById('classify-btn').disabled = false;
  hideError('classify'); hideResults('classify');
}

function removeClassifyFile() {
  state.classifyFile = null;
  renderPills('classify', []);
  document.getElementById('classify-btn').disabled = true;
  hideResults('classify');
}

// ----------------------------------------------------------------
// Rank file management
// ----------------------------------------------------------------
function addRankFiles(files) {
  const existing = new Set(state.rankFiles.map(f => f.name));
  state.rankFiles.push(...files.filter(f => !existing.has(f.name)));
  renderPills('rank', state.rankFiles);
  document.getElementById('rank-btn').disabled = state.rankFiles.length === 0;
  hideError('rank'); hideResults('rank');
}

function removeRankFile(i) {
  state.rankFiles.splice(i, 1);
  renderPills('rank', state.rankFiles);
  document.getElementById('rank-btn').disabled = state.rankFiles.length === 0;
}

// ----------------------------------------------------------------
// Pill rendering
// ----------------------------------------------------------------
function renderPills(ctx, files) {
  const c = document.getElementById(`${ctx}-pills`);
  c.innerHTML = '';
  files.forEach((file, i) => {
    const pill = document.createElement('span');
    pill.className = 'file-pill';
    const removeCall = ctx === 'classify' ? 'removeClassifyFile()' : `removeRankFile(${i})`;
    pill.innerHTML = `
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      ${escHtml(file.name)}
      <span class="file-pill-remove" role="button" tabindex="0"
        onclick="${removeCall}" onkeydown="if(event.key==='Enter'){${removeCall}}">✕</span>`;
    c.appendChild(pill);
  });
}

// ----------------------------------------------------------------
// JD Auto-parse (Mode C)
// ----------------------------------------------------------------
function onJdInput() {
  const val = document.getElementById('rank-jd-text').value.trim();
  document.getElementById('parse-jd-btn').disabled = val.length < 20;
}

async function parseJd() {
  const jdText = document.getElementById('rank-jd-text').value.trim();
  if (!jdText) return;

  const btn = document.getElementById('parse-jd-btn');
  document.getElementById('parse-jd-spinner').style.display = 'inline-flex';
  document.getElementById('parse-jd-icon').style.display    = 'none';
  document.getElementById('parse-jd-label').textContent     = 'Extracting…';
  btn.disabled = true;

  try {
    const res  = await fetch('/parse-jd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jd_text: jdText }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Parse failed');
    applyExtracted(data);
  } catch (err) {
    showError('rank', `JD parse error: ${err.message}`);
  } finally {
    document.getElementById('parse-jd-spinner').style.display = 'none';
    document.getElementById('parse-jd-icon').style.display    = 'inline-flex';
    document.getElementById('parse-jd-label').textContent     = 'Re-Extract';
    btn.disabled = false;
  }
}

function applyExtracted(data) {
  state.extractedSkills = [...(data.skills || [])];
  renderSkillChips();

  const expEl = document.getElementById('meta-exp');
  const eduEl = document.getElementById('meta-edu');
  if (data.experience_years != null) expEl.value = data.experience_years;
  if (data.education)                eduEl.value = data.education;

  const senChip  = document.getElementById('meta-seniority-chip');
  const senBadge = document.getElementById('meta-seniority-badge');
  if (data.seniority) {
    const cls = 'seniority-badge seniority-' + data.seniority.toLowerCase();
    senBadge.className   = cls;
    senBadge.textContent = data.seniority;
    senChip.style.display = 'flex';
  } else {
    senChip.style.display = 'none';
  }

  document.getElementById('extracted-panel').style.display = 'block';
  state.jdParsed = true;
}

function renderSkillChips() {
  const container = document.getElementById('skill-chips-container');
  container.querySelectorAll('.skill-chip').forEach(el => el.remove());

  state.extractedSkills.forEach((skill, i) => {
    const chip = document.createElement('span');
    chip.className = 'skill-chip';
    chip.innerHTML = `${escHtml(skill)}
      <span class="skill-chip-remove" title="Remove ${escHtml(skill)}"
        onclick="removeSkill(${i})" role="button" tabindex="0"
        onkeydown="if(event.key==='Enter'){removeSkill(${i})}">✕</span>`;
    container.insertBefore(chip, document.getElementById('add-skill-input'));
  });
}

function removeSkill(i) {
  state.extractedSkills.splice(i, 1);
  renderSkillChips();
}

function onAddSkillKey(e) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    const val = e.target.value.trim().replace(/,$/, '');
    if (val && !state.extractedSkills.map(s => s.toLowerCase()).includes(val.toLowerCase())) {
      state.extractedSkills.push(val);
      renderSkillChips();
    }
    e.target.value = '';
  }
}

function clearExtracted() {
  state.extractedSkills = [];
  state.jdParsed = false;
  document.getElementById('extracted-panel').style.display = 'none';
  document.getElementById('meta-exp').value  = '';
  document.getElementById('meta-edu').value  = '';
  document.getElementById('meta-seniority-chip').style.display = 'none';
  document.getElementById('parse-jd-label').textContent = 'Auto-Extract Requirements';
}

// ----------------------------------------------------------------
// UI helpers
// ----------------------------------------------------------------
function setLoading(ctx, loading) {
  const btn = document.getElementById(`${ctx}-btn`);
  btn.classList.toggle('loading', loading);
  btn.disabled = loading;
}

function showError(ctx, msg) {
  const el = document.getElementById(`${ctx}-error`);
  el.style.display = '';
  el.innerHTML = `<div class="error-banner">${IC.alertTri} ${escHtml(msg)}</div>`;
}

function hideError(ctx) {
  const el = document.getElementById(`${ctx}-error`);
  el.style.display = 'none';
  el.innerHTML = '';
}

function hideResults(ctx) {
  const el = document.getElementById(`${ctx}-results`);
  el.style.display = 'none';
  el.innerHTML = '';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ----------------------------------------------------------------
// /classify
// ----------------------------------------------------------------
async function submitClassify() {
  if (!state.classifyFile) return;
  hideError('classify'); hideResults('classify'); setLoading('classify', true);

  const form = new FormData();
  form.append('file', state.classifyFile);

  try {
    const res  = await fetch('/classify', { method:'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showError('classify', data.detail || 'Unexpected error.'); return; }
    renderClassifyResults(data);
  } catch {
    showError('classify', 'Network error — is the API running?');
  } finally {
    setLoading('classify', false);
    document.getElementById('classify-btn').disabled = false;
  }
}

// ----------------------------------------------------------------
// /rank (Mode C)
// ----------------------------------------------------------------
async function submitRank() {
  if (!state.rankFiles.length) return;

  const jdText = document.getElementById('rank-jd-text').value.trim();
  if (!jdText && state.extractedSkills.length === 0) {
    showError('rank', 'Please paste a job description or auto-extract requirements first.');
    return;
  }

  hideError('rank'); hideResults('rank'); setLoading('rank', true);

  const form = new FormData();
  form.append('jd_text',             jdText);
  form.append('skills_override',     state.extractedSkills.join(', '));
  form.append('experience_override', document.getElementById('meta-exp').value.trim());
  form.append('education_override',  document.getElementById('meta-edu').value.trim());
  form.append('seniority_override',  document.getElementById('meta-seniority-badge').textContent.trim());

  state.rankFiles.forEach(f => form.append('resumes', f));

  try {
    const res  = await fetch('/rank', { method:'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showError('rank', data.detail || 'Unexpected error.'); return; }
    renderRankResults(data);
  } catch {
    showError('rank', 'Network error — is the API running?');
  } finally {
    setLoading('rank', false);
    document.getElementById('rank-btn').disabled = false;
  }
}

// ----------------------------------------------------------------
// Render classify results
// ----------------------------------------------------------------
function renderClassifyResults(data) {
  const container = document.getElementById('classify-results');
  container.style.display = '';

  if (!data.top5?.length) {
    container.innerHTML = `<div class="results-section">
      <div class="empty-state">
        <span class="empty-state-icon">${IC.helpCircle}</span>
        <p>No categories detected. Try a different file.</p>
      </div></div>`;
    return;
  }

  const medalCls = ['rank-1','rank-2','rank-3','rank-4','rank-5'];
  let html = `<div class="results-section">
    <div class="results-header">${IC.checkCircle} Classification Results</div>`;

  if (data.preview) {
    html += `<div class="preview-box">
      <div class="preview-label">Extracted Text Preview</div>
      ${escHtml(data.preview)}…</div>`;
  }

  html += `<div class="category-list">`;
  data.top5.forEach((item, i) => {
    const pct = Math.round(item.score * 100);
    html += `<div class="category-item" style="animation-delay:${i*80}ms">
      <div class="category-item-header">
        <div class="category-rank">
          <div class="rank-badge ${medalCls[i]}">${item.rank}</div>
          <span class="category-name">${escHtml(item.category)}</span>
        </div>
        <span class="category-score-pct">${pct}%</span>
      </div>
      <div class="score-bar-track">
        <div class="score-bar-fill" data-pct="${pct}" style="width:0%"></div>
      </div></div>`;
  });

  html += `</div></div>`;
  container.innerHTML = html;
  animateBars(container);
}

// ----------------------------------------------------------------
// Render rank results (5-dimension)
// ----------------------------------------------------------------
function renderRankResults(data) {
  const container = document.getElementById('rank-results');
  container.style.display = '';

  const ranked = data.ranked || [];
  if (!ranked.length) {
    container.innerHTML = `<div class="results-section"><div class="empty-state">
      <span class="empty-state-icon">${IC.helpCircle}</span>
      <p>No results. Try uploading valid resume files.</p>
    </div></div>`;
    return;
  }

  const eff = data.effective_requirements || {};

  // Requirements summary bar
  let reqHtml = `<div class="req-summary">`;
  if (eff.skills?.length)
    reqHtml += `<div class="req-summary-item">${IC.tag} <strong>${eff.skills.length} skills</strong> required</div>`;
  if (eff.experience)
    reqHtml += `<div class="req-summary-item">${IC.briefcase} <strong>${eff.experience}+ years</strong> exp</div>`;
  if (eff.education)
    reqHtml += `<div class="req-summary-item">${IC.graduation} <strong>${escHtml(eff.education)}</strong></div>`;
  if (eff.seniority)
    reqHtml += `<div class="req-summary-item">${IC.user} <span class="seniority-badge seniority-${eff.seniority.toLowerCase()}">${escHtml(eff.seniority)}</span></div>`;
  reqHtml += `</div>`;

  let html = `<div class="results-section">
    <div class="results-header">${IC.fileChart} Ranked Candidates (${ranked.length})</div>
    ${reqHtml}
    <div class="ranked-list">`;

  ranked.forEach((c, i) => {
    // Rank position badge
    const posClass = i === 0 ? '' : i === 1 ? 'rank-pos-2' : i === 2 ? 'rank-pos-3' : 'rank-pos-n';
    const medalHtml = `<span class="rank-medal ${posClass}">${c.rank}</span>`;

    const b = c.breakdown || {};
    const pct = key => b[key] ? Math.round(b[key].score * 100) : 0;
    const kwPct  = pct('keywords');
    const semPct = pct('semantic');
    const expPct = pct('experience');
    const eduPct = pct('education');
    const senPct = pct('seniority');

    // Recruiter note
    const score     = c.final_score;
    const noteClass = score >= 80 ? 'strong' : score >= 65 ? 'good' : score >= 45 ? 'partial' : 'weak';
    const noteIcon  = score >= 80 ? IC.checkCircle : score >= 65 ? IC.checkCircle : score >= 45 ? IC.alertTri : IC.circleX;

    // Sub-notes
    let expNote = '';
    if (b.experience) {
      const det = b.experience.detected_years;
      const req = b.experience.required_years;
      if (det != null) expNote = `${det}y detected${req ? ` / ${req}y req` : ''}`;
    }
    const eduNote = b.education?.detected && b.education.detected !== 'Not detected'
      ? b.education.detected : '';
    let senNote = '';
    if (b.seniority?.detected && b.seniority.detected !== 'Not detected') {
      const sl = b.seniority.detected.toLowerCase();
      senNote = `<span class="seniority-badge seniority-${sl}">${escHtml(b.seniority.detected)}</span>`;
    }

    // Skills tags — thumbs up / down icons
    const matched = b.keywords?.matched || [];
    const missing = b.keywords?.missing || [];
    const matchedTags = matched.map(s =>
      `<span class="skill-tag matched">${IC.thumbsUp} ${escHtml(s)}</span>`
    ).join('');
    const missingTags = missing.map(s =>
      `<span class="skill-tag missing">${IC.thumbsDown} ${escHtml(s)}</span>`
    ).join('');

    html += `
    <div class="rank-card" style="animation-delay:${i*100}ms">
      <div class="rank-card-header">
        <div class="rank-card-left">
          ${medalHtml}
          <div>
            <div class="rank-card-name">${escHtml(c.filename)}</div>
            <div class="rank-card-file">Rank #${c.rank}</div>
          </div>
        </div>
        <div class="final-score-circle">
          <div class="final-score-value">${c.final_score}</div>
          <div class="final-score-label">/ 100</div>
        </div>
      </div>

      <!-- 5-dimension breakdown -->
      <div class="dimension-grid-5">

        <div class="dimension-item dim-skills">
          <div class="dimension-header">
            <span class="dimension-name">Keywords</span>
            <span class="dimension-pct">${kwPct}%</span>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" data-pct="${kwPct}" style="width:0%"></div>
          </div>
        </div>

        <div class="dimension-item dim-exp">
          <div class="dimension-header">
            <span class="dimension-name">Experience</span>
            <span class="dimension-pct">${expPct}%</span>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" data-pct="${expPct}" style="width:0%"></div>
          </div>
          ${expNote ? `<div style="font-size:0.7rem;color:var(--text-muted);margin-top:3px">${escHtml(expNote)}</div>` : ''}
        </div>

        <div class="dimension-item dim-edu">
          <div class="dimension-header">
            <span class="dimension-name">Education</span>
            <span class="dimension-pct">${eduPct}%</span>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" data-pct="${eduPct}" style="width:0%"></div>
          </div>
          ${eduNote ? `<div style="font-size:0.7rem;color:var(--text-muted);margin-top:3px">${escHtml(eduNote)}</div>` : ''}
        </div>

        <div class="dimension-item dim-semantic">
          <div class="dimension-header">
            <span class="dimension-name">Semantic</span>
            <span class="dimension-pct">${semPct}%</span>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" data-pct="${semPct}" style="width:0%"></div>
          </div>
        </div>

        <div class="dimension-item dim-seniority">
          <div class="dimension-header">
            <span class="dimension-name">Seniority</span>
            <span class="dimension-pct">${senPct}%</span>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" data-pct="${senPct}" style="width:0%"></div>
          </div>
          ${senNote ? `<div style="margin-top:4px">${senNote}</div>` : ''}
        </div>

      </div>

      <!-- Skills gap -->
      ${(matchedTags || missingTags) ? `
      <div class="divider" style="margin:12px 0"></div>
      ${matchedTags ? `<div class="skills-tags-label">${IC.thumbsUp} Matched Skills</div>
        <div class="skills-tags">${matchedTags}</div>` : ''}
      ${missingTags ? `<div class="skills-tags-label" style="margin-top:8px">${IC.thumbsDown} Missing Skills</div>
        <div class="skills-tags">${missingTags}</div>` : ''}
      ` : ''}

      <!-- Recruiter note -->
      ${c.recruiter_note ? `
      <div class="recruiter-note ${noteClass}">
        <span style="display:inline-flex;align-items:center">${noteIcon}</span>
        <span>${escHtml(c.recruiter_note)}</span>
      </div>` : ''}

      ${c.error ? `<div class="error-banner" style="margin-top:12px">${IC.alertTri} ${escHtml(c.recruiter_note || 'Parse error')}</div>` : ''}
    </div>`;
  });

  html += `</div></div>`;
  container.innerHTML = html;
  animateBars(container);
}

// ----------------------------------------------------------------
// Animate score bar fills
// ----------------------------------------------------------------
function animateBars(container) {
  requestAnimationFrame(() => {
    container.querySelectorAll('.score-bar-fill').forEach(bar => {
      setTimeout(() => { bar.style.width = bar.dataset.pct + '%'; }, 80);
    });
  });
}

// ----------------------------------------------------------------
// Init
// ----------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  // Sync toggle icon with saved / system theme
  const saved = document.documentElement.getAttribute('data-theme') || 'light';
  updateThemeIcons(saved);
});
