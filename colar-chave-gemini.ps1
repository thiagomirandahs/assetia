# Cola sua chave do Google Gemini no .env SEM ela aparecer no terminal.
# Uso (dentro da pasta do projeto):  .\colar-chave-gemini.ps1
# A chave entra mascarada como ****. Pega a sua em: https://aistudio.google.com/apikey

$key = Read-Host "Cole sua chave do Gemini (formato AIza..., vai aparecer como ****)" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
$plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if (-not $plain -or $plain.Length -lt 20) {
    Write-Host "[X] Chave invalida ou vazia." -ForegroundColor Red
    exit 1
}
if (-not $plain.StartsWith("AIza")) {
    Write-Host "[!] AVISO: a chave nao comeca com 'AIza'. Confira em https://aistudio.google.com/apikey" -ForegroundColor Yellow
}

# .env fica na mesma pasta deste script (portatil entre maquinas)
$envPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "[X] .env nao encontrado em $envPath" -ForegroundColor Red
    exit 1
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
$lines = [System.IO.File]::ReadAllText($envPath, $utf8) -split "`r?`n"
$novas = @(); $foundKey = $false; $foundProvider = $false
foreach ($l in $lines) {
    if ($l -like "GEMINI_API_KEY=*")   { $novas += "GEMINI_API_KEY=$plain"; $foundKey = $true }
    elseif ($l -like "LLM_PROVIDER=*")  { $novas += "LLM_PROVIDER=gemini";  $foundProvider = $true }
    else { $novas += $l }
}
if (-not $foundKey)      { $novas += "GEMINI_API_KEY=$plain" }
if (-not $foundProvider) { $novas += "LLM_PROVIDER=gemini" }
[System.IO.File]::WriteAllText($envPath, ($novas -join "`n"), $utf8)

$plain = $null
[GC]::Collect()

Write-Host ""
Write-Host "[OK] Chave do Gemini salva no .env! Provider forcado para 'gemini'." -ForegroundColor Green
Write-Host "    Reinicie o backend (Ctrl+C e suba de novo) ou me avise no chat." -ForegroundColor Cyan
