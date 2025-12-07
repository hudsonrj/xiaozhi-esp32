# Integra├º├úo Notion MCP

Este documento explica como o servidor MCP do Notion foi integrado ├á bridge.

## Estrutura

- **Servidor MCP Local**: `mcp_notion/server.py`
  - Implementa protocolo JSON-RPC 2.0 via STDIO
  - Fornece 8 ferramentas para gerenciar p├íginas no database "Notas"
  - API Key configurada no c├│digo ou via vari├ível de ambiente `NOTION_API_KEY`

- **Bridge Multi-MCP**: `src/bridge_multi.py`
  - Agrega ferramentas de m├║ltiplos servidores MCP
  - Roteia `tools/call` para o servidor correto baseado no nome da ferramenta

## Configura├º├úo

### 1. API Key

A API Key deve ser configurada via vari├ível de ambiente:
```bash
export NOTION_API_KEY="sua-api-key-aqui"
```

**IMPORTANTE**: Nunca commite a API Key no c├│digo. Use sempre vari├íveis de ambiente ou arquivo `.env`.

### 2. Database "Notas"

O servidor procura automaticamente por um database chamado "Notas". Se n├úo encontrar, voc├¬ pode:

1. **Listar todos os databases**: Use `notion_list_databases`
2. **Configurar manualmente**: Use `notion_set_database_id` com o ID do database "Notas"

### 3. Instalar Depend├¬ncias

```bash
pip install notion-client>=2.2.1
```

Ou reinstale todas as depend├¬ncias:
```bash
pip install -r requirements.txt
```

## Ferramentas Dispon├¡veis

### Notion (8 ferramentas)

1. **`notion_search_pages`** - Busca p├íginas no database "Notas" por texto
2. **`notion_list_pages`** - Lista todas as p├íginas do database "Notas"
3. **`notion_get_page`** - Obt├®m detalhes completos de uma p├ígina espec├¡fica
4. **`notion_create_page`** - Cria uma nova p├ígina no database "Notas"
5. **`notion_update_page`** - Atualiza uma p├ígina existente
6. **`notion_delete_page`** - Arquiva (deleta) uma p├ígina
7. **`notion_list_databases`** - Lista todos os databases dispon├¡veis
8. **`notion_set_database_id`** - Configura o ID do database "Notas" manualmente

## Como Funciona

1. **Buscar p├íginas**: Use `notion_search_pages` com uma query de texto
2. **Criar p├íginas**: Use `notion_create_page` com t├¡tulo e conte├║do
3. **Listar p├íginas**: Use `notion_list_pages` para ver todas as p├íginas

## Database "Notas"

O servidor procura automaticamente por um database chamado "Notas". 

**Para confirmar se ├® o database correto:**
1. Use `notion_list_databases` para listar todos os databases
2. Procure por um database com nome "Notas" ou similar
3. Se necess├írio, use `notion_set_database_id` para configurar o ID correto

## Exemplos de Uso

### Buscar p├íginas
```json
{
  "name": "notion_search_pages",
  "arguments": {
    "query": "reuni├úo"
  }
}
```

### Criar p├ígina
```json
{
  "name": "notion_create_page",
  "arguments": {
    "title": "Nova Nota",
    "content": "Conte├║do da nota aqui"
  }
}
```

### Listar p├íginas
```json
{
  "name": "notion_list_pages",
  "arguments": {
    "page_size": 50
  }
}
```

## Troubleshooting

### Erro: "Database 'Notas' n├úo encontrado"
- Use `notion_list_databases` para ver todos os databases dispon├¡veis
- Use `notion_set_database_id` para configurar o ID do database "Notas"

### Erro: "API Key inv├ílida"
- Verifique se a API Key est├í correta
- Certifique-se de que a integra├º├úo do Notion est├í habilitada no seu workspace

### Erro ao criar p├ígina
- Verifique se o database "Notas" existe
- Verifique se a API Key tem permiss├Áes para criar p├íginas no database

## Links ├Üteis

- **Documenta├º├úo Notion API**: https://developers.notion.com/
- **Biblioteca Python**: https://github.com/ramnes/notion-sdk-py


