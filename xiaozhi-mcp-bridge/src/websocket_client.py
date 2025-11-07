"""
Cliente WebSocket para conectar ao xiaozhi.me
"""
import asyncio
import logging
import json
from typing import Optional, Callable, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol
from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Cliente WebSocket para xiaozhi.me"""
    
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.session_id: Optional[str] = None
        self.message_handler = MessageHandler()
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self._reconnect_delay = 5
        self._max_reconnect_delay = 60
        self._reconnect_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None
    
    def _get_websocket_url(self) -> str:
        """Monta a URL completa do WebSocket com token"""
        separator = "&" if "?" in self.url else "?"
        return f"{self.url}{separator}token={self.token}"
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket da xiaozhi.me"""
        try:
            url = self._get_websocket_url()
            logger.info("Conectando ao WebSocket: %s", url.split("token=")[0] + "token=***")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.connected = True
            logger.info("Conectado ao WebSocket com sucesso")
            
            # Enviar mensagem "hello" para anunciar suporte MCP
            await self._send_hello()
            
            if self.on_connected:
                self.on_connected()
            
            # Iniciar loop de leitura apenas se não houver uma task já rodando
            if self._read_task is None or self._read_task.done():
                self._read_task = asyncio.create_task(self._read_loop())
            
            return True
            
        except Exception as e:
            logger.error("Erro ao conectar ao WebSocket: %s", e)
            self.connected = False
            if self.on_error:
                self.on_error(f"Erro ao conectar: {str(e)}")
            return False
    
    async def _read_loop(self):
        """Loop de leitura de mensagens do WebSocket"""
        try:
            while self.connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    
                    # WebSocket pode receber texto ou binário
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    
                    # Log todas as mensagens recebidas para debug
                    logger.debug("Mensagem recebida do servidor: %s", message[:500])
                    
                    await self._process_message(message)
                    
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning("Conexão WebSocket fechada: code=%s, reason=%s", e.code, e.reason)
                    break
                except Exception as e:
                    logger.error("Erro ao ler mensagem do WebSocket: %s", e, exc_info=True)
                    break
                    
        except Exception as e:
            logger.error("Erro fatal no loop de leitura WebSocket: %s", e)
        finally:
            self.connected = False
            if self.on_disconnected:
                self.on_disconnected()
            
            # Tentar reconectar
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())
    
    async def _send_hello(self):
        """Envia mensagem hello para anunciar suporte MCP"""
        try:
            hello_message = {
                "type": "hello",
                "version": 1,
                "features": {
                    "mcp": True
                },
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,
                    "channels": 1,
                    "frame_duration": 60
                }
            }
            message_str = self.message_handler.format_message(hello_message)
            if message_str and self.websocket:
                await self.websocket.send(message_str)
                logger.info("Mensagem 'hello' enviada ao servidor")
        except Exception as e:
            logger.error("Erro ao enviar mensagem hello: %s", e)
    
    async def _process_message(self, message_str: str):
        """Processa uma mensagem recebida do WebSocket"""
        try:
            message = self.message_handler.parse_message(message_str)
            if not message:
                logger.warning("Falha ao fazer parse da mensagem: %s", message_str[:200])
                return
            
            message_type = message.get("type")
            
            # Se tem "type", pode ser "hello" ou "mcp"
            if message_type == "hello":
                self.session_id = message.get("session_id")
                logger.info("✅ Recebida mensagem 'hello' do servidor, session_id: %s", self.session_id)
                return
            
            if message_type == "mcp":
                payload = self.message_handler.extract_mcp_payload(message)
                if payload and self.on_message:
                    await self.on_message(payload)
                return
            
            # Se não tem "type" mas tem "jsonrpc", é uma mensagem JSON-RPC direta (protocolo MCP)
            if "jsonrpc" in message and message.get("jsonrpc") == "2.0":
                method = message.get("method")
                
                # Responder ao initialize
                if method == "initialize":
                    logger.info("Recebido 'initialize' do servidor, respondendo...")
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "serverInfo": {
                                "name": "xiaozhi-mcp-bridge",
                                "version": "1.0.0"
                            }
                        }
                    }
                    await self._send_jsonrpc_response(response)
                    return
                
                # Responder ao ping
                if method == "ping":
                    logger.debug("Recebido 'ping' do servidor, respondendo...")
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {}
                    }
                    await self._send_jsonrpc_response(response)
                    return
                
                # Outras mensagens JSON-RPC (requisições MCP) - encaminhar para bridge
                if self.on_message:
                    # Chamar callback de forma assíncrona se for corrotina, senão chamar diretamente
                    if asyncio.iscoroutinefunction(self.on_message):
                        await self.on_message(message)
                    else:
                        # Se não for async, criar task
                        asyncio.create_task(self._call_callback_safe(self.on_message, message))
                else:
                    logger.warning("on_message callback não configurado, ignorando mensagem: %s", method)
                return
            
            # Mensagem desconhecida
            logger.debug("Mensagem recebida (tipo: %s): %s", message_type, self.message_handler.format_message(message)[:200])
                
        except Exception as e:
            logger.error("Erro ao processar mensagem do WebSocket: %s", e, exc_info=True)
    
    async def _call_callback_safe(self, callback, message):
        """Chama callback de forma segura"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
        except Exception as e:
            logger.error("Erro ao chamar callback: %s", e, exc_info=True)
    
    async def _send_jsonrpc_response(self, response: Dict[str, Any]):
        """Envia uma resposta JSON-RPC diretamente ao WebSocket"""
        try:
            message_str = self.message_handler.format_message(response)
            if message_str and self.websocket:
                await self.websocket.send(message_str)
                logger.debug("Resposta JSON-RPC enviada: %s", message_str[:200])
        except Exception as e:
            logger.error("Erro ao enviar resposta JSON-RPC: %s", e)
    
    async def send_message(self, payload: Dict[str, Any]) -> bool:
        """Envia uma mensagem MCP via WebSocket"""
        if not self.connected or not self.websocket:
            logger.error("Não conectado ao WebSocket")
            return False
        
        try:
            # Se o payload já é JSON-RPC direto (tem jsonrpc), enviar diretamente
            # Caso contrário, envolver em formato MCP
            if "jsonrpc" in payload and payload.get("jsonrpc") == "2.0":
                # Enviar JSON-RPC direto (protocolo do endpoint /mcp/)
                message_str = self.message_handler.format_message(payload)
            else:
                # Envolver em formato MCP do xiaozhi.me (se tiver session_id)
                mcp_message = self.message_handler.wrap_mcp_payload(payload, self.session_id or "")
                message_str = self.message_handler.format_message(mcp_message)
            
            if not message_str:
                return False
            
            await self.websocket.send(message_str)
            logger.debug("Mensagem enviada ao WebSocket: %s", message_str[:200])
            return True
            
        except Exception as e:
            logger.error("Erro ao enviar mensagem ao WebSocket: %s", e)
            self.connected = False
            if self.on_error:
                self.on_error(f"Erro ao enviar mensagem: {str(e)}")
            return False
    
    async def _reconnect(self):
        """Tenta reconectar ao WebSocket"""
        delay = self._reconnect_delay
        while not self.connected:
            logger.info("Tentando reconectar em %d segundos...", delay)
            await asyncio.sleep(delay)
            
            if await self.connect():
                delay = self._reconnect_delay  # Reset delay
                break
            else:
                delay = min(delay * 2, self._max_reconnect_delay)
    
    async def disconnect(self):
        """Desconecta do WebSocket"""
        self.connected = False
        
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error("Erro ao fechar WebSocket: %s", e)
        
        logger.info("Desconectado do WebSocket")
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self.connected and self.websocket is not None

