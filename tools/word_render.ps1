# Renders an email through Microsoft Word, the engine classic Outlook uses, to tools\word-render\<name>.png.
# The simulator shows that PNG under the classic Outlook light preview. Light mode only: Word here follows the Office theme.
#
#   powershell -ExecutionPolicy Bypass -File tools\word_render.ps1 email.html
param([Parameter(Mandatory = $true)][string]$Html)

$src  = (Resolve-Path $Html).Path
$name = [IO.Path]::GetFileNameWithoutExtension($src)
$out  = Join-Path $PSScriptRoot 'word-render'
New-Item -ItemType Directory -Force $out | Out-Null
$pdf = Join-Path $out "$name.pdf"
$png = Join-Path $out "$name.png"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
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
page.get_pixmap(dpi=96).save(sys.argv[2])
'@
$tmp = Join-Path $out 'stack.py'
Set-Content -Path $tmp -Value $py -Encoding ASCII
python -I $tmp $pdf $png
Remove-Item $tmp
Write-Output "Word render: $png"
