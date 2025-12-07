#!/usr/bin/env python3
"""
Script de teste para Google Calendar e Google Keep
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mcp_client import MCPClient

async def test_google_services():
    """Testa Google Calendar e Google Keep"""
    import os
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Configurar cliente para Google Calendar (usando EXATAMENTE o mesmo padrão do main.py)
    calendar_path = os.path.join(base_dir, 'mcp_google_calendar', 'server.py')
    # Usar o mesmo formato que main.py usa
    local_cmd = f'python "{calendar_path}"'
    calendar_client = MCPClient(
        ssh_host='localhost',
        ssh_user=os.getenv('USER', os.getenv('USERNAME', 'user')),
        ssh_command=local_cmd,
        ssh_port=22,
        ssh_password=None
    )
    calendar_client.server_name = "google-calendar"
    
    # Configurar cliente para Google Keep (usando EXATAMENTE o mesmo padrão do main.py)
    keep_path = os.path.join(base_dir, 'mcp_google_keep', 'server.py')
    # Usar o mesmo formato que main.py usa
    keep_cmd = f'python "{keep_path}"'
    keep_client = MCPClient(
        ssh_host='localhost',
        ssh_user=os.getenv('USER', os.getenv('USERNAME', 'user')),
        ssh_command=keep_cmd,
        ssh_port=22,
        ssh_password=None
    )
    keep_client.server_name = "google-keep"
    
    try:
        # Conectar aos servidores
        print("=" * 60)
        print("TESTE 1: Conectando ao Google Calendar...")
        print("=" * 60)
        await calendar_client.connect()
        print("[OK] Conectado ao Google Calendar")
        
        print("\n" + "=" * 60)
        print("TESTE 2: Conectando ao Google Keep...")
        print("=" * 60)
        await keep_client.connect()
        print("[OK] Conectado ao Google Keep")
        
        # Calcular data de amanhã (com timezone UTC)
        amanha = datetime.now() + timedelta(days=1)
        amanha_inicio = amanha.replace(hour=0, minute=0, second=0, microsecond=0)
        amanha_fim = amanha.replace(hour=23, minute=59, second=59, microsecond=0)
        
        # Formato ISO 8601 com timezone UTC (requerido pela API do Google Calendar)
        time_min = amanha_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_max = amanha_fim.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        print("\n" + "=" * 60)
        print(f"TESTE 3: Listando compromissos de amanhã ({amanha.strftime('%d/%m/%Y')})...")
        print("=" * 60)
        print(f"Período: {time_min} até {time_max}")
        
        req_calendar = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "google_calendar_list_events",
                "arguments": {
                    "time_min": time_min,
                    "time_max": time_max,
                    "max_results": 10
                }
            },
            "id": 1
        }
        
        print("\nEnviando requisição...")
        resp_calendar = await calendar_client.send_message(req_calendar)
        
        if resp_calendar and "result" in resp_calendar:
            result = resp_calendar["result"]
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "{}")
                    events = json.loads(text_content)
                    
                    if isinstance(events, list):
                        print(f"\n[OK] Encontrados {len(events)} compromissos:")
                        for i, event in enumerate(events, 1):
                            summary = event.get("summary", "Sem título")
                            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "Sem data")
                            print(f"  {i}. {summary} - {start}")
                    else:
                        print(f"\n[INFO] Resposta: {json.dumps(events, indent=2, ensure_ascii=False)}")
                else:
                    print(f"\n[INFO] Nenhum compromisso encontrado para amanhã")
                    print(f"Resposta completa: {json.dumps(resp_calendar, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n[INFO] Resposta: {json.dumps(resp_calendar, indent=2, ensure_ascii=False)}")
        else:
            print(f"\n[ERRO] Erro na resposta: {json.dumps(resp_calendar, indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("TESTE 4: Listando notas do Google Keep...")
        print("=" * 60)
        
        req_keep = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "google_keep_list_notes",
                "arguments": {
                    "filter": "-trashed",
                    "page_size": 5
                }
            },
            "id": 2
        }
        
        print("\nEnviando requisição...")
        resp_keep = await keep_client.send_message(req_keep)
        
        if resp_keep and "result" in resp_keep:
            result = resp_keep["result"]
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "{}")
                    notes_data = json.loads(text_content)
                    
                    if isinstance(notes_data, dict) and "notes" in notes_data:
                        notes = notes_data["notes"]
                        print(f"\n[OK] Encontradas {len(notes)} notas:")
                        for i, note in enumerate(notes[:5], 1):
                            title = note.get("title", "Sem título")
                            note_id = note.get("name", "Sem ID")
                            print(f"  {i}. {title} (ID: {note_id})")
                    elif isinstance(notes_data, list):
                        print(f"\n[OK] Encontradas {len(notes_data)} notas:")
                        for i, note in enumerate(notes_data[:5], 1):
                            title = note.get("title", "Sem título")
                            note_id = note.get("name", "Sem ID")
                            print(f"  {i}. {title} (ID: {note_id})")
                    else:
                        print(f"\n[INFO] Resposta: {json.dumps(notes_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"\n[INFO] Nenhuma nota encontrada")
                    print(f"Resposta completa: {json.dumps(resp_keep, indent=2, ensure_ascii=False)}")
            else:
                print(f"\n[INFO] Resposta: {json.dumps(resp_keep, indent=2, ensure_ascii=False)}")
        else:
            print(f"\n[ERRO] Erro na resposta: {json.dumps(resp_keep, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante teste: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await calendar_client.disconnect()
        await keep_client.disconnect()
        print("\n" + "=" * 60)
        print("TESTES CONCLUÍDOS")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_google_services())

