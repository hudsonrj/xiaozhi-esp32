"""
Bridge Multi-MCP que agrega ferramentas de múltiplos servidores MCP
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from websocket_client import WebSocketClient
from mcp_client import MCPClient
from mcp_client_http import MCPClientHTTP
from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class MultiMCPBridge:
    """Bridge que conecta WebSocket (xiaozhi.me) e múltiplos servidores MCP locais"""
    
    def __init__(self, ws_url: str, ws_token: str, mcp_servers: List[Dict[str, Any]]):
        self.ws_client = WebSocketClient(ws_url, ws_token)
        self.mcp_clients: List[Union[MCPClient, MCPClientHTTP]] = []
        self.message_handler = MessageHandler()
        self.running = False
        
        # Criar clientes MCP para cada servidor
        for mcp_config in mcp_servers:
            # Verificar se é servidor HTTP
            if mcp_config.get('url'):
                # Servidor HTTP/HTTPS
                headers = mcp_config.get('headers', {})
                api_key = mcp_config.get('api_key', '')
                client = MCPClientHTTP(
                    url=mcp_config['url'],
                    api_key=api_key,
                    headers=headers
                )
            else:
                # Servidor SSH/STDIO (padrão)
                client = MCPClient(
                    ssh_host=mcp_config.get('ssh_host', 'localhost'),
                    ssh_user=mcp_config.get('ssh_user', 'user'),
                    ssh_command=mcp_config.get('ssh_command', ''),
                    ssh_port=mcp_config.get('ssh_port', 22),
                    ssh_password=mcp_config.get('ssh_password')
                )
            client.server_name = mcp_config.get('name', 'unknown')
            self.mcp_clients.append(client)
        
        # Mapeamento de IDs de requisição (cloud_id -> (client_index, local_id))
        self.id_mapping: Dict[Any, tuple] = {}
        self.reverse_id_mapping: Dict[tuple, Any] = {}
        self._local_id_counter = 10000
        
        # Cache de ferramentas agregadas
        self._aggregated_tools: Optional[List[Dict[str, Any]]] = None
        
        # Configurar callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Configura callbacks dos clientes"""
        # WebSocket callbacks
        self.ws_client.on_connected = self._on_ws_connected
        self.ws_client.on_disconnected = self._on_ws_disconnected
        self.ws_client.on_error = self._on_ws_error
        self.ws_client.on_message = self._on_ws_message
        
        # MCP callbacks (configurados dinamicamente)
        for idx, client in enumerate(self.mcp_clients):
            client.on_message = lambda msg, c_idx=idx: self._on_mcp_message(msg, c_idx)
            client.on_error = lambda err, c_idx=idx: self._on_mcp_error(err, c_idx)
    
    def _on_ws_connected(self):
        """Callback quando WebSocket conecta"""
        logger.info("WebSocket conectado")
    
    def _on_ws_disconnected(self):
        """Callback quando WebSocket desconecta"""
        logger.warning("WebSocket desconectado")
    
    def _on_ws_error(self, error: str):
        """Callback de erro do WebSocket"""
        logger.error("Erro WebSocket: %s", error)
    
    def _on_mcp_error(self, error: str, client_idx: int):
        """Callback de erro do MCP"""
        server_name = getattr(self.mcp_clients[client_idx], 'server_name', f'MCP-{client_idx}')
        logger.error("Erro MCP [%s]: %s", server_name, error)
    
    async def _on_ws_message(self, payload: Dict[str, Any]):
        """Processa mensagem recebida do WebSocket (cloud)"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(payload):
                logger.warning("Mensagem JSON-RPC inválida do WebSocket: %s", payload)
                return
            
            method = payload.get("method")
            
            # Interceptar tools/list para agregar ferramentas
            if method == "tools/list":
                logger.info("🔍 Interceptando tools/list do agente (id=%s)", payload.get("id"))
                await self._handle_aggregated_tools_list(payload)
                return
            
            # Interceptar tools/call para rotear para o servidor correto
            if method == "tools/call":
                await self._handle_routed_tool_call(payload)
                return
            
            # Se é uma requisição, encaminhar para todos os servidores (ou apenas o primeiro)
            if self.message_handler.is_request(payload):
                cloud_id = payload.get("id")
                local_id = self._get_next_local_id()
                
                # Por padrão, encaminhar para o primeiro servidor
                # (pode ser melhorado para roteamento inteligente)
                client_idx = 0
                client = self.mcp_clients[client_idx]
                
                # Mapear IDs
                self.id_mapping[cloud_id] = (client_idx, local_id)
                self.reverse_id_mapping[(client_idx, local_id)] = cloud_id
                
                # Criar nova mensagem com ID local
                local_message = payload.copy()
                local_message["id"] = local_id
                
                logger.debug("Proxy Cloud -> Local [%s]: %s (cloud_id=%s -> local_id=%s)",
                           getattr(client, 'server_name', f'MCP-{client_idx}'),
                           method, cloud_id, local_id)
                
                # Enviar para MCP local e aguardar resposta
                asyncio.create_task(self._forward_request_to_mcp(local_message, cloud_id, client_idx))
            
            # Se é uma notificação, encaminhar para todos
            elif self.message_handler.is_notification(payload):
                logger.debug("Proxy Cloud -> Local (notification): %s", method)
                for idx, client in enumerate(self.mcp_clients):
                    asyncio.create_task(self._forward_notification_to_mcp(payload, idx))
            
            # Se é uma resposta, não deveria acontecer
            else:
                logger.warning("Resposta recebida do WebSocket (inesperado): %s", payload)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do WebSocket: %s", e, exc_info=True)
    
    async def _handle_aggregated_tools_list(self, request: Dict[str, Any]):
        """Agrega ferramentas de todos os servidores MCP"""
        try:
            cloud_id = request.get("id")
            
            # Sempre buscar ferramentas frescas (não usar cache)
            # Isso garante que sempre temos as ferramentas mais atualizadas
            logger.info("Buscando ferramentas de todos os servidores MCP...")
            
            # Verificar se há pelo menos um servidor conectado
            connected_clients = [c for c in self.mcp_clients if c.connected]
            if not connected_clients:
                logger.warning("Nenhum servidor MCP conectado, retornando lista vazia")
                response = {
                    "jsonrpc": "2.0",
                    "id": cloud_id,
                    "result": {
                        "tools": []
                    }
                }
                await self._forward_response_to_cloud(response)
                return
            
            # Buscar ferramentas de todos os servidores conectados
            all_tools = []
            
            logger.info("Verificando %d clientes MCP (%d conectados)...", len(self.mcp_clients), len(connected_clients))
            for idx, client in enumerate(self.mcp_clients):
                server_name = getattr(client, 'server_name', f'MCP-{idx}')
                
                if not client.connected:
                    logger.warning("Cliente MCP %d (%s) não conectado, pulando", idx, server_name)
                    continue
                
                # Enviar tools/list para este servidor
                tools_list_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": request.get("params", {}),
                    "id": self._get_next_local_id()
                }
                
                logger.info("Enviando tools/list para %s (id=%s)", server_name, tools_list_request["id"])
                try:
                    response = await client.send_message(tools_list_request)
                    logger.info("Resposta recebida de %s: %s", server_name, "result" in response if response else "None")
                    
                    if response and "result" in response:
                        tools = response["result"].get("tools", [])
                        logger.info("Ferramentas brutas de %s: %d ferramentas", server_name, len(tools))
                        
                        # Adicionar prefixo ao nome das ferramentas para identificar origem
                        for tool in tools:
                            tool_name = tool.get("name", "")
                            # Só adicionar prefixo se não tiver já
                            if not tool_name.startswith("portal_") and not tool_name.startswith("sql_") and not tool_name.startswith("aperag_"):
                                tool["name"] = f"{server_name.lower().replace('-', '_')}_{tool_name}"
                        all_tools.extend(tools)
                        logger.info("✅ Recebidas %d ferramentas de %s", len(tools), server_name)
                    else:
                        logger.warning("Resposta inválida de %s: %s", server_name, response)
                except Exception as e:
                    logger.error("❌ Erro ao buscar ferramentas de %s: %s", server_name, e, exc_info=True)
            
            # Cachear ferramentas agregadas
            self._aggregated_tools = all_tools
            
            # Enviar resposta agregada para cloud
            response = {
                "jsonrpc": "2.0",
                "id": cloud_id,
                "result": {
                    "tools": all_tools
                }
            }
            
            logger.info("Total de ferramentas agregadas: %d", len(all_tools))
            await self._forward_response_to_cloud(response)
            
        except Exception as e:
            logger.error("Erro ao agregar ferramentas: %s", e, exc_info=True)
            error_response = self.message_handler.create_error_response(
                request.get("id"), -32000, f"Erro ao agregar ferramentas: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response)
    
    async def _handle_routed_tool_call(self, request: Dict[str, Any]):
        """Roteia tools/call para o servidor correto baseado no nome da ferramenta"""
        try:
            cloud_id = request.get("id")
            params = request.get("params", {})
            tool_name = params.get("name", "")
            
            # Determinar qual servidor deve processar esta ferramenta
            client_idx = None
            
            # Verificar prefixos dos servidores (sql-dw_, portal-transparencia_)
            for idx, client in enumerate(self.mcp_clients):
                server_name = getattr(client, 'server_name', '').lower()
                prefix = f"{server_name}_"
                if tool_name.startswith(prefix):
                    client_idx = idx
                    break
            
            # Se não encontrou pelo prefixo, tentar padrões conhecidos
            if client_idx is None:
                if tool_name.startswith("portal_"):
                    # Ferramentas do Portal da Transparência (sem prefixo)
                    for idx, client in enumerate(self.mcp_clients):
                        server_name = getattr(client, 'server_name', '').lower()
                        if 'portal' in server_name or 'transparencia' in server_name:
                            client_idx = idx
                            break
                elif tool_name.startswith("aperag_") or tool_name.startswith("aperag-mcp_"):
                    # Ferramentas do ApeRAG
                    for idx, client in enumerate(self.mcp_clients):
                        server_name = getattr(client, 'server_name', '').lower()
                        if 'aperag' in server_name:
                            client_idx = idx
                            break
                elif tool_name.startswith("sql_") or any(tool_name.startswith(prefix) for prefix in ["list_tables", "execute_select", "count_records", "get_table_sample", "describe_table", "list_schemas"]):
                    # Ferramentas SQL/DW (sem prefixo)
                    for idx, client in enumerate(self.mcp_clients):
                        server_name = getattr(client, 'server_name', '').lower()
                        if 'sql' in server_name or 'dw' in server_name or 'sensr' in server_name:
                            client_idx = idx
                            break
            
            # Se não encontrou, tentar primeiro servidor
            if client_idx is None:
                client_idx = 0
                logger.warning("Não foi possível determinar servidor para %s, usando primeiro servidor", tool_name)
            
            if client_idx >= len(self.mcp_clients):
                error_response = self.message_handler.create_error_response(
                    cloud_id, -32601, f"Servidor MCP não encontrado para ferramenta: {tool_name}"
                )
                await self._forward_response_to_cloud(error_response)
                return
            
            client = self.mcp_clients[client_idx]
            server_name = getattr(client, 'server_name', f'MCP-{client_idx}')
            
            if not client.connected:
                error_response = self.message_handler.create_error_response(
                    cloud_id, -32000, f"Servidor MCP {server_name} não está conectado"
                )
                await self._forward_response_to_cloud(error_response)
                return
            
            # Mapear IDs
            local_id = self._get_next_local_id()
            self.id_mapping[cloud_id] = (client_idx, local_id)
            self.reverse_id_mapping[(client_idx, local_id)] = cloud_id
            
            # Criar mensagem local
            local_message = request.copy()
            local_message["id"] = local_id
            
            # Remover prefixo do nome da ferramenta se necessário
            original_tool_name = tool_name
            server_name_normalized = server_name.lower().replace('-', '_')
            
            # Remover prefixos comuns do ApeRAG
            # O servidor é "aperag-mcp", então o prefixo pode ser:
            # - "aperag-mcp_" -> remove tudo
            # - "aperag_mcp_" -> remove tudo (underscore no lugar do hífen)
            # - "aperag_" -> remove apenas "aperag_"
            # O nome real das ferramentas do ApeRAG não tem "mcp_" no início
            if tool_name.startswith("aperag-mcp_"):
                tool_name = tool_name[len("aperag-mcp_"):]
            elif tool_name.startswith("aperag_mcp_"):
                tool_name = tool_name[len("aperag_mcp_"):]
            elif tool_name.startswith("aperag_"):
                # Se começa com "aperag_" mas não é "aperag_mcp_", pode ser que o nome original já tenha "mcp_"
                # Mas o nome real não deve ter "mcp_", então removemos apenas "aperag_"
                tool_name = tool_name[len("aperag_"):]
                # Se ainda começa com "mcp_", remover também
                if tool_name.startswith("mcp_"):
                    tool_name = tool_name[len("mcp_"):]
            elif tool_name.startswith(f"{server_name_normalized}_"):
                tool_name = tool_name[len(f"{server_name_normalized}_"):]
                # Se ainda começa com "mcp_", remover também
                if tool_name.startswith("mcp_"):
                    tool_name = tool_name[len("mcp_"):]
            elif tool_name.startswith(f"{server_name.lower()}_"):
                tool_name = tool_name[len(f"{server_name.lower()}_"):]
                # Se ainda começa com "mcp_", remover também
                if tool_name.startswith("mcp_"):
                    tool_name = tool_name[len("mcp_"):]
            
            local_message["params"]["name"] = tool_name
            
            # NOTA: A API key do ApeRAG é passada apenas no header Authorization,
            # não nos argumentos da ferramenta. O MCPClientHTTP já faz isso automaticamente.
            
            logger.info("Roteando tools/call para %s: %s -> %s (cloud_id=%s -> local_id=%s)",
                       server_name, original_tool_name, tool_name, cloud_id, local_id)
            
            # Encaminhar para o servidor correto
            asyncio.create_task(self._forward_request_to_mcp(local_message, cloud_id, client_idx))
            
        except Exception as e:
            logger.error("Erro ao rotear tools/call: %s", e, exc_info=True)
            error_response = self.message_handler.create_error_response(
                request.get("id"), -32000, f"Erro ao rotear chamada: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response)
    
    def _on_mcp_message(self, message: Dict[str, Any], client_idx: int):
        """Processa mensagem recebida do MCP local"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(message):
                logger.warning("Mensagem JSON-RPC inválida do MCP: %s", message)
                return
            
            server_name = getattr(self.mcp_clients[client_idx], 'server_name', f'MCP-{client_idx}')
            
            # Se é uma resposta, mapear ID de volta e enviar para cloud
            if self.message_handler.is_response(message):
                local_id = message.get("id")
                key = (client_idx, local_id)
                cloud_id = self.reverse_id_mapping.get(key)
                
                if cloud_id is None:
                    logger.warning("ID local não encontrado no mapeamento: %s (servidor: %s)", local_id, server_name)
                    return
                
                # Criar mensagem com ID cloud
                cloud_message = message.copy()
                cloud_message["id"] = cloud_id
                
                # Remover do mapeamento
                del self.id_mapping[cloud_id]
                del self.reverse_id_mapping[key]
                
                logger.debug("Proxy Local -> Cloud [%s]: resposta (local_id=%s -> cloud_id=%s)",
                           server_name, local_id, cloud_id)
                
                # Enviar para cloud
                asyncio.create_task(self._forward_response_to_cloud(cloud_message))
            
            # Se é uma notificação, encaminhar para cloud
            elif self.message_handler.is_notification(message):
                logger.debug("Proxy Local -> Cloud [%s] (notification): %s",
                           server_name, message.get("method"))
                asyncio.create_task(self._forward_notification_to_cloud(message))
            
            # Se é uma requisição, não deveria acontecer
            else:
                logger.warning("Requisição recebida do MCP [%s] (inesperado): %s",
                             server_name, message)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do MCP: %s", e, exc_info=True)
    
    async def _forward_request_to_mcp(self, local_message: Dict[str, Any], cloud_id: Any, client_idx: int):
        """Encaminha requisição do cloud para MCP local"""
        try:
            client = self.mcp_clients[client_idx]
            response = await client.send_message(local_message)
            
            if response:
                # Mapear ID de volta
                local_id = response.get("id")
                key = (client_idx, local_id)
                if key in self.reverse_id_mapping:
                    cloud_id = self.reverse_id_mapping[key]
                    cloud_response = response.copy()
                    cloud_response["id"] = cloud_id
                    
                    # Remover do mapeamento
                    del self.id_mapping[cloud_id]
                    del self.reverse_id_mapping[key]
                    
                    # Enviar resposta para cloud
                    await self._forward_response_to_cloud(cloud_response)
            else:
                # Enviar erro para cloud
                error_response = self.message_handler.create_error_response(
                    cloud_id, -32000, "Erro ao processar requisição no servidor MCP"
                )
                await self._forward_response_to_cloud(error_response)
                
        except Exception as e:
            logger.error("Erro ao encaminhar requisição para MCP: %s", e)
            error_response = self.message_handler.create_error_response(
                cloud_id, -32000, f"Erro interno: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response)
    
    async def _forward_notification_to_mcp(self, notification: Dict[str, Any], client_idx: int):
        """Encaminha notificação do cloud para MCP local"""
        try:
            client = self.mcp_clients[client_idx]
            await client.send_message(notification)
        except Exception as e:
            logger.error("Erro ao encaminhar notificação para MCP: %s", e)
    
    async def _forward_response_to_cloud(self, response: Dict[str, Any]):
        """Encaminha resposta do MCP local para cloud"""
        try:
            await self.ws_client.send_message(response)
            logger.debug("Resposta enviada para cloud: %s", response.get("id"))
        except Exception as e:
            logger.error("Erro ao encaminhar resposta para cloud: %s", e)
    
    async def _forward_notification_to_cloud(self, notification: Dict[str, Any]):
        """Encaminha notificação do MCP local para cloud"""
        try:
            await self.ws_client.send_message(notification)
            logger.debug("Notificação enviada para cloud: %s", notification.get("method"))
        except Exception as e:
            logger.error("Erro ao encaminhar notificação para cloud: %s", e)
    
    def _get_next_local_id(self) -> int:
        """Gera próximo ID local"""
        self._local_id_counter += 1
        return self._local_id_counter
    
    async def start(self):
        """Inicia a bridge"""
        logger.info("Iniciando Multi-MCP Bridge com %d servidores...", len(self.mcp_clients))
        self.running = True
        
        # Conectar a todos os servidores MCP PRIMEIRO (antes do WebSocket)
        # Isso garante que quando o agente solicitar tools/list, os servidores já estarão prontos
        for idx, client in enumerate(self.mcp_clients):
            server_name = getattr(client, 'server_name', f'MCP-{idx}')
            logger.info("Conectando ao servidor MCP: %s", server_name)
            
            mcp_connected = await client.connect()
            if not mcp_connected:
                logger.error("Falha ao conectar ao servidor MCP: %s", server_name)
                continue
            
            # Inicializar sessão MCP
            mcp_initialized = await client.initialize()
            if not mcp_initialized:
                logger.error("Falha ao inicializar sessão MCP: %s", server_name)
                await client.disconnect()
                continue
            
            logger.info("Servidor MCP conectado e inicializado: %s", server_name)
        
        # Verificar se pelo menos um servidor está conectado
        connected_count = sum(1 for client in self.mcp_clients if client.connected)
        if connected_count == 0:
            logger.error("Nenhum servidor MCP conectado")
            return False
        
        # AGORA conectar ao WebSocket (depois que os servidores estão prontos)
        ws_connected = await self.ws_client.connect()
        if not ws_connected:
            logger.error("Falha ao conectar ao WebSocket")
            return False
        
        logger.info("Multi-MCP Bridge iniciada com sucesso (%d/%d servidores conectados)",
                   connected_count, len(self.mcp_clients))
        return True
    
    async def stop(self):
        """Para a bridge"""
        logger.info("Parando Multi-MCP Bridge...")
        self.running = False
        
        for client in self.mcp_clients:
            await client.disconnect()
        
        await self.ws_client.disconnect()
        
        logger.info("Multi-MCP Bridge parada")
    
    async def run(self):
        """Executa a bridge até ser interrompida"""
        if not await self.start():
            return
        
        try:
            # Manter rodando
            while self.running:
                await asyncio.sleep(1)
                
                # Verificar conexões
                if not self.ws_client.is_connected():
                    pass  # WebSocket tem reconexão automática
                
                # Verificar reconexão de servidores MCP
                for idx, client in enumerate(self.mcp_clients):
                    if not client.connected:
                        server_name = getattr(client, 'server_name', f'MCP-{idx}')
                        logger.warning("MCP desconectado [%s], tentando reconectar...", server_name)
                        try:
                            if await client.connect():
                                if not await client.initialize():
                                    logger.error("Falha ao inicializar sessão MCP após reconexão: %s", server_name)
                        except Exception as e:
                            logger.error("Erro ao reconectar MCP [%s]: %s", server_name, e)
        
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
        except Exception as e:
            logger.error("Erro fatal na bridge: %s", e, exc_info=True)
        finally:
            await self.stop()

