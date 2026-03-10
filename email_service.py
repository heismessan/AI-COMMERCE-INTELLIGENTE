"""
email_service.py — AI Commerce Intelligence
─────────────────────────────────────────────────────────
Service d'envoi d'emails via l'API Brevo (ex-Sendinblue).
Utilise HTTPS port 443 — jamais bloqué par les FAI.

Prérequis :
    pip install requests  (déjà installé)

Configuration :
    Remplis BREVO_API_KEY et SENDER_EMAIL ci-dessous
"""

import os
import requests
import secrets
import datetime

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION — remplis ces deux valeurs
# ══════════════════════════════════════════════════════════════════

from config import BREVO_API_KEY, SENDER_EMAIL, SENDER_NAME, APP_URL

APP_NAME = "AI Commerce Intelligence"

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


# ── Token ────────────────────────────────────────────────────────

def generate_verification_token() -> str:
    return secrets.token_urlsafe(48)

def token_expiry() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=24)


# ── Templates ────────────────────────────────────────────────────

def _confirmation_html(confirm_url, user_email):
    year = datetime.datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Courier New',monospace;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
  <tr><td style="padding-bottom:28px;text-align:center;">
    <span style="font-size:13px;font-weight:800;letter-spacing:0.1em;color:#e8e8f0;text-transform:uppercase;">
      <span style="display:inline-block;width:8px;height:8px;background:#00ff88;border-radius:50%;margin-right:8px;vertical-align:middle;"></span>
      {APP_NAME}
    </span>
  </td></tr>
  <tr><td style="background:#13131c;border:1px solid #1e1e2e;border-radius:6px;overflow:hidden;">
    <div style="height:3px;background:linear-gradient(90deg,#00ff88,#0066ff);"></div>
    <table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:36px 40px 32px;">
      <p style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#6b6b85;margin:0 0 14px;">Confirmation d'inscription</p>
      <h1 style="font-size:21px;font-weight:800;color:#e8e8f0;margin:0 0 20px;">Confirme ton adresse email</h1>
      <p style="font-size:13px;color:#a0a0b8;line-height:1.75;margin:0 0 28px;">
        Tu viens de créer un compte sur <strong style="color:#e8e8f0">{APP_NAME}</strong>
        avec l'adresse <strong style="color:#00ff88">{user_email}</strong>.<br><br>
        Clique sur le bouton ci-dessous pour confirmer ton email et activer ton compte.
        Ce lien est valable <strong style="color:#e8e8f0">24 heures</strong>.
      </p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
      <tr><td style="background:#00ff88;border-radius:3px;">
        <a href="{confirm_url}" style="display:inline-block;padding:14px 32px;font-size:13px;font-weight:700;letter-spacing:0.06em;color:#000;text-decoration:none;">
          ✓ Confirmer mon email →
        </a>
      </td></tr></table>
      <p style="font-size:11px;color:#6b6b85;line-height:1.6;margin:0 0 22px;">
        Si le bouton ne fonctionne pas :<br>
        <a href="{confirm_url}" style="color:#0066ff;word-break:break-all;">{confirm_url}</a>
      </p>
      <div style="background:#0d0d16;border:1px solid #1e1e2e;border-radius:3px;padding:14px 16px;">
        <p style="font-size:11px;color:#6b6b85;margin:0;line-height:1.6;">
          ⚠️ Si tu n'es pas à l'origine de cette inscription, ignore cet email.
        </p>
      </div>
    </td></tr></table>
  </td></tr>
  <tr><td style="padding:22px 0 0;text-align:center;">
    <p style="font-size:10px;color:#3a3a4e;margin:0;">
      {APP_NAME} · Ce message est automatique. © {year}
    </p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _welcome_html(user_email):
    year = datetime.datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Courier New',monospace;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
  <tr><td style="padding-bottom:28px;text-align:center;">
    <span style="font-size:13px;font-weight:800;letter-spacing:0.1em;color:#e8e8f0;text-transform:uppercase;">
      <span style="display:inline-block;width:8px;height:8px;background:#00ff88;border-radius:50%;margin-right:8px;vertical-align:middle;"></span>
      {APP_NAME}
    </span>
  </td></tr>
  <tr><td style="background:#13131c;border:1px solid #1e1e2e;border-radius:6px;overflow:hidden;">
    <div style="height:3px;background:linear-gradient(90deg,#00ff88,#0066ff);"></div>
    <table width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:36px 40px 32px;">
      <p style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#6b6b85;margin:0 0 14px;">Compte activé</p>
      <h1 style="font-size:21px;font-weight:800;color:#00ff88;margin:0 0 20px;">Bienvenue sur {APP_NAME} ! 🎉</h1>
      <p style="font-size:13px;color:#a0a0b8;line-height:1.75;margin:0 0 24px;">
        Ton compte <strong style="color:#e8e8f0">{user_email}</strong> est maintenant actif.
      </p>
      <div style="background:#0d0d16;border:1px solid #1e1e2e;border-radius:3px;padding:16px 18px;margin-bottom:24px;">
        <p style="font-size:11px;color:#6b6b85;margin:0 0 6px;">Ton plan actuel</p>
        <p style="font-size:14px;color:#e8e8f0;margin:0;font-weight:700;">Plan Gratuit</p>
        <p style="font-size:11px;color:#6b6b85;margin:8px 0 0;">
          Passe au Plan Pro (11 500 FCFA / 17,52 €/mois) pour débloquer scores, comparaisons et export CSV.
        </p>
      </div>
      <table cellpadding="0" cellspacing="0">
      <tr><td style="background:#00ff88;border-radius:3px;">
        <a href="{APP_URL}/login.html" style="display:inline-block;padding:13px 28px;font-size:13px;font-weight:700;color:#000;text-decoration:none;">
          Accéder au dashboard →
        </a>
      </td></tr></table>
    </td></tr></table>
  </td></tr>
  <tr><td style="padding:22px 0 0;text-align:center;">
    <p style="font-size:10px;color:#3a3a4e;margin:0;">{APP_NAME} · © {year}</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


# ── Envoi via API Brevo ──────────────────────────────────────────

def _send(to_email: str, subject: str, html: str, text: str) -> dict:
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("REMPLACE"):
        return {"success": False, "error": "Brevo non configuré dans email_service.py"}

    headers = {
        "accept":       "application/json",
        "content-type": "application/json",
        "api-key":      BREVO_API_KEY,
    }
    payload = {
        "sender":      {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to":          [{"email": to_email}],
        "subject":     subject,
        "htmlContent": html,
        "textContent": text,
    }

    try:
        r = requests.post(BREVO_URL, headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            print(f"✅ Email envoyé à {to_email}")
            return {"success": True, "error": None}
        else:
            err = r.json().get("message", r.text)
            print(f"❌ Brevo {r.status_code} : {err}")
            return {"success": False, "error": f"Brevo {r.status_code} : {err}"}
    except requests.exceptions.ConnectionError:
        msg = "Impossible de joindre l'API Brevo. Vérifie ta connexion."
        print(f"❌ {msg}")
        return {"success": False, "error": msg}
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return {"success": False, "error": str(e)}


# ── Emails publics ───────────────────────────────────────────────

def send_confirmation_email(to_email: str, token: str) -> dict:
    confirm_url = f"{APP_URL}/auth/confirm-email?token={token}"
    return _send(
        to_email = to_email,
        subject  = f"✓ Confirme ton email — {APP_NAME}",
        html     = _confirmation_html(confirm_url, to_email),
        text     = f"Confirme ton email : {confirm_url} (valable 24h)",
    )

def send_welcome_email(to_email: str) -> dict:
    return _send(
        to_email = to_email,
        subject  = f"🎉 Bienvenue sur {APP_NAME} — Compte activé !",
        html     = _welcome_html(to_email),
        text     = f"Bienvenue ! Ton compte est actif → {APP_URL}/login.html",
    )


# ── Test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Test d'envoi d'email de confirmation…")
    result = send_confirmation_email(
        to_email = SENDER_EMAIL,
        token    = generate_verification_token()
    )
    if result["success"]:
        print("✅ Email envoyé ! Vérifie ta boîte mail.")
    else:
        print(f"❌ Erreur : {result['error']}")
