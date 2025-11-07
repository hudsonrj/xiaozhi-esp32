"""
Classe principal Bridge que orquestra comunicação entre WebSocket e MCP
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from websocket_client import WebSocketClient
from mcp_client import MCPClient
from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class Bridge:
    """Bridge que conecta WebSocket (xiaozhi.me) e MCP local"""
    
    def __init__(self, ws_url: str, ws_token: str, 
                 ssh_host: str, ssh_user: str, ssh_command: str, ssh_port: int = 22, ssh_password: Optional[str] = None):
        self.ws_client = WebSocketClient(ws_url, ws_token)
        self.mcp_client = MCPClient(ssh_host, ssh_user, ssh_command, ssh_port, ssh_password)
        self.message_handler = MessageHandler()
        self.running = False
        
        # Mapeamento de IDs de requisição (cloud_id -> local_id)
        self.id_mapping: Dict[Any, Any] = {}
        self.reverse_id_mapping: Dict[Any, Any] = {}
        self._local_id_counter = 10000  # IDs locais começam em 10000
        
        # Configurar callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """Configura callbacks dos clientes"""
        # WebSocket callbacks
        self.ws_client.on_connected = self._on_ws_connected
        self.ws_client.on_disconnected = self._on_ws_disconnected
        self.ws_client.on_error = self._on_ws_error
        self.ws_client.on_message = self._on_ws_message
        
        # MCP callbacks
        self.mcp_client.on_message = self._on_mcp_message
        self.mcp_client.on_error = self._on_mcp_error
    
    def _on_ws_connected(self):
        """Callback quando WebSocket conecta"""
        logger.info("WebSocket conectado")
    
    def _on_ws_disconnected(self):
        """Callback quando WebSocket desconecta"""
        logger.warning("WebSocket desconectado")
    
    def _on_ws_error(self, error: str):
        """Callback de erro do WebSocket"""
        logger.error("Erro WebSocket: %s", error)
    
    def _on_mcp_error(self, error: str):
        """Callback de erro do MCP"""
        logger.error("Erro MCP: %s", error)
    
    async def _on_ws_message(self, payload: Dict[str, Any]):
        """Processa mensagem recebida do WebSocket (cloud)"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(payload):
                logger.warning("Mensagem JSON-RPC inválida do WebSocket: %s", payload)
                return
            
            # Se é uma requisição, mapear ID e enviar para MCP local
            if self.message_handler.is_request(payload):
                cloud_id = payload.get("id")
                local_id = self._get_next_local_id()
                
                # Mapear IDs
                self.id_mapping[cloud_id] = local_id
                self.reverse_id_mapping[local_id] = cloud_id
                
                # Criar nova mensagem com ID local
                local_message = payload.copy()
                local_message["id"] = local_id
                
                logger.debug("Proxy Cloud -> Local: %s (cloud_id=%s -> local_id=%s)", 
                           payload.get("method"), cloud_id, local_id)
                
                # Enviar para MCP local e aguardar resposta
                asyncio.create_task(self._forward_request_to_mcp(local_message, cloud_id))
            
            # Se é uma notificação, apenas encaminhar
            elif self.message_handler.is_notification(payload):
                logger.debug("Proxy Cloud -> Local (notification): %s", payload.get("method"))
                asyncio.create_task(self._forward_notification_to_mcp(payload))
            
            # Se é uma resposta, não deveria acontecer (cloud não envia respostas)
            else:
                logger.warning("Resposta recebida do WebSocket (inesperado): %s", payload)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do WebSocket: %s", e)
    
    def _on_mcp_message(self, message: Dict[str, Any]):
        """Processa mensagem recebida do MCP local"""
        try:
            # Validar mensagem JSON-RPC
            if not self.message_handler.validate_jsonrpc(message):
                logger.warning("Mensagem JSON-RPC inválida do MCP: %s", message)
                return
            
            # Se é uma resposta, mapear ID de volta e enviar para cloud
            if self.message_handler.is_response(message):
                local_id = message.get("id")
                cloud_id = self.reverse_id_mapping.get(local_id)
                
                if cloud_id is None:
                    logger.warning("ID local não encontrado no mapeamento: %s", local_id)
                    return
                
                # Criar mensagem com ID cloud
                cloud_message = message.copy()
                cloud_message["id"] = cloud_id
                
                # Remover do mapeamento
                del self.id_mapping[cloud_id]
                del self.reverse_id_mapping[local_id]
                
                logger.debug("Proxy Local -> Cloud: resposta (local_id=%s -> cloud_id=%s)", 
                           local_id, cloud_id)
                
                # Enviar para cloud
                asyncio.create_task(self._forward_response_to_cloud(cloud_message))
            
            # Se é uma notificação, encaminhar para cloud
            elif self.message_handler.is_notification(message):
                logger.debug("Proxy Local -> Cloud (notification): %s", message.get("method"))
                asyncio.create_task(self._forward_notification_to_cloud(message))
            
            # Se é uma requisição, não deveria acontecer (MCP local não envia requisições)
            else:
                logger.warning("Requisição recebida do MCP (inesperado): %s", message)
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do MCP: %s", e)
    
    async def _forward_request_to_mcp(self, local_message: Dict[str, Any], cloud_id: Any):
        """Encaminha requisição do cloud para MCP local"""
        try:
            response = await self.mcp_client.send_message(local_message)
            
            if response:
                # Mapear ID de volta
                local_id = response.get("id")
                if local_id in self.reverse_id_mapping:
                    cloud_id = self.reverse_id_mapping[local_id]
                    cloud_response = response.copy()
                    cloud_response["id"] = cloud_id
                    
                    # Remover do mapeamento
                    del self.id_mapping[cloud_id]
                    del self.reverse_id_mapping[local_id]
                    
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
    
    async def _forward_notification_to_mcp(self, notification: Dict[str, Any]):
        """Encaminha notificação do cloud para MCP local"""
        try:
            await self.mcp_client.send_message(notification)
        except Exception as e:
            logger.error("Erro ao encaminhar notificação para MCP: %s", e)
    
    async def _forward_response_to_cloud(self, response: Dict[str, Any]):
        """Encaminha resposta do MCP local para cloud"""
        try:
            # Enviar JSON-RPC direto (protocolo do endpoint /mcp/)
            await self.ws_client.send_message(response)
            logger.debug("Resposta enviada para cloud: %s", response.get("id"))
        except Exception as e:
            logger.error("Erro ao encaminhar resposta para cloud: %s", e)
    
    async def _forward_notification_to_cloud(self, notification: Dict[str, Any]):
        """Encaminha notificação do MCP local para cloud"""
        try:
            # Enviar JSON-RPC direto (protocolo do endpoint /mcp/)
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
        logger.info("Iniciando Bridge...")
        self.running = True
        
        # Conectar ao WebSocket
        ws_connected = await self.ws_client.connect()
        if not ws_connected:
            logger.error("Falha ao conectar ao WebSocket")
            return False
        
        # Conectar ao MCP local
        mcp_connected = await self.mcp_client.connect()
        if not mcp_connected:
            logger.error("Falha ao conectar ao servidor MCP")
            await self.ws_client.disconnect()
            return False
        
        # Inicializar sessão MCP
        mcp_initialized = await self.mcp_client.initialize()
        if not mcp_initialized:
            logger.error("Falha ao inicializar sessão MCP")
            await self.mcp_client.disconnect()
            await self.ws_client.disconnect()
            return False
        
        logger.info("Bridge iniciada com sucesso")
        return True
    
    async def stop(self):
        """Para a bridge"""
        logger.info("Parando Bridge...")
        self.running = False
        
        await self.mcp_client.disconnect()
        await self.ws_client.disconnect()
        
        logger.info("Bridge parada")
    
    async def run(self):
        """Executa a bridge até ser interrompida"""
        if not await self.start():
            return
        
        try:
            # Manter rodando
            while self.running:
                await asyncio.sleep(1)
                
                # Verificar conexões (com delay para evitar reconexões múltiplas)
                if not self.ws_client.is_connected():
                    # WebSocket tem reconexão automática, não precisa fazer nada aqui
                    pass
                
                if not self.mcp_client.connected:
                    logger.warning("MCP desconectado, tentando reconectar...")
                    try:
                        if await self.mcp_client.connect():
                            if not await self.mcp_client.initialize():
                                logger.error("Falha ao inicializar sessão MCP após reconexão")
                    except Exception as e:
                        logger.error("Erro ao reconectar MCP: %s", e)
        
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
        except Exception as e:
            logger.error("Erro fatal na bridge: %s", e)
        finally:
            await self.stop()

