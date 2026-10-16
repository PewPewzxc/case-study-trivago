"""Run the AMPscript test cases through Salesforce Labs' AMPscript Core engine as a second opinion.

    python tools/ampscript_core_check.py path/to/ampscript-0.0.6.vsix

ampscript_run.py was written from the same reading of the docs as the email, so it can share its blind
spots. AMPscript Core is an independent, open-source AMPscript engine from Salesforce Labs (the VS Code
extension listed in Salesforce's AMPscript docs). It is not Marketing Cloud either, and it is partial.

Needs: the .vsix from https://github.com/SalesforceLabs/ampscript-core/releases (0.0.6 tested) and the
.NET 8 and ASP.NET Core 8 runtimes. Writes each rendered email to tests/ampscript/core/.

The engine runs a test copy with two changes, each for a gap in the engine, not in the email:
  1. LookupOrderedRows() becomes LookupRows(); the engine has no LookupOrderedRows(). The CSV rows are
     written in A to Z order, so the result is the same rows in the same order.
  2. IF @moreCount > 0 becomes IF @propertyCount > @listedCount (the same condition). The engine crashes
     when it compares a Subtract() result with a number ("Unable to cast Double to Decimal").
Every subscriber also gets all four sendable columns, empty where the case has no value, because a data
extension row always has every column (the engine prints a missing one as raw text).
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
sys.dont_write_bytecode = True
import ampscript_run as runner  # noqa: E402

PORT = 5077
CHANGES = [('LookupOrderedRows(@propertiesDE, 0, "property_name ASC", "hotelier_id", @hotelierId)',
            'LookupRows(@propertiesDE, "hotelier_id", @hotelierId)'),
           ("IF @moreCount > 0 THEN", "IF @propertyCount > @listedCount THEN")]
SENDABLE = ["hotelier_id", "hotelier_name", "property_name", "commission_rate"]
SYSTEM = ["subscription_center_url", "unsub_center_url"]   # not supported by the engine yet


def engine_folder(vsix):
    """Unpack only the engine (the extension's node_modules paths are too long for Windows)."""
    folder = Path(tempfile.gettempdir()) / Path(vsix).stem
    if not (folder / "extension/.Sage/Sage.Webhost.dll").exists():
        with zipfile.ZipFile(vsix) as z:
            z.extractall(folder, [n for n in z.namelist() if n.startswith("extension/.Sage/")])
    return folder / "extension/.Sage"


def render(engine, folder):
    """Start the engine on folder/email.ampscript, fetch the page once, stop it. Returns (status, body)."""
    log = open(folder / "host.log", "w")
    host = subprocess.Popen(["dotnet", str(engine / "Sage.Webhost.dll"), "ampscript", "--source", str(folder / "email.ampscript")],
                            cwd=folder, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "ASPNETCORE_URLS": f"http://127.0.0.1:{PORT}"})
    try:
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=30) as r:
                    return r.status, r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                return e.code, ""
            except OSError:
                time.sleep(1)
        return 0, ""
    finally:
        host.kill()
        host.wait()
        log.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    engine = engine_folder(sys.argv[1])
    source = (PROJECT / "email-ampscript.html").read_text(encoding="utf-8")
    test_copy = source
    for old, new in CHANGES:
        assert test_copy.count(old) == 1, f"not found once in email-ampscript.html: {old}"
        test_copy = test_copy.replace(old, new)

    data = json.loads((PROJECT / "tests/ampscript/cases.json").read_text(encoding="utf-8"))
    out_dir = PROJECT / "tests/ampscript/core"
    out_dir.mkdir(exist_ok=True)
    failed = 0
    for case in data["cases"]:
        des = case.get("data_extensions", data["data_extensions"])
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "DataExtensions").mkdir()
            (folder / "email.ampscript").write_text(test_copy, encoding="utf-8")
            subscriber = {**{c: "" for c in SENDABLE}, **case["subscriber"]}
            (folder / "subscriber.json").write_text(json.dumps(subscriber, ensure_ascii=False), encoding="utf-8")
            for name, rows in des.items():
                rows = sorted(rows, key=lambda r: runner.normalize("NFKD", runner.text(r.get("property_name")))
                              .encode("ascii", "ignore").decode().lower())   # the same A to Z as the runner
                with open(folder / "DataExtensions" / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, list(dict.fromkeys(k for r in rows for k in r)))
                    w.writeheader()
                    w.writerows(rows)
            status, html = render(engine, folder)
        for name in SYSTEM:
            html = html.replace(f"%%{name}%%", f"https://example.invalid/{name}")
        try:
            ours, ours_error = runner.render(source, case["subscriber"], des), ""
        except runner.AmpError as error:
            ours, ours_error = "", str(error)

        if case.get("expect_error"):
            ok = status != 200 and ours_error
            verdict = "both stop with an error" if ok else f"engine returned {status}, runner: {ours_error or 'no error'}"
        elif status != 200:
            ok, verdict = False, f"engine failed (HTTP {status})"
        else:
            (out_dir / f"{case['name']}.html").write_text(html, encoding="utf-8")
            problems = runner.check_case(case, html)
            same = runner.visible_text(html) == runner.visible_text(ours)
            ok = same and not problems
            verdict = ("same text as the runner" if same else "TEXT DIFFERS from the runner") + \
                      ("" if not problems else "; " + "; ".join(problems))
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {case['name']}: {verdict}")
    print(f"\n{len(data['cases']) - failed} of {len(data['cases'])} cases agree. Outputs: tests/ampscript/core/")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
