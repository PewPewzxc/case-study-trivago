"""Pre-flight checks for the email HTML files.

Run before every test send:

    python tools/preflight.py email.html email-ampscript.html

It catches the mistakes that are easy to make and hard to see in a browser preview:
broken conditional comments, images that only exist on this machine, unbalanced AMPscript,
and anything that would get the message clipped or its styles stripped by Gmail.
Exit code is 1 if any check fails, so it can also run in CI.
"""
import re
import sys
from html.parser import HTMLParser

GMAIL_CLIP_BYTES = 102 * 1024      # Gmail hides everything after ~102 KB behind "View entire message"
GMAIL_STYLE_CHARS = 8192           # Gmail drops a <style> block longer than this
VOID = {"meta", "img", "br", "hr", "link", "input"}
# Tags whose nesting we verify. <p> inside <td> etc. is covered; inline tags are included because
# an unclosed <a> or <span> silently restyles everything after it in some clients.
TRACKED = {"html", "head", "body", "table", "tr", "td", "th", "p", "h1", "h2", "h3", "a", "span", "div", "strong", "em", "style", "title"}


class Balance(HTMLParser):
    """Collects tags and reports nesting errors with line numbers."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.imgs, self.tables, self.links = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if tag == "img":
            self.imgs.append((line, a))
        if tag == "table":
            self.tables.append((line, a))
        if tag == "a":
            self.links.append((line, a))
        if tag in TRACKED and tag not in VOID:
            self.stack.append((tag, line))

    def handle_endtag(self, tag):
        if tag not in TRACKED:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: </{tag}> with nothing open")
            return
        open_tag, open_line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(f"line {self.getpos()[0]}: </{tag}> closes <{open_tag}> opened on line {open_line}")


def keep_lines(m):
    """Replacement for a removed span: its newlines only, so reported line numbers match the file."""
    return "\n" * m.group(0).count("\n")


def strip_ampscript(text):
    """Remove AMPscript so the HTML parser only sees markup. Returns (html, problems)."""
    problems = []
    blocks = re.findall(r"%%\[(.*?)\]%%", text, flags=re.S)
    code = "\n".join(re.sub(r"/\*.*?\*/", "", b, flags=re.S) for b in blocks)   # comments removed
    code = re.sub(r'"[^"]*"', '""', code)                                        # string literals removed
    count = lambda word: len(re.findall(rf"\b{word}\b", code, flags=re.I))
    if text.count("%%[") != text.count("]%%"):
        problems.append(f"AMPscript block delimiters unbalanced: {text.count('%%[')} opening, {text.count(']%%')} closing")
    # Word boundaries mean "IF" does not match inside ELSEIF, ENDIF or IIF, so each IF needs exactly one ENDIF.
    ifs, endifs = count("IF"), count("ENDIF")
    if ifs != endifs:
        problems.append(f"AMPscript IF/ENDIF unbalanced: {ifs} IF, {endifs} ENDIF")
    fors, nexts = count("FOR"), count("NEXT")
    if fors != nexts:
        problems.append(f"AMPscript FOR/NEXT unbalanced: {fors} FOR, {nexts} NEXT")
    if re.search(r"=%%%", text):
        problems.append("three percent signs in a row after an inline expression: build the % with Concat() instead")
    # Blank out the [if !mso] markers first (same length, so line numbers hold). The "<!-->" inside the
    # opener otherwise looks like the start of a comment that runs to the closer and swallows real markup.
    plain = text.replace("<!--[if !mso]><!-->", " " * 19).replace("<!--<![endif]-->", " " * 16)
    for m in re.finditer(r"<!--(?!\[if)(.*?)-->", plain, flags=re.S):
        if "%%" in m.group(1):
            line = plain.count("\n", 0, m.start()) + 1
            problems.append(f"line {line}: double-percent syntax inside an HTML comment (Marketing Cloud will evaluate it)")
    html = re.sub(r"%%\[.*?\]%%", keep_lines, text, flags=re.S)
    html = re.sub(r"%%=.*?=%%", lambda m: "x" + keep_lines(m), html, flags=re.S)
    return html, problems


def check(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    fails, warns = [], []

    # --- size and encoding -------------------------------------------------------------------
    if len(raw) > GMAIL_CLIP_BYTES:
        fails.append(f"{len(raw)} bytes: over Gmail's ~102 KB clipping limit")
    non_ascii = sorted({c for c in text if ord(c) > 127})
    if non_ascii:
        fails.append(f"non-ASCII characters {non_ascii}: write them as HTML entities so a wrong charset cannot corrupt them")
    head = raw[:1024].lower()
    if b"<!doctype html>" in head and b"charset" not in head:
        fails.append("no charset declaration in the first 1024 bytes")

    # --- conditional comments ----------------------------------------------------------------
    for m in re.finditer(r"<!--\[if mso[^\]]*\]>(.*?)<!\[endif\]-->", text, flags=re.S):
        if "<!--" in m.group(1) or "-->" in m.group(1):
            line = text.count("\n", 0, m.start()) + 1
            fails.append(f"line {line}: HTML comment inside an [if mso] block ends the block early for every other client")
    if text.count("<!--[if !mso]><!-->") != text.count("<!--<![endif]-->"):
        fails.append("[if !mso] openers and closers do not match")
    opens = len(re.findall(r"<!--\[if (?:gte )?mso[^\]]*\]>", text))
    closes = len(re.findall(r"(?<!<!--)<!\[endif\]-->", text))
    if opens != closes:
        fails.append(f"[if mso] blocks unbalanced: {opens} opened, {closes} closed")

    # --- embedded stylesheet -----------------------------------------------------------------
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, flags=re.S):
        css = m.group(1)
        if len(css) > GMAIL_STYLE_CHARS:
            fails.append(f"<style> block is {len(css)} characters: Gmail drops blocks over {GMAIL_STYLE_CHARS}")
        if css.count("{") != css.count("}"):
            fails.append("unbalanced braces in a <style> block: Gmail discards the whole block")

    # --- AMPscript, then markup --------------------------------------------------------------
    html, amp_problems = strip_ampscript(text)
    fails += amp_problems
    # What Outlook sees and what everyone else sees are two different documents; check the non-Outlook one.
    visible = re.sub(r"<!--\[if !mso\]><!-->|<!--<!\[endif\]-->", "", html)
    visible = re.sub(r"<!--.*?-->", keep_lines, visible, flags=re.S)
    p = Balance()
    p.feed(visible)
    fails += p.errors
    fails += [f"<{t}> opened on line {l} is never closed" for t, l in p.stack]

    for line, a in p.imgs:
        src = a.get("src", "")
        if "alt" not in a:
            fails.append(f"img {src}: missing alt attribute")
        if not a.get("width") or not a.get("height"):
            fails.append(f"img {src}: missing width/height attribute (Outlook falls back to the file's pixel size)")
        if not src.startswith("https://"):
            warns.append(f"img {src}: not an absolute https URL, so it only loads on this machine")
    for line, a in p.tables:
        if a.get("role") != "presentation":
            fails.append(f"a <table> without role=\"presentation\": screen readers will announce it as a data table")
    for line, a in p.links:
        href = a.get("href", "")
        if href in ("", "#") or href.startswith("javascript"):
            fails.append(f"link with empty or dead href: {href!r}")
    if not re.search(r"<html[^>]*\slang=", text):
        fails.append("no lang attribute on <html>")
    if "<title>" not in text:
        fails.append("no <title>")

    print(f"\n{path}  ({len(raw):,} bytes, {len(p.imgs)} images, {len(p.links)} links, {len(p.tables)} tables)")
    for w in warns:
        print(f"  WARN  {w}")
    for f in fails:
        print(f"  FAIL  {f}")
    if not fails:
        print("  PASS" + ("  (with warnings)" if warns else ""))
    return not fails


if __name__ == "__main__":
    files = sys.argv[1:] or ["email.html", "email-ampscript.html"]
    results = [check(f) for f in files]      # run every file even if an earlier one fails
    sys.exit(0 if all(results) else 1)
