@echo off
REM Script para executar o MCP Portal da Transparência localmente no Windows

set PORTAL_API_KEY=%PORTAL_API_KEY%
if "%PORTAL_API_KEY%"=="" set PORTAL_API_KEY=2c56919ba91b8c1b13473dcef43fb031

cd /d "%~dp0"
node server.js

