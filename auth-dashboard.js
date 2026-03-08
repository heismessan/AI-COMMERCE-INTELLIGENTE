// ═══════════════════════════════════════════════════════════════
//  auth-dashboard.js — AI Commerce Intelligence
//  Auth + Modal Produit + Export CSV
//  Dépend de dashboard.js (API, esc() doivent être chargés avant)
// ═══════════════════════════════════════════════════════════════


// ── AUTH ─────────────────────────────────────────────────────────

function logout() {
  localStorage.removeItem('aci_token');
  localStorage.removeItem('aci_user');
  window.location.href = 'login.html';
}

async function handleUpgrade() {
  const token = localStorage.getItem('aci_token');
  if (!token) { window.location.href = 'login.html'; return; }
  try {
    const r = await fetch(AUTH_API + '/auth/create-checkout', {
      method:  'POST',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    const d = await r.json();
    if (d.success && d.checkout_url) {
      window.open(d.checkout_url, '_blank');
    } else {
      alert(d.error || 'Erreur checkout');
    }
  } catch (e) {
    alert('Serveur auth inaccessible.');
  }
}

function initAuth() {
  const token = localStorage.getItem('aci_token');
  const user  = JSON.parse(localStorage.getItem('aci_user') || 'null');

  if (!token || !user) {
    window.location.href = 'login.html';
    return;
  }

  const emailEl = document.getElementById('userEmail');
  if (emailEl) emailEl.textContent = user.email;

  const pillEl = document.getElementById('planPill');
  if (pillEl) {
    if (user.plan === 'pro') {
      pillEl.textContent = '★ PRO';
      pillEl.className   = 'plan-pill plan-pro';
      const bar = document.getElementById('upgradeBar');
      if (bar) bar.style.display = 'none';
    } else {
      pillEl.textContent = 'FREE';
      pillEl.className   = 'plan-pill plan-free';
      const bar = document.getElementById('upgradeBar');
      if (bar) bar.style.display = 'flex';
    }
  }
}


// ── EXPORT CSV ───────────────────────────────────────────────────

async function exportCSV() {
  const user = JSON.parse(localStorage.getItem('aci_user') || 'null');

  if (!user || user.plan !== 'pro') {
    showExportToast('🔒 Export réservé au plan Pro — 11 500 FCFA / 17,52 €/mois', true);
    return;
  }

  // Récupérer les filtres actifs
  const platform  = document.getElementById('exportPlatform').value || activePlatform || '';
  const search    = (document.getElementById('searchInput')  || {}).value || '';
  const sort      = (document.getElementById('sortFilter')   || {}).value || 'opportunity_score';

  let url = `${API}/api/products?per_page=9999&sort=${sort}`;
  if (platform) url += `&platform=${encodeURIComponent(platform)}`;
  if (search.trim()) url += `&q=${encodeURIComponent(search.trim())}`;

  showExportToast('⏳ Préparation de l\'export…');

  try {
    const r = await fetch(url);
    const d = await r.json();
    const products = d.products || [];

    if (!products.length) {
      showExportToast('⚠️ Aucun produit à exporter.', true);
      return;
    }

    // Construire le CSV avec BOM UTF-8 pour Excel
    const headers = [
      'ID', 'Titre', 'Plateforme', 'Prix ($)', 'Marge (%)',
      'Ventes/mois', 'Avis', 'Note /5', 'Score /10', 'URL Affilié', 'Date scraping'
    ];

    const rows = products.map(p => [
      p.id,
      '"' + (p.title || '').replace(/"/g, '""') + '"',
      p.platform || '',
      p.price     ? Number(p.price).toFixed(2)    : '0.00',
      p.margin    !== undefined ? Number(p.margin).toFixed(1) : '0',
      p.sales     || 0,
      p.reviews   || 0,
      p.rating    ? Number(p.rating).toFixed(1)   : '0',
      p.opportunity_score ? Number(p.opportunity_score).toFixed(1) : '0',
      p.affiliate_url || '',
      p.scraped_at ? p.scraped_at.split('T')[0]   : ''
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });

    const a        = document.createElement('a');
    const pfx      = platform ? '_' + platform.toLowerCase() : '_toutes-plateformes';
    const dateStr  = new Date().toISOString().split('T')[0];
    a.href         = URL.createObjectURL(blob);
    a.download     = `aci_produits${pfx}_${dateStr}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);

    showExportToast('✅ ' + products.length + ' produits exportés avec succès !');

  } catch (e) {
    console.error('Export error:', e);
    showExportToast('❌ Erreur lors de l\'export : ' + e.message, true);
  }
}

function showExportToast(msg, isError = false) {
  const el = document.getElementById('exportToast');
  if (!el) return;
  el.textContent    = msg;
  el.style.background = isError ? 'var(--warn)' : 'var(--accent2)';
  el.style.opacity  = '1';
  el.style.transform = 'translateY(0)';
  clearTimeout(el._t);
  el._t = setTimeout(() => {
    el.style.opacity   = '0';
    el.style.transform = 'translateY(20px)';
  }, 3500);
}


// ── DÉMARRAGE ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  loadAll();
});
