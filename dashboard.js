// ═══════════════════════════════════════════════════════════════
//  dashboard.js — AI Commerce Intelligence
//  Logique principale du dashboard
// ═══════════════════════════════════════════════════════════════

const API      = 'https://ai-commerce-intelligente-production.up.railway.app';
const AUTH_API = 'https://ai-commerce-intelligente-production.up.railway.app';

let activePlatform = '';
let searchTimer    = null;
let currentPage    = 1;


// ── Helpers ──────────────────────────────────────────────────────

function sc(s)  { return s >= 8 ? 'high' : s >= 5 ? 'mid' : 'low'; }
function esc(s) {
  return String(s)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) =>
    t.classList.toggle('active', ['products', 'compare', 'top'][i] === name)
  );
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (name === 'top') loadTop();
  if (name === 'trends') loadTrends();
}


// ── Stats ────────────────────────────────────────────────────────

async function loadStats() {
  try {
    const r = await fetch(`${API}/api/stats`);
    const d = await r.json();
    if (!d.success) return;
    document.getElementById('statTotal').textContent  = d.total_products;
    document.getElementById('statScore').textContent  = d.avg_score.toFixed(1);
    document.getElementById('statPrice').textContent  = '$' + d.avg_price.toFixed(0);
    document.getElementById('statRating').textContent = (d.avg_rating || 0).toFixed(1);
    document.getElementById('statMargin').textContent = d.avg_margin_pct.toFixed(0) + '%';
    const pl = Object.entries(d.by_platform).map(([k, v]) => `${k} (${v})`).join(' · ');
    document.getElementById('statPlatforms').textContent = pl;
  } catch (e) {}
}


// ── Platform pills ────────────────────────────────────────────────

async function loadPlatformPills() {
  try {
    const r = await fetch(`${API}/api/platforms`);
    const d = await r.json();
    if (!d.success) return;
    const container = document.getElementById('platformPills');
    container.innerHTML = '';
    const all = [{ label: 'Toutes', val: '' }].concat(d.platforms.map(p => ({ label: p, val: p })));
    all.forEach(({ label, val }) => {
      const pill = document.createElement('div');
      pill.className = 'pill' + (val === activePlatform ? ' active' : '');
      pill.dataset.p = val;
      pill.textContent = label;
      pill.onclick = () => { activePlatform = val; loadPlatformPills(); loadProducts(1); };
      container.appendChild(pill);
    });
  } catch (e) {}
}


// ── Products ─────────────────────────────────────────────────────

function affiliateBtn(url, platform) {
  if (!url) return '<span style="color:var(--muted);font-size:.7rem">—</span>';
  const label = { Amazon: 'Amazon ↗', eBay: 'eBay ↗', Walmart: 'Walmart ↗', Etsy: 'Etsy ↗' }[platform] || '↗';
  return `<a href="${esc(url)}" target="_blank" class="affil-btn" onclick="event.stopPropagation()">${label}</a>`;
}

async function loadProducts(page = 1) {
  currentPage = page;
  const q    = document.getElementById('searchInput').value.trim();
  const sort = document.getElementById('sortFilter').value;
  document.getElementById('productsBody').innerHTML =
    `<tr><td colspan="8" class="loading-cell"><span class="spinner"></span>Chargement…</td></tr>`;

  try {
    let data;
    if (q.length >= 2) {
      let url = `${API}/api/products/search?q=${encodeURIComponent(q)}&limit=50`;
      if (activePlatform) url += `&platform=${encodeURIComponent(activePlatform)}`;
      const r = await fetch(url);
      data = await r.json();
      renderProducts(data.products || [], data.count || 0);
      document.getElementById('pagination').innerHTML = '';
      return;
    }
    let params = `?page=${page}&per_page=20&sort=${sort}`;
    if (activePlatform) params += `&platform=${encodeURIComponent(activePlatform)}`;
    const r = await fetch(`${API}/api/products${params}`);
    data = await r.json();
    if (!data.success) throw new Error(data.error);
    renderProducts(data.products, data.total);
    renderPagination(data.page, data.pages);
  } catch (e) {
    document.getElementById('productsBody').innerHTML =
      `<tr><td colspan="8" class="loading-cell">❌ API inaccessible. Lance python api.py</td></tr>`;
  }
}

function renderProducts(products, total) {
  document.getElementById('productCount').textContent = total + ' produit' + (total > 1 ? 's' : '');
  if (!products.length) {
    document.getElementById('productsBody').innerHTML =
      `<tr><td colspan="8" class="loading-cell">Aucun produit trouvé.</td></tr>`;
    return;
  }
  document.getElementById('productsBody').innerHTML = products.map(p => {
    const c   = sc(p.opportunity_score);
    const pct = Math.round((p.opportunity_score / 10) * 100);
    return `<tr class="product-row" onclick="openProductModal(${p.id})">
      <td><div class="product-title" title="${esc(p.title)}">${esc(p.title)}</div></td>
      <td><span class="platform-badge pb-${p.platform}">${p.platform}</span></td>
      <td>$${p.price.toFixed(2)}</td>
      <td class="hide-m" style="color:var(--accent);font-size:.73rem">${p.margin.toFixed(1)}%</td>
      <td class="hide-m" style="color:#ffd700">${p.rating > 0 ? '★ ' + p.rating.toFixed(1) : '—'}</td>
      <td class="hide-m" style="color:var(--muted);font-size:.73rem">${p.sales.toLocaleString()}</td>
      <td><div class="score-bar">
        <div class="score-track"><div class="score-fill fill-${c}" style="width:${pct}%"></div></div>
        <span class="score-num s-${c}">${p.opportunity_score.toFixed(1)}</span>
      </div></td>
      <td>${affiliateBtn(p.affiliate_url, p.platform)}</td>
    </tr>`;
  }).join('');
}


// ── Pagination ────────────────────────────────────────────────────

function renderPagination(page, pages) {
  if (pages <= 1) { document.getElementById('pagination').innerHTML = ''; return; }
  let html = `<button class="page-btn" onclick="loadProducts(${page - 1})" ${page === 1 ? 'disabled' : ''}>←</button>`;
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || (i >= page - 2 && i <= page + 2))
      html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="loadProducts(${i})">${i}</button>`;
    else if (i === page - 3 || i === page + 3)
      html += `<span class="page-btn" style="cursor:default">…</span>`;
  }
  html += `<button class="page-btn" onclick="loadProducts(${page + 1})" ${page === pages ? 'disabled' : ''}>→</button>`;
  document.getElementById('pagination').innerHTML = html;
}


// ── Comparaison ───────────────────────────────────────────────────

async function loadComparison() {
  const q = document.getElementById('compareSearch').value.trim();
  if (!q) return;
  document.getElementById('compareGrid').innerHTML =
    `<div style="color:var(--muted);font-size:.8rem"><span class="spinner"></span>Recherche…</div>`;
  try {
    const r = await fetch(`${API}/api/products/search?q=${encodeURIComponent(q)}&limit=50`);
    const d = await r.json();
    if (!d.success || !d.products.length) {
      document.getElementById('compareGrid').innerHTML =
        `<div style="color:var(--muted);font-size:.8rem">Aucun résultat pour "${esc(q)}".</div>`;
      return;
    }
    const byPlatform = {};
    d.products.forEach(p => {
      if (!byPlatform[p.platform] || p.opportunity_score > byPlatform[p.platform].opportunity_score)
        byPlatform[p.platform] = p;
    });
    const prices   = Object.values(byPlatform).map(p => p.price);
    const minPrice = Math.min(...prices);
    const cards = Object.values(byPlatform)
      .sort((a, b) => a.price - b.price)
      .map(p => {
        const isBest = p.price === minPrice;
        const c = sc(p.opportunity_score);
        return `<div class="compare-card" style="${isBest ? 'border-color:var(--accent)' : ''}">
          ${isBest ? '<div style="font-size:.65rem;color:var(--accent);letter-spacing:.1em;margin-bottom:10px">★ MEILLEUR PRIX</div>' : ''}
          <div class="compare-card-title">${esc(p.title)}</div>
          <div class="compare-row">
            <span class="compare-plat"><span class="platform-badge pb-${p.platform}">${p.platform}</span></span>
            <span class="compare-price ${isBest ? 'best-price' : ''}">$${p.price.toFixed(2)}</span>
          </div>
          <div class="compare-row"><span style="color:var(--muted)">Note</span><span style="color:#ffd700">★ ${p.rating.toFixed(1)}</span></div>
          <div class="compare-row"><span style="color:var(--muted)">Marge estimée</span><span style="color:var(--accent)">${p.margin.toFixed(1)}%</span></div>
          <div class="compare-row"><span style="color:var(--muted)">Score</span><span class="s-${c}">${p.opportunity_score.toFixed(1)}/10</span></div>
          <div style="margin-top:12px">${affiliateBtn(p.affiliate_url, p.platform)}</div>
        </div>`;
      }).join('');
    document.getElementById('compareGrid').innerHTML = cards ||
      `<div style="color:var(--muted);font-size:.8rem">Pas assez de données pour "${esc(q)}".</div>`;
  } catch (e) {
    document.getElementById('compareGrid').innerHTML =
      `<div style="color:var(--warn);font-size:.8rem">❌ Erreur de chargement.</div>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const cs = document.getElementById('compareSearch');
  if (cs) cs.addEventListener('keydown', e => { if (e.key === 'Enter') loadComparison(); });
});


// ── Top Opportunités ──────────────────────────────────────────────

async function loadTop() {
  document.getElementById('topBody').innerHTML =
    `<tr><td colspan="7" class="loading-cell"><span class="spinner"></span>Chargement…</td></tr>`;
  try {
    const r = await fetch(`${API}/api/products/top?limit=20`);
    const d = await r.json();
    if (!d.success) throw new Error();
    document.getElementById('topBody').innerHTML = d.products.map((p, i) => {
      const c   = sc(p.opportunity_score);
      const pct = Math.round((p.opportunity_score / 10) * 100);
      return `<tr class="product-row" onclick="openProductModal(${p.id})">
        <td style="color:var(--muted);font-size:.7rem">#${i + 1}</td>
        <td><div class="product-title" title="${esc(p.title)}">${esc(p.title)}</div></td>
        <td><span class="platform-badge pb-${p.platform}">${p.platform}</span></td>
        <td>$${p.price.toFixed(2)}</td>
        <td style="color:#ffd700">${p.rating > 0 ? '★ ' + p.rating.toFixed(1) : '—'}</td>
        <td><div class="score-bar">
          <div class="score-track"><div class="score-fill fill-${c}" style="width:${pct}%"></div></div>
          <span class="score-num s-${c}">${p.opportunity_score.toFixed(1)}</span>
        </div></td>
        <td>${affiliateBtn(p.affiliate_url, p.platform)}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    document.getElementById('topBody').innerHTML =
      `<tr><td colspan="7" class="loading-cell">❌ Erreur de chargement.</td></tr>`;
  }
}


// ── Search ────────────────────────────────────────────────────────

function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadProducts(1), 350);
}


// ── Tendances Google Trends (Pro) ────────────────────────────────

async function loadTrends() {
  const user = JSON.parse(localStorage.getItem('aci_user') || 'null');
  const grid = document.getElementById('trendsGrid');
  if (!grid) return;

  // Vérifier plan Pro
  if (!user || user.plan !== 'pro') {
    grid.innerHTML = `
      <div class="trends-locked">
        <div class="trends-locked-icon">🔒</div>
        <div class="trends-locked-title">Fonctionnalité Pro</div>
        <div class="trends-locked-desc">
          Les tendances Google sont réservées aux abonnés Pro.<br>
          Découvre quels produits sont les plus recherchés en Afrique de l'Ouest et dans le monde.
        </div>
        <button class="trends-locked-btn" onclick="handleUpgrade()">
          Passer Pro — 11 500 FCFA / 17,52 €/mois →
        </button>
      </div>`;
    return;
  }

  grid.innerHTML = '<div style="color:var(--muted);font-size:.8rem;padding:20px 0"><span class="spinner"></span> Chargement…</div>';

  const geo      = (document.getElementById('trendsGeo') || {}).value || '';
  const category = (document.getElementById('trendsCat') || {}).value || '';

  try {
    let url = `${API}/api/trends?limit=50`;
    if (geo)      url += `&geo=${encodeURIComponent(geo)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;

    const r = await fetch(url);
    const d = await r.json();

    if (!d.success || !d.trends.length) {
      grid.innerHTML = `<div style="color:var(--muted);font-size:.8rem;padding:20px 0">
        Aucune tendance disponible.<br>
        <span style="font-size:.7rem">Lance python trends_scraper.py pour alimenter les données.</span>
      </div>`;
      return;
    }

    // Mettre à jour la date
    const updateEl = document.getElementById('trendsUpdate');
    if (updateEl && d.trends[0].scraped_at) {
      const date = new Date(d.trends[0].scraped_at);
      updateEl.textContent = 'Mis à jour : ' + date.toLocaleString('fr-FR');
    }

    // Afficher les cards
    grid.innerHTML = d.trends.map((t, i) => {
      const pct     = Math.round(t.trend_value);
      const related = (t.related || []).slice(0, 3);
      const catColor = {
        'Mode & Beauté':  '#ff6b9d',
        'Électronique':   '#4d9fff',
        'Maison':         '#ffd700',
        'Sport & Santé':  '#00ff88',
        'Bébé & Enfant':  '#ff9900',
      }[t.category] || 'var(--muted)';

      return `<div class="trend-card">
        <div class="trend-rank">#${i+1} · ${esc(t.geo_label)}</div>
        <div class="trend-keyword">${esc(t.keyword)}</div>
        <div class="trend-bar-wrap">
          <div class="trend-bar-bg">
            <div class="trend-bar-fill" style="width:${pct}%;background:${pct > 60 ? 'var(--accent)' : pct > 30 ? '#ffd700' : 'var(--warn)'}"></div>
          </div>
          <span class="trend-score">${pct}</span>
        </div>
        <div class="trend-meta">
          <span class="trend-cat" style="border-color:${catColor};color:${catColor}">${esc(t.category || 'Général')}</span>
        </div>
        ${related.length ? `
          <div class="trend-related">
            <div class="trend-related-title">Recherches associées</div>
            ${related.map(r => `<span class="trend-tag">${esc(r)}</span>`).join('')}
          </div>` : ''}
      </div>`;
    }).join('');

  } catch(e) {
    grid.innerHTML = `<div style="color:var(--warn);font-size:.8rem">❌ Erreur : ${e.message}</div>`;
  }
}

// ── Init ─────────────────────────────────────────────────────────

async function loadAll() {
  document.getElementById('statusBadge').textContent = 'SYNC…';
  await loadStats();
  await loadPlatformPills();
  await loadProducts(1);
  document.getElementById('statusBadge').textContent = 'LIVE';
  showToast('✓ Données actualisées');
}
