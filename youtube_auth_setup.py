#!/usr/bin/env python3
"""Einmaliges interaktives YouTube-OAuth-Setup - lokal ausfuehren, nicht per Cron.

Gleiches Prinzip wie das bestehende reauth-expanded.mjs fuer Gmail: ein
lokaler HTTP-Listener auf 127.0.0.1 faengt den OAuth-Redirect ab (Google
erlaubt bei "Desktop-App"-Clients beliebige localhost-Ports ohne
Vorab-Registrierung), der Browser oeffnet sich zur Anmeldung/Bestaetigung.

Voraussetzung: ~/.config/boardstats/youtube_client.json muss schon existieren
(aus Google Cloud Console heruntergeladener OAuth-Client vom Typ "Desktop-App",
YouTube Data API v3 fuer das Projekt aktiviert).

Aufruf: python3 youtube_auth_setup.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from youtube_auth import CLIENT_DATEI, KONFIG_DIR, SCOPE, TOKEN_DATEI, _client  # noqa: E402

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"


def _code_einholen(client_id: str) -> tuple[str, str]:
    ergebnis: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if "code" in params:
                ergebnis["code"] = params["code"][0]
                self.wfile.write(
                    "<html><body style='font-family:sans-serif;padding:2em'>"
                    "<h2>Autorisierung erfolgreich</h2><p>Dieses Fenster kann "
                    "geschlossen werden.</p></body></html>".encode("utf-8"))
            else:
                ergebnis["error"] = params.get("error", ["unbekannt"])[0]
                self.wfile.write(f"Fehler: {ergebnis['error']}".encode("utf-8"))

        def log_message(self, *args: object) -> None:  # Konsole nicht zumuellen
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    url = AUTH_URI + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    print(f"\nBrowser oeffnet sich fuer die Anmeldung.\nFalls nicht: {url}\n")
    webbrowser.open(url)

    server.timeout = 300
    while "code" not in ergebnis and "error" not in ergebnis:
        server.handle_request()
    server.server_close()

    if "error" in ergebnis:
        raise RuntimeError(f"OAuth-Autorisierung fehlgeschlagen: {ergebnis['error']}")
    return ergebnis["code"], redirect_uri


def main() -> None:
    if not CLIENT_DATEI.exists():
        raise SystemExit(
            f"Fehlt: {CLIENT_DATEI}\n"
            "Erst in Google Cloud Console einen OAuth-Client vom Typ "
            "'Desktop-App' anlegen, YouTube Data API v3 aktivieren, "
            "client_secret.json herunterladen und dorthin kopieren.")

    cred = _client()
    code, redirect_uri = _code_einholen(client_id=cred["client_id"])

    daten = urllib.parse.urlencode({
        "client_id": cred["client_id"],
        "client_secret": cred["client_secret"],
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        cred.get("token_uri", "https://oauth2.googleapis.com/token"),
        data=daten, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            antwort = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"Token-Austausch fehlgeschlagen ({e.code}): {detail}") from e

    if "refresh_token" not in antwort:
        raise SystemExit(
            "Keine refresh_token in der Antwort - vermutlich war schon einmal "
            "ohne 'prompt=consent' zugestimmt worden. Zugriff unter "
            "https://myaccount.google.com/permissions widerrufen und erneut "
            "versuchen.")

    antwort["expiry_date"] = int((time.time() + antwort.get("expires_in", 3600)) * 1000)
    KONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_DATEI.write_text(json.dumps(antwort, indent=2), encoding="utf-8")
    try:
        TOKEN_DATEI.chmod(0o600)
    except OSError:
        pass
    print(f"\nToken gespeichert unter {TOKEN_DATEI}")
    print(f"Scope: {antwort.get('scope', '(unbekannt)')}")


if __name__ == "__main__":
    main()
