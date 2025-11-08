# Script PowerShell para instalar MCP Portal da Transparência via SSH

param(
    [string]$SshHost = "100.124.250.21",
    [int]$SshPort = 4422,
    [string]$SshUser = "allied",
    [string]$ApiKey = "2c56919ba91b8c1b13473dcef43fb031"
)

Write-Host "=== Instalando MCP Portal da Transparência no servidor ===" -ForegroundColor Cyan

# Ler senha SSH
$sshPassword = $env:SSH_PASSWORD
if (-not $sshPassword) {
    $sshPassword = Read-Host "Digite a senha SSH" -AsSecureString
    $sshPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sshPassword))
}

# Criar script de instalação temporário
$installScript = @"
#!/bin/bash
set -e

echo "=== Instalando MCP Portal da Transparência ==="

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "Node.js não encontrado. Instalando..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node.js: \$(node --version)"
echo "npm: \$(npm --version)"

# Criar diretório
MCP_DIR="\$HOME/mcp_portal_transparencia"
mkdir -p "\$MCP_DIR"
cd "\$MCP_DIR"

# Instalar pacote
echo "Instalando mcp-portal-transparencia-brasil..."
npm install mcp-portal-transparencia-brasil

# Criar script de execução
cat > "\$MCP_DIR/run_mcp_portal.sh" << 'SCRIPTEOF'
#!/bin/bash
export PORTAL_API_KEY="${ApiKey}"
cd "\$HOME/mcp_portal_transparencia"
node_modules/.bin/mcp-portal-transparencia-brasil
SCRIPTEOF

chmod +x "\$MCP_DIR/run_mcp_portal.sh"

echo "✅ Instalação concluída!"
echo "Script: \$MCP_DIR/run_mcp_portal.sh"
"@

# Salvar script temporário
$tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
$installScript | Out-File -FilePath $tempScript -Encoding UTF8

Write-Host "📤 Enviando script de instalação para o servidor..." -ForegroundColor Yellow

# Usar plink (PuTTY) ou sshpass se disponível, ou criar conexão SSH com senha
# Como estamos no Windows, vamos usar uma abordagem diferente
Write-Host "⚠️  Execute manualmente no servidor ou use um cliente SSH com suporte a senha" -ForegroundColor Yellow
Write-Host ""
Write-Host "Script de instalação salvo em: $tempScript" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para instalar manualmente, execute no servidor:" -ForegroundColor Green
Write-Host "  ssh -p $SshPort $SshUser@$SshHost" -ForegroundColor White
Write-Host "  # Depois cole o conteúdo do script acima" -ForegroundColor Gray

# Mostrar o script
Write-Host "`n=== CONTEÚDO DO SCRIPT ===" -ForegroundColor Cyan
Write-Host $installScript

