# Script seguro para colar sua chave do Groq SEM ela aparecer no terminal.
# Uso:  & "C:\Users\Thiago Henrique\OneDrive\Documentos\curriculo\assetia\colar-chave-groq.ps1"

$key = Read-Host "Cole sua chave do Groq (formato gsk_..., vai aparecer como ****)" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
$plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if (-not $plain -or $plain.Length -lt 10) {
    Write-Host "[X] Chave invalida ou vazia." -ForegroundColor Red
    exit 1
}
if (-not $plain.StartsWith("gsk_")) {
    Write-Host "[!] AVISO: a chave nao comeca com 'gsk_'. Confira em https://console.groq.com/keys" -ForegroundColor Yellow
}

$envPath = "C:\Users\Thiago Henrique\OneDrive\Documentos\curriculo\assetia\.env"
$lines = Get-Content $envPath
$novas = @()
$foundGroq = $false; $foundProvider = $false
foreach ($l in $lines) {
    if ($l -like "GROQ_API_KEY=*") { $novas += "GROQ_API_KEY=$plain"; $foundGroq = $true }
    elseif ($l -like "LLM_PROVIDER=*") { $novas += "LLM_PROVIDER=groq"; $foundProvider = $true }
    elseif ($l -like "GEMINI_API_KEY=*") { $novas += "GEMINI_API_KEY=" }  # zera a do Gemini
    else { $novas += $l }
}
if (-not $foundGroq) { $novas += "GROQ_API_KEY=$plain" }
if (-not $foundProvider) { $novas += "LLM_PROVIDER=groq" }
$novas | Out-File -FilePath $envPath -Encoding ASCII

$plain = $null
[GC]::Collect()

Write-Host ""
Write-Host "[OK] Chave do Groq salva! Provider forcado para 'groq'." -ForegroundColor Green
Write-Host "    Me responde 'configurei' no chat para eu reiniciar o backend." -ForegroundColor Cyan
