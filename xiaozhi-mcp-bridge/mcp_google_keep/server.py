#!/usr/bin/env python3
"""
Servidor MCP local para Google Keep
Implementa protocolo JSON-RPC 2.0 via STDIO

Usa a API oficial do Google Keep (keep.googleapis.com) com Service Account.
Escopo necessário: https://www.googleapis.com/auth/keep
Documentação: https://developers.google.com/workspace/keep?hl=pt_BR
"""
import sys
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

# Importar bibliotecas do Google Keep API oficial
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Erro: Bibliotecas do Google não instaladas. Execute: pip install google-api-python-client google-auth-httplib2 google-auth", file=sys.stderr)
    sys.exit(1)

# Caminho para o arquivo de credenciais
# O arquivo JSON está no diretório raiz do projeto (xiaozhi-mcp-bridge)
# Tentar múltiplos caminhos para garantir que encontre o arquivo
def find_credentials_file():
    """Encontra o arquivo de credenciais em vários locais possíveis"""
    filename = "hudson-3202f-208569b89e03.json"
    
    # 1. Tentar no diretório pai do script (padrão)
    script_dir = Path(__file__).parent.parent
    cred_file = script_dir / filename
    if cred_file.exists():
        return cred_file
    
    # 2. Tentar no diretório de trabalho atual
    cwd_file = Path(os.getcwd()) / filename
    if cwd_file.exists():
        return cwd_file
    
    # 3. Tentar procurar recursivamente a partir do diretório atual
    current = Path(os.getcwd())
    for parent in [current] + list(current.parents):
        potential_file = parent / filename
        if potential_file.exists():
            return potential_file
    
    # 4. Se não encontrou, retornar o caminho padrão (para gerar erro claro)
    return script_dir / filename

CREDENTIALS_FILE = find_credentials_file()

# Escopos necessários para Google Keep
SCOPES = ['https://www.googleapis.com/auth/keep']

# Cache do serviço do Google Keep
_keep_service: Optional[Any] = None


def get_keep_service():
    """Obtém serviço do Google Keep autenticado usando Service Account"""
    global _keep_service
    
    if _keep_service is not None:
        return _keep_service
    
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
    
    # Carregar credenciais da service account
    credentials = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES
    )
    
    # Usar Domain-Wide Delegation para atuar em nome do usuário hudsonrj@gmail.com
    # Isso permite que a service account acesse as notas do usuário específico
    user_email = os.getenv('GOOGLE_USER_EMAIL', 'hudsonrj@gmail.com')
    credentials = credentials.with_subject(user_email)
    
    print(f"Usando notas do usuário: {user_email}", file=sys.stderr)
    
    # Criar serviço usando discovery API
    try:
        _keep_service = build('keep', 'v1', credentials=credentials)
        print("Serviço Google Keep criado com sucesso", file=sys.stderr)
    except Exception as e:
        error_msg = str(e)
        troubleshooting = ""
        
        if "404" in error_msg or "not found" in error_msg.lower():
            troubleshooting = (
                "\n\nTROUBLESHOOTING:\n"
                "1. Verifique se a API do Google Keep está habilitada no Google Cloud Console\n"
                "   https://console.cloud.google.com/apis/library/keep.googleapis.com\n"
                "2. Para service accounts, configure delegação em todo o domínio:\n"
                "   - Google Admin Console > Segurança > Controle de acesso à API\n"
                "   - Adicione o Client ID do service account\n"
                "   - Autorize os escopos: https://www.googleapis.com/auth/keep\n"
                "3. Consulte: https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br"
            )
        elif "403" in error_msg or "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            troubleshooting = (
                "\n\nTROUBLESHOOTING:\n"
                "1. Para service accounts, configure delegação em todo o domínio no Google Admin Console\n"
                "2. Verifique se o escopo https://www.googleapis.com/auth/keep está autorizado\n"
                "3. A API do Google Keep está disponível principalmente para Google Workspace\n"
                "4. Consulte: https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br"
            )
        
        raise Exception(f"Erro ao criar serviço Google Keep: {error_msg}{troubleshooting}")
    
    return _keep_service


def list_notes(filter_str: Optional[str] = None, page_size: int = 50, 
               page_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Lista notas do Google Keep usando filtros e paginação.
    
    Filtros suportados pela API:
    - create_time > "2021-01-01T00:00:00Z" - notas criadas após data
    - -trashed - excluir notas na lixeira
    - trashed - apenas notas na lixeira
    - -archived - excluir notas arquivadas
    - archived - apenas notas arquivadas
    
    NOTA: A API do Google Keep pode não aceitar múltiplos filtros separados por espaço.
    Use apenas um filtro por vez ou combine usando AND/OR se suportado.
    """
    try:
        service = get_keep_service()
        notes_resource = service.notes()
        
        # Construir parâmetros da requisição
        params = {}
        
        # Validar e processar filtro
        if filter_str:
            filter_str = filter_str.strip()
            # Se houver múltiplos filtros separados por espaço, processar adequadamente
            if ' ' in filter_str and not filter_str.startswith('create_time'):
                # Para filtros simples como "-trashed -archived", a API não aceita múltiplos
                # Vamos tentar usar apenas o primeiro filtro válido
                filters = filter_str.split()
                valid_filters = []
                
                # Coletar todos os filtros válidos
                for f in filters:
                    f_clean = f.strip()
                    if f_clean in ['-trashed', 'trashed', '-archived', 'archived']:
                        valid_filters.append(f_clean)
                
                if valid_filters:
                    # Usar apenas o primeiro filtro válido (a API não aceita múltiplos)
                    params['filter'] = valid_filters[0]
                    if len(valid_filters) > 1:
                        print(f"AVISO: API não aceita múltiplos filtros. Usando apenas '{valid_filters[0]}' (ignorando: {', '.join(valid_filters[1:])})", file=sys.stderr)
                else:
                    # Se não encontrar filtro válido, tentar sem filtro
                    print(f"AVISO: Nenhum filtro válido encontrado em '{filter_str}'. Tentando sem filtro.", file=sys.stderr)
            else:
                # Filtro único ou filtro de data (create_time > "...")
                params['filter'] = filter_str
        
        # Parâmetros de paginação
        if page_size and page_size > 0:
            params['pageSize'] = min(page_size, 1000)  # Limitar a 1000
        
        if page_token:
            params['pageToken'] = page_token
        
        # Executar requisição
        print(f"Parâmetros da requisição: {params}", file=sys.stderr)
        request = notes_resource.list(**params)
        response = request.execute()
        
        return response
    except HttpError as error:
        error_details = f"Status: {error.resp.status}, Reason: {error.resp.reason}"
        if error.content:
            try:
                error_content = json.loads(error.content.decode('utf-8'))
                error_message = error_content.get('error', {}).get('message', 'Unknown error')
                error_details += f", Message: {error_message}"
            except:
                error_details += f", Content: {error.content.decode('utf-8', errors='ignore')[:200]}"
        
        troubleshooting = (
            "\n\nTROUBLESHOOTING:\n"
            "1. Verifique se a API do Google Keep está habilitada no Google Cloud Console\n"
            "2. Para service accounts, configure delegação em todo o domínio no Google Admin Console\n"
            "3. A API do Google Keep está disponível principalmente para Google Workspace\n"
            "4. Verifique se o formato do filtro está correto (use apenas um filtro por vez)\n"
            "5. Consulte: https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br"
        )
        
        raise Exception(f"Erro ao listar notas: {error_details}{troubleshooting}")
    except Exception as e:
        raise Exception(f"Erro ao listar notas: {str(e)}")


def get_note(note_id: str) -> Dict[str, Any]:
    """Obtém detalhes de uma nota específica incluindo anexos"""
    try:
        service = get_keep_service()
        note = service.notes().get(name=note_id).execute()
        return note
    except HttpError as error:
        raise Exception(f"Erro ao obter nota: {error}")
    except Exception as e:
        raise Exception(f"Erro ao obter nota: {str(e)}")


def create_text_note(title: str, text_content: str, parent: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria uma nova nota de texto.
    
    Args:
        title: Título da nota
        text_content: Conteúdo de texto da nota
        parent: ID do pai (opcional)
    """
    try:
        service = get_keep_service()
        
        # Estrutura da nota de texto conforme API oficial
        note_data = {
            'title': title,
            'body': {
                'text': {
                    'text': text_content
                }
            }
        }
        
        # Criar nota
        if parent:
            note = service.notes().create(parent=parent, body=note_data).execute()
        else:
            note = service.notes().create(body=note_data).execute()
        return note
    except HttpError as error:
        raise Exception(f"Erro ao criar nota de texto: {error}")
    except Exception as e:
        raise Exception(f"Erro ao criar nota de texto: {str(e)}")


def create_list_note(title: str, list_items: List[Dict[str, Any]], parent: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria uma nova nota de lista.
    
    Args:
        title: Título da nota
        list_items: Lista de itens. Cada item deve ter:
            - text: texto do item
            - checked: se está marcado (opcional, default False)
            - child_list_items: lista de sub-itens (opcional)
        parent: ID do pai (opcional)
    """
    try:
        service = get_keep_service()
        
        # Converter lista de itens para formato da API
        formatted_items = []
        for item in list_items:
            list_item = {
                'text': {
                    'text': item.get('text', '')
                },
                'checked': item.get('checked', False)
            }
            
            # Adicionar sub-itens se existirem
            if 'child_list_items' in item and item['child_list_items']:
                child_items = []
                for child in item['child_list_items']:
                    child_items.append({
                        'text': {
                            'text': child.get('text', '')
                        },
                        'checked': child.get('checked', False)
                    })
                list_item['childListItems'] = child_items
            
            formatted_items.append(list_item)
        
        # Estrutura da nota de lista conforme API oficial
        note_data = {
            'title': title,
            'body': {
                'list': {
                    'listItems': formatted_items
                }
            }
        }
        
        # Criar nota
        if parent:
            note = service.notes().create(parent=parent, body=note_data).execute()
        else:
            note = service.notes().create(body=note_data).execute()
        return note
    except HttpError as error:
        raise Exception(f"Erro ao criar nota de lista: {error}")
    except Exception as e:
        raise Exception(f"Erro ao criar nota de lista: {str(e)}")


def create_note(parent: Optional[str] = None, title: str = "", 
                body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Cria uma nova nota no Google Keep (método genérico).
    Use create_text_note ou create_list_note para tipos específicos.
    
    Args:
        parent: ID do pai (opcional, para organizar em pastas)
        title: Título da nota
        body: Corpo da nota (estrutura específica da API)
    """
    try:
        service = get_keep_service()
        
        # Estrutura básica da nota
        note_data = {
            'title': title,
        }
        
        # Adicionar corpo se fornecido
        if body:
            note_data['body'] = body
        
        # Criar nota
        if parent:
            note = service.notes().create(parent=parent, body=note_data).execute()
        else:
            note = service.notes().create(body=note_data).execute()
        return note
    except HttpError as error:
        raise Exception(f"Erro ao criar nota: {error}")
    except Exception as e:
        raise Exception(f"Erro ao criar nota: {str(e)}")


def update_note(note_id: str, update_mask: Optional[str] = None,
                title: Optional[str] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Atualiza uma nota existente.
    
    Args:
        note_id: ID da nota
        update_mask: Máscara de atualização (campos a atualizar, ex: "title,body")
        title: Novo título
        body: Novo corpo da nota
    """
    try:
        service = get_keep_service()
        
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if body:
            update_data.update(body)
        
        # Atualizar nota
        request = service.notes().patch(name=note_id, body=update_data)
        if update_mask:
            request = request.setUpdateMask(update_mask)
        
        note = request.execute()
        return note
    except HttpError as error:
        raise Exception(f"Erro ao atualizar nota: {error}")
    except Exception as e:
        raise Exception(f"Erro ao atualizar nota: {str(e)}")


def delete_note(note_id: str) -> bool:
    """Deleta uma nota"""
    try:
        service = get_keep_service()
        service.notes().delete(name=note_id).execute()
        return True
    except HttpError as error:
        raise Exception(f"Erro ao deletar nota: {error}")
    except Exception as e:
        raise Exception(f"Erro ao deletar nota: {str(e)}")


def get_note_permissions(note_id: str) -> List[Dict[str, Any]]:
    """Obtém permissões de uma nota"""
    try:
        service = get_keep_service()
        permissions = service.notes().permissions().list(parent=note_id).execute()
        return permissions.get('permissions', [])
    except HttpError as error:
        raise Exception(f"Erro ao obter permissões: {error}")
    except Exception as e:
        raise Exception(f"Erro ao obter permissões: {str(e)}")


def create_note_permission(note_id: str, email: str, role: str = 'READER') -> Dict[str, Any]:
    """
    Cria/modifica permissão de uma nota.
    
    Roles: READER, WRITER
    """
    try:
        service = get_keep_service()
        permission_data = {
            'email': email,
            'role': role
        }
        permission = service.notes().permissions().create(
            parent=note_id,
            body=permission_data
        ).execute()
        return permission
    except HttpError as error:
        raise Exception(f"Erro ao criar permissão: {error}")
    except Exception as e:
        raise Exception(f"Erro ao criar permissão: {str(e)}")


def delete_note_permission(note_id: str, permission_id: str) -> bool:
    """Remove permissão de uma nota"""
    try:
        service = get_keep_service()
        service.notes().permissions().delete(
            name=f"{note_id}/permissions/{permission_id}"
        ).execute()
        return True
    except HttpError as error:
        raise Exception(f"Erro ao deletar permissão: {error}")
    except Exception as e:
        raise Exception(f"Erro ao deletar permissão: {str(e)}")


def get_note_attachments(note_id: str) -> List[Dict[str, Any]]:
    """
    Obtém lista de anexos de uma nota.
    Primeiro passo: obter os recursos de anexo da nota.
    """
    try:
        service = get_keep_service()
        note = service.notes().get(name=note_id).execute()
        attachments = note.get('attachments', [])
        return attachments
    except HttpError as error:
        raise Exception(f"Erro ao obter anexos: {error}")
    except Exception as e:
        raise Exception(f"Erro ao obter anexos: {str(e)}")


def download_note_attachment(attachment_name: str, mime_type: str, output_path: Optional[str] = None) -> bytes:
    """
    Baixa um anexo de uma nota.
    Segundo passo: usar media().download() para baixar o arquivo.
    
    Args:
        attachment_name: Nome do anexo (formato: notes/ID/attachments/ATTACHMENT_ID)
        mime_type: Tipo MIME do anexo
        output_path: Caminho para salvar o arquivo (opcional, retorna bytes se não fornecido)
    """
    try:
        service = get_keep_service()
        
        # Baixar anexo usando media().download()
        import io
        
        if output_path:
            # Salvar diretamente em arquivo
            with open(output_path, 'wb') as fh:
                request = service.media().download(name=attachment_name)
                request.headers['Accept'] = mime_type
                
                downloader = request
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"Progresso: {int(status.progress() * 100)}%", file=sys.stderr)
                    fh.write(status.resumable_progress if status else b'')
            
            # Ler arquivo para retornar bytes
            with open(output_path, 'rb') as f:
                return f.read()
        else:
            # Retornar bytes diretamente
            fh = io.BytesIO()
            request = service.media().download(name=attachment_name)
            request.headers['Accept'] = mime_type
            
            downloader = request
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"Progresso: {int(status.progress() * 100)}%", file=sys.stderr)
                    # Obter conteúdo do chunk
                    chunk_data = status.resumable_progress if hasattr(status, 'resumable_progress') else b''
                    fh.write(chunk_data)
            
            fh.seek(0)
            return fh.read()
    except HttpError as error:
        raise Exception(f"Erro ao baixar anexo: {error}")
    except Exception as e:
        raise Exception(f"Erro ao baixar anexo: {str(e)}")


# Lista de ferramentas do Google Keep
TOOLS = [
    {
        "name": "google_keep_list_notes",
        "description": "Lista notas do Google Keep com filtros e paginação. Filtros: create_time > \"data\", -trashed, trashed, -archived, archived",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filtro de busca (ex: 'create_time > \"2021-01-01T00:00:00Z\"', '-trashed', '-archived')"
                },
                "page_size": {
                    "type": "number",
                    "description": "Número máximo de notas para retornar",
                    "default": 50
                },
                "page_token": {
                    "type": "string",
                    "description": "Token de paginação para próxima página"
                },
            },
        },
    },
    {
        "name": "google_keep_get_note",
        "description": "Obtém detalhes completos de uma nota específica incluindo anexos",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "google_keep_create_text_note",
        "description": "Cria uma nova nota de texto no Google Keep",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título da nota"
                },
                "text_content": {
                    "type": "string",
                    "description": "Conteúdo de texto da nota"
                },
                "parent": {
                    "type": "string",
                    "description": "ID do pai (opcional, para organizar em pastas)"
                },
            },
            "required": ["title", "text_content"],
        },
    },
    {
        "name": "google_keep_create_list_note",
        "description": "Cria uma nova nota de lista no Google Keep com itens marcáveis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título da nota"
                },
                "list_items": {
                    "type": "array",
                    "description": "Lista de itens. Cada item pode ter: text (obrigatório), checked (opcional), child_list_items (opcional)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "checked": {"type": "boolean", "default": False},
                            "child_list_items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "checked": {"type": "boolean", "default": False}
                                    }
                                }
                            }
                        },
                        "required": ["text"]
                    }
                },
                "parent": {
                    "type": "string",
                    "description": "ID do pai (opcional, para organizar em pastas)"
                },
            },
            "required": ["title", "list_items"],
        },
    },
    {
        "name": "google_keep_create_note",
        "description": "Cria uma nova nota no Google Keep (método genérico - use create_text_note ou create_list_note para tipos específicos)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent": {
                    "type": "string",
                    "description": "ID do pai (opcional, para organizar em pastas)"
                },
                "title": {
                    "type": "string",
                    "description": "Título da nota"
                },
                "body": {
                    "type": "object",
                    "description": "Corpo da nota (estrutura específica da API)"
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "google_keep_update_note",
        "description": "Atualiza uma nota existente",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
                "title": {
                    "type": "string",
                    "description": "Novo título da nota"
                },
                "update_mask": {
                    "type": "string",
                    "description": "Máscara de atualização (campos a atualizar, ex: 'title,body')"
                },
                "body": {
                    "type": "object",
                    "description": "Novo corpo da nota"
                },
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "google_keep_delete_note",
        "description": "Deleta uma nota",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "google_keep_get_permissions",
        "description": "Obtém lista de permissões de uma nota",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "google_keep_create_permission",
        "description": "Cria ou modifica permissão de uma nota (compartilhar)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
                "email": {
                    "type": "string",
                    "description": "Email do usuário para compartilhar"
                },
                "role": {
                    "type": "string",
                    "description": "Papel: READER (leitura) ou WRITER (escrita)",
                    "enum": ["READER", "WRITER"],
                    "default": "READER"
                },
            },
            "required": ["note_id", "email"],
        },
    },
    {
        "name": "google_keep_delete_permission",
        "description": "Remove permissão de uma nota (deixar de compartilhar)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
                "permission_id": {
                    "type": "string",
                    "description": "ID da permissão a ser removida"
                },
            },
            "required": ["note_id", "permission_id"],
        },
    },
    {
        "name": "google_keep_get_attachments",
        "description": "Obtém lista de anexos de uma nota (primeiro passo para baixar)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "ID da nota (formato: notes/ID)"
                },
            },
            "required": ["note_id"],
        },
    },
    {
        "name": "google_keep_download_attachment",
        "description": "Baixa um anexo de uma nota (segundo passo: usar após get_attachments)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attachment_name": {
                    "type": "string",
                    "description": "Nome do anexo (formato: notes/ID/attachments/ATTACHMENT_ID)"
                },
                "mime_type": {
                    "type": "string",
                    "description": "Tipo MIME do anexo (ex: image/png, application/pdf)"
                },
                "output_path": {
                    "type": "string",
                    "description": "Caminho para salvar o arquivo (opcional, retorna base64 se não fornecido)"
                },
            },
            "required": ["attachment_name", "mime_type"],
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
                        "name": "google-keep",
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
                
                if tool_name == "google_keep_list_notes":
                    filter_str = arguments.get("filter")
                    page_size = arguments.get("page_size", 50)
                    page_token = arguments.get("page_token")
                    
                    response_data = list_notes(
                        filter_str=filter_str,
                        page_size=page_size,
                        page_token=page_token
                    )
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(response_data, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_get_note":
                    note_id = arguments.get("note_id")
                    if not note_id:
                        raise ValueError("note_id é obrigatório")
                    
                    note = get_note(note_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(note, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_create_text_note":
                    title = arguments.get("title", "")
                    text_content = arguments.get("text_content", "")
                    parent = arguments.get("parent")
                    
                    if not title:
                        raise ValueError("title é obrigatório")
                    if not text_content:
                        raise ValueError("text_content é obrigatório")
                    
                    note = create_text_note(title=title, text_content=text_content, parent=parent)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(note, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_create_list_note":
                    title = arguments.get("title", "")
                    list_items = arguments.get("list_items", [])
                    parent = arguments.get("parent")
                    
                    if not title:
                        raise ValueError("title é obrigatório")
                    if not list_items:
                        raise ValueError("list_items é obrigatório")
                    
                    note = create_list_note(title=title, list_items=list_items, parent=parent)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(note, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_create_note":
                    title = arguments.get("title", "")
                    parent = arguments.get("parent")
                    body = arguments.get("body")
                    
                    if not title:
                        raise ValueError("title é obrigatório")
                    
                    note = create_note(parent=parent, title=title, body=body)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(note, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_update_note":
                    note_id = arguments.get("note_id")
                    if not note_id:
                        raise ValueError("note_id é obrigatório")
                    
                    note = update_note(
                        note_id=note_id,
                        title=arguments.get("title"),
                        update_mask=arguments.get("update_mask"),
                        body=arguments.get("body")
                    )
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(note, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_delete_note":
                    note_id = arguments.get("note_id")
                    if not note_id:
                        raise ValueError("note_id é obrigatório")
                    
                    success = delete_note(note_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"success": success, "message": "Nota deletada com sucesso"}, ensure_ascii=False),
                        }
                    ]
                
                elif tool_name == "google_keep_get_permissions":
                    note_id = arguments.get("note_id")
                    if not note_id:
                        raise ValueError("note_id é obrigatório")
                    
                    permissions = get_note_permissions(note_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"permissions": permissions}, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_create_permission":
                    note_id = arguments.get("note_id")
                    email = arguments.get("email")
                    role = arguments.get("role", "READER")
                    
                    if not note_id or not email:
                        raise ValueError("note_id e email são obrigatórios")
                    
                    permission = create_note_permission(note_id, email, role)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(permission, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_delete_permission":
                    note_id = arguments.get("note_id")
                    permission_id = arguments.get("permission_id")
                    
                    if not note_id or not permission_id:
                        raise ValueError("note_id e permission_id são obrigatórios")
                    
                    success = delete_note_permission(note_id, permission_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"success": success, "message": "Permissão removida com sucesso"}, ensure_ascii=False),
                        }
                    ]
                
                elif tool_name == "google_keep_get_attachments":
                    note_id = arguments.get("note_id")
                    if not note_id:
                        raise ValueError("note_id é obrigatório")
                    
                    attachments = get_note_attachments(note_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"attachments": attachments}, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "google_keep_download_attachment":
                    attachment_name = arguments.get("attachment_name")
                    mime_type = arguments.get("mime_type")
                    output_path = arguments.get("output_path")
                    
                    if not attachment_name or not mime_type:
                        raise ValueError("attachment_name e mime_type são obrigatórios")
                    
                    file_content = download_note_attachment(attachment_name, mime_type, output_path)
                    
                    # Se não forneceu output_path, retornar base64
                    import base64
                    file_base64 = base64.b64encode(file_content).decode('utf-8')
                    
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "mime_type": mime_type,
                                "size_bytes": len(file_content),
                                "file_path": output_path if output_path else None,
                                "file_base64": file_base64 if not output_path else None
                            }, indent=2, ensure_ascii=False),
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
    print("Servidor MCP Google Keep iniciado (API oficial - Service Account)", file=sys.stderr)
    print(f"Usando credenciais: {CREDENTIALS_FILE}", file=sys.stderr)
    print(f"Escopo: {SCOPES[0]}", file=sys.stderr)
    print("Funcionalidades: Criar, Listar, Modificar permissões, Recuperar notas e anexos", file=sys.stderr)
    
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
