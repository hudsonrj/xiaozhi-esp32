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
    mcp_config = config.get('mcp_local', {})
    
    if not xiaozhi_config.get('websocket_url'):
        logger.error("Configuração 'xiaozhi.websocket_url' não encontrada")
        sys.exit(1)
    
    if not xiaozhi_config.get('token'):
        logger.error("Configuração 'xiaozhi.token' não encontrada")
        sys.exit(1)
    
    if not mcp_config.get('ssh_host'):
        logger.error("Configuração 'mcp_local.ssh_host' não encontrada")
        sys.exit(1)
    
    if not mcp_config.get('ssh_user'):
        logger.error("Configuração 'mcp_local.ssh_user' não encontrada")
        sys.exit(1)
    
    if not mcp_config.get('ssh_command'):
        logger.error("Configuração 'mcp_local.ssh_command' não encontrada")
        sys.exit(1)
    
    # Criar bridge
    ssh_port = mcp_config.get('ssh_port', 22)
    # Ler senha SSH da variável de ambiente ou do config (prioridade para env)
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

