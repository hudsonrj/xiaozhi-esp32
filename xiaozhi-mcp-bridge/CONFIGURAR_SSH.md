# Configurar Autenticação SSH sem Senha

## Problema
A aplicação não consegue inserir senha interativamente. É necessário configurar autenticação por chave SSH.

## Solução: Configurar Chave SSH

### Passo 1: Gerar Chave SSH (se não tiver)

```bash
ssh-keygen -t ed25519 -C "xiaozhi-bridge"
```

Pressione Enter para usar o local padrão e escolha uma senha (ou deixe vazio).

### Passo 2: Copiar Chave para o Servidor

```bash
ssh-copy-id -p 4422 allied@100.124.250.21
```

**OU manualmente:**

```bash
# Copiar conteúdo da chave pública
type $env:USERPROFILE\.ssh\id_ed25519.pub

# Depois, no servidor, executar:
# ssh allied@100.124.250.21 -p 4422
# mkdir -p ~/.ssh
# echo "SUA_CHAVE_PUBLICA_AQUI" >> ~/.ssh/authorized_keys
# chmod 600 ~/.ssh/authorized_keys
# chmod 700 ~/.ssh
```

### Passo 3: Testar Conexão sem Senha

```bash
ssh -p 4422 allied@100.124.250.21 "echo OK"
```

Se não pedir senha, está configurado corretamente!

### Passo 4: Executar Aplicação

```bash
python main.py
```

## Alternativa: Usar sshpass (não recomendado para produção)

Se não puder configurar chave SSH, pode usar `sshpass`:

1. Instalar sshpass (Windows):
   - Baixar de: https://github.com/keimpx/sshpass-win32
   - Ou usar WSL

2. Atualizar código para usar sshpass (não implementado ainda)

**Recomendação**: Use autenticação por chave SSH - é mais seguro e prático.

