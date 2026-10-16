"""Send one or more of the HTML files to real inboxes for render testing.

    python tools/send_test.py email.html you@example.com you@example.org      (your own addresses)
    python tools/send_test.py "tests/ampscript/demo/out/*.html" you@example.com      (several files, one login)

Why a script: pasting HTML into a mail client's compose window does not work as a test. The client
rewrites the markup on the way out (Outlook runs it through Word, Gmail strips the stylesheet), so
you would be testing the sender, not the email. SMTP sends the file byte for byte.

It sends through Gmail's SMTP server and needs a Google "app password" (Google Account > Security >
2-Step Verification > App passwords). Both prompts are typed at run time; nothing is saved.
"""
import getpass
import glob
import re
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


def check(path, html, checked):
    """Stop before sending anything that would arrive broken."""
    local_images = re.findall(r'<img[^>]+src="(?!https://)([^"]+)"', html)
    if local_images:
        sys.exit(f"Not sending {path}: {len(local_images)} image(s) are not absolute https URLs, e.g. {local_images[0]}.\n"
                 "They would arrive broken. Host the images first.")
    # A hosted image that is not uploaded yet looks exactly like a mail-app bug, so check every one loads.
    urls = sorted(set(re.findall(r'(?:src|background)="(https://[^"]+)"', html) + re.findall(r"url\('?(https://[^')]+)'?\)", html)) - checked)
    checked.update(urls)   # several files share the same images: check each URL once
    missing = []
    for url in urls:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15) as response:
                if response.status != 200:
                    missing.append(f"{response.status}  {url}")
        except Exception as error:
            missing.append(f"{error}  {url}")
    if missing:
        sys.exit(f"Not sending {path}: these images do not load. Upload them first.\n  " + "\n  ".join(missing)
                 + "\nJust uploaded them? GitHub can keep serving the old 'not found' for up to 5 minutes. Wait and run this again.")
    if "%%[" in html or "%%=" in html:
        print(f"Note: {path} contains AMPscript. Outside Marketing Cloud it arrives as raw text.")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    # PowerShell does not expand *.html itself, so patterns are expanded here.
    args = [m for a in sys.argv[1:] for m in (sorted(glob.glob(a)) if "*" in a else [a])]
    files = [a for a in args if a.lower().endswith(".html")]
    recipients = [a for a in args if "@" in a]
    unknown = [a for a in args if a not in files and a not in recipients]
    if unknown:
        sys.exit(f"Not an .html file or an email address: {unknown[0]} (a pattern that matched no file looks like this too).\n{__doc__}")
    if not files or not recipients:
        sys.exit(__doc__)
    pages = [(f, open(f, encoding="utf-8").read()) for f in files]
    checked = set()
    for f, html in pages:
        check(f, html, checked)

    sender = input("Gmail address to send from: ").strip()
    password = getpass.getpass("App password (hidden): ").replace(" ", "")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(sender, password)
        for f, html in pages:
            title = re.search(r"<title>(.*?)</title>", html, flags=re.S)
            # With several files, the file name tells the test emails apart in the inbox.
            name = f" ({Path(f).stem})" if len(pages) > 1 else ""
            subject = f"[TEST] {title.group(1).strip() if title else f}{name}"
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = subject, sender, ", ".join(recipients)
            msg["Date"], msg["Message-ID"] = formatdate(localtime=True), make_msgid()
            # A plain-text part first, then the HTML: mail clients show the last part they can render,
            # and a message with both parts is less likely to be treated as spam.
            msg.set_content("This is an HTML email render test. Open it in a client that shows HTML.")
            msg.add_alternative(html, subtype="html")
            smtp.send_message(msg)
            print(f"Sent '{subject}' to {len(recipients)} address(es).")


if __name__ == "__main__":
    main()
