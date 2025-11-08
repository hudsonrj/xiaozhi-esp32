#!/bin/bash
# Script para executar o MCP Portal da Transparência localmente

export PORTAL_API_KEY="${PORTAL_API_KEY:-2c56919ba91b8c1b13473dcef43fb031}"

# Executar o servidor MCP
cd "$(dirname "$0")"
node server.js

