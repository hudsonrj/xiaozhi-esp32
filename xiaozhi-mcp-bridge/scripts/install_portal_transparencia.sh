#!/bin/bash
# Script para instalar o MCP Portal da Transparência no servidor

set -e

echo "=== Instalando MCP Portal da Transparência ==="

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não encontrado. Instalando Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "✅ Node.js versão: $(node --version)"
echo "✅ npm versão: $(npm --version)"

# Criar diretório para o MCP Portal da Transparência
MCP_DIR="$HOME/mcp_portal_transparencia"
mkdir -p "$MCP_DIR"
cd "$MCP_DIR"

echo "📦 Instalando pacote mcp-portal-transparencia-brasil..."

# Instalar globalmente ou localmente
if [ "$1" == "global" ]; then
    sudo npm install -g mcp-portal-transparencia-brasil
    MCP_CMD="mcp-portal-transparencia-brasil"
else
    npm install mcp-portal-transparencia-brasil
    MCP_CMD="$MCP_DIR/node_modules/.bin/mcp-portal-transparencia-brasil"
fi

# Criar script de execução
cat > "$MCP_DIR/run_mcp_portal.sh" << 'EOF'
#!/bin/bash
# Script para executar o MCP Portal da Transparência

export PORTAL_API_KEY="${PORTAL_API_KEY:-2c56919ba91b8c1b13473dcef43fb031}"

# Executar o servidor MCP
if command -v mcp-portal-transparencia-brasil &> /dev/null; then
    mcp-portal-transparencia-brasil
elif [ -f "$HOME/mcp_portal_transparencia/node_modules/.bin/mcp-portal-transparencia-brasil" ]; then
    "$HOME/mcp_portal_transparencia/node_modules/.bin/mcp-portal-transparencia-brasil"
else
    npx -y mcp-portal-transparencia-brasil
fi
EOF

chmod +x "$MCP_DIR/run_mcp_portal.sh"

echo "✅ Instalação concluída!"
echo ""
echo "📝 Configuração:"
echo "   Diretório: $MCP_DIR"
echo "   Script: $MCP_DIR/run_mcp_portal.sh"
echo "   API Key: configurada no script (pode ser sobrescrita via env)"
echo ""
echo "🧪 Teste a instalação:"
echo "   cd $MCP_DIR && ./run_mcp_portal.sh"

