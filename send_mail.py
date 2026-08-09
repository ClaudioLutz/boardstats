#!/usr/bin/env python3
"""Mailversand fuer den /biz/ Lagebericht - ohne MCP, ohne neues Passwort.

Warum nicht der Gmail-MCP-Server: der laeuft nur auf dem Windows-Rechner, und
der Versand haengt daran, dass das Modell selbst ein Werkzeug korrekt aufruft -
beim Lauf am 06.08. wich es eigenmaechtig auf ein anderes Konto aus und legte
ungefragt eine Datei an, am 07.08. kam gar keine Mail an. Hier versendet
stattdessen das Skript, und das Modell schreibt nur noch Text.

Warum kein App-Passwort: die vorhandene OAuth-Anmeldung des MCP-Servers hat den
Scope https://mail.google.com/, und der deckt SMTP ab. Es werden also genau die
Zugangsdaten weiterverwendet, die auf dem Rechner ohnehin schon liegen -
nichts Neues einzurichten, nichts zusaetzlich zu verwalten.

Erwartet wird der Kontoordner des MCP-Servers:

    ~/.gmail-multi-mcp/accounts/<konto>/credentials.json   (client_id/secret)
    ~/.gmail-multi-mcp/accounts/<konto>/token.json         (refresh_token)

Das abgelaufene Zugriffstoken wird selbstaendig erneuert und zurueckgeschrieben.

Alternativ, falls diese Dateien fehlen, ein klassischer SMTP-Zugang ueber
~/.config/boardstats/mail.env (SMTP_HOST/PORT/USER/PASS, chmod 600).
"""
from __future__ import annotations

import base64
import json
import os
import smtplib
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

OAUTH_ROOT = Path.home() / ".gmail-multi-mcp" / "accounts"
KONFIG = Path.home() / ".config" / "boardstats" / "mail.env"
KONTO = os.environ.get("BOARDSTATS_GMAIL_KONTO", "lutzcv")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


# ----------------------------------------------------------- OAuth-Weg

def _konto_pfade(konto: str) -> tuple[Path, Path]:
    ordner = OAUTH_ROOT / konto
    return ordner / "credentials.json", ordner / "token.json"


def _absender(konto: str) -> str:
    """Die Adresse steht in accounts.json des MCP-Servers."""
    p = OAUTH_ROOT.parent / "accounts.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        for a in d.get("accounts", []):
            if a.get("id") == konto and a.get("email"):
                return a["email"]
    raise RuntimeError(f"Absenderadresse fuer Konto '{konto}' nicht gefunden")


def _access_token(konto: str) -> tuple[str, str]:
    """Gibt (Absenderadresse, gueltiges Zugriffstoken) zurueck und erneuert es
    bei Bedarf. Google-Zugriffstoken laufen nach einer Stunde ab, der
    Aktualisierungstoken bleibt gueltig."""
    cred_p, tok_p = _konto_pfade(konto)
    if not (cred_p.exists() and tok_p.exists()):
        raise FileNotFoundError(f"keine OAuth-Dateien unter {cred_p.parent}")

    cred = json.loads(cred_p.read_text(encoding="utf-8"))
    cred = cred.get("installed") or cred.get("web") or cred
    tok = json.loads(tok_p.read_text(encoding="utf-8"))

    # 5 Minuten Sicherheitsabstand, damit das Token nicht mitten im Versand faellt
    if tok.get("access_token") and tok.get("expiry_date", 0) > (time.time() + 300) * 1000:
        return _absender(konto), tok["access_token"]

    daten = urllib.parse.urlencode({
        "client_id": cred["client_id"],
        "client_secret": cred["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        cred.get("token_uri", "https://oauth2.googleapis.com/token"),
        data=daten, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            antwort = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # Ohne das hier auszulesen, verrät "HTTP Error 400: Bad Request" im
        # Aufruferlog nur, DASS es fehlschlug - Googles Fehlerkoerper (meist
        # {"error": "invalid_grant", ...}) sagt, WARUM, z.B. dass der
        # Aktualisierungstoken widerrufen wurde und eine interaktive
        # Neuanmeldung noetig ist.
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Token-Erneuerung fehlgeschlagen ({e.code}): {detail}") from e

    tok["access_token"] = antwort["access_token"]
    tok["expiry_date"] = int((time.time() + antwort.get("expires_in", 3600)) * 1000)
    tok_p.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    try:
        tok_p.chmod(0o600)
    except OSError:
        pass
    return _absender(konto), tok["access_token"]


def _sende_oauth(absender: str, token: str, msg: EmailMessage) -> None:
    roh = f"user={absender}\x01auth=Bearer {token}\x01\x01"
    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as s:
        s.starttls(context=ctx)
        s.docmd("AUTH", "XOAUTH2 " + base64.b64encode(roh.encode()).decode())
        s.send_message(msg)


# ----------------------------------------------------------- Passwort-Weg

def _lade_env() -> dict:
    cfg = {k: v for k, v in os.environ.items() if k.startswith("SMTP_")}
    if KONFIG.exists():
        for zeile in KONFIG.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#") or "=" not in zeile:
                continue
            k, _, v = zeile.partition("=")
            cfg.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return cfg


def _sende_passwort(cfg: dict, msg: EmailMessage) -> None:
    port = int(cfg.get("SMTP_PORT", 587))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(cfg["SMTP_HOST"], port, context=ctx, timeout=60) as s:
            s.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg["SMTP_HOST"], port, timeout=60) as s:
            s.starttls(context=ctx)
            s.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            s.send_message(msg)


# ----------------------------------------------------------- oeffentlich

def versende(empfaenger: str, betreff: str, text: str, konto: str = KONTO,
             html_teil: bool = True) -> str:
    """Versendet und gibt den benutzten Weg zurueck. Bevorzugt OAuth, weil dann
    nichts zusaetzlich zu pflegen ist; faellt auf ein hinterlegtes Passwort
    zurueck, falls die OAuth-Dateien fehlen.

    Die Mail geht als multipart/alternative raus: HTML fuer die Lesbarkeit,
    Klartext als Rueckfallebene fuer Clients ohne HTML. Schlaegt die
    Umwandlung fehl, bleibt es bei Klartext - eine kaputte Darstellung darf
    den Versand nicht verhindern."""
    msg = EmailMessage()
    msg["To"] = empfaenger
    msg["Subject"] = betreff
    msg.set_content(text)
    if html_teil:
        try:
            from bericht_html import zu_html
            msg.add_alternative(zu_html(text, betreff), subtype="html")
        except Exception:                                   # noqa: BLE001
            pass

    try:
        absender, token = _access_token(konto)
    except (FileNotFoundError, KeyError, RuntimeError) as e:
        cfg = _lade_env()
        fehlend = [k for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS") if not cfg.get(k)]
        if fehlend:
            raise RuntimeError(
                f"Kein Versandweg verfuegbar. OAuth: {e}. "
                f"Passwort-Weg unvollstaendig ({', '.join(fehlend)}) in {KONFIG}.") from e
        msg["From"] = cfg.get("SMTP_FROM") or cfg["SMTP_USER"]
        _sende_passwort(cfg, msg)
        return "SMTP mit Passwort"

    msg["From"] = absender
    _sende_oauth(absender, token, msg)
    return f"SMTP mit OAuth ({absender})"


if __name__ == "__main__":
    import sys
    ziel = sys.argv[1] if len(sys.argv) > 1 else None
    if not ziel:
        raise SystemExit("Aufruf: send_mail.py <empfaenger>  (Testmail)")
    weg = versende(ziel, "boardstats Testmail",
                   "Wenn diese Mail ankommt, ist der Versand vom Server aus eingerichtet.")
    print(f"Testmail an {ziel} versandt, Weg: {weg}")
