# Renders an email through Microsoft Word, the engine classic Outlook uses, to tools\word-render\<name>.png.
# The simulator shows that PNG under the classic Outlook light preview. Light mode only: Word here follows the Office theme.
#
#   powershell -ExecutionPolicy Bypass -File tools\word_render.ps1 email.html
param([Parameter(Mandatory = $true)][string]$Html)

$src  = (Resolve-Path $Html).Path
$name = [IO.Path]::GetFileNameWithoutExtension($src)
$out  = Join-Path $PSScriptRoot 'word-render'
New-Item -ItemType Directory -Force $out | Out-Null
$pdf = Join-Path $env:TEMP "word-render-$name.pdf"
$png = Join-Path $out "$name.png"

# shortcut: Word hangs at the PDF export when driven straight from this script, but not from a background job
# (cause not found on 15 Oct 2026). The job also gives a timeout, so a stuck Word can never block forever.
$job = Start-Job -ArgumentList $src, $pdf -ScriptBlock {
    param($src, $pdf)
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0                                 # no dialogs
    try {
        $doc = $word.Documents.Open($src, $false, $true)    # no conversion prompt, read-only
        $ps = $doc.PageSetup
        # 720px page (540pt) with 10px margins leaves the 700px the email's Outlook wrapper uses; tallest page Word allows.
        $ps.PageWidth = 540; $ps.PageHeight = 1584
        $ps.LeftMargin = 7.5; $ps.RightMargin = 7.5; $ps.TopMargin = 7.5; $ps.BottomMargin = 7.5
        $doc.ExportAsFixedFormat($pdf, 17)                  # 17 = PDF
        $doc.Close($false)
    } finally {
        $word.Quit()
    }
}
if (-not (Wait-Job $job -Timeout 120)) {
    Get-CimInstance Win32_Process -Filter "Name='WINWORD.EXE'" | Where-Object CommandLine -like '*Automation*' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    throw 'Word did not finish within 2 minutes.'
}
Receive-Job $job
Remove-Job $job -Force
if (-not (Test-Path $pdf)) { throw 'Word did not write the PDF.' }

# Pages stacked into one image, 1 CSS pixel per pixel (96 dpi).
$py = @'
import sys, pymupdf
src = pymupdf.open(sys.argv[1])
w = src[0].rect.width
h = sum(p.rect.height for p in src)
out = pymupdf.open()
page = out.new_page(width=w, height=h)
y = 0
for p in src:
    page.show_pdf_page(pymupdf.Rect(0, y, w, y + p.rect.height), src, p.number)
    y += p.rect.height
# Cut the empty page below the email: keep down to the lowest thing Word drew, plus a 10px margin.
# Skip shadings (Word logs them as endless) and zero-size marks such as the empty last paragraph.
bottom = max(r[3] for kind, r in page.get_bboxlog() if kind != 'fill-shade' and r[2] > r[0] and r[3] > r[1])
page.get_pixmap(dpi=96, clip=pymupdf.Rect(0, 0, w, min(h, bottom + 7.5))).save(sys.argv[2])
'@
$tmp = Join-Path $out 'stack.py'
Set-Content -Path $tmp -Value $py -Encoding ASCII
python -I $tmp $pdf $png
$failed = $LASTEXITCODE
Remove-Item $tmp, $pdf
if ($failed) { throw 'Turning the PDF into a PNG failed (see the Python error above).' }
Write-Output "Word render: $png"

