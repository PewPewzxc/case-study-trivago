"""Send one of the HTML files to real inboxes for render testing.

    python tools/send_test.py email.html me@gmail.com me@outlook.com me@icloud.com

Why a script: pasting HTML into a mail client's compose window does not work as a test. The client
rewrites the markup on the way out (Outlook runs it through Word, Gmail strips the stylesheet), so
you would be testing the sender, not the email. SMTP sends the file byte for byte.

It sends through Gmail's SMTP server and needs a Google "app password" (Google Account > Security >
2-Step Verification > App passwords). Both prompts are typed at run time; nothing is saved.
"""
import getpass
import re
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, recipients = sys.argv[1], sys.argv[2:]
    html = open(path, encoding="utf-8").read()

    local_images = re.findall(r'<img[^>]+src="(?!https://)([^"]+)"', html)
    if local_images:
        sys.exit(f"Not sending: {len(local_images)} image(s) are not absolute https URLs, e.g. {local_images[0]}.\n"
                 "They would arrive broken. Host the images first.")
    # A hosted image that is not uploaded yet looks exactly like a mail-app bug, so check every one loads.
    urls = sorted(set(re.findall(r'(?:src|background)="(https://[^"]+)"', html) + re.findall(r"url\('?(https://[^')]+)'?\)", html)))
    missing = []
    for url in urls:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15) as response:
                if response.status != 200:
                    missing.append(f"{response.status}  {url}")
        except Exception as error:
            missing.append(f"{error}  {url}")
    if missing:
        sys.exit("Not sending: these images do not load. Upload them first.\n  " + "\n  ".join(missing)
                 + "\nJust uploaded them? GitHub can keep serving the old 'not found' for up to 5 minutes. Wait and run this again.")
    if "%%[" in html or "%%=" in html:
        print("Note: this file contains AMPscript. Outside Marketing Cloud it arrives as raw text.")

    title = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    subject = f"[TEST] {title.group(1).strip() if title else path}"

    sender = input("Gmail address to send from: ").strip()
    password = getpass.getpass("App password (hidden): ").replace(" ", "")

    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, ", ".join(recipients)
    msg["Date"], msg["Message-ID"] = formatdate(localtime=True), make_msgid()
    # A plain-text part first, then the HTML: mail clients show the last part they can render,
    # and a message with both parts is less likely to be treated as spam.
    msg.set_content("This is an HTML email render test. Open it in a client that shows HTML.")
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)
    print(f"Sent '{subject}' to {len(recipients)} address(es).")


if __name__ == "__main__":
    main()
