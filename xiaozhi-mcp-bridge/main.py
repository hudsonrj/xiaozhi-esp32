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
            
            # Determinar tipo de conexão (SSH ou local)
            if mcp_config.get('ssh_host'):
                # Servidor remoto via SSH
                ssh_port = mcp_config.get('ssh_port', 22)
                ssh_password = os.environ.get('SSH_PASSWORD') or mcp_config.get('ssh_password')
                
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
                logger.error("Servidor MCP '%s' deve ter 'ssh_host' ou 'local_command'", mcp_config.get('name'))
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

