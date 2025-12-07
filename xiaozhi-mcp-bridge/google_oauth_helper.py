#!/usr/bin/env python3
"""
Módulo auxiliar para autenticação OAuth 2.0 do Google
Gerencia o fluxo de autenticação com credenciais de cliente (client ID e secret)
"""
import os
import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError

# Credenciais OAuth 2.0
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '581001865946-e0lnpqifbs4i8r82hg37qo4ku86fok66.apps.googleusercontent.com')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'SUvj2I3bxbZ-Hjte_OxoAnlO')

# Caminho para salvar o token
def get_token_file_path(service_name: str = "google") -> Path:
    """Retorna o caminho do arquivo de token"""
    script_dir = Path(__file__).parent
    return script_dir / f".{service_name}_token.json"


def get_oauth_credentials(scopes: list, service_name: str = "google") -> Credentials:
    """
    Obtém credenciais OAuth 2.0 para os escopos especificados.
    
    Se o token já existir e for válido, reutiliza.
    Caso contrário, abre uma janela do navegador para autenticação.
    
    Args:
        scopes: Lista de escopos OAuth necessários
        service_name: Nome do serviço (para nomear o arquivo de token)
    
    Returns:
        Credentials: Objeto de credenciais OAuth 2.0
    """
    token_file = get_token_file_path(service_name)
    creds = None
    
    # Tentar carregar token existente
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)
            print(f"Token carregado de: {token_file}", file=sys.stderr)
        except Exception as e:
            print(f"Erro ao carregar token: {e}", file=sys.stderr)
            creds = None
    
    # Se não há credenciais válidas, fazer login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Tentar renovar o token
            try:
                print("Token expirado. Renovando...", file=sys.stderr)
                creds.refresh(Request())
                print("Token renovado com sucesso!", file=sys.stderr)
            except RefreshError:
                print("Não foi possível renovar o token. Será necessário fazer login novamente.", file=sys.stderr)
                creds = None
        else:
            # Criar credenciais OAuth 2.0 a partir do client ID e secret
            # IMPORTANTE: O redirect_uri deve corresponder EXATAMENTE ao configurado no Google Cloud Console
            # O run_local_server usa http://localhost:PORTA/ (com barra no final)
            client_config = {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [
                        "http://localhost:8080/",
                        "http://localhost:8080",
                        "http://localhost/",
                        "http://localhost",
                        "http://127.0.0.1:8080/",
                        "http://127.0.0.1:8080",
                        "http://127.0.0.1/",
                        "http://127.0.0.1"
                    ]
                }
            }
            
            # Criar fluxo OAuth
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
            
            print("", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print("AUTENTICACAO OAUTH 2.0 - GOOGLE", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print("", file=sys.stderr)
            print("Abrindo navegador para autenticacao...", file=sys.stderr)
            print("Por favor, autorize o acesso quando solicitado.", file=sys.stderr)
            print("", file=sys.stderr)
            
            # Executar fluxo local (abre janela do navegador automaticamente)
            # IMPORTANTE: O run_local_server configura o redirect_uri automaticamente
            # e abre o navegador com a URL correta
            try:
                creds = flow.run_local_server(port=8080, open_browser=True)
            except OSError as e:
                error_str = str(e).lower()
                if ("address already in use" in error_str or 
                    "10048" in str(e) or  # Windows error code
                    "address is already in use" in error_str):
                    print(f"Porta 8080 ocupada. Tentando porta alternativa...", file=sys.stderr)
                    # Obter URL de autorização ANTES de iniciar servidor com porta alternativa
                    authorization_url, _ = flow.authorization_url(prompt='consent')
                    print("", file=sys.stderr)
                    print("URL de autorizacao:", file=sys.stderr)
                    print(authorization_url, file=sys.stderr)
                    print("", file=sys.stderr)
                    print("Tentando abrir navegador...", file=sys.stderr)
                    # Tentar abrir navegador manualmente
                    try:
                        webbrowser.open(authorization_url)
                        print("Navegador aberto!", file=sys.stderr)
                    except Exception as browser_error:
                        print(f"Nao foi possivel abrir navegador automaticamente: {browser_error}", file=sys.stderr)
                        print("Por favor, copie a URL acima e cole no navegador manualmente.", file=sys.stderr)
                    print("", file=sys.stderr)
                    print("Aguardando autorizacao...", file=sys.stderr)
                    # Tentar porta alternativa (port=0 usa porta aleatória)
                    # O run_local_server vai configurar o redirect_uri automaticamente
                    creds = flow.run_local_server(port=0, open_browser=False)  # Já abrimos manualmente
                    print("ATENCAO: Foi usada uma porta diferente de 8080.", file=sys.stderr)
                    print("Se aparecer erro de redirect_uri_mismatch, verifique qual porta foi usada", file=sys.stderr)
                    print("e adicione o redirect URI correspondente no Google Cloud Console.", file=sys.stderr)
                else:
                    raise
            
            print("", file=sys.stderr)
            print("Autenticacao concluida com sucesso!", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
        
        # Salvar credenciais para uso futuro
        if creds:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Token salvo em: {token_file}", file=sys.stderr)
    
    return creds

