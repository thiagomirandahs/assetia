# Coletor de eventos de SEGURANCA do Windows -> ReconIA SOC.
# Uso (de preferencia como Administrador, p/ ler o log de Security):
#   .\coletor-winevent.ps1 -ApiBase http://localhost:8000 -Minutos 60
# Roteie de novo a cada X min (Agendador de Tarefas) p/ ter um feed continuo.

param(
  [string]$ApiBase = "http://localhost:8000",
  [string]$Email = "admin@example.com",
  [string]$Senha = "demo123",
  [int]$Minutos = 60,
  [int]$Max = 100
)

$login = Invoke-RestMethod "$ApiBase/api/auth/login" -Method Post -ContentType 'application/json' -Body (@{email=$Email; senha=$Senha} | ConvertTo-Json)
$tok = $login.access_token

$desde = (Get-Date).AddMinutes(-$Minutos)
$evts = Get-WinEvent -FilterHashtable @{ LogName = 'Security'; StartTime = $desde } -MaxEvents $Max -ErrorAction SilentlyContinue
if (-not $evts) { Write-Host "Nenhum evento de Security no periodo (rodar como Admin?)." -ForegroundColor Yellow; exit }

$lote = @()
foreach ($e in $evts) {
  $sev = if ($e.Id -eq 4625 -or $e.LevelDisplayName -eq 'Error') { 'warning' } else { 'info' }
  $lote += @{
    fonte = 'windows'
    host = $env:COMPUTERNAME
    severidade = $sev
    mensagem = (($e.Message -split "`r?`n")[0])
    ts = $e.TimeCreated.ToString('o')
  }
}

$json = $lote | ConvertTo-Json -Depth 4
if ($lote.Count -eq 1) { $json = "[$json]" }  # garante array p/ a API

Invoke-RestMethod "$ApiBase/api/soc/ingest" -Method Post -ContentType 'application/json' -Headers @{ Authorization = "Bearer $tok" } -Body $json | Out-Null
Write-Host "[OK] $($lote.Count) eventos enviados ao SOC." -ForegroundColor Green
