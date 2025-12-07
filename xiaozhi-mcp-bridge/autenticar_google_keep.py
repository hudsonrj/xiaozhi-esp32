#!/usr/bin/env python3
"""
Script para autenticar Google Keep manualmente
Execute este script para abrir o navegador e autenticar
"""
import sys
import os
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from google_oauth_helper import get_oauth_credentials

def main():
    print("\n" + "=" * 70)
    print("AUTENTICACAO GOOGLE KEEP - OAUTH 2.0")
    print("=" * 70)
    print("\nEste script vai:")
    print("1. Abrir o navegador automaticamente")
    print("2. Mostrar a URL de autorizacao (caso o navegador nao abra)")
    print("3. Aguardar sua autorizacao")
    print("4. Salvar o token para uso futuro")
    print("\n" + "=" * 70 + "\n")
    
    # Escopos do Google Keep
    scopes = ['https://www.googleapis.com/auth/keep']
    
    try:
        print("Solicitando credenciais OAuth 2.0...\n")
        credentials = get_oauth_credentials(scopes, service_name="google_keep")
        
        if credentials:
            print("\n" + "=" * 70)
            print("[OK] Autenticacao bem-sucedida!")
            print("=" * 70)
            print(f"\nToken salvo em: .google_keep_token.json")
            print("\nAgora voce pode usar as ferramentas do Google Keep no bridge.")
            print("=" * 70 + "\n")
        else:
            print("\n[ERRO] Falha na autenticacao\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[AVISO] Autenticacao cancelada pelo usuario.\n")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 70)
        print("[ERRO] Erro durante autenticacao:")
        print("=" * 70)
        print(str(e))
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


