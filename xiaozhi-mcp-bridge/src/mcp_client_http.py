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
        # Normalizar URL: garantir que termine com / se não tiver
        url = url.rstrip('/')
        if not url.endswith('/'):
            url += '/'
        self.url = url
        self.api_key = api_key or ''
        self.custom_headers = headers or {}
        
        # Garantir que Authorization nos custom_headers tenha Bearer se não tiver
        if 'Authorization' in self.custom_headers:
            auth_val = self.custom_headers['Authorization']
            if not auth_val.startswith('Bearer '):
                self.custom_headers['Authorization'] = f"Bearer {auth_val}"
        
        # Log para debug (apenas primeiros caracteres da API key)
        if self.api_key:
            logger.info("MCPClientHTTP inicializado com API key: %s... (tamanho: %d)", self.api_key[:10], len(self.api_key))
        else:
            logger.warning("MCPClientHTTP inicializado SEM API key!")
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
            # Garantir que Authorization tenha "Bearer" se não tiver
            # Prioridade: 1) api_key, 2) custom_headers['Authorization']
            auth_header = ''
            if self.api_key:
                # Usar api_key como fonte principal
                auth_header = f"Bearer {self.api_key}"
            else:
                # Se não tem api_key, tentar usar custom_headers
                auth_header = self.custom_headers.get('Authorization', '')
                if auth_header and not auth_header.startswith('Bearer '):
                    # Se custom_headers tem Authorization mas sem "Bearer", adicionar
                    auth_header = f"Bearer {auth_header}"
            
            # Se ainda não tem Authorization válido, usar api_key mesmo que vazio (para log de erro)
            if not auth_header or auth_header == 'Bearer ':
                if self.api_key:
                    auth_header = f"Bearer {self.api_key}"
                else:
                    logger.error("Nenhuma API key configurada! Verifique api_key no config.yaml")
                    auth_header = ''
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                **{k: v for k, v in self.custom_headers.items() if k.lower() != 'authorization'}
            }
            
            # Adicionar Authorization apenas se tiver valor válido
            if auth_header:
                headers["Authorization"] = auth_header
                logger.info("Authorization header configurado: %s... (tamanho: %d)", auth_header[:30], len(auth_header))
            else:
                logger.error("ATENÇÃO: Authorization header NÃO configurado! Verifique api_key no config.yaml")
            
            # Criar sessão HTTP sem headers padrão (vamos passar em cada requisição)
            # Isso garante que os headers sejam sempre enviados corretamente
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Armazenar headers para usar em cada requisição
            self._default_headers = headers
            logger.debug("Headers padrão configurados: %s", {k: (v[:30] + '...' if len(v) > 30 else v) if k.lower() == 'authorization' else v for k, v in headers.items()})
            
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
                # Headers para a requisição - usar os headers padrão configurados
                # Isso garante que Authorization sempre seja enviado
                request_headers = self._default_headers.copy() if hasattr(self, '_default_headers') else {}
                
                # Garantir que Authorization está presente e com Bearer
                # Prioridade: 1) api_key, 2) request_headers['Authorization']
                auth_header = ''
                if self.api_key:
                    # Sempre usar api_key como fonte principal
                    auth_header = f"Bearer {self.api_key}"
                else:
                    # Se não tem api_key, tentar usar do request_headers
                    auth_header = request_headers.get('Authorization', '')
                    if auth_header and not auth_header.startswith('Bearer '):
                        auth_header = f"Bearer {auth_header}"
                
                # Se ainda não tem Authorization válido, logar erro
                if not auth_header or auth_header == 'Bearer ':
                    logger.error("API key não configurada no MCPClientHTTP! Verifique api_key no config.yaml")
                    if future:
                        request_id = message.get("id")
                        if request_id in self._pending_requests:
                            del self._pending_requests[request_id]
                    return None
                
                # Garantir que Authorization está nos headers da requisição
                request_headers['Authorization'] = auth_header
                
                # Log detalhado do Authorization header e mensagem
                auth_header_log = request_headers.get('Authorization', 'NÃO ENCONTRADO')
                method_name = message.get('method', 'unknown')
                params = message.get('params', {})
                tool_name = params.get('name', 'unknown') if isinstance(params, dict) else 'unknown'
                
                # Log completo do Authorization header (sem truncar para debug)
                logger.info("Enviando requisição HTTP POST para %s - Method: %s, Tool: %s", 
                          self.url, method_name, tool_name)
                logger.info("Authorization header completo: %s (tamanho: %d)", auth_header, len(auth_header))
                logger.info("API key usada: %s (tamanho: %d)", self.api_key, len(self.api_key) if self.api_key else 0)
                
                # Log completo dos headers antes de enviar
                logger.debug("Headers completos da requisição: %s", {k: (v[:30] + '...' if len(v) > 30 else v) if k.lower() == 'authorization' else v for k, v in request_headers.items()})
                
                # Garantir que Authorization está presente e correto antes de enviar
                if 'Authorization' not in request_headers or not request_headers['Authorization']:
                    logger.error("ERRO CRÍTICO: Authorization header não encontrado antes de enviar requisição!")
                    if future:
                        request_id = message.get("id")
                        if request_id in self._pending_requests:
                            del self._pending_requests[request_id]
                    return None
                
                # Log final antes de enviar (para debug)
                logger.debug("URL da requisição: %s", self.url)
                logger.debug("Authorization header final: %s", request_headers.get('Authorization', 'NÃO ENCONTRADO'))
                
                async with self._session.post(
                    self.url,
                    json=message,
                    headers=request_headers
                ) as response:
                    # Aceitar códigos 2xx como sucesso (200 OK, 202 Accepted, etc)
                    if response.status < 200 or response.status >= 300:
                        error_text = await response.text()
                        logger.error("Erro HTTP %d: %s", response.status, error_text)
                        if future:
                            request_id = message.get("id")
                            if request_id in self._pending_requests:
                                del self._pending_requests[request_id]
                        return None
                    
                    # Log para debug se for 202 (Accepted)
                    if response.status == 202:
                        logger.debug("Resposta HTTP 202 (Accepted) - requisição aceita e sendo processada")
                    
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

