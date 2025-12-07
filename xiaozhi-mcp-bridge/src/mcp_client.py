"""
Cliente MCP para conectar ao servidor MCP local via SSH/STDIO
"""
import asyncio
import logging
import subprocess
import os
from typing import Optional, Callable, Dict, Any
from message_handler import MessageHandler
import paramiko
from io import StringIO

logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente MCP que se conecta via SSH/STDIO"""
    
    def __init__(self, ssh_host: str, ssh_user: str, ssh_command: str, ssh_port: int = 22, ssh_password: Optional[str] = None):
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_command = ssh_command
        self.ssh_port = ssh_port
        self.ssh_password = ssh_password
        self.process: Optional[subprocess.Popen] = None
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.ssh_channel: Optional[paramiko.Channel] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.message_handler = MessageHandler()
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self._read_task: Optional[asyncio.Task] = None
        self._request_id_counter = 0
        self._pending_requests: Dict[Any, asyncio.Future] = {}
    
    async def connect(self) -> bool:
        """Conecta ao servidor MCP via SSH/STDIO"""
        try:
            logger.info("Conectando ao servidor MCP via SSH: %s@%s:%d:%s", 
                       self.ssh_user, self.ssh_host, self.ssh_port, self.ssh_command)
            
            # Log sobre senha (sem mostrar a senha completa)
            if self.ssh_password:
                logger.debug("Senha SSH configurada: %s caracteres", len(self.ssh_password))
            else:
                logger.warning("Senha SSH não configurada - tentando conexão sem autenticação")
            
            # Usar paramiko se tiver senha, senão usar subprocess
            if self.ssh_password:
                return await self._connect_with_paramiko()
            else:
                return await self._connect_with_subprocess()
            
        except Exception as e:
            logger.error("Erro ao conectar ao servidor MCP: %s", e, exc_info=True)
            self.connected = False
            if self.on_error:
                self.on_error(f"Erro ao conectar: {str(e)}")
            return False
    
    async def _connect_with_paramiko(self) -> bool:
        """Conecta usando paramiko (suporta senha)"""
        try:
            logger.info("Usando paramiko para conectar com senha SSH")
            # Criar cliente SSH
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Conectar em thread separada (paramiko não é async nativo)
            logger.debug("Conectando SSH via paramiko: %s@%s:%d", self.ssh_user, self.ssh_host, self.ssh_port)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.ssh_client.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=30,  # Aumentar timeout de conexão SSH
                    look_for_keys=False,
                    allow_agent=False
                )
            )
            logger.info("Conexão SSH estabelecida com sucesso")
            
            # Executar comando e obter canal
            transport = self.ssh_client.get_transport()
            if not transport:
                logger.error("Falha ao obter transporte SSH")
                return False
            
            logger.debug("Executando comando remoto: %s", self.ssh_command)
            self.ssh_channel = transport.open_session()
            self.ssh_channel.exec_command(self.ssh_command)
            
            # Aguardar um pouco para o comando iniciar
            await asyncio.sleep(0.5)
            
            # Verificar se o canal está ativo
            if self.ssh_channel.closed:
                logger.error("Canal SSH fechado imediatamente após execução")
                return False
            
            logger.debug("Canal SSH aberto e pronto")
            
            # Criar StreamReader para ler do canal
            self.reader = asyncio.StreamReader()
            
            # Task para ler do canal SSH e alimentar reader
            async def feed_reader():
                try:
                    logger.debug("Iniciando feed_reader para canal SSH")
                    while self.connected and self.ssh_channel and not self.ssh_channel.closed:
                        if self.ssh_channel.recv_ready():
                            data = self.ssh_channel.recv(4096)
                            if not data:
                                logger.debug("Nenhum dado recebido do canal SSH")
                                break
                            logger.debug("Dados recebidos do canal SSH: %d bytes", len(data))
                            self.reader.feed_data(data)
                        else:
                            await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error("Erro ao alimentar reader do canal SSH: %s", e, exc_info=True)
                finally:
                    logger.debug("feed_reader terminando")
                    if not self.reader.at_eof():
                        self.reader.feed_eof()
            
            # Iniciar task para alimentar reader
            asyncio.create_task(feed_reader())
            
            # Task para monitorar stderr do canal SSH
            async def monitor_stderr():
                try:
                    logger.debug("Iniciando monitoramento de stderr do canal SSH")
                    while self.connected and self.ssh_channel and not self.ssh_channel.closed:
                        if self.ssh_channel.recv_stderr_ready():
                            data = self.ssh_channel.recv_stderr(4096)
                            if data:
                                error_msg = data.decode('utf-8', errors='ignore').strip()
                                if error_msg:
                                    logger.warning("SSH stderr (paramiko): %s", error_msg)
                        await asyncio.sleep(0.1)
                except Exception as e:
                    logger.debug("Erro ao monitorar stderr: %s", e)
            
            asyncio.create_task(monitor_stderr())
            
            self.connected = True
            
            # Iniciar task de leitura
            self._read_task = asyncio.create_task(self._read_loop())
            
            logger.info("Conectado ao servidor MCP com sucesso (paramiko)")
            return True
            
        except Exception as e:
            logger.error("Erro ao conectar com paramiko: %s", e, exc_info=True)
            return False
    
    async def _connect_with_subprocess(self) -> bool:
        """Conecta usando subprocess (quando não tem senha)"""
        try:
            # Se for localhost, executar comando diretamente (sem SSH)
            if self.ssh_host == "localhost" or self.ssh_host == "127.0.0.1":
                import platform
                import shlex
                if platform.system() == 'Windows':
                    # Windows: dividir comando em partes e executar
                    clean_command = self.ssh_command
                    
                    # Detectar e corrigir caminhos duplicados de forma robusta
                    import re
                    # Padrão para detectar duplicação: C:\path\"C:\path\file.py
                    # Ou: C:\path\C:\path\file.py (sem aspas intermediárias)
                    duplicate_pattern1 = r'([A-Z]:[^"]+)"([A-Z]:[^"]+server\.py)'
                    duplicate_pattern2 = r'([A-Z]:[^"]+)([A-Z]:[^"]+server\.py)'
                    
                    match1 = re.search(duplicate_pattern1, clean_command)
                    match2 = re.search(duplicate_pattern2, clean_command)
                    
                    if match1 or match2:
                        logger.warning("Caminho duplicado detectado no comando: %s", clean_command)
                        # Encontrar TODOS os caminhos que terminam com server.py
                        all_paths = re.findall(r'[A-Z]:[^"]*server\.py', clean_command)
                        if all_paths:
                            # Usar sempre o ÚLTIMO caminho encontrado (deve ser o correto)
                            correct_path = all_paths[-1]
                            # Determinar comando python
                            python_cmd = 'python'
                            if 'python3' in clean_command.lower():
                                python_cmd = 'python3'
                            # Reconstruir comando limpo SEM aspas duplicadas
                            clean_command = f'{python_cmd} "{correct_path}"'
                            logger.info("Comando corrigido: %s", clean_command)
                    
                    # Processar o comando - sempre extrair python e caminho manualmente
                    python_match = re.search(r'(python3?)\s+"([^"]+server\.py)"', clean_command)
                    if python_match:
                        python_cmd = python_match.group(1)
                        path = python_match.group(2)
                        # Garantir que o caminho não está duplicado
                        if path.count('C:') > 1:
                            path_parts = re.findall(r'[A-Z]:[^"]*server\.py', path)
                            if path_parts:
                                path = path_parts[-1]
                        cmd = [python_cmd, path]
                        logger.debug("Comando processado manualmente: %s", cmd)
                    else:
                        # Tentar sem aspas
                        python_match2 = re.search(r'(python3?)\s+([A-Z]:[^"]*server\.py)', clean_command)
                        if python_match2:
                            python_cmd = python_match2.group(1)
                            path = python_match2.group(2)
                            # Garantir que o caminho não está duplicado
                            if path.count('C:') > 1:
                                path_parts = re.findall(r'[A-Z]:[^"]*server\.py', path)
                                if path_parts:
                                    path = path_parts[-1]
                            cmd = [python_cmd, path]
                            logger.debug("Comando processado (sem aspas): %s", cmd)
                        else:
                            # Fallback: tentar shlex
                            try:
                                parts = shlex.split(clean_command, posix=False)
                                cmd = parts
                            except Exception as e:
                                logger.warning("Erro ao processar comando com shlex: %s", e)
                                # Último fallback: dividir por espaços
                                cmd = clean_command.split()
                else:
                    # Unix: executar via shell
                    cmd = ["/bin/bash", "-c", self.ssh_command]
                
                logger.info("Executando comando local: %s", self.ssh_command)
                logger.debug("Comando processado: %s", cmd)
            else:
                # Construir comando SSH para servidor remoto
                ssh_cmd = [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(self.ssh_port),
                    f"{self.ssh_user}@{self.ssh_host}",
                    self.ssh_command
                ]
                cmd = ssh_cmd
            
            # Criar processo assíncrono
            # Para comandos locais, definir diretório de trabalho como raiz do projeto
            cwd = None
            if self.ssh_host == "localhost" or self.ssh_host == "127.0.0.1":
                # Obter diretório raiz do projeto (2 níveis acima de src/)
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(script_dir))
                cwd = project_root
            
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Verificar se processo foi criado corretamente
            if not self.process.stdout or not self.process.stdin:
                logger.error("Processo SSH não retornou stdout/stdin válidos")
                return False
            
            # Criar StreamReader manualmente
            self.reader = asyncio.StreamReader()
            
            # Criar uma task para ler do stdout e alimentar o reader
            async def feed_reader():
                try:
                    while self.connected and self.process and self.process.returncode is None:
                        if self.process.stdout:
                            data = await self.process.stdout.read(4096)
                            if not data:
                                break
                            self.reader.feed_data(data)
                        else:
                            await asyncio.sleep(0.1)
                except Exception as e:
                    logger.debug("Erro ao alimentar reader: %s", e)
                finally:
                    if not self.reader.at_eof():
                        self.reader.feed_eof()
            
            # Iniciar task para alimentar reader
            asyncio.create_task(feed_reader())
            
            # Iniciar task de monitoramento de stderr
            asyncio.create_task(self._monitor_stderr())
            
            self.connected = True
            
            # Iniciar task de leitura
            self._read_task = asyncio.create_task(self._read_loop())
            
            logger.info("Conectado ao servidor MCP com sucesso (subprocess)")
            return True
            
        except Exception as e:
            logger.error("Erro ao conectar com subprocess: %s", e, exc_info=True)
            return False
    
    async def _monitor_stderr(self):
        """Monitora stderr do processo SSH para detectar erros"""
        try:
            if self.process and self.process.stderr:
                while self.connected and self.process and self.process.returncode is None:
                    line = await self.process.stderr.readline()
                    if not line:
                        break
                    error_msg = line.decode('utf-8', errors='ignore').strip()
                    if error_msg:
                        logger.warning("SSH stderr: %s", error_msg)
        except Exception as e:
            logger.debug("Erro ao monitorar stderr: %s", e)
    
    async def _read_loop(self):
        """Loop de leitura de mensagens do servidor MCP"""
        buffer = ""
        try:
            # Verificar se está usando paramiko ou subprocess
            using_paramiko = self.ssh_channel is not None
            using_subprocess = self.process is not None
            
            while self.connected and (using_paramiko or (using_subprocess and self.process.returncode is None)):
                try:
                    # Ler dados do stdout
                    if self.reader:
                        try:
                            data = await asyncio.wait_for(
                                self.reader.read(4096),
                                timeout=1.0
                            )
                            if not data:
                                # Verificar se processo ainda está rodando
                                if self.process.returncode is not None:
                                    logger.warning("Processo SSH terminou com código: %d", self.process.returncode)
                                    break
                                continue
                            
                            buffer += data.decode('utf-8', errors='ignore')
                            
                            # Processar linhas completas (mensagens JSON-RPC são separadas por \n)
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                if line:
                                    await self._process_message(line)
                        except asyncio.TimeoutError:
                            # Timeout é normal, continuar
                            continue
                        except BrokenPipeError:
                            logger.warning("Pipe quebrado, desconectando")
                            break
                        except Exception as e:
                            logger.error("Erro ao ler dados: %s", e, exc_info=True)
                            break
                    else:
                        await asyncio.sleep(0.1)
                                
                except Exception as e:
                    logger.error("Erro no loop de leitura: %s", e, exc_info=True)
                    break
                    
        except Exception as e:
            logger.error("Erro fatal no loop de leitura: %s", e, exc_info=True)
        finally:
            self.connected = False
            if self.on_error:
                self.on_error("Conexão com servidor MCP perdida")
    
    async def _process_message(self, line: str):
        """Processa uma mensagem recebida"""
        message = self.message_handler.parse_message(line)
        if not message:
            return
        
        if not self.message_handler.validate_jsonrpc(message):
            logger.warning("Mensagem JSON-RPC inválida recebida: %s", line)
            return
        
        # Se é uma resposta, verificar se há uma requisição pendente
        if self.message_handler.is_response(message):
            request_id = message.get("id")
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(message)
                return
        
        # Se é uma notificação ou mensagem não esperada, chamar callback
        if self.on_message:
            self.on_message(message)
    
    async def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Envia uma mensagem e aguarda resposta"""
        # Verificar conexão (paramiko ou subprocess)
        if not self.connected:
            logger.error("Não conectado ao servidor MCP")
            return None
        
        if self.ssh_channel is None and (not self.process or not self.process.stdin):
            logger.error("Canal de comunicação não disponível")
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
            
            # Formatar e enviar mensagem
            message_str = self.message_handler.format_message(message)
            if not message_str:
                logger.error("Falha ao formatar mensagem")
                return None
            
            # Enviar com newline (padrão STDIO)
            try:
                if self.ssh_channel and not self.ssh_channel.closed:
                    # Usar paramiko
                    data = (message_str + "\n").encode('utf-8')
                    self.ssh_channel.send(data)
                elif self.process and self.process.stdin:
                    # Usar subprocess
                    data = (message_str + "\n").encode('utf-8')
                    self.process.stdin.write(data)
                    await self.process.stdin.drain()
                else:
                    logger.error("Canal stdin não disponível")
                    self.connected = False
                    return None
            except BrokenPipeError:
                logger.error("Pipe quebrado ao enviar mensagem")
                self.connected = False
                return None
            except Exception as e:
                logger.error("Erro ao enviar mensagem: %s", e, exc_info=True)
                self.connected = False
                return None
            
            logger.debug("Mensagem enviada ao servidor MCP: %s", message_str)
            
            # Se é requisição, aguardar resposta
            if future:
                try:
                    # Aumentar timeout para 60 segundos (servidores remotos podem demorar mais)
                    response = await asyncio.wait_for(future, timeout=60.0)
                    return response
                except asyncio.TimeoutError:
                    logger.error("Timeout aguardando resposta do servidor MCP (60s)")
                    request_id = message.get("id")
                    if request_id in self._pending_requests:
                        del self._pending_requests[request_id]
                    return None
            
            return None
            
        except Exception as e:
            logger.error("Erro ao enviar mensagem ao servidor MCP: %s", e)
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
            logger.info("Sessão MCP inicializada com sucesso")
            return True
        else:
            logger.error("Falha ao inicializar sessão MCP")
            return False
    
    async def disconnect(self):
        """Desconecta do servidor MCP"""
        self.connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        # Fechar canal SSH (paramiko)
        if self.ssh_channel:
            try:
                self.ssh_channel.close()
            except Exception as e:
                logger.debug("Erro ao fechar canal SSH: %s", e)
        
        # Fechar cliente SSH (paramiko)
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception as e:
                logger.debug("Erro ao fechar cliente SSH: %s", e)
        
        # Fechar subprocess
        if self.process and self.process.stdin:
            try:
                self.process.stdin.close()
                await self.process.stdin.wait_closed()
            except Exception as e:
                logger.debug("Erro ao fechar stdin: %s", e)
        
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            except Exception as e:
                logger.error("Erro ao finalizar processo SSH: %s", e)
        
        logger.info("Desconectado do servidor MCP")

