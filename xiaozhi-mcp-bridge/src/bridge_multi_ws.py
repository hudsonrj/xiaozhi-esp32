"""
Bridge Multi-WebSocket que conecta múltiplos endpoints WebSocket aos mesmos servidores MCP
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from websocket_client import WebSocketClient
from mcp_client import MCPClient
from mcp_client_http import MCPClientHTTP
from message_handler import MessageHandler

logger = logging.getLogger(__name__)

# Limite de tamanho de mensagem WebSocket (50KB para ser conservador)
MAX_MESSAGE_SIZE = 50 * 1024  # 50KB
MAX_CONTENT_LENGTH = 2000  # Máximo de caracteres por conteúdo de resultado


class MultiWebSocketBridge:
    """Bridge que conecta múltiplos WebSockets (xiaozhi.me) aos mesmos servidores MCP locais"""
    
    def __init__(self, ws_endpoints: List[Dict[str, str]], mcp_servers: List[Dict[str, Any]]):
        """
        Args:
            ws_endpoints: Lista de dicionários com 'url' e 'token' para cada endpoint WebSocket
            mcp_servers: Lista de configurações de servidores MCP (compartilhados por todos os WebSockets)
        """
        # Criar clientes WebSocket para cada endpoint
        self.ws_clients: List[WebSocketClient] = []
        for idx, endpoint in enumerate(ws_endpoints):
            ws_url = endpoint.get('url', '')
            ws_token = endpoint.get('token', '')
            if not ws_url or not ws_token:
                logger.error("Endpoint WebSocket %d está faltando 'url' ou 'token'", idx)
                continue
            ws_client = WebSocketClient(ws_url, ws_token)
            ws_client.endpoint_id = f"endpoint-{idx}"
            self.ws_clients.append(ws_client)
        
        # Servidores MCP compartilhados por todos os WebSockets
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
        
        # Mapeamento de IDs de requisição por WebSocket
        # Estrutura: {ws_endpoint_id: {cloud_id -> (client_index, local_id)}}
        self.id_mappings: Dict[str, Dict[Any, tuple]] = {}
        self.reverse_id_mappings: Dict[str, Dict[tuple, Any]] = {}
        self._local_id_counter = 10000
        
        # Cache de ferramentas agregadas (compartilhado)
        self._aggregated_tools: Optional[List[Dict[str, Any]]] = None
        
        # Cache de mapeamento nome -> ID de collections (compartilhado)
        self._collection_name_to_id: Dict[str, str] = {}
        
        # Configurar callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Configura callbacks dos clientes"""
        # WebSocket callbacks (um para cada endpoint)
        for ws_client in self.ws_clients:
            endpoint_id = getattr(ws_client, 'endpoint_id', 'unknown')
            
            # Criar função factory para capturar endpoint_id corretamente
            def create_message_handler(eid: str):
                async def handler(msg):
                    await self._on_ws_message(msg, eid)
                return handler
            
            def create_connected_handler(eid: str):
                def handler():
                    self._on_ws_connected(eid)
                return handler
            
            def create_disconnected_handler(eid: str):
                def handler():
                    self._on_ws_disconnected(eid)
                return handler
            
            def create_error_handler(eid: str):
                def handler(err: str):
                    self._on_ws_error(err, eid)
                return handler
            
            ws_client.on_connected = create_connected_handler(endpoint_id)
            ws_client.on_disconnected = create_disconnected_handler(endpoint_id)
            ws_client.on_error = create_error_handler(endpoint_id)
            ws_client.on_message = create_message_handler(endpoint_id)
        
        # MCP callbacks (configurados dinamicamente)
        for idx, client in enumerate(self.mcp_clients):
            client.on_message = lambda msg, c_idx=idx: self._on_mcp_message(msg, c_idx)
            client.on_error = lambda err, c_idx=idx: self._on_mcp_error(err, c_idx)
    
    def _on_ws_connected(self, endpoint_id: str):
        """Callback quando WebSocket conecta"""
        logger.info("WebSocket conectado [%s]", endpoint_id)
    
    def _on_ws_disconnected(self, endpoint_id: str):
        """Callback quando WebSocket desconecta"""
        logger.warning("WebSocket desconectado [%s]", endpoint_id)
    
    def _on_ws_error(self, error: str, endpoint_id: str):
        """Callback de erro do WebSocket"""
        logger.error("Erro WebSocket [%s]: %s", endpoint_id, error)
    
    def _on_mcp_error(self, error: str, client_idx: int):
        """Callback de erro do MCP"""
        server_name = getattr(self.mcp_clients[client_idx], 'server_name', f'MCP-{client_idx}')
        logger.error("Erro MCP [%s]: %s", server_name, error)
    
    async def _on_ws_message(self, payload: Dict[str, Any], endpoint_id: str):
        """Processa mensagem recebida do WebSocket (cloud)"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(payload):
                logger.warning("Mensagem JSON-RPC inválida do WebSocket [%s]: %s", endpoint_id, payload)
                return
            
            method = payload.get("method")
            
            # Interceptar tools/list para agregar ferramentas
            if method == "tools/list":
                logger.info("[BUSCA] Interceptando tools/list do agente [%s] (id=%s)", endpoint_id, payload.get("id"))
                await self._handle_aggregated_tools_list(payload, endpoint_id)
                return
            
            # Interceptar tools/call para rotear para o servidor correto
            if method == "tools/call":
                await self._handle_routed_tool_call(payload, endpoint_id)
                return
            
            # Se é uma requisição, encaminhar para todos os servidores (ou apenas o primeiro)
            if self.message_handler.is_request(payload):
                cloud_id = payload.get("id")
                local_id = self._get_next_local_id()
                
                # Por padrão, encaminhar para o primeiro servidor
                client_idx = 0
                client = self.mcp_clients[client_idx]
                
                # Mapear IDs (por endpoint)
                if endpoint_id not in self.id_mappings:
                    self.id_mappings[endpoint_id] = {}
                    self.reverse_id_mappings[endpoint_id] = {}
                
                self.id_mappings[endpoint_id][cloud_id] = (client_idx, local_id)
                self.reverse_id_mappings[endpoint_id][(client_idx, local_id)] = cloud_id
                
                # Criar nova mensagem com ID local
                local_message = payload.copy()
                local_message["id"] = local_id
                
                logger.debug("Proxy Cloud -> Local [%s] [%s]: %s (cloud_id=%s -> local_id=%s)",
                           getattr(client, 'server_name', f'MCP-{client_idx}'),
                           endpoint_id, method, cloud_id, local_id)
                
                # Enviar para MCP local e aguardar resposta
                asyncio.create_task(self._forward_request_to_mcp(local_message, cloud_id, client_idx, endpoint_id))
            
            # Se é uma notificação, encaminhar para todos
            elif self.message_handler.is_notification(payload):
                logger.debug("Proxy Cloud -> Local [%s] (notification): %s", endpoint_id, method)
                for idx, client in enumerate(self.mcp_clients):
                    asyncio.create_task(self._forward_notification_to_mcp(payload, idx))
            
            # Se é uma resposta, não deveria acontecer
            else:
                logger.warning("Resposta recebida do WebSocket [%s] (inesperado): %s", endpoint_id, payload)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do WebSocket [%s]: %s", endpoint_id, e, exc_info=True)
    
    async def _handle_aggregated_tools_list(self, request: Dict[str, Any], endpoint_id: str):
        """Agrega ferramentas de todos os servidores MCP"""
        try:
            cloud_id = request.get("id")
            
            # Sempre buscar ferramentas frescas (não usar cache)
            logger.info("Buscando ferramentas de todos os servidores MCP para [%s]...", endpoint_id)
            
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
                await self._forward_response_to_cloud(response, endpoint_id)
                return
            
            # Buscar ferramentas de todos os servidores conectados em paralelo
            logger.info("Verificando %d clientes MCP (%d conectados)...", len(self.mcp_clients), len(connected_clients))
            
            # Criar lista de tarefas para executar em paralelo
            async def fetch_tools_from_server(idx: int, client):
                """Busca ferramentas de um servidor MCP específico"""
                server_name = getattr(client, 'server_name', f'MCP-{idx}')
                
                if not client.connected:
                    logger.warning("Cliente MCP %d (%s) não conectado, pulando", idx, server_name)
                    return []
                
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
                        server_prefix = server_name.lower().replace('-', '_')
                        for tool in tools:
                            tool_name = tool.get("name", "")
                            # Só adicionar prefixo se não tiver já
                            if (not tool_name.startswith("portal_") and 
                                not tool_name.startswith("sql_") and 
                                not tool_name.startswith("aperag_") and
                                not tool_name.startswith("google_calendar_") and
                                not tool_name.startswith("notion_") and
                                not tool_name.startswith(f"{server_prefix}_")):
                                tool["name"] = f"{server_prefix}_{tool_name}"
                        logger.info("[OK] Recebidas %d ferramentas de %s", len(tools), server_name)
                        return tools
                    else:
                        logger.warning("Resposta inválida de %s: %s", server_name, response)
                        return []
                except Exception as e:
                    logger.error("[ERRO] Erro ao buscar ferramentas de %s: %s", server_name, e, exc_info=True)
                    return []
            
            # Executar todas as buscas em paralelo
            tasks = []
            for idx, client in enumerate(self.mcp_clients):
                tasks.append(fetch_tools_from_server(idx, client))
            
            # Aguardar todas as respostas em paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Agregar todas as ferramentas
            all_tools = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error("Exceção ao buscar ferramentas: %s", result, exc_info=True)
                elif isinstance(result, list):
                    all_tools.extend(result)
            
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
            
            logger.info("Total de ferramentas agregadas para [%s]: %d", endpoint_id, len(all_tools))
            await self._forward_response_to_cloud(response, endpoint_id)
            
        except Exception as e:
            logger.error("Erro ao agregar ferramentas [%s]: %s", endpoint_id, e, exc_info=True)
            error_response = self.message_handler.create_error_response(
                request.get("id"), -32000, f"Erro ao agregar ferramentas: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response, endpoint_id)
    
    async def _handle_routed_tool_call(self, request: Dict[str, Any], endpoint_id: str):
        """Roteia tools/call para o servidor correto baseado no nome da ferramenta"""
        try:
            cloud_id = request.get("id")
            params = request.get("params", {})
            tool_name = params.get("name", "")
            
            # Determinar qual servidor deve processar esta ferramenta
            client_idx = None
            
            # Verificar prefixos dos servidores (sql-dw_, portal-transparencia_, google-calendar_, notion_)
            for idx, client in enumerate(self.mcp_clients):
                server_name = getattr(client, 'server_name', '').lower()
                # Tentar com hífen e underscore
                prefix_with_hyphen = f"{server_name}_"
                prefix_with_underscore = f"{server_name.replace('-', '_')}_"
                # Também verificar se o nome da ferramenta contém o padrão do servidor (mesmo com duplicação)
                if (tool_name.startswith(prefix_with_hyphen) or 
                    tool_name.startswith(prefix_with_underscore) or
                    # Verificar padrões específicos mesmo com duplicação
                    (server_name == 'google-calendar' and 'google_calendar_' in tool_name) or
                    (server_name == 'notion' and 'notion_' in tool_name)):
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
                elif "google_calendar_" in tool_name:
                    # Ferramentas do Google Calendar (mesmo com prefixo duplicado)
                    for idx, client in enumerate(self.mcp_clients):
                        server_name = getattr(client, 'server_name', '').lower()
                        if 'google' in server_name and 'calendar' in server_name:
                            client_idx = idx
                            break
                elif tool_name.startswith("notion_"):
                    # Ferramentas do Notion
                    for idx, client in enumerate(self.mcp_clients):
                        server_name = getattr(client, 'server_name', '').lower()
                        if 'notion' in server_name:
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
                await self._forward_response_to_cloud(error_response, endpoint_id)
                return
            
            client = self.mcp_clients[client_idx]
            server_name = getattr(client, 'server_name', f'MCP-{client_idx}')
            
            if not client.connected:
                error_response = self.message_handler.create_error_response(
                    cloud_id, -32000, f"Servidor MCP {server_name} não está conectado"
                )
                await self._forward_response_to_cloud(error_response, endpoint_id)
                return
            
            # Mapear IDs (por endpoint)
            if endpoint_id not in self.id_mappings:
                self.id_mappings[endpoint_id] = {}
                self.reverse_id_mappings[endpoint_id] = {}
            
            local_id = self._get_next_local_id()
            self.id_mappings[endpoint_id][cloud_id] = (client_idx, local_id)
            self.reverse_id_mappings[endpoint_id][(client_idx, local_id)] = cloud_id
            
            # Criar mensagem local (deep copy para poder modificar)
            import copy
            local_message = copy.deepcopy(request)
            local_message["id"] = local_id
            
            # Remover prefixo do nome da ferramenta se necessário
            original_tool_name = tool_name
            server_name_normalized = server_name.lower().replace('-', '_')
            
            # Para Google Calendar e Notion, as ferramentas já têm o prefixo no nome
            # NUNCA remover o prefixo, apenas verificar se está duplicado
            if server_name_normalized in ["google_calendar", "notion"]:
                # Verificar se está duplicado (ex: google_calendar_google_calendar_list_events)
                prefix = f"{server_name_normalized}_"
                double_prefix = f"{prefix}{prefix}"
                if tool_name.startswith(double_prefix):
                    # Está duplicado, remover apenas um prefixo (deixar google_calendar_list_events)
                    tool_name = tool_name[len(prefix):]
                    logger.debug("Removido prefixo duplicado: %s -> %s", original_tool_name, tool_name)
                else:
                    # Não está duplicado, manter o nome original (já tem o prefixo correto)
                    tool_name = tool_name
                    logger.debug("Mantido nome original para %s: %s", server_name_normalized, tool_name)
            else:
                # Para outros servidores, aplicar lógica normal de remoção de prefixo
                # Remover prefixos comuns do ApeRAG
                if tool_name.startswith("aperag-mcp_"):
                    tool_name = tool_name[len("aperag-mcp_"):]
                elif tool_name.startswith("aperag_mcp_"):
                    tool_name = tool_name[len("aperag_mcp_"):]
                elif tool_name.startswith("aperag_"):
                    tool_name = tool_name[len("aperag_"):]
                    if tool_name.startswith("mcp_"):
                        tool_name = tool_name[len("mcp_"):]
                elif tool_name.startswith(f"{server_name_normalized}_"):
                    temp_name = tool_name[len(f"{server_name_normalized}_"):]
                    if temp_name.startswith(f"{server_name_normalized}_"):
                        # Duplicado, remover ambos
                        tool_name = temp_name[len(f"{server_name_normalized}_"):]
                    else:
                        tool_name = temp_name
                    if tool_name.startswith("mcp_"):
                        tool_name = tool_name[len("mcp_"):]
                elif tool_name.startswith(f"{server_name.lower()}_"):
                    temp_name = tool_name[len(f"{server_name.lower()}_"):]
                    if temp_name.startswith(f"{server_name.lower()}_"):
                        tool_name = temp_name[len(f"{server_name.lower()}_"):]
                    else:
                        tool_name = temp_name
                    if tool_name.startswith("mcp_"):
                        tool_name = tool_name[len("mcp_"):]
            
            local_message["params"]["name"] = tool_name
            
            # Log para debug
            logger.debug("Nome da ferramenta após processamento: '%s' (original: '%s', servidor: '%s')", 
                        tool_name, original_tool_name, server_name)
            
            # Se é uma busca em collection e o collection_id não começa com "col",
            # tentar converter nome para ID
            logger.debug("Verificando se tool_name '%s' requer conversão de collection_id", tool_name)
            if tool_name in ["search_collection", "search_chat_files"]:
                # Garantir que params e arguments existem
                if "params" not in local_message:
                    local_message["params"] = {}
                if "arguments" not in local_message["params"]:
                    local_message["params"]["arguments"] = {}
                
                arguments = local_message["params"]["arguments"]
                collection_id = arguments.get("collection_id")
                
                logger.info("Verificando collection_id: '%s' (tipo: %s, tool_name: %s)", collection_id, type(collection_id), tool_name)
                
                if collection_id and isinstance(collection_id, str) and not collection_id.startswith("col"):
                    # É um nome, não um ID - tentar converter
                    logger.info("Collection ID '%s' parece ser um nome (não começa com 'col'), tentando converter para ID...", collection_id)
                    converted_id = await self._convert_collection_name_to_id(collection_id, client_idx)
                    if converted_id:
                        arguments["collection_id"] = converted_id
                        logger.info("Convertido '%s' -> '%s'", collection_id, converted_id)
                    else:
                        logger.warning("Não foi possível converter collection '%s' para ID, tentando usar como está", collection_id)
                elif collection_id:
                    logger.debug("Collection ID '%s' já parece ser um ID válido (começa com 'col')", collection_id)
                else:
                    logger.warning("collection_id não encontrado ou está vazio nos arguments")
            
            logger.info("Roteando tools/call para %s [%s]: %s -> %s (cloud_id=%s -> local_id=%s)",
                       server_name, endpoint_id, original_tool_name, tool_name, cloud_id, local_id)
            
            # Encaminhar para o servidor correto
            asyncio.create_task(self._forward_request_to_mcp(local_message, cloud_id, client_idx, endpoint_id))
            
        except Exception as e:
            logger.error("Erro ao rotear tools/call [%s]: %s", endpoint_id, e, exc_info=True)
            error_response = self.message_handler.create_error_response(
                request.get("id"), -32000, f"Erro ao rotear chamada: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response, endpoint_id)
    
    def _on_mcp_message(self, message: Dict[str, Any], client_idx: int):
        """Processa mensagem recebida do MCP local"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(message):
                logger.warning("Mensagem JSON-RPC inválida do MCP: %s", message)
                return
            
            server_name = getattr(self.mcp_clients[client_idx], 'server_name', f'MCP-{client_idx}')
            
            # Se é uma resposta, mapear ID de volta e enviar para todos os WebSockets que têm essa requisição
            if self.message_handler.is_response(message):
                local_id = message.get("id")
                
                # Procurar em todos os endpoints qual tem esse ID mapeado
                for endpoint_id, reverse_mapping in self.reverse_id_mappings.items():
                    key = (client_idx, local_id)
                    cloud_id = reverse_mapping.get(key)
                    
                    if cloud_id is not None:
                        # Criar mensagem com ID cloud
                        cloud_message = message.copy()
                        cloud_message["id"] = cloud_id
                        
                        # Remover do mapeamento
                        if endpoint_id in self.id_mappings:
                            del self.id_mappings[endpoint_id][cloud_id]
                        del reverse_mapping[key]
                        
                        logger.debug("Proxy Local -> Cloud [%s] [%s]: resposta (local_id=%s -> cloud_id=%s)",
                                   server_name, endpoint_id, local_id, cloud_id)
                        
                        # Enviar para cloud (apenas para o endpoint que fez a requisição)
                        asyncio.create_task(self._forward_response_to_cloud(cloud_message, endpoint_id))
                        break
                else:
                    logger.warning("ID local não encontrado no mapeamento: %s (servidor: %s)", local_id, server_name)
            
            # Se é uma notificação, encaminhar para todos os WebSockets
            elif self.message_handler.is_notification(message):
                logger.debug("Proxy Local -> Cloud [%s] (notification): %s",
                           server_name, message.get("method"))
                for ws_client in self.ws_clients:
                    endpoint_id = getattr(ws_client, 'endpoint_id', 'unknown')
                    asyncio.create_task(self._forward_notification_to_cloud(message, endpoint_id))
            
            # Se é uma requisição, não deveria acontecer
            else:
                logger.warning("Requisição recebida do MCP [%s] (inesperado): %s",
                             server_name, message)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do MCP: %s", e, exc_info=True)
    
    async def _forward_request_to_mcp(self, local_message: Dict[str, Any], cloud_id: Any, client_idx: int, endpoint_id: str):
        """Encaminha requisição do cloud para MCP local"""
        try:
            client = self.mcp_clients[client_idx]
            response = await client.send_message(local_message)
            
            if response:
                # Mapear ID de volta
                local_id = response.get("id")
                key = (client_idx, local_id)
                
                if endpoint_id in self.reverse_id_mappings:
                    reverse_mapping = self.reverse_id_mappings[endpoint_id]
                    if key in reverse_mapping:
                        cloud_id = reverse_mapping[key]
                        cloud_response = response.copy()
                        cloud_response["id"] = cloud_id
                        
                        # Remover do mapeamento
                        if endpoint_id in self.id_mappings:
                            del self.id_mappings[endpoint_id][cloud_id]
                        del reverse_mapping[key]
                        
                        # Enviar resposta para cloud (apenas para o endpoint que fez a requisição)
                        await self._forward_response_to_cloud(cloud_response, endpoint_id)
            else:
                # Enviar erro para cloud
                error_response = self.message_handler.create_error_response(
                    cloud_id, -32000, "Erro ao processar requisição no servidor MCP"
                )
                await self._forward_response_to_cloud(error_response, endpoint_id)
                
        except Exception as e:
            logger.error("Erro ao encaminhar requisição para MCP: %s", e)
            error_response = self.message_handler.create_error_response(
                cloud_id, -32000, f"Erro interno: {str(e)}"
            )
            await self._forward_response_to_cloud(error_response, endpoint_id)
    
    async def _forward_notification_to_mcp(self, notification: Dict[str, Any], client_idx: int):
        """Encaminha notificação do cloud para MCP local"""
        try:
            client = self.mcp_clients[client_idx]
            await client.send_message(notification)
        except Exception as e:
            logger.error("Erro ao encaminhar notificação para MCP: %s", e)
    
    async def _forward_response_to_cloud(self, response: Dict[str, Any], endpoint_id: str):
        """Encaminha resposta do MCP local para cloud (endpoint específico)"""
        try:
            # Encontrar o WebSocket client correto
            ws_client = None
            for ws in self.ws_clients:
                if getattr(ws, 'endpoint_id', 'unknown') == endpoint_id:
                    ws_client = ws
                    break
            
            if not ws_client:
                logger.error("WebSocket client não encontrado para endpoint_id: %s", endpoint_id)
                return
            
            # Truncar resposta se muito grande
            truncated_response = self._truncate_response(response)
            await ws_client.send_message(truncated_response)
            logger.debug("Resposta enviada para cloud [%s]: %s", endpoint_id, truncated_response.get("id"))
        except Exception as e:
            logger.error("Erro ao encaminhar resposta para cloud [%s]: %s", endpoint_id, e)
    
    async def _forward_notification_to_cloud(self, notification: Dict[str, Any], endpoint_id: str):
        """Encaminha notificação do MCP local para cloud (endpoint específico)"""
        try:
            # Encontrar o WebSocket client correto
            ws_client = None
            for ws in self.ws_clients:
                if getattr(ws, 'endpoint_id', 'unknown') == endpoint_id:
                    ws_client = ws
                    break
            
            if not ws_client:
                logger.error("WebSocket client não encontrado para endpoint_id: %s", endpoint_id)
                return
            
            await ws_client.send_message(notification)
            logger.debug("Notificação enviada para cloud [%s]: %s", endpoint_id, notification.get("method"))
        except Exception as e:
            logger.error("Erro ao encaminhar notificação para cloud [%s]: %s", endpoint_id, e)
    
    def _get_next_local_id(self) -> int:
        """Gera próximo ID local"""
        self._local_id_counter += 1
        return self._local_id_counter
    
    async def _convert_collection_name_to_id(self, collection_name: str, client_idx: int) -> Optional[str]:
        """Converte nome de collection para ID usando list_collections"""
        try:
            # Verificar cache primeiro
            if collection_name in self._collection_name_to_id:
                return self._collection_name_to_id[collection_name]
            
            client = self.mcp_clients[client_idx]
            if not client.connected:
                logger.warning("Cliente MCP não conectado, não é possível converter nome para ID")
                return None
            
            # Chamar list_collections
            list_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "list_collections",
                    "arguments": {}
                },
                "id": self._get_next_local_id()
            }
            
            logger.debug("Chamando list_collections para converter '%s' para ID", collection_name)
            response = await client.send_message(list_request)
            
            if response and "result" in response:
                result = response["result"]
                
                # Tentar structuredContent primeiro
                if "structuredContent" in result:
                    structured = result["structuredContent"]
                    if "items" in structured:
                        collections = structured["items"]
                        for coll in collections:
                            coll_id = coll.get("id", "")
                            coll_title = coll.get("title", "").lower()
                            coll_name_lower = collection_name.lower()
                            
                            # Comparar título (case-insensitive)
                            if coll_title == coll_name_lower:
                                self._collection_name_to_id[collection_name] = coll_id
                                logger.info("Encontrado ID para '%s': %s", collection_name, coll_id)
                                return coll_id
                
                # Tentar content (formato alternativo)
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                try:
                                    text_data = json.loads(item["text"])
                                    if "items" in text_data:
                                        collections = text_data["items"]
                                        for coll in collections:
                                            coll_id = coll.get("id", "")
                                            coll_title = coll.get("title", "").lower()
                                            coll_name_lower = collection_name.lower()
                                            
                                            if coll_title == coll_name_lower:
                                                self._collection_name_to_id[collection_name] = coll_id
                                                logger.info("Encontrado ID para '%s': %s", collection_name, coll_id)
                                                return coll_id
                                except (json.JSONDecodeError, KeyError):
                                    continue
            
            logger.warning("Collection '%s' não encontrada em list_collections", collection_name)
            return None
            
        except Exception as e:
            logger.error("Erro ao converter nome de collection para ID: %s", e, exc_info=True)
            return None
    
    def _truncate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Trunca resposta se muito grande para evitar erro 'message too big'"""
        try:
            # Serializar para verificar tamanho
            response_str = json.dumps(response, ensure_ascii=False)
            response_size = len(response_str.encode('utf-8'))
            
            if response_size <= MAX_MESSAGE_SIZE:
                return response
            
            logger.warning("Resposta muito grande (%d bytes), truncando...", response_size)
            
            # Se é uma resposta de ferramenta, tentar truncar o conteúdo dos resultados
            result = response.get("result", {})
            
            # Verificar se é resposta de search_collection ou search_chat_files
            if isinstance(result, dict):
                # Truncar conteúdo de resultados de busca
                if "items" in result:
                    items = result["items"]
                    truncated_items = []
                    for item in items:
                        truncated_item = item.copy()
                        content = truncated_item.get("content", "")
                        if isinstance(content, str):
                            # Limitar tamanho do conteúdo
                            if len(content) > MAX_CONTENT_LENGTH:
                                truncated_item["content"] = content[:MAX_CONTENT_LENGTH] + "... [truncado]"
                        truncated_items.append(truncated_item)
                    
                    # Se ainda muito grande, reduzir número de itens
                    if len(truncated_items) > 5:
                        truncated_items = truncated_items[:5]
                        logger.info("Reduzido número de resultados de %d para 5", len(items))
                    
                    result["items"] = truncated_items
                    logger.info("Truncados %d resultados de busca", len(truncated_items))
                
                # Truncar conteúdo direto se existir
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, str):
                        if len(content) > MAX_CONTENT_LENGTH:
                            result["content"] = content[:MAX_CONTENT_LENGTH] + "... [truncado]"
                    elif isinstance(content, list):
                        truncated_content = []
                        total_length = 0
                        max_items = 10  # Limite inicial de itens
                        for idx, item in enumerate(content):
                            if isinstance(item, dict) and "text" in item:
                                text = item["text"]
                                if isinstance(text, str):
                                    # Limitar tamanho de cada texto de forma mais agressiva
                                    max_text_length = min(MAX_CONTENT_LENGTH, (MAX_MESSAGE_SIZE // 4) - 100)
                                    if len(text) > max_text_length:
                                        item = item.copy()
                                        item["text"] = text[:max_text_length] + "... [truncado]"
                                    total_length += len(item.get("text", ""))
                                    # Limitar número de itens se muito grande
                                    if total_length > MAX_MESSAGE_SIZE // 2 or idx >= max_items:
                                        logger.info("Parando truncamento de content em item %d (tamanho total: %d)", idx, total_length)
                                        break
                            truncated_content.append(item)
                        result["content"] = truncated_content
                        logger.info("Truncado content de %d para %d itens", len(content), len(truncated_content))
            
            # Verificar tamanho novamente após truncamento
            response_str = json.dumps(response, ensure_ascii=False)
            response_size = len(response_str.encode('utf-8'))
            
            # Se ainda muito grande, tentar reduzir ainda mais
            if response_size > MAX_MESSAGE_SIZE:
                logger.warning("Resposta ainda muito grande após primeiro truncamento (%d bytes), aplicando truncamento mais agressivo...", response_size)
                
                # Reduzir ainda mais o conteúdo
                if isinstance(result, dict):
                    # Reduzir items se existir
                    if "items" in result:
                        items = result["items"]
                        if len(items) > 2:
                            result["items"] = items[:2]
                            logger.warning("Reduzido para apenas 2 resultados devido ao tamanho")
                        # Truncar ainda mais o conteúdo de cada item
                        for item in result["items"]:
                            if "content" in item and isinstance(item["content"], str):
                                if len(item["content"]) > 1000:
                                    item["content"] = item["content"][:1000] + "... [truncado]"
                    
                    # Reduzir content se existir
                    if "content" in result:
                        content = result["content"]
                        if isinstance(content, list):
                            # Manter apenas primeiros 3 itens e truncar cada um
                            result["content"] = content[:3]
                            for item in result["content"]:
                                if isinstance(item, dict) and "text" in item:
                                    text = item["text"]
                                    if isinstance(text, str) and len(text) > 5000:
                                        item["text"] = text[:5000] + "... [truncado]"
                        elif isinstance(content, str):
                            if len(content) > 10000:
                                result["content"] = content[:10000] + "... [truncado]"
                
                # Verificar tamanho novamente
                response_str = json.dumps(response, ensure_ascii=False)
                response_size = len(response_str.encode('utf-8'))
                logger.info("Tamanho após truncamento agressivo: %d bytes", response_size)
            
            if response_size > MAX_MESSAGE_SIZE:
                # Se ainda muito grande, criar resposta de erro
                logger.error("Resposta ainda muito grande após truncamento (%d bytes), retornando erro", response_size)
                return {
                    "jsonrpc": "2.0",
                    "id": response.get("id"),
                    "error": {
                        "code": -32603,
                        "message": "Resposta muito grande. Tente reduzir o número de resultados (topk) ou refinar a busca.",
                        "data": {
                            "original_size": response_size,
                            "max_size": MAX_MESSAGE_SIZE
                        }
                    }
                }
            
            logger.info("Resposta truncada para %d bytes", response_size)
            return response
            
        except Exception as e:
            logger.error("Erro ao truncar resposta: %s", e, exc_info=True)
            return response
    
    async def start(self):
        """Inicia a bridge"""
        logger.info("Iniciando Multi-WebSocket Bridge com %d endpoints e %d servidores MCP...", 
                   len(self.ws_clients), len(self.mcp_clients))
        self.running = True
        
        # Conectar a todos os servidores MCP PRIMEIRO (antes dos WebSockets)
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
        
        # AGORA conectar a todos os WebSockets (depois que os servidores estão prontos)
        for ws_client in self.ws_clients:
            endpoint_id = getattr(ws_client, 'endpoint_id', 'unknown')
            logger.info("Conectando ao WebSocket [%s]...", endpoint_id)
            ws_connected = await ws_client.connect()
            if not ws_connected:
                logger.error("Falha ao conectar ao WebSocket [%s]", endpoint_id)
            else:
                logger.info("WebSocket conectado [%s]", endpoint_id)
        
        # Verificar se pelo menos um WebSocket está conectado
        ws_connected_count = sum(1 for ws in self.ws_clients if ws.is_connected())
        if ws_connected_count == 0:
            logger.error("Nenhum WebSocket conectado")
            return False
        
        logger.info("Multi-WebSocket Bridge iniciada com sucesso (%d/%d WebSockets conectados, %d/%d servidores MCP conectados)",
                   ws_connected_count, len(self.ws_clients), connected_count, len(self.mcp_clients))
        return True
    
    async def stop(self):
        """Para a bridge"""
        logger.info("Parando Multi-WebSocket Bridge...")
        self.running = False
        
        # Desconectar todos os WebSockets
        for ws_client in self.ws_clients:
            await ws_client.disconnect()
        
        # Desconectar todos os servidores MCP
        for client in self.mcp_clients:
            await client.disconnect()
        
        logger.info("Multi-WebSocket Bridge parada")
    
    async def run(self):
        """Executa a bridge até ser interrompida"""
        if not await self.start():
            return
        
        try:
            # Manter rodando
            while self.running:
                await asyncio.sleep(1)
                
                # Verificar conexões WebSocket
                for ws_client in self.ws_clients:
                    if not ws_client.is_connected():
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

