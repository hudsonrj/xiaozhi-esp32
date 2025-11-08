# Integração ApeRAG MCP

Este documento explica como o servidor MCP do ApeRAG foi integrado à bridge.

## Estrutura

- **Servidor MCP HTTP**: `https://rag.apecloud.com/mcp/`
  - Implementa protocolo JSON-RPC 2.0 via HTTP/HTTPS
  - Autenticação via Bearer Token
  - Collection: conhecimento

- **Cliente MCP HTTP**: `src/mcp_client_http.py`
  - Implementa cliente MCP para servidores HTTP/HTTPS
  - Usa `aiohttp` para requisições assíncronas
  - Suporta autenticação Bearer Token e headers customizados

- **Bridge Multi-MCP**: `src/bridge_multi.py`
  - Agrega ferramentas de múltiplos servidores MCP (SSH, local e HTTP)
  - Roteia `tools/call` para o servidor correto baseado no nome da ferramenta
  - Intercepta `tools/list` para retornar ferramentas agregadas

## Configuração

O arquivo `config/config.yaml` foi atualizado para incluir o ApeRAG:

```yaml
mcp_servers:
  # Servidor ApeRAG (HTTP/HTTPS)
  - name: "aperag-mcp"
    url: "https://rag.apecloud.com/mcp/"
    api_key: "sk-51e8f3895c7746588d38d26dac50eb2f"
    headers:
      Authorization: "Bearer sk-51e8f3895c7746588d38d26dac50eb2f"
    # Collection: conhecimento
```

## Como Funciona

1. **Inicialização**: A bridge conecta ao servidor ApeRAG via HTTP
2. **Autenticação**: Usa Bearer Token no header Authorization
3. **Listagem de Ferramentas**: Quando o agente solicita `tools/list`, a bridge:
   - Busca ferramentas de todos os servidores MCP (incluindo ApeRAG)
   - Adiciona prefixo `aperag-mcp_` às ferramentas do ApeRAG
   - Retorna lista agregada de todas as ferramentas
4. **Chamada de Ferramentas**: Quando o agente chama uma ferramenta `aperag-mcp_*`:
   - A bridge identifica que é do ApeRAG pelo prefixo
   - Remove o prefixo e envia a requisição para o servidor ApeRAG
   - Retorna a resposta para o agente

## Ferramentas Disponíveis

As ferramentas do ApeRAG serão automaticamente descobertas quando o bridge iniciar. Elas aparecerão com o prefixo `aperag-mcp_` na lista de ferramentas disponíveis.

## Dependências

Foi adicionada a dependência `aiohttp>=3.9.0` ao `requirements.txt` para suportar requisições HTTP assíncronas.

## Instalação

Para instalar as dependências atualizadas:

```bash
pip install -r requirements.txt
```

## Teste

Para testar a integração:

1. Inicie o bridge:
   ```bash
   python main.py
   ```

2. Verifique os logs para confirmar que o ApeRAG foi conectado:
   ```
   Conectando ao servidor MCP via HTTP: https://rag.apecloud.com/mcp/
   Conectado ao servidor MCP HTTP com sucesso
   Servidor MCP conectado e inicializado: aperag-mcp
   ```

3. As ferramentas do ApeRAG devem aparecer na lista de ferramentas disponíveis quando o agente solicitar `tools/list`.

## Notas

- O cliente HTTP não mantém uma conexão persistente como SSH/STDIO
- Cada requisição é uma chamada HTTP POST independente
- O timeout padrão é de 30 segundos por requisição
- A autenticação é feita via Bearer Token no header Authorization

