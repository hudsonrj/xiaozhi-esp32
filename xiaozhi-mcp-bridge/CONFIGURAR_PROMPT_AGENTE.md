# Como Configurar o Prompt do Agente para Usar Ferramentas MCP

## Problema

O endpoint MCP está "Online" e as ferramentas estão disponíveis, mas o agente diz que não tem acesso ou não pode responder.

## Solução: Configurar o System Prompt do Agente

Você precisa adicionar instruções no **System Prompt** ou **Instructions** do agente para que ele saiba usar as ferramentas MCP disponíveis.

### Passo 1: Encontrar a Configuração do Prompt

Na interface do xiaozhi.me, procure por:
- **"System Prompt"**
- **"Instructions"** 
- **"Agent Instructions"**
- **"Prompt"** ou **"Custom Instructions"**

Geralmente está em:
- Configurações do Agente → Advanced Settings → System Prompt
- Ou na página principal do agente

### Passo 2: Adicionar Instruções sobre as Ferramentas MCP

Adicione o seguinte texto no System Prompt do agente:

```
Você tem acesso a um Data Warehouse (DW) através de ferramentas MCP. Use essas ferramentas para consultar informações sobre tickets, empresas, SLA e outros dados do DW.

Ferramentas disponíveis:
- list_schemas: Lista todos os schemas do banco de dados DW
- list_tables: Lista todas as tabelas de um schema específico
- describe_table: Descreve a estrutura de uma tabela (colunas, tipos, etc.)
- list_views: Lista todas as views de um schema
- execute_select: Executa uma query SELECT no banco de dados
- count_records: Conta o número de registros em uma tabela
- get_table_sample: Obtém uma amostra dos dados de uma tabela
- list_datamarts: Lista todos os datamarts disponíveis
- describe_datamart: Descreve um datamart específico

Quando o usuário perguntar sobre tickets, empresas, SLA ou qualquer informação do DW:
1. Use as ferramentas MCP apropriadas para consultar os dados
2. Sempre use as ferramentas quando necessário - você TEM acesso a elas
3. Se não souber qual schema ou tabela usar, primeiro liste os schemas disponíveis
4. Depois liste as tabelas do schema relevante
5. Use execute_select para consultas específicas ou get_table_sample para ver exemplos

Exemplos de como usar:
- Para ver tickets: use list_tables no schema apropriado, depois execute_select ou get_table_sample
- Para ver empresas: use list_tables e procure por tabelas relacionadas a empresas
- Para ver SLA: use list_tables e procure por tabelas relacionadas a SLA

IMPORTANTE: Você TEM acesso a essas ferramentas. Sempre use-as quando o usuário perguntar sobre dados do DW.
```

### Passo 3: Versão Mais Simples (se a anterior for muito longa)

Se o prompt acima for muito longo, use esta versão mais curta:

```
Você tem acesso a ferramentas MCP para consultar um Data Warehouse. Use as ferramentas list_schemas, list_tables, execute_select, count_records e get_table_sample para responder perguntas sobre tickets, empresas, SLA e outros dados do DW. SEMPRE use essas ferramentas quando necessário - você TEM acesso a elas.
```

### Passo 4: Salvar e Testar

1. **Salve** as configurações do agente
2. **Limpe a memória** do agente (botão "Clear Memory") para aplicar as novas instruções
3. **Teste** fazendo uma pergunta como:
   - "Liste os schemas disponíveis no DW"
   - "Quais tabelas temos sobre tickets?"
   - "Quantos tickets temos no total?"

## Verificar se Está Funcionando

Você pode monitorar os logs da bridge para ver se o agente está chamando as ferramentas:

```powershell
# Ver logs em tempo real
Get-Content bridge.log -Wait -Tail 20

# Procurar por chamadas de ferramentas
Get-Content bridge.log | Select-String -Pattern "tools/call|execute_select|list_tables"
```

Quando o agente usar uma ferramenta, você verá mensagens como:
- `Proxy Cloud -> Local: tools/call`
- `Mensagem enviada ao servidor MCP: {"method": "execute_select", ...}`

## Dicas Adicionais

1. **Se o agente ainda não usar as ferramentas:**
   - Tente ser mais específico nas perguntas: "Use a ferramenta list_schemas para listar os schemas"
   - Verifique se o modelo LLM suporta function calling (Qwen3 235B deve suportar)

2. **Se aparecer erro ao chamar ferramentas:**
   - Verifique os logs da bridge para ver o erro específico
   - Certifique-se de que a bridge está rodando: `.\status_bridge.ps1`

3. **Para ver todas as ferramentas disponíveis:**
   - Na interface do MCP Endpoint, você já vê a lista de "Enabled Services"
   - Essas são as ferramentas que o agente pode usar

## Exemplo de Prompt Completo

Se quiser um prompt mais detalhado e contextualizado:

```
Você é um assistente especializado em análise de dados de um Data Warehouse (DW). Você tem acesso direto ao DW através de ferramentas MCP.

FERRAMENTAS DISPONÍVEIS:
- list_schemas: Descobrir quais schemas existem no DW
- list_tables: Ver tabelas de um schema específico  
- describe_table: Ver estrutura de uma tabela (colunas, tipos)
- execute_select: Executar queries SQL SELECT
- count_records: Contar registros em uma tabela
- get_table_sample: Ver amostra de dados de uma tabela
- list_datamarts: Listar datamarts disponíveis

COMO USAR:
1. Quando perguntarem sobre tickets: primeiro liste schemas/tabelas, depois consulte dados de tickets
2. Quando perguntarem sobre empresas: use list_tables para encontrar tabelas de empresas
3. Quando perguntarem sobre SLA: procure tabelas relacionadas a SLA e consulte os dados
4. Sempre use as ferramentas - você TEM acesso completo ao DW

IMPORTANTE: Você TEM acesso a essas ferramentas. Use-as sempre que necessário para responder perguntas sobre dados do DW.
```

