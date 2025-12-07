#!/usr/bin/env python3
"""
Script de teste para Google Keep e Google Calendar
"""
import sys
import asyncio
import json
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mcp_client import MCPClient
from main import load_config

async def test_tools():
    """Testa as ferramentas do Google Keep e Google Calendar"""
    
    # Carregar configuração
    config = load_config()
    mcp_servers = config.get('mcp_servers', [])
    
    keep_client = None
    calendar_client = None
    
    # Encontrar clientes usando o mesmo método do main.py
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for mcp_config in mcp_servers:
        name = mcp_config.get('name', '').lower()
        
        if 'keep' in name:
            # Criar cliente para Google Keep usando o mesmo método do main.py
            local_cmd = mcp_config.get('local_command', '')
            if 'mcp_google_keep' in local_cmd:
                keep_path = os.path.join(base_dir, 'mcp_google_keep', 'server.py')
                keep_path = os.path.normpath(keep_path)
                # Substituir o caminho relativo pelo absoluto (sem aspas extras)
                local_cmd = local_cmd.replace('mcp_google_keep/server.py', keep_path)
            
            keep_client = MCPClient(
                ssh_host='localhost',
                ssh_user=os.getenv('USER', os.getenv('USERNAME', 'user')),
                ssh_command=local_cmd,
                ssh_port=22,
                ssh_password=None
            )
            keep_client.server_name = mcp_config.get('name', 'google-keep')
            print(f"[OK] Cliente Google Keep criado: {keep_client.server_name}")
            print(f"  Comando: {local_cmd}")
            
        elif 'calendar' in name:
            # Criar cliente para Google Calendar usando o mesmo método do main.py
            local_cmd = mcp_config.get('local_command', '')
            if 'mcp_google_calendar' in local_cmd:
                calendar_path = os.path.join(base_dir, 'mcp_google_calendar', 'server.py')
                calendar_path = os.path.normpath(calendar_path)
                # Substituir o caminho relativo pelo absoluto (sem aspas extras)
                local_cmd = local_cmd.replace('mcp_google_calendar/server.py', calendar_path)
            
            calendar_client = MCPClient(
                ssh_host='localhost',
                ssh_user=os.getenv('USER', os.getenv('USERNAME', 'user')),
                ssh_command=local_cmd,
                ssh_port=22,
                ssh_password=None
            )
            calendar_client.server_name = mcp_config.get('name', 'google-calendar')
            print(f"[OK] Cliente Google Calendar criado: {calendar_client.server_name}")
            print(f"  Comando: {local_cmd}")
    
    # Testar Google Keep
    if keep_client:
        print("\n" + "="*60)
        print("TESTE 1: Google Keep - Listar Notas")
        print("="*60)
        try:
            await keep_client.connect()
            await asyncio.sleep(1)  # Aguardar conexão
            
            if keep_client.connected:
                print("[OK] Conectado ao servidor Google Keep")
                
                # Testar listar notas
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "google_keep_list_notes",
                        "arguments": {
                            "page_size": 5
                        }
                    },
                    "id": 1
                }
                
                print(f"\nEnviando requisição: {json.dumps(request, indent=2, ensure_ascii=False)}")
                response = await keep_client.send_message(request)
                
                print(f"\nResposta recebida:")
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
                if response.get("result"):
                    print("\n[OK] Teste Google Keep: SUCESSO")
                else:
                    print("\n[ERRO] Teste Google Keep: FALHOU")
                    if "error" in response:
                        print(f"Erro: {response['error']}")
            else:
                print("[ERRO] Nao foi possivel conectar ao servidor Google Keep")
                
        except Exception as e:
            print(f"\n[ERRO] Erro ao testar Google Keep: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if keep_client:
                await keep_client.disconnect()
    
    # Testar Google Calendar
    if calendar_client:
        print("\n" + "="*60)
        print("TESTE 2: Google Calendar - Listar Eventos")
        print("="*60)
        try:
            await calendar_client.connect()
            await asyncio.sleep(1)  # Aguardar conexão
            
            if calendar_client.connected:
                print("[OK] Conectado ao servidor Google Calendar")
                
                # Testar listar eventos
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "google_calendar_list_events",
                        "arguments": {
                            "time_min": "2025-01-01T00:00:00Z",
                            "time_max": "2025-12-31T23:59:59Z",
                            "max_results": 5
                        }
                    },
                    "id": 2
                }
                
                print(f"\nEnviando requisição: {json.dumps(request, indent=2, ensure_ascii=False)}")
                response = await calendar_client.send_message(request)
                
                print(f"\nResposta recebida:")
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
                if response.get("result"):
                    print("\n[OK] Teste Google Calendar: SUCESSO")
                else:
                    print("\n[ERRO] Teste Google Calendar: FALHOU")
                    if "error" in response:
                        print(f"Erro: {response['error']}")
            else:
                print("[ERRO] Nao foi possivel conectar ao servidor Google Calendar")
                
        except Exception as e:
            print(f"\n[ERRO] Erro ao testar Google Calendar: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if calendar_client:
                await calendar_client.disconnect()
    
    print("\n" + "="*60)
    print("TESTES CONCLUÍDOS")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_tools())

