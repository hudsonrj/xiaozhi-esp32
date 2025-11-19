# Script para monitorar logs de busca na collection
Write-Host "🔍 Monitorando logs do bridge para requisições de busca..." -ForegroundColor Cyan
Write-Host "Pressione Ctrl+C para parar`n" -ForegroundColor Yellow

$logFile = "bridge.log"
$keywords = @(
    "collection",
    "Collection", 
    "converter",
    "Convertido",
    "search_collection",
    "Conhecimento",
    "Verificando collection_id",
    "Roteando tools/call",
    "Collection ID",
    "parece ser um nome",
    "ERRO",
    "ERROR",
    "erro",
    "error"
)

if (Test-Path $logFile) {
    Get-Content $logFile -Wait -Tail 50 | ForEach-Object {
        $line = $_
        foreach ($keyword in $keywords) {
            if ($line -match $keyword) {
                $timestamp = if ($line -match "^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}") {
                    $matches[0]
                } else {
                    "N/A"
                }
                
                # Destacar linhas importantes
                if ($line -match "Convertido|parece ser um nome|Verificando collection_id") {
                    Write-Host "[$timestamp] $line" -ForegroundColor Green
                } elseif ($line -match "ERRO|ERROR|erro|error|Collection not found") {
                    Write-Host "[$timestamp] $line" -ForegroundColor Red
                } elseif ($line -match "Roteando tools/call|search_collection") {
                    Write-Host "[$timestamp] $line" -ForegroundColor Yellow
                } else {
                    Write-Host "[$timestamp] $line" -ForegroundColor White
                }
                break
            }
        }
    }
} else {
    Write-Host "Arquivo $logFile não encontrado. Aguardando criação..." -ForegroundColor Yellow
    while (-not (Test-Path $logFile)) {
        Start-Sleep -Seconds 2
    }
    Write-Host "Arquivo encontrado! Iniciando monitoramento..." -ForegroundColor Green
    Get-Content $logFile -Wait -Tail 50 | ForEach-Object {
        $line = $_
        foreach ($keyword in $keywords) {
            if ($line -match $keyword) {
                Write-Host $line
                break
            }
        }
    }
}

