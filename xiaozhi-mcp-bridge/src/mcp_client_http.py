"""
Cliente MCP para conectar ao servidor MCP via HTTP/HTTPS
"""
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from message_handler import MessageHandler
import aiohttp
import json

logger = logging.getLogger(__name__)


class MCPClientHTTP:
    """Cliente MCP que se conecta via HTTP/HTTPS"""
    
    def __init__(self, url: str, api_key: str, headers: Optional[Dict[str, str]] = None):
        self.url = url.rstrip('/')  # Remover barra final se houver
        self.api_key = api_key
        self.custom_headers = headers or {}
        self.connected = False
        self.message_handler = MessageHandler()
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self._request_id_counter = 0
        self._pending_requests: Dict[Any, asyncio.Future] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Conecta ao servidor MCP via HTTP"""
        try:
            logger.info("Conectando ao servidor MCP via HTTP: %s", self.url)
            
            # Criar sessão HTTP
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self.api_key}",
                **self.custom_headers
            }
            
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            self.connected = True
            logger.info("Conectado ao servidor MCP HTTP com sucesso")
            return True
            
        except Exception as e:
            logger.error("Erro ao conectar ao servidor MCP HTTP: %s", e, exc_info=True)
            self.connected = False
            if self.on_error:
                self.on_error(f"Erro ao conectar: {str(e)}")
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Envia uma mensagem e aguarda resposta"""
        if not self.connected or not self._session:
            logger.error("Não conectado ao servidor MCP HTTP")
            return None
        
        try:
            # Validar mensagem
            if not self.message_handler.validate_jsonrpc(message):
                logger.error("Mensagem JSON-RPC inválida: %s", message)
                return None
            
            # Se é uma requisição, criar future para aguardar resposta
            future = None
            if self.message_handler.is_request(message):
                request_id = message.get("id")
                future = asyncio.Future()
                self._pending_requests[request_id] = future
            
            # Enviar requisição HTTP POST
            try:
                async with self._session.post(
                    self.url,
                    json=message,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Erro HTTP %d: %s", response.status, error_text)
                        if future:
                            request_id = message.get("id")
                            if request_id in self._pending_requests:
                                del self._pending_requests[request_id]
                        return None
                    
                    # Verificar tipo de conteúdo
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    # Ler resposta (pode ser JSON ou SSE)
                    try:
                        if 'text/event-stream' in content_type:
                            # Processar Server-Sent Events (SSE)
                            response_text = await response.text()
                            response_data = self._parse_sse_response(response_text)
                            if not response_data:
                                logger.error("Falha ao parsear resposta SSE: %s", response_text[:200])
                                if future:
                                    request_id = message.get("id")
                                    if request_id in self._pending_requests:
                                        del self._pending_requests[request_id]
                                return None
                        else:
                            # Resposta JSON normal
                            response_data = await response.json()
                    except Exception as e:
                        error_text = await response.text()
                        logger.error("Erro ao fazer parse da resposta: %s. Resposta: %s", e, error_text[:500])
                        if future:
                            request_id = message.get("id")
                            if request_id in self._pending_requests:
                                del self._pending_requests[request_id]
                        return None
                    
                    logger.debug("Resposta recebida do servidor MCP HTTP: %s", response_data)
                    
                    # Se é uma requisição, aguardar resposta já foi feito acima
                    # A resposta HTTP já contém a resposta JSON-RPC
                    if future:
                        if not future.done():
                            future.set_result(response_data)
                        return response_data
                    
                    return response_data
                    
            except aiohttp.ClientError as e:
                logger.error("Erro ao enviar requisição HTTP: %s", e, exc_info=True)
                if future:
                    request_id = message.get("id")
                    if request_id in self._pending_requests:
                        del self._pending_requests[request_id]
                self.connected = False
                if self.on_error:
                    self.on_error(f"Erro HTTP: {str(e)}")
                return None
            except Exception as e:
                logger.error("Erro ao processar resposta HTTP: %s", e, exc_info=True)
                if future:
                    request_id = message.get("id")
                    if request_id in self._pending_requests:
                        del self._pending_requests[request_id]
                return None
            
        except Exception as e:
            logger.error("Erro ao enviar mensagem ao servidor MCP HTTP: %s", e)
            return None
    
    async def initialize(self) -> bool:
        """Inicializa a sessão MCP"""
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "xiaozhi-mcp-bridge",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self.send_message(init_message)
        if response and "result" in response:
            logger.info("Sessão MCP HTTP inicializada com sucesso")
            return True
        else:
            logger.error("Falha ao inicializar sessão MCP HTTP: %s", response)
            return False
    
    async def disconnect(self):
        """Desconecta do servidor MCP"""
        self.connected = False
        
        # Cancelar requisições pendentes
        for request_id, future in list(self._pending_requests.items()):
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        # Fechar sessão HTTP
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.debug("Erro ao fechar sessão HTTP: %s", e)
        
        logger.info("Desconectado do servidor MCP HTTP")
    
    def _parse_sse_response(self, sse_text: str) -> Optional[Dict[str, Any]]:
        """Parse Server-Sent Events (SSE) e extrai JSON-RPC"""
        try:
            lines = sse_text.strip().split('\n')
            data_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('data: '):
                    # Extrair JSON após "data: "
                    json_str = line[6:]  # Remove "data: "
                    data_lines.append(json_str)
            
            # Se encontrou dados SSE, parsear o primeiro JSON válido
            for json_str in data_lines:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
            
            # Se não encontrou formato SSE, tentar parsear como JSON direto
            try:
                return json.loads(sse_text)
            except json.JSONDecodeError:
                pass
            
            return None
        except Exception as e:
            logger.error("Erro ao parsear SSE: %s", e)
            return None

