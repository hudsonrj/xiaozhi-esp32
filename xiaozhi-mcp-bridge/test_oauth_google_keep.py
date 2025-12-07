#!/usr/bin/env python3
"""
Script para testar autenticação OAuth 2.0 do Google Keep
Força a abertura do navegador para autenticação
"""
import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from google_oauth_helper import get_oauth_credentials

def main():
    print("=" * 60)
    print("Teste de Autenticação OAuth 2.0 - Google Keep")
    print("=" * 60)
    print()
    print("Este script vai abrir uma janela do navegador para autenticação.")
    print("Por favor, autorize o acesso quando solicitado.")
    print()
    
    # Escopos do Google Keep
    scopes = ['https://www.googleapis.com/auth/keep']
    
    try:
        print("Solicitando credenciais OAuth 2.0...")
        credentials = get_oauth_credentials(scopes, service_name="google_keep")
        
        if credentials:
            print()
            print("=" * 60)
            print("[OK] Autenticacao bem-sucedida!")
            print("=" * 60)
            print(f"Token salvo em: .google_keep_token.json")
            print()
            print("Agora voce pode usar as ferramentas do Google Keep.")
        else:
            print()
            print("[ERRO] Falha na autenticacao")
            sys.exit(1)
            
    except OSError as e:
        if "10048" in str(e) or "address is already in use" in str(e).lower():
            print()
            print("=" * 60)
            print("[AVISO] Porta 8080 esta em uso!")
            print("=" * 60)
            print("A porta 8080 ja esta sendo usada (provavelmente pelo bridge).")
            print()
            print("Opcoes:")
            print("1. Pare o bridge temporariamente: .\\stop_bridge.ps1")
            print("2. Ou aguarde e tente usar uma ferramenta do Google Keep")
            print("   (a autenticacao sera solicitada automaticamente)")
            print()
        else:
            print()
            print("=" * 60)
            print("[ERRO] Erro durante autenticacao:")
            print("=" * 60)
            print(str(e))
            print()
            import traceback
            traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERRO] Erro durante autenticacao:")
        print("=" * 60)
        print(str(e))
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

