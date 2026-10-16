"""Run the AMPscript in an email against test data, without Marketing Cloud.

    python tools/ampscript_run.py                     run every case in tests/ampscript/cases.json
    python tools/ampscript_run.py my-copy.html        run the same cases against another file
    python tools/ampscript_run.py --previews          also rewrite previews/ from the cases marked "preview"
    python tools/ampscript_run.py --demo              only render one email per hotelier in tests/ampscript/demo/
                                                      (edit hoteliers.csv and properties.csv there; no checks)
    python tools/ampscript_run.py --csv               also write the cases as CSV files to import into
                                                      Marketing Cloud, for the same test there

AMPscript only runs inside Salesforce Marketing Cloud, and there is no free sandbox. This script
executes the part of the language this email uses, so the logic can be tested on any PC:

  - VAR, SET, IF / ELSEIF / ELSE / ENDIF, FOR ... TO ... DO / NEXT (its counter must not be declared), comments
  - inline output (%%=v(@x)=%%) and personalisation strings (%%field%%)
  - the functions in FUNCS below. Anything else stops with an error, so an invented
    or misspelt function is caught instead of silently printing nothing.

It is strict on purpose: Row() past the last row, Field() with an unknown column, a lookup on a data
extension that does not exist, and a personalisation string with no matching column all stop with an
error. Salesforce's documentation says the last one fails the send; the others are assumptions I could
not test in Marketing Cloud.

shortcut: it imitates documented behaviour, it is not Marketing Cloud. Formatting details
(numbers, dates, character encoding) can differ. The final check is Preview and Test inside
Marketing Cloud with a test data extension built from the same cases.
"""
import json
import re
import sys
from contextlib import redirect_stdout
from html import unescape
from io import StringIO
from pathlib import Path
from unicodedata import normalize

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
sys.dont_write_bytecode = True   # no __pycache__ folder appearing in the submission
import preflight  # noqa: E402  (the same checks as before a test send)

# Marketing Cloud fills these in itself at send time; here they get placeholder links.
SYSTEM_STRINGS = {"subscription_center_url", "unsub_center_url", "view_email_url", "emailname_"}


class AmpError(Exception):
    pass


# ---------------------------------------------------------------- reading the file
TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|\d+(?:\.\d+)?|@\w+|[A-Za-z_]\w*|==|!=|>=|<=|[><=(),]')


def items(source):
    """The file as a flat list: ('text', s), ('out', tokens), ('tok', token)."""
    out, pos = [], 0
    for m in re.finditer(r"%%\[(.*?)\]%%|%%=(.*?)=%%|%%(\w+)%%", source, flags=re.S):
        out.append(("text", source[pos:m.start()]))
        block, inline, name = m.groups()
        if block is not None:
            code = re.sub(r"/\*.*?\*/", " ", block, flags=re.S)
            leftover = TOKEN.sub(" ", code).strip()
            if leftover:
                raise AmpError(f"cannot read {leftover[:20]!r} in a code block")
            out += [("tok", t) for t in TOKEN.findall(code)]
        elif inline is not None:
            out.append(("out", TOKEN.findall(inline)))
        else:
            out.append(("pers", name))
        pos = m.end()
    out.append(("text", source[pos:]))
    return out


class Parser:
    """Turns the item list into a tree of statements."""

    def __init__(self, its):
        self.its, self.i, self.declared = its, 0, set()

    def peek(self):
        it = self.its[self.i] if self.i < len(self.its) else ("end", None)
        return it[1].upper() if it[0] == "tok" else None

    def take(self, expected=None):
        kind, val = self.its[self.i]
        if kind != "tok" or (expected and val.upper() != expected):
            raise AmpError(f"expected {expected or 'code'}, found {val!r}")
        self.i += 1
        return val

    def body(self, stop=()):
        nodes = []
        while self.i < len(self.its):
            kind, val = self.its[self.i]
            if kind != "tok":
                self.i += 1
                if kind == "out":
                    nodes.append(("out", Parser([("tok", t) for t in val]).expr()))
                else:
                    nodes.append((kind, val))
                continue
            word = val.upper()
            if word in stop:
                return nodes
            self.i += 1
            if word == "VAR":
                while self.peek() and self.peek().startswith("@"):
                    self.declared.add(self.take().lower())
                    if self.peek() == ",":
                        self.take()
            elif word == "SET":
                name = self.take()
                self.take("=")
                nodes.append(("set", name.lower(), self.expr()))
            elif word == "IF":
                branches, cond = [], self.expr()
                self.take("THEN")
                while True:
                    branches.append((cond, self.body(("ELSEIF", "ELSE", "ENDIF"))))
                    nxt = self.take().upper()
                    if nxt == "ELSEIF":
                        cond = self.expr()
                        self.take("THEN")
                    elif nxt == "ELSE":
                        branches.append((None, self.body(("ENDIF",))))
                        self.take("ENDIF")
                        break
                    else:
                        break
                nodes.append(("if", branches))
            elif word == "FOR":
                var = self.take().lower()
                if var in self.declared:
                    # Salesforce's AMPscript reference (Language Elements): declaring a FOR counter with VAR
                    # "will result in a validation or runtime error".
                    raise AmpError(f"FOR counter {var} was declared with VAR; Marketing Cloud rejects that")
                self.take("=")
                start = self.expr()
                self.take("TO")
                end = self.expr()
                self.take("DO")
                loop = self.body(("NEXT",))
                self.take("NEXT")
                if self.peek() and self.peek().lower() == var:
                    self.take()
                nodes.append(("for", var, start, end, loop))
            else:
                raise AmpError(f"unexpected {val!r}")
        if stop:
            raise AmpError(f"missing {' or '.join(stop)}")
        return nodes

    # expressions: OR < AND < NOT < comparison < value
    def expr(self):
        left = self.and_()
        while self.peek() == "OR":
            self.take()
            left = ("or", left, self.and_())
        return left

    def and_(self):
        left = self.not_()
        while self.peek() == "AND":
            self.take()
            left = ("and", left, self.not_())
        return left

    def not_(self):
        if self.peek() == "NOT":
            self.take()
            return ("not", self.not_())
        left = self.value()
        if self.peek() in ("==", "!=", ">", "<", ">=", "<="):
            return ("cmp", self.take(), left, self.value())
        return left

    def value(self):
        tok = self.take()
        if tok[0] in "\"'":
            return ("lit", tok[1:-1])
        if tok[0].isdigit():
            return ("lit", float(tok) if "." in tok else int(tok))
        if tok.startswith("@"):
            return ("var", tok.lower())
        if tok == "(":
            inner = self.expr()
            self.take(")")
            return inner
        if tok.upper() in ("TRUE", "FALSE"):
            return ("lit", tok.upper() == "TRUE")
        self.take("(")
        args = []
        while self.peek() != ")":
            args.append(self.expr())
            if self.peek() == ",":
                self.take()
        self.take(")")
        return ("call", tok.lower(), args)


# ---------------------------------------------------------------- running it
def text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def number(v):
    try:
        return float(text(v))
    except ValueError:
        return None


def compare(op, a, b):
    x, y = number(a), number(b)
    if x is None or y is None:   # not both numbers: compare as text, ignoring case
        x, y = text(a).lower(), text(b).lower()
    return {"==": x == y, "!=": x != y, ">": x > y, "<": x < y, ">=": x >= y, "<=": x <= y}[op]


def lookup_ordered_rows(ctx, de, count, order, field, value):
    if de not in ctx["des"]:
        raise AmpError(f"data extension {de!r} does not exist")
    rows = [r for r in ctx["des"][de] if text(r.get(field)).lower() == text(value).lower()]
    col, _, direction = order.partition(" ")
    # Marketing Cloud sorts in SQL Server, where A-umlaut sits next to A. Python would put it after Z,
    # so accents are folded away for the sort.
    # shortcut: approximates the default collation; for exact order, compare with a real preview.
    fold = lambda v: normalize("NFKD", text(v)).encode("ascii", "ignore").decode().lower()
    rows.sort(key=lambda r: fold(r.get(col)), reverse=direction.strip().upper() == "DESC")
    return rows[:2000 if int(count) < 1 else min(int(count), 2000)]   # below 1 = all, up to 2,000 (docs)


def row(rows, i):
    if not 1 <= int(i) <= len(rows):
        raise AmpError(f"Row() asked for row {i} of {len(rows)}")
    return rows[int(i) - 1]


def field(r, name):
    if name not in r:
        raise AmpError(f"Field() asked for unknown column {name!r}")
    return r[name]


FUNCS = {
    "v": lambda ctx, x: x,
    "attributevalue": lambda ctx, name: ctx["subscriber"].get(name),
    "empty": lambda ctx, x: text(x) == "",
    "concat": lambda ctx, *xs: "".join(text(x) for x in xs),
    "trim": lambda ctx, x: text(x).strip(),
    "lookuporderedrows": lookup_ordered_rows,
    "rowcount": lambda ctx, rows: len(rows),
    "row": lambda ctx, rows, i: row(rows, i),
    "field": lambda ctx, r, name: field(r, name),
    "add": lambda ctx, a, b: number(a) + number(b),
    "subtract": lambda ctx, a, b: number(a) - number(b),
    "redirectto": lambda ctx, url: url,
}


def evaluate(node, ctx):
    kind = node[0]
    if kind == "lit":
        return node[1]
    if kind == "var":
        return ctx["vars"].get(node[1])
    if kind == "not":
        return not evaluate(node[1], ctx)
    if kind == "and":
        return evaluate(node[1], ctx) and evaluate(node[2], ctx)
    if kind == "or":
        return evaluate(node[1], ctx) or evaluate(node[2], ctx)
    if kind == "cmp":
        return compare(node[1], evaluate(node[2], ctx), evaluate(node[3], ctx))
    if node[1] not in FUNCS:
        raise AmpError(f"unknown function {node[1]}()")
    return FUNCS[node[1]](ctx, *[evaluate(a, ctx) for a in node[2]])


def run(nodes, ctx, out):
    for node in nodes:
        kind = node[0]
        if kind == "text":
            out.append(node[1])
        elif kind == "out":
            out.append(text(evaluate(node[1], ctx)))
        elif kind == "pers":
            name = node[1]
            if name in SYSTEM_STRINGS:
                out.append(f"https://example.invalid/{name}")
            elif name in ctx["subscriber"]:
                out.append(text(ctx["subscriber"][name]))
            else:
                raise AmpError(f"personalisation string %%{name}%% has no column")
        elif kind == "set":
            ctx["vars"][node[1]] = evaluate(node[2], ctx)
        elif kind == "if":
            for cond, body in node[1]:
                if cond is None or evaluate(cond, ctx):
                    run(body, ctx, out)
                    break
        elif kind == "for":
            start, end = int(number(evaluate(node[2], ctx))), int(number(evaluate(node[3], ctx)))
            for i in range(start, end + 1):
                ctx["vars"][node[1]] = i
                run(node[4], ctx, out)


def render(source, subscriber, des):
    ctx = {"subscriber": subscriber, "des": des, "vars": {}}
    out = []
    run(Parser(items(source)).body(), ctx, out)
    return "".join(out)


# ---------------------------------------------------------------- the test cases
def visible_text(html):
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<(style|title)[^>]*>.*?</\1>", " ", html, flags=re.S)
    # unescape: a German template writes &uuml;, the reader (and the test) sees u-umlaut.
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def check_case(case, html):
    problems = []
    words = visible_text(html)
    for s in case.get("expect", []):
        if s not in words:
            problems.append(f"missing: {s!r}")
    for s in case.get("forbid", []):
        if s in words:
            problems.append(f"should not appear: {s!r}")
    # Same order as listed, e.g. the property rates.
    positions = [words.find(s) for s in case.get("expect_in_order", [])]
    if -1 in positions or positions != sorted(positions):
        problems.append(f"not in this order: {case['expect_in_order']}")
    if "%%" in html:
        problems.append("AMPscript left in the output")
    size = len(html.encode("utf-8"))
    if size > preflight.GMAIL_CLIP_BYTES:
        problems.append(f"{size:,} bytes: Gmail would clip it")
    # The template's own checks, on the finished email. Data may contain characters such as
    # u-umlaut; Marketing Cloud encodes those at send time, so only the template is held to ASCII.
    ascii_html = "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in html)
    tmp = PROJECT / "tests" / "ampscript" / "out" / "_check.html"
    tmp.write_text(ascii_html, encoding="utf-8")
    report = StringIO()
    with redirect_stdout(report):
        ok = preflight.check(str(tmp))
    tmp.unlink()
    if not ok:
        problems += [l.strip() for l in report.getvalue().splitlines() if "FAIL" in l]
    return problems


def write_csv(data, folder):
    """One CSV per data extension: the subscribers (one row per case) and each lookup table."""
    import csv
    # A sendable data extension needs a subscriber key and an address: the case name, and yours.
    subs = [{"SubscriberKey": c["name"], "EmailAddress": "", **c["subscriber"]} for c in data["cases"] if "data_extensions" not in c]
    tables = {"RateConnect_Test_Sendable": subs, **data["data_extensions"]}
    for name, rows in tables.items():
        columns = list(dict.fromkeys(k for r in rows for k in r))
        with open(folder / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, columns)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {name}.csv ({len(rows)} rows)")


def render_demo(source):
    """--demo: one finished email per hotelier in tests/ampscript/demo/hoteliers.csv, using the properties in
    tests/ampscript/demo/properties.csv. The two files are laid out like the Marketing Cloud data extensions,
    so they open in Excel; add rows or change names there and run again."""
    import csv
    folder = PROJECT / "tests" / "ampscript" / "demo"
    read = lambda name: list(csv.DictReader(open(folder / name, encoding="utf-8-sig", newline="")))
    hoteliers, properties = read("hoteliers.csv"), read("properties.csv")
    out = folder / "out"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.html"):
        old.unlink()
    for h in hoteliers:
        key = h.pop("SubscriberKey")
        html = render(source, h, {"RateConnect_Properties": properties})
        (out / f"{key}.html").write_text(html, encoding="utf-8")
        print(f"wrote demo/out/{key}.html  ({h.get('hotelier_name') or 'no name'}, {sum(p['hotelier_id'] == h.get('hotelier_id') for p in properties)} properties)")


def main():
    if "--demo" in sys.argv:
        return render_demo((PROJECT / "email-ampscript.html").read_text(encoding="utf-8"))
    write_previews = "--previews" in sys.argv
    cases_file = PROJECT / "tests" / "ampscript" / "cases.json"
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    # A file name on the command line tests that file (e.g. a practice copy) instead of the template.
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    source = Path(files[0] if files else PROJECT / data["template"]).read_text(encoding="utf-8")
    out_dir = PROJECT / "tests" / "ampscript" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    if "--csv" in sys.argv:
        write_csv(data, PROJECT / "tests" / "ampscript")

    failed = 0
    for case in data["cases"]:
        try:
            html = render(source, case["subscriber"], case.get("data_extensions", data["data_extensions"]))
            problems = check_case(case, html)
            (out_dir / f"{case['name']}.html").write_text(html, encoding="utf-8")
            if write_previews and case.get("preview"):
                (PROJECT / "previews" / case["preview"]).write_text(html, encoding="utf-8")
        except AmpError as error:
            problems = [f"AMPscript error: {error}"]
        if case.get("expect_error"):
            hit = any(case["expect_error"] in p for p in problems)
            problems = [] if hit else [f"expected an error containing {case['expect_error']!r}"]
        failed += bool(problems)
        print(f"{'PASS' if not problems else 'FAIL'}  {case['name']}: {case['about']}")
        for p in problems:
            print(f"      {p}")
    print(f"\n{len(data['cases']) - failed} of {len(data['cases'])} cases pass. Outputs: tests/ampscript/out/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
