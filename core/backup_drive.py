"""Daily backup of the whole database to the owner's Google Drive.

Why not a Google "service account": a service account has no Drive storage of its own, so Google
refuses uploads into a normal Gmail Drive folder. Instead a tiny Google Apps Script (run as the
owner, free) receives the backup and saves it in the owner's own Drive. Set in Render, Environment:
  BACKUP_SCRIPT_URL   the web-app address of the Apps Script
  BACKUP_SECRET       the same secret word written inside the Apps Script
"""
import base64
import gzip
import json
import os
import tempfile
import urllib.request
from datetime import date

from django.core.management import call_command

from .schedule_models import ReportSendLog

SKIP = [
    "contenttypes", "sessions", "admin.logentry", "auth.permission",
    "core.loginthrottle", "core.activityphoto",
]
MAX_BYTES = 30 * 1024 * 1024  # Apps Script accepts roughly 50 MB per request


def is_configured():
    return bool(os.environ.get("BACKUP_SCRIPT_URL") and os.environ.get("BACKUP_SECRET"))


def _dump_gz(*labels, exclude=None):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        call_command("dumpdata", *labels, exclude=exclude or [], output=path, verbosity=0)
        with open(path, "rb") as f:
            return gzip.compress(f.read(), compresslevel=6)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _upload(name, blob):
    body = json.dumps({
        "token": os.environ["BACKUP_SECRET"],
        "name": name,
        "data": base64.b64encode(blob).decode("ascii"),
    }).encode("utf-8")
    req = urllib.request.Request(
        os.environ["BACKUP_SCRIPT_URL"], data=body,
        headers={"content-type": "text/plain;charset=utf-8"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        reply = resp.read().decode("utf-8", "replace")
    try:
        data = json.loads(reply)
    except ValueError:
        return False, "Unexpected reply from the backup script: %s" % reply[:150]
    return bool(data.get("ok")), data.get("error", "")


def run_backup(force=False):
    today = date.today().isoformat()
    key = "backup-%s" % today
    if not force and ReportSendLog.objects.filter(key=key, ok=True).exists():
        return "already done today"
    if not is_configured():
        return "not set up (BACKUP_SCRIPT_URL / BACKUP_SECRET missing)"
    notes, ok = [], True
    try:
        data_blob = _dump_gz(exclude=SKIP)
        if len(data_blob) > MAX_BYTES:
            raise ValueError("data backup is too large for the Drive script (%d MB)" % (len(data_blob) // 1048576))
        good, err = _upload("promis-data-%s.json.gz" % today, data_blob)
        ok = ok and good
        notes.append("data %s KB%s" % (len(data_blob) // 1024, "" if good else " FAILED: " + err))
        del data_blob
        photo_blob = _dump_gz("core.ActivityPhoto")
        if len(photo_blob) > MAX_BYTES:
            notes.append("photos skipped (%d MB is too large)" % (len(photo_blob) // 1048576))
        else:
            good, err = _upload("promis-photos-%s.json.gz" % today, photo_blob)
            ok = ok and good
            notes.append("photos %s KB%s" % (len(photo_blob) // 1024, "" if good else " FAILED: " + err))
    except Exception as exc:
        ok = False
        notes.append("error: %s" % str(exc)[:200])
    obj, _ = ReportSendLog.objects.get_or_create(key=key, defaults={"kind": "backup"})
    obj.kind, obj.label, obj.ok, obj.note = "backup", "Backup to Google Drive", ok, "; ".join(notes)[:300]
    obj.save()
    return "done: " + "; ".join(notes) if ok else "failed: " + "; ".join(notes)
