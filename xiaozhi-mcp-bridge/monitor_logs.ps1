# monitor_logs.ps1
# Monitora logs da bridge filtrando apenas mensagens importantes

Write-Host "Monitorando logs da bridge (Ctrl+C para parar)..." -ForegroundColor Cyan
Write-Host "Procurando por: tools/call, execute_select, list_tables, Proxy, Resposta, ERROR" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Gray

Get-Content bridge.log -Wait -Tail 50 | Where-Object {
    $_ -match "tools/call|execute_select|list_tables|list_schemas|describe_table|count_records|get_table_sample|Proxy|Resposta|ERROR|tools/list|initialize" -or
    $_ -match "Mensagem recebida do servidor.*method" -or
    $_ -match "Mensagem enviada ao servidor MCP"
} | ForEach-Object {
    $timestamp = if ($_ -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})") { $matches[1] } else { "" }
    
    if ($_ -match "ERROR") {
        Write-Host "$timestamp ❌ $_" -ForegroundColor Red
    } elseif ($_ -match "tools/call|execute_select|list_tables|list_schemas") {
        Write-Host "$timestamp 🔧 $_" -ForegroundColor Green
    } elseif ($_ -match "Proxy Cloud -> Local|Proxy Local -> Cloud") {
        Write-Host "$timestamp 🔄 $_" -ForegroundColor Cyan
    } elseif ($_ -match "Resposta enviada") {
        Write-Host "$timestamp ✅ $_" -ForegroundColor Yellow
    } else {
        Write-Host "$timestamp ℹ️  $_" -ForegroundColor White
    }
}

