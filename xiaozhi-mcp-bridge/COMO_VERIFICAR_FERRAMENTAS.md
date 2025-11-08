# Como Verificar se as Ferramentas Estão Aparecendo

## Status Atual

✅ **Bridge Multi-MCP está rodando**
✅ **Ambos os servidores conectados:**
   - sql-dw: ✅ Conectado
   - portal-transparencia: ✅ Conectado

## O Problema

O agente xiaozhi.me solicita `tools/list` durante a inicialização. Se os servidores ainda não estiverem conectados nesse momento, retorna lista vazia e não solicita novamente automaticamente.

## Solução

**Recarregue a página do agente xiaozhi.me** para forçar uma nova solicitação de `tools/list` agora que ambos os servidores estão conectados.

## Como Verificar nos Logs

Após recarregar a página do agente, você deve ver nos logs:

```powershell
Get-Content bridge.log -Wait | Select-String -Pattern "Interceptando|Buscando|Enviando tools/list|Recebidas.*ferramentas|Total de ferramentas"
```

Você deve ver:
- ✅ "🔍 Interceptando tools/list do agente"
- ✅ "Buscando ferramentas de todos os servidores MCP..."
- ✅ "Verificando 2 clientes MCP (2 conectados)..."
- ✅ "Enviando tools/list para sql-dw"
- ✅ "Enviando tools/list para portal-transparencia"
- ✅ "✅ Recebidas X ferramentas de sql-dw"
- ✅ "✅ Recebidas X ferramentas de portal-transparencia"
- ✅ "Total de ferramentas agregadas: X" (deve ser ~16)

## Se Ainda Não Aparecer

1. Verifique se a bridge está rodando: `.\status_bridge.ps1`
2. Verifique os logs: `Get-Content bridge.log -Tail 50`
3. Reinicie a bridge: `.\stop_bridge.ps1` e depois `.\start_bridge.ps1`
4. Aguarde 30 segundos para ambos os servidores conectarem
5. Recarregue a página do agente

