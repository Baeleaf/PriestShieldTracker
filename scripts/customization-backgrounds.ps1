param([Parameter(Mandatory=$true)][string]$OutputDirectory, [Parameter(Mandatory=$true)][string]$StagesPath)
Add-Type -AssemblyName System.Drawing
$stages = Get-Content -LiteralPath $StagesPath -Raw | ConvertFrom-Json
$brandFont = New-Object System.Drawing.Font('Segoe UI', 20, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$titleFont = New-Object System.Drawing.Font('Segoe UI', 18, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$smallFont = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$muted = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(164,159,177))
for ($i = 0; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $bitmap = New-Object System.Drawing.Bitmap(680,230)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::FromArgb(12,11,17))
    $accent = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($stage.accent))
    $graphics.FillRectangle($accent,20,20,3,26)
    $graphics.DrawString('SoulShield',$brandFont,[System.Drawing.Brushes]::White,32,19)
    $caption = $stage.style + ' / ' + $stage.palette
    $size = $graphics.MeasureString($caption,$titleFont)
    $graphics.DrawString($caption,$titleFont,$accent,658-$size.Width,21)
    $graphics.DrawString('Options > AddOns > SoulShield',$smallFont,$muted,20,207)
    $graphics.DrawString('Sample values',$smallFont,$muted,573,207)
    $bitmap.Save((Join-Path $OutputDirectory ('background-{0}.png' -f $i)),[System.Drawing.Imaging.ImageFormat]::Png)
    $accent.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
}
$brandFont.Dispose(); $titleFont.Dispose(); $smallFont.Dispose(); $muted.Dispose()
