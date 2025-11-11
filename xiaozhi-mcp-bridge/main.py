#!/usr/bin/env python3
"""
Ponto de entrada da aplicação Xiaozhi MCP Bridge
"""
import asyncio
import logging
import sys
import os
import yaml
from pathlib import Path

# Tentar carregar variáveis de ambiente do arquivo .env
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        # Verificar se SSH_PASSWORD foi carregada (sem mostrar o valor)
        ssh_pass = os.environ.get('SSH_PASSWORD')
        if ssh_pass:
            print(f"[INFO] Arquivo .env carregado - SSH_PASSWORD encontrada ({len(ssh_pass)} caracteres)")
        else:
            print("[INFO] Arquivo .env carregado - SSH_PASSWORD não encontrada")
    else:
        print(f"[INFO] Arquivo .env não encontrado em: {env_path}")
except ImportError:
    # python-dotenv não instalado, continuar sem ele
    print("[WARNING] python-dotenv não instalado - variáveis de ambiente do .env não serão carregadas")
except Exception as e:
    print(f"[WARNING] Erro ao carregar .env: {e}")

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bridge import Bridge
from bridge_multi import MultiMCPBridge


def setup_logging(config: dict):
    """Configura logging"""
    log_level = getattr(logging, config.get('level', 'INFO').upper())
    log_file = config.get('file', 'bridge.log')
    
    # Criar formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def load_config(config_path: str = 'config/config.yaml') -> dict:
    """Carrega configuração do arquivo YAML"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração não encontrado: {config_path}")
        print("Copie config/config.example.yaml para config/config.yaml e configure.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Erro ao ler arquivo de configuração: {e}")
        sys.exit(1)


def main():
    """Função principal"""
    # Carregar configuração
    config = load_config()
    
    # Configurar logging
    setup_logging(config.get('logging', {}))
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Xiaozhi MCP Bridge - Iniciando...")
    logger.info("=" * 60)
    
    # Validar configuração
    xiaozhi_config = config.get('xiaozhi', {})
    
    if not xiaozhi_config.get('websocket_url'):
        logger.error("Configuração 'xiaozhi.websocket_url' não encontrada")
        sys.exit(1)
    
    if not xiaozhi_config.get('token'):
        logger.error("Configuração 'xiaozhi.token' não encontrada")
        sys.exit(1)
    
    # Verificar se há múltiplos servidores MCP configurados
    mcp_servers_config = config.get('mcp_servers', [])
    
    if mcp_servers_config and len(mcp_servers_config) > 0:
        # Usar MultiMCPBridge para múltiplos servidores
        logger.info("Configuração multi-MCP detectada: %d servidores", len(mcp_servers_config))
        
        mcp_servers = []
        for mcp_config in mcp_servers_config:
            # Validar configuração de cada servidor
            if not mcp_config.get('name'):
                logger.error("Configuração 'name' não encontrada para servidor MCP")
                sys.exit(1)
            
            # Determinar tipo de conexão (HTTP, SSH ou local)
            if mcp_config.get('url'):
                # Servidor HTTP/HTTPS
                # Usar API key do config.yaml (já está configurada lá)
                api_key = mcp_config.get('api_key', '')
                headers = mcp_config.get('headers', {})
                
                # Garantir que API key está configurada
                if not api_key:
                    logger.error("API key não encontrada para servidor MCP HTTP: %s", mcp_config.get('name'))
                    sys.exit(1)
                
                # Garantir que Authorization header está configurado
                if 'Authorization' not in headers:
                    headers['Authorization'] = f'Bearer {api_key}'
                
                # Log para debug
                logger.info("Configurando servidor HTTP %s com API key: %s...", 
                          mcp_config.get('name'), api_key[:10] if api_key else 'VAZIA')
                
                mcp_servers.append({
                    'name': mcp_config['name'],
                    'url': mcp_config['url'],
                    'api_key': api_key,
                    'headers': headers
                })
            elif mcp_config.get('ssh_host'):
                # Servidor remoto via SSH
                ssh_port = mcp_config.get('ssh_port', 22)
                ssh_password = os.environ.get('SSH_PASSWORD') or mcp_config.get('ssh_password')
                
                # Log sobre senha SSH (sem mostrar a senha completa)
                if ssh_password:
                    logger.info("Senha SSH encontrada para servidor %s: %d caracteres", 
                              mcp_config.get('name'), len(ssh_password))
                else:
                    logger.warning("Senha SSH não encontrada para servidor %s (variável SSH_PASSWORD ou config.yaml)", 
                                 mcp_config.get('name'))
                
                mcp_servers.append({
                    'name': mcp_config['name'],
                    'ssh_host': mcp_config['ssh_host'],
                    'ssh_user': mcp_config.get('ssh_user', 'user'),
                    'ssh_command': mcp_config.get('ssh_command', ''),
                    'ssh_port': ssh_port,
                    'ssh_password': ssh_password
                })
            elif mcp_config.get('local_command'):
                # Servidor local (executar comando localmente)
                # Obter diretório base do projeto
                base_dir = os.path.dirname(os.path.abspath(__file__))
                local_cmd = mcp_config['local_command']
                
                # Converter caminho relativo para absoluto se necessário
                if 'mcp_portal_transparencia' in local_cmd:
                    # Substituir caminho relativo por absoluto
                    portal_path = os.path.join(base_dir, 'mcp_portal_transparencia', 'server.js')
                    local_cmd = local_cmd.replace('mcp_portal_transparencia/server.js', portal_path)
                
                mcp_servers.append({
                    'name': mcp_config['name'],
                    'ssh_host': 'localhost',
                    'ssh_user': os.getenv('USER', os.getenv('USERNAME', 'user')),
                    'ssh_command': local_cmd,
                    'ssh_port': 22,
                    'ssh_password': None
                })
            else:
                logger.error("Servidor MCP '%s' deve ter 'url', 'ssh_host' ou 'local_command'", mcp_config.get('name'))
                sys.exit(1)
        
        bridge = MultiMCPBridge(
            ws_url=xiaozhi_config['websocket_url'],
            ws_token=xiaozhi_config['token'],
            mcp_servers=mcp_servers
        )
    else:
        # Usar Bridge simples para um único servidor (compatibilidade)
        mcp_config = config.get('mcp_local', {})
        
        if not mcp_config.get('ssh_host'):
            logger.error("Configuração 'mcp_local.ssh_host' não encontrada")
            sys.exit(1)
        
        if not mcp_config.get('ssh_user'):
            logger.error("Configuração 'mcp_local.ssh_user' não encontrada")
            sys.exit(1)
        
        if not mcp_config.get('ssh_command'):
            logger.error("Configuração 'mcp_local.ssh_command' não encontrada")
            sys.exit(1)
        
        ssh_port = mcp_config.get('ssh_port', 22)
        ssh_password = os.environ.get('SSH_PASSWORD') or mcp_config.get('ssh_password')
        
        bridge = Bridge(
            ws_url=xiaozhi_config['websocket_url'],
            ws_token=xiaozhi_config['token'],
            ssh_host=mcp_config['ssh_host'],
            ssh_user=mcp_config['ssh_user'],
            ssh_command=mcp_config['ssh_command'],
            ssh_port=ssh_port,
            ssh_password=ssh_password
        )
    
    # Executar bridge
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("Aplicação interrompida pelo usuário")
    except Exception as e:
        logger.error("Erro fatal: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

