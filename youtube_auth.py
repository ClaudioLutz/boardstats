#!/usr/bin/env python3
"""YouTube-OAuth + Resumable-Upload - gleiches Muster wie send_mail.py.

Warum kein google-api-python-client: die restliche Pipeline kommt komplett
ohne Google-Bibliotheken aus (send_mail.py macht den Gmail-OAuth-Refresh per
urllib von Hand) - fuer einen einzigen taeglichen Video-Upload lohnt sich die
zusaetzliche Abhaengigkeit nicht, ein rohes Resumable-Upload ist wenige Zeilen.

Erwartet wird, ausserhalb des Repos:

    ~/.config/boardstats/youtube_client.json   (aus Google Cloud Console,
                                                 OAuth-Client "Desktop-App")
    ~/.config/boardstats/youtube_token.json    (refresh_token, geschrieben von
                                                 youtube_auth_setup.py)

Das abgelaufene Zugriffstoken wird selbstaendig erneuert und zurueckgeschrieben.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KONFIG_DIR = Path.home() / ".config" / "boardstats"
CLIENT_DATEI = KONFIG_DIR / "youtube_client.json"
TOKEN_DATEI = KONFIG_DIR / "youtube_token.json"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


def _client() -> dict:
    cred = json.loads(CLIENT_DATEI.read_text(encoding="utf-8"))
    return cred.get("installed") or cred.get("web") or cred


def access_token() -> str:
    """Gibt ein gueltiges Zugriffstoken zurueck und erneuert es bei Bedarf."""
    if not (CLIENT_DATEI.exists() and TOKEN_DATEI.exists()):
        raise FileNotFoundError(
            f"keine YouTube-OAuth-Dateien unter {KONFIG_DIR} - "
            "erst youtube_auth_setup.py einmalig ausfuehren")

    cred = _client()
    tok = json.loads(TOKEN_DATEI.read_text(encoding="utf-8"))

    # 5 Minuten Sicherheitsabstand, damit das Token nicht mitten im Upload faellt
    if tok.get("access_token") and tok.get("expiry_date", 0) > (time.time() + 300) * 1000:
        return tok["access_token"]

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
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"YouTube-Token-Erneuerung fehlgeschlagen ({e.code}): {detail}") from e

    tok["access_token"] = antwort["access_token"]
    tok["expiry_date"] = int((time.time() + antwort.get("expires_in", 3600)) * 1000)
    TOKEN_DATEI.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    try:
        TOKEN_DATEI.chmod(0o600)
    except OSError:
        pass
    return tok["access_token"]


def hochladen(video_pfad: Path, titel: str, beschreibung: str,
              privacy_status: str = "unlisted", category_id: str = "25",
              tags: list[str] | None = None) -> tuple[str, str]:
    """Laedt ein Video per Resumable-Upload hoch, gibt (video_id, url) zurueck."""
    token = access_token()
    snippet: dict[str, object] = {"title": titel, "description": beschreibung, "categoryId": category_id}
    if tags:
        snippet["tags"] = tags
    metadaten = {"snippet": snippet, "status": {"privacyStatus": privacy_status}}
    metadaten_bytes = json.dumps(metadaten).encode("utf-8")
    groesse = video_pfad.stat().st_size

    start_req = urllib.request.Request(
        f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
        data=metadaten_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(groesse),
        },
    )
    try:
        with urllib.request.urlopen(start_req, timeout=30) as r:
            session_uri = r.headers.get("Location")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"YouTube-Upload-Session fehlgeschlagen ({e.code}): {detail}") from e
    if not session_uri:
        raise RuntimeError("YouTube hat keine Upload-Session-URL zurueckgegeben")

    upload_req = urllib.request.Request(
        session_uri, data=video_pfad.read_bytes(), method="PUT",
        headers={"Content-Type": "video/mp4", "Content-Length": str(groesse)})
    try:
        with urllib.request.urlopen(upload_req, timeout=600) as r:
            antwort = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"YouTube-Video-Upload fehlgeschlagen ({e.code}): {detail}") from e

    video_id = antwort["id"]
    return video_id, f"https://youtu.be/{video_id}"
