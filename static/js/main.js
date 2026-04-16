/**
 * SMPC Shield — Global JavaScript
 * Privacy-Preserving Data Collaboration | VVIT Nambur
 */

'use strict';

// ─── UTILITIES ────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const csrfToken = () => $('meta[name="csrf-token"]')?.content || '';

function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

async function apiFetch(url, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
    credentials: 'same-origin'
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

// ─── NAVBAR ───────────────────────────────────────────────────────
function initNavbar() {
  const nav = $('.navbar');
  if (!nav) return;

  // Scroll shadow
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 30 ? '0 4px 30px rgba(0,0,0,0.6)' : '';
  }, { passive: true });

  // Mobile toggle
  const toggle = $('.nav-toggle');
  const links  = $('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      links.classList.toggle('open');
      toggle.classList.toggle('open');
    });
    // Close on outside click
    document.addEventListener('click', e => {
      if (!nav.contains(e.target)) links.classList.remove('open');
    });
  }
}

// ─── FLASH AUTO-DISMISS ────────────────────────────────────────────
function initFlashes() {
  $$('.flash-msg').forEach((el, i) => {
    setTimeout(() => el.remove(), 4500 + i * 300);
    el.querySelector('.flash-close')?.addEventListener('click', () => el.remove());
  });
}

// ─── SMOOTH SCROLL ────────────────────────────────────────────────
function initSmoothScroll() {
  $$('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = $(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ─── PROGRESS BARS ────────────────────────────────────────────────
function initProgressBars() {
  const bars = $$('[data-progress]');
  if (!bars.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target.querySelector('.progress-fill');
        if (fill) fill.style.width = entry.target.dataset.progress + '%';
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });
  bars.forEach(b => io.observe(b));
}

// ─── BAR CHART ANIMATION ──────────────────────────────────────────
function initBarCharts() {
  const fills = $$('.bar-fill[data-w]');
  if (!fills.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        $$('.bar-fill[data-w]', entry.target.closest('.bar-chart') || document)
          .forEach(f => { f.style.width = f.dataset.w + '%'; });
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  // observe first bar in each chart
  $$('.bar-chart').forEach(chart => {
    const first = chart.querySelector('.bar-fill');
    if (first) io.observe(first);
  });
}

// ─── FADE-IN OBSERVER ─────────────────────────────────────────────
function initFadeIn() {
  const items = $$('[data-fadein]');
  if (!items.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  items.forEach(el => io.observe(el));
}

// ─── STATS COUNTER ────────────────────────────────────────────────
function animateCount(el, target, duration = 1000) {
  const start = performance.now();
  const update = now => {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    el.textContent = Math.round(ease * target);
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

function initCounters() {
  const counters = $$('[data-count]');
  if (!counters.length) return;
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCount(entry.target, parseInt(entry.target.dataset.count));
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(el => io.observe(el));
}

// ─── DASHBOARD STATS LOADER ────────────────────────────────────────
async function loadDashboardStats() {
  const el = id => document.getElementById(id);
  if (!el('statUsers')) return;

  try {
    const { ok, data } = await apiFetch('/api/stats');
    if (!ok) return;
    const set = (id, val) => { const e = el(id); if (e) e.textContent = val; };
    set('statUsers',  data.total_users);
    set('statOk',     data.successful_logins);
    set('statFail',   data.failed_logins);
    set('statMfa',    data.mfa_enabled);
    set('statLocked', data.locked_accounts);
  } catch (e) {
    console.warn('Stats unavailable:', e);
  }
}

// ─── SMPC SIMULATOR ────────────────────────────────────────────────
async function runSMPCSimulator(secretId, partiesId, thresholdId, outputId) {
  const out = document.getElementById(outputId);
  if (!out) return;

  const secret    = parseInt(document.getElementById(secretId)?.value || 42);
  const parties   = parseInt(document.getElementById(partiesId)?.value || 5);
  const threshold = parseInt(document.getElementById(thresholdId)?.value || 3);

  out.innerHTML = '<div style="color:var(--cyan);display:flex;align-items:center;gap:8px;"><span class="spinner"></span> Running SMPC simulation over GF(2³¹-1)...</div>';

  try {
    const { ok, data } = await apiFetch('/api/smpc/simulate', 'POST', { secret, parties, threshold });
    if (!ok) {
      out.innerHTML = `<div style="color:var(--red);">⚠ Error: ${data.error || 'Request failed'}</div>`;
      return;
    }

    let html = `
      <div style="margin-bottom:12px;font-size:12px;color:var(--gray);">
        Protocol: <strong style="color:var(--white)">${data.protocol}</strong> &nbsp;|&nbsp;
        Field: <strong style="color:var(--white)">GF(${data.prime})</strong> &nbsp;|&nbsp;
        Threshold: <strong style="color:var(--orange)">${data.threshold} of ${data.parties}</strong>
      </div>
      <div style="display:flex;flex-direction:column;gap:7px;margin-bottom:12px;">`;

    data.shares.forEach((s, i) => {
      const colors = ['var(--cyan)','var(--green)','var(--orange)','var(--purple)','var(--red)'];
      const c = colors[i % colors.length];
      html += `
        <div style="display:flex;align-items:center;gap:10px;background:var(--navy);
                    border-radius:6px;padding:9px 14px;border-left:3px solid ${c};">
          <span style="color:${c};font-weight:700;width:60px;">Party ${s.x}</span>
          <span style="color:var(--gray2);">x = ${s.x}</span>
          <span style="color:var(--gray2);">→</span>
          <span style="color:${c};font-family:var(--font-m);">y = ${s.y_masked}</span>
          <span style="color:var(--gray2);font-size:10px;margin-left:auto;">masked</span>
        </div>`;
    });

    html += `</div>
      <div style="background:rgba(16,232,154,0.07);border:1px solid rgba(16,232,154,0.2);
                  border-radius:8px;padding:10px 14px;font-size:12px;color:var(--green);">
        🔒 ${data.security_note}
      </div>`;

    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = `<div style="color:var(--red);">⚠ Simulation failed. Are you logged in?</div>`;
  }
}

// expose globally
window.runSim  = () => runSMPCSimulator('simSecret',  'simParties',  'simThreshold',  'simOutput');
window.runDemo = () => runSMPCSimulator('dSecret',     'dParties',    'dThreshold',    'demoOut');

// ─── PARTICLE CANVAS ──────────────────────────────────────────────
function initParticleCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, particles = [];

  const resize = () => {
    W = canvas.width  = canvas.offsetWidth  || window.innerWidth;
    H = canvas.height = canvas.offsetHeight || window.innerHeight;
  };
  resize();
  window.addEventListener('resize', debounce(resize, 200));

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x  = Math.random() * W;
      this.y  = Math.random() * H;
      this.r  = Math.random() * 1.4 + 0.3;
      this.vx = (Math.random() - 0.5) * 0.35;
      this.vy = (Math.random() - 0.5) * 0.35;
      this.a  = Math.random() * 0.45 + 0.08;
    }
    update() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < -5 || this.x > W + 5 || this.y < -5 || this.y > H + 5) this.reset();
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,212,232,${this.a})`;
      ctx.fill();
    }
  }

  for (let i = 0; i < 100; i++) particles.push(new Particle());

  const CONN_DIST = 110;
  let raf;
  const loop = () => {
    ctx.clearRect(0, 0, W, H);
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < CONN_DIST) {
          ctx.strokeStyle = `rgba(0,212,232,${0.07 * (1 - d / CONN_DIST)})`;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
    particles.forEach(p => { p.update(); p.draw(); });
    raf = requestAnimationFrame(loop);
  };
  loop();

  // Pause when tab is hidden
  document.addEventListener('visibilitychange', () => {
    document.hidden ? cancelAnimationFrame(raf) : loop();
  });
}

// ─── PASSWORD STRENGTH ────────────────────────────────────────────
function initPasswordStrength() {
  const pwInput = $('input[name="password"]');
  const confirm = $('input[name="confirm_password"]');
  if (!pwInput) return;

  // Add strength indicator
  const bar = document.createElement('div');
  bar.className = 'progress-track';
  bar.style.cssText = 'margin-top:6px;';
  bar.innerHTML = '<div class="progress-fill" style="width:0;transition:width .3s,background .3s;"></div>';

  const hint = document.createElement('div');
  hint.className = 'form-hint';
  pwInput.parentNode.insertBefore(bar,  pwInput.nextSibling);
  pwInput.parentNode.insertBefore(hint, bar.nextSibling);

  const fill = bar.querySelector('.progress-fill');

  pwInput.addEventListener('input', () => {
    const v = pwInput.value;
    let score = 0;
    if (v.length >= 8)  score += 25;
    if (v.length >= 12) score += 15;
    if (/[A-Z]/.test(v))  score += 20;
    if (/[0-9]/.test(v))  score += 20;
    if (/[^A-Za-z0-9]/.test(v)) score += 20;

    const colors = ['var(--red)', 'var(--orange)', 'var(--yellow,#ffd700)', 'var(--green)'];
    const labels = ['Too weak', 'Weak', 'Good', 'Strong'];
    const idx    = Math.min(3, Math.floor(score / 26));

    fill.style.width = score + '%';
    fill.style.background = colors[idx];
    hint.textContent = v.length ? `Password strength: ${labels[idx]}` : '';
    hint.style.color = colors[idx];
  });

  // Confirm match indicator
  if (confirm) {
    confirm.addEventListener('input', () => {
      const match = confirm.value === pwInput.value && confirm.value.length > 0;
      confirm.style.borderColor = confirm.value ? (match ? 'var(--green)' : 'var(--red)') : '';
    });
  }
}

// ─── OTP AUTO-SUBMIT ──────────────────────────────────────────────
function initOTPInput() {
  const otp = $('input[name="otp"]');
  if (!otp) return;
  otp.addEventListener('input', () => {
    if (otp.value.replace(/\D/g,'').length === 6) {
      otp.value = otp.value.replace(/\D/g,'');
      otp.closest('form')?.submit();
    }
    otp.value = otp.value.replace(/\D/g,'');
  });
}

// ─── COPY TO CLIPBOARD ────────────────────────────────────────────
window.copyToClipboard = async function(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    const orig = btn?.textContent;
    if (btn) { btn.textContent = '✓ Copied!'; setTimeout(() => { btn.textContent = orig; }, 2000); }
  } catch (_) {
    alert('Copy: ' + text);
  }
};

// ─── CONFIRM DIALOG ───────────────────────────────────────────────
$$('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});

// ─── TABLE SEARCH ─────────────────────────────────────────────────
function initTableSearch() {
  const searchInput = $('#tableSearch');
  if (!searchInput) return;
  searchInput.addEventListener('input', debounce(() => {
    const q = searchInput.value.toLowerCase();
    $$('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  }, 200));
}

// ─── KEYBOARD SHORTCUTS ───────────────────────────────────────────
document.addEventListener('keydown', e => {
  // Ctrl/Cmd + K → focus search (if present)
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    const search = $('#tableSearch');
    if (search) { e.preventDefault(); search.focus(); }
  }
  // Escape → close mobile nav
  if (e.key === 'Escape') {
    $('.nav-links')?.classList.remove('open');
  }
});

// ─── INIT ALL ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initFlashes();
  initSmoothScroll();
  initProgressBars();
  initBarCharts();
  initFadeIn();
  initCounters();
  initPasswordStrength();
  initOTPInput();
  initTableSearch();
  loadDashboardStats();
  initParticleCanvas('heroCanvas');

  // Activate nav link for current page
  $$('.nav-links a').forEach(a => {
    if (a.href === window.location.href) a.classList.add('active');
  });

  console.log('%c🔐 SMPC Shield | Security-First Web App', 'color:#00d4e8;font-size:14px;font-weight:bold;');
  console.log('%cBuilt by: Shaik Ayan, P. Radha Krishna Sai, V. Jaswanth Kumar, D. Sai Aditya', 'color:#8aa4bc;font-size:11px;');
});
