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
# youtube.upload deckt Video-Upload und Thumbnail; captions.insert (eigene
# Untertitel) verlangt zusaetzlich youtube.force-ssl; yt-analytics.readonly ist
# nur lesend und liefert Abrufe/Wiedergabedauer/Abbruchkurve je Video. Nach einer
# Erweiterung hier muss youtube_auth_setup.py einmalig neu durchlaufen werden
# (Re-Consent), sonst traegt der gespeicherte refresh_token nur die alten Scopes.
SCOPE = ("https://www.googleapis.com/auth/youtube.upload "
         "https://www.googleapis.com/auth/youtube.force-ssl "
         "https://www.googleapis.com/auth/yt-analytics.readonly")
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMBNAIL_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
CAPTIONS_URL = "https://www.googleapis.com/upload/youtube/v3/captions"


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
              tags: list[str] | None = None,
              sprache: str | None = None) -> tuple[str, str]:
    """Laedt ein Video per Resumable-Upload hoch, gibt (video_id, url) zurueck."""
    token = access_token()
    snippet: dict[str, object] = {"title": titel, "description": beschreibung, "categoryId": category_id}
    if tags:
        snippet["tags"] = tags
    if sprache:
        # Metadaten- und Tonsprache (BCP-47, z.B. "de"): steuert, welchem
        # Publikum YouTube das Video zuordnet, und hilft den Auto-Untertiteln.
        snippet["defaultLanguage"] = sprache
        snippet["defaultAudioLanguage"] = sprache
    # selfDeclaredMadeForKids=False deklariert "nicht speziell fuer Kinder" -
    # sonst verlangt YouTube Studio die Angabe bei jedem Video von Hand.
    metadaten = {"snippet": snippet,
                 "status": {"privacyStatus": privacy_status,
                            "selfDeclaredMadeForKids": False}}
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


def status_setzen(video_id: str, privacy_status: str) -> None:
    """Setzt den privacyStatus eines bestehenden Videos (videos.update).

    Dient dazu, ein zunaechst privat hochgeladenes Video erst nach Thumbnail,
    Untertiteln und Playlist-Eintrag auf oeffentlich zu schalten - so sieht
    niemand ein Video ohne Vorschaubild oder Beschreibung. Braucht den
    force-ssl-Scope."""
    token = access_token()
    daten = json.dumps({"id": video_id,
                        "status": {"privacyStatus": privacy_status}}).encode("utf-8")
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/videos?part=status",
        data=daten, method="PUT",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Status-Aenderung fehlgeschlagen ({e.code}): {detail}") from e


def loeschen(video_id: str) -> None:
    """Loescht ein Video des Kanals endgueltig (videos.delete; braucht den
    force-ssl-Scope). Nur auf ausdrueckliche Anweisung aufrufen."""
    token = access_token()
    req = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/videos?id={video_id}",
        method="DELETE", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"YouTube-Loeschung fehlgeschlagen ({e.code}): {detail}") from e


def playlist_eintragen(video_id: str, playlist_id: str,
                       position: int | None = 0) -> None:
    """Traegt ein Video in eine Playlist ein (playlistItems.insert).

    position=0 setzt es an den Anfang (Tagesberichte: neuester zuerst),
    None haengt es hinten an. Braucht den force-ssl-Scope. YouTube prueft
    nicht auf Duplikate, ein zweiter Aufruf legt also einen zweiten Eintrag
    an - deshalb nur direkt nach einem gelungenen Upload aufrufen. Ein Fehler
    hier ist kein Upload-Fehler, der Aufrufer soll ihn abfangen."""
    token = access_token()
    snippet: dict[str, object] = {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": video_id},
    }
    if position is not None:
        snippet["position"] = position
    daten = json.dumps({"snippet": snippet}).encode("utf-8")
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
        data=daten, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Playlist-Eintrag fehlgeschlagen ({e.code}): {detail}") from e


def kanal_trailer_setzen(video_id: str) -> bool:
    """Macht das Video zum Kanal-Trailer (brandingSettings.unsubscribedTrailer).

    Das ist das Video, das YouTube nicht abonnierten Besuchern oben auf der
    Kanalseite zeigt und automatisch startet - bei einer Tagesreihe soll dort
    immer der neueste Bericht stehen. Rueckgabe True, wenn geschrieben wurde,
    False, wenn schon dasselbe Video drinstand (dann kein Schreibcall).

    Braucht den force-ssl-Scope. channels.update loescht jedes Feld des
    gesendeten Teilbaums, das nicht mitkommt, deshalb wird der komplette
    channel-Teilbaum gelesen und samt title, description und keywords
    zurueckgeschickt. Ein Fehler hier ist kein Upload-Fehler, der Aufrufer
    soll ihn abfangen.

    Fuer Abonnenten zeigt YouTube ein eigenes "empfohlenes Video" - das gibt
    die Data API nicht her und bleibt Handarbeit im Studio."""
    token = access_token()
    kopf = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/channels"
        "?part=brandingSettings&mine=true", headers=kopf)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            antwort = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Kanal-Abfrage fehlgeschlagen ({e.code}): {detail}") from e
    items = antwort.get("items") or []
    if not items:
        raise RuntimeError("channels.list hat keinen eigenen Kanal geliefert")
    kanal_id = items[0]["id"]
    teil = dict((items[0].get("brandingSettings") or {}).get("channel") or {})
    if teil.get("unsubscribedTrailer") == video_id:
        return False
    teil["unsubscribedTrailer"] = video_id
    daten = json.dumps({"id": kanal_id,
                        "brandingSettings": {"channel": teil}}).encode("utf-8")
    put = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings",
        data=daten, method="PUT",
        headers={**kopf, "Content-Type": "application/json; charset=UTF-8"})
    try:
        with urllib.request.urlopen(put, timeout=30) as r:
            zurueck = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            f"Kanal-Trailer setzen fehlgeschlagen ({e.code}): {detail}") from e
    # Geprueft wird an der Antwort des PUT, nicht an einem GET danach: ein
    # sofortiger GET liefert teils noch den alten Wert (17.08.2026 erlebt).
    gesetzt = ((zurueck.get("brandingSettings") or {}).get("channel")
               or {}).get("unsubscribedTrailer")
    if gesetzt != video_id:
        raise RuntimeError(
            f"Kanal-Trailer nicht uebernommen, steht auf {gesetzt!r}")
    return True


def untertitel_setzen(video_id: str, srt_pfad: Path, sprache: str,
                      name: str = "") -> None:
    """Laedt eine eigene Untertitel-Spur (SRT) zu einem Video hoch.

    Braucht den Scope youtube.force-ssl - traegt der gespeicherte Token nur
    youtube.upload, antwortet YouTube mit 403 (insufficientPermissions); der
    Aufrufer soll das abfangen, fehlende Untertitel sind kein Upload-Fehler.
    name="" macht die Spur zur unbenannten Standard-Spur der Sprache."""
    token = access_token()
    metadaten = {"snippet": {"videoId": video_id, "language": sprache,
                             "name": name, "isDraft": False}}
    metadaten_bytes = json.dumps(metadaten).encode("utf-8")
    daten = srt_pfad.read_bytes()

    start_req = urllib.request.Request(
        f"{CAPTIONS_URL}?uploadType=resumable&part=snippet",
        data=metadaten_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "application/octet-stream",
            "X-Upload-Content-Length": str(len(daten)),
        },
    )
    try:
        with urllib.request.urlopen(start_req, timeout=30) as r:
            session_uri = r.headers.get("Location")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Untertitel-Session fehlgeschlagen ({e.code}): {detail}") from e
    if not session_uri:
        raise RuntimeError("YouTube hat keine Untertitel-Session-URL zurueckgegeben")

    upload_req = urllib.request.Request(
        session_uri, data=daten, method="PUT",
        headers={"Content-Type": "application/octet-stream",
                 "Content-Length": str(len(daten))})
    try:
        with urllib.request.urlopen(upload_req, timeout=120):
            pass
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Untertitel-Upload fehlgeschlagen ({e.code}): {detail}") from e


def thumbnail_setzen(video_id: str, bild_pfad: Path) -> None:
    """Setzt das Vorschaubild eines Videos (max. 2 MB, ideal 1280x720).

    Der youtube.upload-Scope deckt thumbnails/set ab; zusaetzlich verlangt
    YouTube aber einen fuer eigene Thumbnails verifizierten Kanal
    (Telefon-Verifizierung), sonst kommt ein 403 - der Aufrufer soll das
    abfangen, ein fehlendes Vorschaubild ist kein Upload-Fehler."""
    token = access_token()
    daten = bild_pfad.read_bytes()
    typ = "image/png" if bild_pfad.suffix.lower() == ".png" else "image/jpeg"
    req = urllib.request.Request(
        f"{THUMBNAIL_URL}?videoId={urllib.parse.quote(video_id)}",
        data=daten, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": typ,
                 "Content-Length": str(len(daten))})
    try:
        with urllib.request.urlopen(req, timeout=60):
            pass
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Thumbnail-Setzen fehlgeschlagen ({e.code}): {detail}") from e
