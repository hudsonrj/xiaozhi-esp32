# Script PowerShell para parar a Bridge
# Uso: .\stop_bridge.ps1

Write-Host "Parando Xiaozhi MCP Bridge..." -ForegroundColor Yellow

$processes = Get-Process python -ErrorAction SilentlyContinue
if ($processes) {
    foreach ($proc in $processes) {
        try {
            Stop-Process -Id $proc.Id -Force
            Write-Host "Processo Python (PID: $($proc.Id)) parado" -ForegroundColor Green
        } catch {
            Write-Host "Erro ao parar processo $($proc.Id): $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "Nenhum processo Python encontrado" -ForegroundColor Yellow
}

