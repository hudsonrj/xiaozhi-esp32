#!/usr/bin/env python3
"""
Servidor MCP local para Google Calendar
Implementa protocolo JSON-RPC 2.0 via STDIO
"""
import sys
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# Importar bibliotecas do Google Calendar
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Erro: Bibliotecas do Google Calendar não instaladas. Execute: pip install google-api-python-client google-auth-httplib2 google-auth google-auth-oauthlib", file=sys.stderr)
    sys.exit(1)

# Importar helper de OAuth 2.0
try:
    # Adicionar o diretório pai ao path para importar o helper
    helper_path = Path(__file__).parent.parent
    if str(helper_path) not in sys.path:
        sys.path.insert(0, str(helper_path))
    from google_oauth_helper import get_oauth_credentials
except ImportError as e:
    print(f"Erro ao importar helper de OAuth: {e}", file=sys.stderr)
    sys.exit(1)

# Escopos necessários para Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Cache do serviço do Google Calendar
_calendar_service: Optional[Any] = None


def get_calendar_service():
    """Obtém serviço do Google Calendar autenticado usando OAuth 2.0"""
    global _calendar_service
    
    if _calendar_service is not None:
        return _calendar_service
    
    # Obter credenciais OAuth 2.0 (abre janela do navegador se necessário)
    credentials = get_oauth_credentials(SCOPES, service_name="google_calendar")
    
    print("Autenticação OAuth 2.0 concluída para Google Calendar", file=sys.stderr)
    
    # Criar serviço
    _calendar_service = build('calendar', 'v3', credentials=credentials)
    return _calendar_service


def list_calendars() -> List[Dict[str, Any]]:
    """Lista todos os calendários disponíveis"""
    try:
        service = get_calendar_service()
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        raise Exception(f"Erro ao listar calendários: {error}")


def get_primary_calendar_id() -> str:
    """Obtém o ID do calendário primário"""
    try:
        calendars = list_calendars()
        for calendar in calendars:
            if calendar.get('primary', False):
                return calendar['id']
        # Se não encontrar primário, retornar o primeiro
        if calendars:
            return calendars[0]['id']
        return 'primary'
    except Exception:
        return 'primary'


def list_events(calendar_id: Optional[str] = None, 
                time_min: Optional[str] = None,
                time_max: Optional[str] = None,
                max_results: int = 10) -> List[Dict[str, Any]]:
    """Lista eventos do calendário"""
    try:
        service = get_calendar_service()
        
        if calendar_id is None:
            calendar_id = get_primary_calendar_id()
        
        # Configurar parâmetros
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except HttpError as error:
        raise Exception(f"Erro ao listar eventos: {error}")


def create_event(calendar_id: Optional[str] = None,
                 summary: str = "",
                 description: Optional[str] = None,
                 start_time: Optional[str] = None,
                 end_time: Optional[str] = None,
                 location: Optional[str] = None,
                 attendees: Optional[List[str]] = None) -> Dict[str, Any]:
    """Cria um novo evento no calendário"""
    try:
        service = get_calendar_service()
        
        if calendar_id is None:
            calendar_id = get_primary_calendar_id()
        
        # Criar objeto de evento
        event = {
            'summary': summary,
        }
        
        if description:
            event['description'] = description
        
        if location:
            event['location'] = location
        
        # Configurar horários
        if start_time and end_time:
            # Assumir formato ISO 8601 ou datetime
            event['start'] = {
                'dateTime': start_time,
                'timeZone': 'America/Sao_Paulo',
            }
            event['end'] = {
                'dateTime': end_time,
                'timeZone': 'America/Sao_Paulo',
            }
        elif start_time:
            # Apenas data (evento de dia inteiro)
            event['start'] = {
                'date': start_time,
            }
            event['end'] = {
                'date': start_time,
            }
        
        # Adicionar participantes
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Criar evento
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        return created_event
    except HttpError as error:
        raise Exception(f"Erro ao criar evento: {error}")


def update_event(calendar_id: Optional[str] = None,
                 event_id: str = "",
                 summary: Optional[str] = None,
                 description: Optional[str] = None,
                 start_time: Optional[str] = None,
                 end_time: Optional[str] = None,
                 location: Optional[str] = None) -> Dict[str, Any]:
    """Atualiza um evento existente"""
    try:
        service = get_calendar_service()
        
        if calendar_id is None:
            calendar_id = get_primary_calendar_id()
        
        # Buscar evento existente
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # Atualizar campos
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_time is not None:
            if 'dateTime' in event.get('start', {}):
                event['start'] = {
                    'dateTime': start_time,
                    'timeZone': 'America/Sao_Paulo',
                }
            else:
                event['start'] = {'date': start_time}
        if end_time is not None:
            if 'dateTime' in event.get('end', {}):
                event['end'] = {
                    'dateTime': end_time,
                    'timeZone': 'America/Sao_Paulo',
                }
            else:
                event['end'] = {'date': end_time}
        
        # Atualizar evento
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        return updated_event
    except HttpError as error:
        raise Exception(f"Erro ao atualizar evento: {error}")


def delete_event(calendar_id: Optional[str] = None, event_id: str = "") -> bool:
    """Deleta um evento"""
    try:
        service = get_calendar_service()
        
        if calendar_id is None:
            calendar_id = get_primary_calendar_id()
        
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return True
    except HttpError as error:
        raise Exception(f"Erro ao deletar evento: {error}")


def get_event(calendar_id: Optional[str] = None, event_id: str = "") -> Dict[str, Any]:
    """Obtém detalhes de um evento específico"""
    try:
        service = get_calendar_service()
        
        if calendar_id is None:
            calendar_id = get_primary_calendar_id()
        
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return event
    except HttpError as error:
        raise Exception(f"Erro ao obter evento: {error}")


# Lista de ferramentas do Google Calendar
TOOLS = [
    {
        "name": "google_calendar_list_calendars",
        "description": "Lista todos os calendários disponíveis na conta do Google Calendar",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "google_calendar_list_events",
        "description": "Lista eventos do calendário. Pode filtrar por período e calendário específico.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "ID do calendário (opcional, usa calendário primário se não especificado)"
                },
                "time_min": {
                    "type": "string",
                    "description": "Data/hora mínima no formato ISO 8601 (ex: 2024-01-01T00:00:00Z)"
                },
                "time_max": {
                    "type": "string",
                    "description": "Data/hora máxima no formato ISO 8601 (ex: 2024-12-31T23:59:59Z)"
                },
                "max_results": {
                    "type": "number",
                    "description": "Número máximo de resultados (padrão: 10)",
                    "default": 10
                },
            },
        },
    },
    {
        "name": "google_calendar_get_event",
        "description": "Obtém detalhes de um evento específico pelo ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "ID do calendário (opcional, usa calendário primário se não especificado)"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID do evento"
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "google_calendar_create_event",
        "description": "Cria um novo evento no calendário",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "ID do calendário (opcional, usa calendário primário se não especificado)"
                },
                "summary": {
                    "type": "string",
                    "description": "Título do evento"
                },
                "description": {
                    "type": "string",
                    "description": "Descrição do evento"
                },
                "start_time": {
                    "type": "string",
                    "description": "Data/hora de início no formato ISO 8601 (ex: 2024-01-01T10:00:00) ou data (ex: 2024-01-01)"
                },
                "end_time": {
                    "type": "string",
                    "description": "Data/hora de término no formato ISO 8601 (ex: 2024-01-01T11:00:00) ou data (ex: 2024-01-01)"
                },
                "location": {
                    "type": "string",
                    "description": "Local do evento"
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de emails dos participantes"
                },
            },
            "required": ["summary"],
        },
    },
    {
        "name": "google_calendar_update_event",
        "description": "Atualiza um evento existente no calendário",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "ID do calendário (opcional, usa calendário primário se não especificado)"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID do evento a ser atualizado"
                },
                "summary": {
                    "type": "string",
                    "description": "Novo título do evento"
                },
                "description": {
                    "type": "string",
                    "description": "Nova descrição do evento"
                },
                "start_time": {
                    "type": "string",
                    "description": "Nova data/hora de início no formato ISO 8601"
                },
                "end_time": {
                    "type": "string",
                    "description": "Nova data/hora de término no formato ISO 8601"
                },
                "location": {
                    "type": "string",
                    "description": "Novo local do evento"
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "google_calendar_delete_event",
        "description": "Deleta um evento do calendário",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {
                    "type": "string",
                    "description": "ID do calendário (opcional, usa calendário primário se não especificado)"
                },
                "event_id": {
                    "type": "string",
                    "description": "ID do evento a ser deletado"
                },
            },
            "required": ["event_id"],
        },
    },
]


def handle_message(line: str):
    """Processa uma mensagem JSON-RPC"""
    try:
        message = json.loads(line)
        
        # Responder ao initialize
        if message.get("method") == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "google-calendar",
                        "version": "1.0.0",
                    },
                },
            }
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
            return
        
        # Responder ao tools/list
        if message.get("method") == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": TOOLS,
                },
            }
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
            return
        
        # Responder ao tools/call
        if message.get("method") == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            try:
                result_content = None
                
                if tool_name == "google_calendar_list_calendars":
                    calendars = list_calendars()
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(calendars, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_calendar_list_events":
                    calendar_id = arguments.get("calendar_id")
                    time_min = arguments.get("time_min")
                    time_max = arguments.get("time_max")
                    max_results = arguments.get("max_results", 10)
                    
                    events = list_events(
                        calendar_id=calendar_id,
                        time_min=time_min,
                        time_max=time_max,
                        max_results=max_results
                    )
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(events, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_calendar_get_event":
                    calendar_id = arguments.get("calendar_id")
                    event_id = arguments.get("event_id")
                    
                    if not event_id:
                        raise ValueError("event_id é obrigatório")
                    
                    event = get_event(calendar_id=calendar_id, event_id=event_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(event, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_calendar_create_event":
                    calendar_id = arguments.get("calendar_id")
                    summary = arguments.get("summary", "")
                    description = arguments.get("description")
                    start_time = arguments.get("start_time")
                    end_time = arguments.get("end_time")
                    location = arguments.get("location")
                    attendees = arguments.get("attendees")
                    
                    if not summary:
                        raise ValueError("summary é obrigatório")
                    
                    event = create_event(
                        calendar_id=calendar_id,
                        summary=summary,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        attendees=attendees
                    )
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(event, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_calendar_update_event":
                    calendar_id = arguments.get("calendar_id")
                    event_id = arguments.get("event_id")
                    
                    if not event_id:
                        raise ValueError("event_id é obrigatório")
                    
                    event = update_event(
                        calendar_id=calendar_id,
                        event_id=event_id,
                        summary=arguments.get("summary"),
                        description=arguments.get("description"),
                        start_time=arguments.get("start_time"),
                        end_time=arguments.get("end_time"),
                        location=arguments.get("location")
                    )
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(event, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_calendar_delete_event":
                    calendar_id = arguments.get("calendar_id")
                    event_id = arguments.get("event_id")
                    
                    if not event_id:
                        raise ValueError("event_id é obrigatório")
                    
                    success = delete_event(calendar_id=calendar_id, event_id=event_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"success": success, "message": "Evento deletado com sucesso"}, ensure_ascii=False),
                        }
                    ]
                
                else:
                    raise ValueError(f"Ferramenta desconhecida: {tool_name}")
                
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "content": result_content,
                    },
                }
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()
                
            except Exception as error:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32000,
                        "message": f"Erro ao executar ferramenta {tool_name}: {str(error)}",
                    },
                }
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
            return
        
        # Método não implementado
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -32601,
                "message": f"Método não implementado: {message.get('method')}",
            },
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.stdout.flush()
        
    except json.JSONDecodeError as error:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": f"Erro ao processar JSON: {str(error)}",
            },
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.stdout.flush()
    except Exception as error:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Erro interno: {str(error)}",
            },
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.stdout.flush()


def main():
    """Função principal - lê mensagens do stdin"""
    # Log de inicialização para stderr (não quebra o protocolo)
    print("Servidor MCP Google Calendar iniciado", file=sys.stderr)
    
    # Ler mensagens linha por linha do stdin
    buffer = ""
    for line in sys.stdin:
        buffer += line
        
        # Processar linhas completas
        lines = buffer.split('\n')
        buffer = lines.pop() if lines else ""
        
        for complete_line in lines:
            if complete_line.strip():
                handle_message(complete_line.strip())


if __name__ == "__main__":
    main()


