#!/usr/bin/env python3
"""
mail_bus.py — bus de agentes por correo, sin Postgres ni MCP SSE compartidos.

Lee INBOX por IMAP, guarda cada correo nuevo como JSON en mailbox/inbox/,
y permite responder por SMTP siguiendo docs/EMAIL_PROTOCOL.md.

Config via variables de entorno (nunca hardcodeadas ni committeadas):
    MAIL_IMAP_HOST, MAIL_IMAP_USER, MAIL_IMAP_PASS
    MAIL_SMTP_HOST, MAIL_SMTP_USER, MAIL_SMTP_PASS
    MAIL_SMTP_PORT (default 587), MAIL_IMAP_PORT (default 993)

Uso:
    python mail_bus.py poll          # lee correos nuevos no vistos, los guarda
    python mail_bus.py send --to X --subject "[REPORT #id] ..." --body-file f.txt
"""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.header import decode_header
from pathlib import Path

MAILBOX_DIR = Path(__file__).resolve().parent.parent / "mailbox"
INBOX_DIR = MAILBOX_DIR / "inbox"
SENT_DIR = MAILBOX_DIR / "sent"


def _env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise SystemExit(f"Falta variable de entorno requerida: {name}")
    return val


def _decode(raw) -> str:
    if raw is None:
        return ""
    parts = decode_header(raw)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def poll() -> int:
    """Lee correos no vistos, los persiste como JSON, los marca vistos."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    host = _env("MAIL_IMAP_HOST")
    user = _env("MAIL_IMAP_USER")
    pw = _env("MAIL_IMAP_PASS")
    port = int(os.environ.get("MAIL_IMAP_PORT", "993"))

    saved = 0
    with imaplib.IMAP4_SSL(host, port) as imap:
        imap.login(user, pw)
        imap.select("INBOX")
        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            print(f"IMAP search fallo: {status}", file=sys.stderr)
            return 0
        ids = data[0].split()
        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = _decode(msg.get("Subject"))
            sender = _decode(msg.get("From"))
            date = msg.get("Date")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(
                                part.get_content_charset() or "utf-8",
                                errors="replace",
                            )
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(
                        msg.get_content_charset() or "utf-8", errors="replace"
                    )

            record = {
                "received_at_utc": datetime.now(timezone.utc).isoformat(),
                "from": sender,
                "subject": subject,
                "date_header": date,
                "body": body,
            }
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            out_path = INBOX_DIR / f"{ts}_{msg_id.decode()}.json"
            out_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            saved += 1
            print(f"guardado: {out_path}")
    return saved


def send(to: str, subject: str, body: str) -> None:
    """Envia un correo siguiendo el formato de docs/EMAIL_PROTOCOL.md."""
    SENT_DIR.mkdir(parents=True, exist_ok=True)
    host = _env("MAIL_SMTP_HOST")
    user = _env("MAIL_SMTP_USER")
    pw = _env("MAIL_SMTP_PASS")
    port = int(os.environ.get("MAIL_SMTP_PORT", "587"))

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, pw)
        smtp.send_message(msg)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    record = {
        "sent_at_utc": datetime.now(timezone.utc).isoformat(),
        "to": to,
        "subject": subject,
        "body": body,
    }
    (SENT_DIR / f"{ts}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"enviado a {to}: {subject}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("poll", help="Lee correos nuevos y los guarda como JSON")

    p_send = sub.add_parser("send", help="Envia un correo")
    p_send.add_argument("--to", required=True)
    p_send.add_argument("--subject", required=True)
    p_send.add_argument("--body-file", required=True, help="Archivo de texto plano con el cuerpo")

    args = parser.parse_args()

    if args.cmd == "poll":
        n = poll()
        print(f"Total nuevos: {n}")
    elif args.cmd == "send":
        body = Path(args.body_file).read_text(encoding="utf-8")
        send(args.to, args.subject, body)


if __name__ == "__main__":
    main()
