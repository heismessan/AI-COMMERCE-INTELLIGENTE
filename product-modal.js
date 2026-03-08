// ═══════════════════════════════════════════════════════════════
//  product-modal.js — AI Commerce Intelligence
//  Modal détail produit — chargé après dashboard.js
// ═══════════════════════════════════════════════════════════════

(function () {

  // ── Injecter les styles du modal ────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #pm-overlay {
      display: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,.82);
      z-index: 2000;
      align-items: center;
      justify-content: center;
      padding: 20px;
      backdrop-filter: blur(6px);
      animation: pmFadeIn .2s ease;
    }
    #pm-overlay.open { display: flex; }
    @keyframes pmFadeIn { from{opacity:0} to{opacity:1} }

    #pm-box {
      background: #13131c;
      border: 1px solid #1e1e2e;
      border-radius: 6px;
      width: 100%;
      max-width: 600px;
      max-height: 90vh;
      overflow-y: auto;
      font-family: 'DM Mono', monospace;
      color: #e8e8f0;
      box-shadow: 0 24px 80px rgba(0,0,0,.7);
      animation: pmSlideUp .25s ease;
    }
    @keyframes pmSlideUp {
      from { opacity:0; transform: translateY(16px); }
      to   { opacity:1; transform: translateY(0); }
    }
    #pm-box::-webkit-scrollbar { width: 4px; }
    #pm-box::-webkit-scrollbar-track { background: #0d0d16; }
    #pm-box::-webkit-scrollbar-thumb { background: #1e1e2e; border-radius: 2px; }

    .pm-header {
      padding: 22px 26px 18px;
      border-bottom: 1px solid #1e1e2e;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
    }
    .pm-platform {
      font-size: .6rem;
      letter-spacing: .14em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .pm-title {
      font-family: 'Syne', sans-serif;
      font-size: .95rem;
      font-weight: 700;
      line-height: 1.45;
      color: #e8e8f0;
    }
    .pm-close {
      background: none;
      border: 1px solid #2a2a3e;
      color: #6b6b85;
      width: 32px; height: 32px;
      border-radius: 3px;
      cursor: pointer;
      font-size: .85rem;
      flex-shrink: 0;
      transition: all .2s;
      line-height: 1;
    }
    .pm-close:hover { border-color: #e8e8f0; color: #e8e8f0; }

    .pm-metrics {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      border-bottom: 1px solid #1e1e2e;
    }
    .pm-metric {
      padding: 18px 16px;
      text-align: center;
      border-right: 1px solid #1e1e2e;
    }
    .pm-metric:last-child { border-right: none; }
    .pm-metric-label {
      font-size: .58rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: #6b6b85;
      margin-bottom: 7px;
    }
    .pm-metric-value {
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      line-height: 1.1;
    }
    .pm-metric-sub {
      font-size: .6rem;
      color: #6b6b85;
      margin-top: 4px;
    }

    .pm-section {
      padding: 18px 26px;
      border-bottom: 1px solid #1e1e2e;
    }
    .pm-section-title {
      font-size: .6rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: #6b6b85;
      margin-bottom: 14px;
    }

    .pm-stats-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .pm-stat {
      background: #0d0d16;
      border: 1px solid #1e1e2e;
      border-radius: 3px;
      padding: 12px 14px;
    }
    .pm-stat-label {
      font-size: .58rem;
      color: #6b6b85;
      letter-spacing: .1em;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    .pm-stat-value {
      font-size: .88rem;
      font-weight: 600;
    }

    .pm-analysis {
      font-size: .76rem;
      color: #a0a0b8;
      line-height: 1.85;
    }

    .pm-actions {
      padding: 18px 26px 22px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .pm-btn-primary {
      flex: 1;
      background: #00ff88;
      color: #000;
      padding: 12px 16px;
      text-align: center;
      text-decoration: none;
      border-radius: 3px;
      font-size: .78rem;
      font-weight: 700;
      letter-spacing: .05em;
      font-family: 'Syne', sans-serif;
      transition: background .2s;
      border: none;
      cursor: pointer;
    }
    .pm-btn-primary:hover { background: #00e67a; }
    .pm-btn-secondary {
      background: none;
      border: 1px solid #1e1e2e;
      color: #6b6b85;
      padding: 12px 20px;
      border-radius: 3px;
      font-size: .75rem;
      cursor: pointer;
      font-family: 'DM Mono', monospace;
      transition: all .2s;
    }
    .pm-btn-secondary:hover { border-color: #6b6b85; }
    .pm-btn-disabled {
      flex: 1;
      background: rgba(0,255,136,.05);
      border: 1px solid rgba(0,255,136,.15);
      color: #00ff88;
      padding: 12px 16px;
      text-align: center;
      border-radius: 3px;
      font-size: .75rem;
      font-family: 'DM Mono', monospace;
    }

    .pm-footer {
      padding: 0 26px 16px;
      font-size: .6rem;
      color: #2a2a3e;
    }

    .pm-score-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 6px;
    }
    .pm-score-track {
      flex: 1;
      height: 4px;
      background: #1e1e2e;
      border-radius: 2px;
      overflow: hidden;
    }
    .pm-score-fill { height: 100%; border-radius: 2px; }

    .pm-loading {
      padding: 60px;
      text-align: center;
      color: #6b6b85;
      font-size: .8rem;
    }
    .pm-error {
      padding: 40px 26px;
      text-align: center;
      color: #ff6b35;
      font-size: .78rem;
    }
  `;
  document.head.appendChild(style);

  // ── Créer l'overlay dans le DOM ────────────────────────────────
  const overlay = document.createElement('div');
  overlay.id = 'pm-overlay';
  overlay.innerHTML = '<div id="pm-box"></div>';
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeProductModal();
  });
  document.body.appendChild(overlay);

  // Fermer avec Échap
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeProductModal();
  });


  // ── Helpers internes ───────────────────────────────────────────

  function _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _scoreColor(s) {
    return s >= 8 ? '#00ff88' : s >= 5 ? '#ffd700' : '#ff6b35';
  }

  function _marginColor(m) {
    return m >= 30 ? '#00ff88' : m >= 15 ? '#ffd700' : '#ff6b35';
  }

  function _stars(rating) {
    if (!rating || rating <= 0) return '—';
    const full  = Math.round(rating);
    const empty = 5 - full;
    return '<span style="color:#ffd700">' + '★'.repeat(full) + '</span>' +
           '<span style="color:#2a2a3e">' + '☆'.repeat(empty) + '</span>';
  }

  function _platColor(platform) {
    const map = { Amazon: '#ff9900', eBay: '#4d9fff', Walmart: '#0071ce', Etsy: '#f45800' };
    return map[platform] || '#6b6b85';
  }

  function _metric(label, value, sub, color, fontSize) {
    return `
      <div class="pm-metric">
        <div class="pm-metric-label">${label}</div>
        <div class="pm-metric-value" style="font-size:${fontSize};color:${color};">${value}</div>
        ${sub ? `<div class="pm-metric-sub">${sub}</div>` : ''}
      </div>`;
  }

  function _stat(label, value, color) {
    return `
      <div class="pm-stat">
        <div class="pm-stat-label">${label}</div>
        <div class="pm-stat-value" style="color:${color};">${value}</div>
      </div>`;
  }

  function _analysis(p) {
    const lines  = [];
    const score  = Number(p.opportunity_score || 0);
    const margin = Number(p.margin || 0);
    const rating = Number(p.rating || 0);
    const revs   = Number(p.reviews || 0);
    const sales  = Number(p.sales || 0);

    if (score >= 8)
      lines.push('🟢 <strong style="color:#e8e8f0">Excellente opportunité</strong> — score dans le top de la base.');
    else if (score >= 6)
      lines.push('🟡 <strong style="color:#e8e8f0">Bonne opportunité</strong> — potentiel commercial intéressant.');
    else
      lines.push('🔴 <strong style="color:#e8e8f0">Opportunité limitée</strong> — concurrence forte ou marge faible.');

    if (margin >= 30)
      lines.push('✅ Marge solide (' + margin.toFixed(1) + '%) — bon potentiel de rentabilité.');
    else if (margin >= 15)
      lines.push('⚠️ Marge correcte (' + margin.toFixed(1) + '%) — surveiller les coûts logistiques.');
    else
      lines.push('⚠️ Marge faible (' + margin.toFixed(1) + '%) — volume élevé nécessaire pour rentabiliser.');

    if (revs > 1000)
      lines.push('📊 Très forte preuve sociale (' + revs.toLocaleString() + ' avis) — demande confirmée.');
    else if (revs > 200)
      lines.push('📊 Popularité établie (' + revs.toLocaleString() + ' avis) — marché actif.');
    else if (revs > 0)
      lines.push('📊 Peu d\'avis (' + revs + ') — produit récent ou niche spécifique.');

    if (rating >= 4.5)
      lines.push('⭐ Excellente satisfaction client (' + rating.toFixed(1) + '/5) — faible risque de retour.');
    else if (rating >= 4.0)
      lines.push('⭐ Bonne satisfaction client (' + rating.toFixed(1) + '/5).');
    else if (rating >= 3.0)
      lines.push('⚠️ Note moyenne (' + rating.toFixed(1) + '/5) — consulter les avis négatifs avant de revendre.');
    else if (rating > 0)
      lines.push('🔴 Note faible (' + rating.toFixed(1) + '/5) — produit potentiellement problématique.');

    if (sales > 500)
      lines.push('🔥 Volume de ventes élevé (' + sales.toLocaleString() + '/mois) — produit en forte demande.');
    else if (sales > 100)
      lines.push('📈 Ventes régulières (' + sales.toLocaleString() + '/mois) — demande stable.');
    else if (sales > 0)
      lines.push('📉 Ventes faibles (' + sales + '/mois) — niche ou produit récent.');

    return lines.join('<br>');
  }


  // ── Rendu du modal ─────────────────────────────────────────────

  function _render(p) {
    const score   = Number(p.opportunity_score || 0);
    const margin  = Number(p.margin || 0);
    const price   = Number(p.price || 0);
    const rating  = Number(p.rating || 0);
    const scorePct = Math.round((score / 10) * 100);
    const scColor = _scoreColor(score);
    const hasLink = p.affiliate_url && p.affiliate_url.length > 5;

    return `
      <!-- En-tête -->
      <div class="pm-header">
        <div style="flex:1">
          <div class="pm-platform" style="color:${_platColor(p.platform)}">${_esc(p.platform)}</div>
          <div class="pm-title">${_esc(p.title)}</div>
        </div>
        <button class="pm-close" onclick="closeProductModal()">✕</button>
      </div>

      <!-- Métriques principales -->
      <div class="pm-metrics">
        ${_metric('Score opportunité',
          `<span style="color:${scColor}">${score.toFixed(1)}</span>`,
          `<div class="pm-score-bar">
            <div class="pm-score-track">
              <div class="pm-score-fill" style="width:${scorePct}%;background:${scColor}"></div>
            </div>
            <span style="font-size:.65rem;color:${scColor}">${scorePct}%</span>
          </div>`,
          scColor, '2rem')}
        ${_metric('Prix', '$' + price.toFixed(2), 'USD', '#e8e8f0', '1.6rem')}
        ${_metric('Note client', _stars(rating), rating > 0 ? rating.toFixed(1) + ' / 5' : 'N/A', '#ffd700', '1rem')}
      </div>

      <!-- Données commerciales -->
      <div class="pm-section">
        <div class="pm-section-title">Données commerciales</div>
        <div class="pm-stats-grid">
          ${_stat('Marge estimée',  margin.toFixed(1) + '%',                        _marginColor(margin))}
          ${_stat('Ventes / mois',  Number(p.sales   || 0).toLocaleString(),        '#e8e8f0')}
          ${_stat('Nombre d\'avis', Number(p.reviews || 0).toLocaleString(),        '#e8e8f0')}
          ${_stat('Tendance',       p.trend_score ? (p.trend_score*100).toFixed(0)+'%' : '—', '#e8e8f0')}
        </div>
      </div>

      <!-- Analyse automatique -->
      <div class="pm-section">
        <div class="pm-section-title">Analyse rapide</div>
        <div class="pm-analysis">${_analysis(p)}</div>
      </div>

      <!-- Actions -->
      <div class="pm-actions">
        ${hasLink
          ? `<a href="${_esc(p.affiliate_url)}" target="_blank"
               class="pm-btn-primary"
               onclick="event.stopPropagation()">
               Voir sur ${_esc(p.platform)} →
             </a>`
          : `<div class="pm-btn-disabled">Lien affilié disponible prochainement</div>`
        }
        <button class="pm-btn-secondary" onclick="closeProductModal()">Fermer</button>
      </div>

      <!-- Footer -->
      <div class="pm-footer">
        Dernière mise à jour : ${p.scraped_at ? new Date(p.scraped_at).toLocaleString('fr-FR') : '—'}
        &nbsp;·&nbsp; ID #${p.id}
      </div>`;
  }


  // ── API publique ───────────────────────────────────────────────

  window.openProductModal = async function (id) {
    const box = document.getElementById('pm-box');
    box.innerHTML = '<div class="pm-loading"><span class="spinner"></span> Chargement…</div>';
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';

    try {
      // L'API retourne { success: true, product: {...} }
      const r = await fetch(API + '/api/products/' + id);
      const data = await r.json();

      if (!data.success || !data.product) {
        box.innerHTML = '<div class="pm-error">❌ Produit introuvable (ID ' + id + ')</div>';
        return;
      }

      box.innerHTML = _render(data.product);

    } catch (e) {
      console.error('Modal error:', e);
      box.innerHTML = '<div class="pm-error">❌ Erreur de chargement.<br><span style="font-size:.68rem;color:#6b6b85">' + e.message + '</span></div>';
    }
  };

  window.closeProductModal = function () {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  };

})();
