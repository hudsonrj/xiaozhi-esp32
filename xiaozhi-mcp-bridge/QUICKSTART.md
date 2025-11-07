# Quick Start Guide

## Instalação Rápida

1. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

2. **Configurar:**
```bash
cp config/config.example.yaml config/config.yaml
# Edite config/config.yaml com suas credenciais
```

3. **Testar componentes básicos:**
```bash
python test_basic.py
```

4. **Executar:**
```bash
python main.py
```

## Configuração Mínima

Edite `config/config.yaml`:

```yaml
xiaozhi:
  websocket_url: "wss://api.xiaozhi.me/mcp/"
  token: "SEU_TOKEN_AQUI"

mcp_local:
  ssh_host: "10.60.254.6"
  ssh_user: "allied"
  ssh_command: "/home/allied/AlliedIT_DW/mcp_server/run_mcp.sh"
```

## Verificação de Conexão SSH

Antes de executar, teste a conexão SSH:

```bash
ssh allied@10.60.254.6 "echo OK"
```

Se pedir senha, configure chave SSH:

```bash
ssh-copy-id allied@10.60.254.6
```

## Logs

Os logs aparecem no console e são salvos em `bridge.log` (ou conforme configurado).

## Parar a Aplicação

Pressione `Ctrl+C` para parar graciosamente.

