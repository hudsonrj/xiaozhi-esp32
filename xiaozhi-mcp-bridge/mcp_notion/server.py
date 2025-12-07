#!/usr/bin/env python3
"""
Servidor MCP local para Notion
Implementa protocolo JSON-RPC 2.0 via STDIO
"""
import sys
import json
import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

# Importar biblioteca do Notion
try:
    from notion_client import Client
except ImportError:
    print("Erro: Biblioteca do Notion n├úo instalada. Execute: pip install notion-client", file=sys.stderr)
    sys.exit(1)

# API Key do Notion (deve ser configurada via vari├ível de ambiente)
NOTION_API_KEY = os.getenv('NOTION_API_KEY', '')

# IDs do database "Notas" (ser├í obtido dinamicamente ou configurado)
NOTAS_DATABASE_ID = os.getenv('NOTION_NOTAS_DATABASE_ID', '')  # database_id para databases.retrieve
NOTAS_DATA_SOURCE_ID = os.getenv('NOTION_NOTAS_DATA_SOURCE_ID', '')  # data_source_id para data_sources.query

# Cliente Notion
_notion_client: Optional[Client] = None


def get_notion_client() -> Client:
    """Obt├®m cliente do Notion autenticado com timeout aumentado"""
    global _notion_client
    
    if _notion_client is not None:
        return _notion_client
    
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY n├úo configurada. Configure via vari├ível de ambiente ou c├│digo.")
    
    # Criar cliente com timeout aumentado (60 segundos)
    # A biblioteca notion-client usa httpx internamente
    try:
        import httpx
        # Configurar timeout customizado (60s total, 30s para conectar)
        timeout = httpx.Timeout(60.0, connect=30.0)
        # Criar cliente httpx customizado com timeout
        http_client = httpx.Client(timeout=timeout)
        # Passar cliente customizado para notion-client atrav├®s de options
        _notion_client = Client(auth=NOTION_API_KEY, client=http_client)
    except (ImportError, TypeError, Exception) as e:
        # Se n├úo conseguir configurar timeout customizado, usar cliente padr├úo
        print(f"AVISO: N├úo foi poss├¡vel configurar timeout customizado: {e}. Usando timeout padr├úo.", file=sys.stderr)
        _notion_client = Client(auth=NOTION_API_KEY)
    
    print(f"Cliente Notion inicializado com API Key: {NOTION_API_KEY[:10]}... (timeout: 60s)", file=sys.stderr)
    return _notion_client


def find_notas_database() -> Optional[Dict[str, str]]:
    """Encontra o database 'Notas' procurando em todos os databases
    Retorna dict com 'data_source_id' e 'database_id'"""
    try:
        client = get_notion_client()
        
        # Buscar todos os databases (usar "data_source" em vez de "database" na API atual)
        databases = client.search(filter={"property": "object", "value": "data_source"}).get("results", [])
        
        # Procurar por "Notas" (case-insensitive)
        for db in databases:
            title = ""
            if "title" in db and db["title"]:
                if isinstance(db["title"], list) and len(db["title"]) > 0:
                    title = db["title"][0].get("plain_text", "")
                elif isinstance(db["title"], str):
                    title = db["title"]
            
            if "Notas" in title or "notas" in title.lower():
                data_source_id = db.get("id", "")
                # Obter database_id do parent
                parent = db.get("parent", {})
                database_id = parent.get("database_id", data_source_id)  # Fallback para data_source_id se n├úo tiver parent
                
                result = {
                    "data_source_id": data_source_id,
                    "database_id": database_id
                }
                print(f"Database 'Notas' encontrado - data_source_id: {data_source_id}, database_id: {database_id}", file=sys.stderr)
                return result
        
        print("AVISO: Database 'Notas' n├úo encontrado. Use notion_set_database_id para configurar.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Erro ao buscar database 'Notas': {e}", file=sys.stderr)
        return None


def get_notas_database_id() -> str:
    """Obt├®m o database_id do database 'Notas' (para usar com databases.retrieve)"""
    global NOTAS_DATABASE_ID
    
    if NOTAS_DATABASE_ID:
        return NOTAS_DATABASE_ID
    
    # Tentar encontrar automaticamente
    db_info = find_notas_database()
    if db_info:
        database_id = db_info.get("database_id")
        if database_id:
            NOTAS_DATABASE_ID = database_id
            return database_id
    
    raise ValueError("Database 'Notas' n├úo encontrado. Use notion_set_database_id para configurar.")


def get_notas_data_source_id() -> str:
    """Obt├®m o data_source_id do database 'Notas' (para usar com data_sources.query)"""
    global NOTAS_DATA_SOURCE_ID, NOTAS_DATABASE_ID
    
    if NOTAS_DATA_SOURCE_ID:
        return NOTAS_DATA_SOURCE_ID
    
    # Tentar encontrar automaticamente
    db_info = find_notas_database()
    if db_info:
        data_source_id = db_info.get("data_source_id", "")
        if data_source_id:
            NOTAS_DATA_SOURCE_ID = data_source_id
            return data_source_id
    
    # Fallback: tentar usar database_id (pode funcionar em alguns casos)
    if NOTAS_DATABASE_ID:
        return NOTAS_DATABASE_ID
    
    raise ValueError("Database 'Notas' n├úo encontrado. Use notion_set_database_id para configurar.")


def search_pages(query: str, database_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca p├íginas no database 'Notas'"""
    try:
        client = get_notion_client()
        
        if database_id is None:
            database_id = get_notas_database_id()
        
        # Primeiro, obter estrutura do database para saber quais propriedades existem
        try:
            db_info = client.databases.retrieve(database_id=database_id)
            properties = db_info.get("properties", {})
            
            # Criar filtros para todas as propriedades de texto/t├¡tulo
            filters = []
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get("type", "")
                if prop_type in ["title", "rich_text", "text"]:
                    filters.append({
                        "property": prop_name,
                        prop_type: {
                            "contains": query
                        }
                    })
            
            # Obter data_source_id correto
            # Se database_id for data_source_id, usar diretamente; sen├úo obter do find_notas_database
            data_source_id = database_id
            try:
                # Tentar usar como data_source_id
                test_query = client.data_sources.query(data_source_id=database_id, page_size=1)
            except:
                # Se falhar, obter data_source_id correto
                data_source_id = get_notas_data_source_id()
            
            # Se n├úo encontrou propriedades de texto, buscar sem filtro e filtrar depois
            if not filters:
                # Buscar todas as p├íginas e filtrar manualmente
                all_pages = client.data_sources.query(data_source_id=data_source_id, page_size=100)
                results = []
                query_lower = query.lower()
                for page in all_pages.get("results", []):
                    page_str = json.dumps(page, default=str).lower()
                    if query_lower in page_str:
                        results.append(page)
                return results
            else:
                # Usar filtros constru├¡dos
                results = client.data_sources.query(
                    data_source_id=data_source_id,
                    filter={
                        "or": filters
                    }
                )
                return results.get("results", [])
        except Exception as filter_error:
            # Se falhar com filtros, tentar busca simples
            print(f"AVISO: Erro ao usar filtros, tentando busca simples: {filter_error}", file=sys.stderr)
            # Obter data_source_id correto
            try:
                data_source_id = get_notas_data_source_id()
            except:
                data_source_id = database_id
            all_pages = client.data_sources.query(data_source_id=data_source_id, page_size=100)
            results = []
            query_lower = query.lower()
            for page in all_pages.get("results", []):
                page_str = json.dumps(page, default=str).lower()
                if query_lower in page_str:
                    results.append(page)
            return results
    except Exception as e:
        raise Exception(f"Erro ao buscar p├íginas: {str(e)}")


def list_pages(database_id: Optional[str] = None, page_size: int = 50) -> Dict[str, Any]:
    """Lista todas as p├íginas do database 'Notas'"""
    try:
        client = get_notion_client()
        
        if database_id is None:
            database_id = get_notas_database_id()
        
        # Obter data_source_id correto (data_sources.query precisa do data_source_id)
        if database_id:
            # Tentar usar como data_source_id primeiro
            try:
                results = client.data_sources.query(
                    data_source_id=database_id,
                    page_size=page_size
                )
            except:
                # Se falhar, obter data_source_id correto
                data_source_id = get_notas_data_source_id()
                results = client.data_sources.query(
                    data_source_id=data_source_id,
                    page_size=page_size
                )
        else:
            # Usar data_source_id padr├úo
            data_source_id = get_notas_data_source_id()
            results = client.data_sources.query(
                data_source_id=data_source_id,
                page_size=page_size
            )
        
        return results
    except Exception as e:
        raise Exception(f"Erro ao listar p├íginas: {str(e)}")


def get_page(page_id: str) -> Dict[str, Any]:
    """Obt├®m detalhes de uma p├ígina espec├¡fica incluindo conte├║do/blocos"""
    try:
        client = get_notion_client()
        # Obter metadados da p├ígina
        page = client.pages.retrieve(page_id=page_id)
        
        # Obter blocos de conte├║do da p├ígina (com pagina├º├úo se necess├írio)
        try:
            all_blocks = []
            next_cursor = None
            max_iterations = 1000  # Limite de seguran├ºa para evitar loops infinitos
            iteration = 0
            page_size = 100  # Aumentar page_size para reduzir n├║mero de requisi├º├Áes
            
            print(f"Recuperando blocos da p├ígina {page_id}...", file=sys.stderr)
            
            # Obter todos os blocos (lidar com pagina├º├úo)
            while iteration < max_iterations:
                iteration += 1
                try:
                    if next_cursor:
                        blocks_result = client.blocks.children.list(
                            block_id=page_id, 
                            start_cursor=next_cursor,
                            page_size=page_size
                        )
                    else:
                        blocks_result = client.blocks.children.list(
                            block_id=page_id,
                            page_size=page_size
                        )
                    
                    blocks = blocks_result.get("results", [])
                    all_blocks.extend(blocks)
                    
                    print(f"  Blocos recuperados: {len(all_blocks)} (itera├º├úo {iteration})", file=sys.stderr)
                    
                    next_cursor = blocks_result.get("next_cursor")
                    if not next_cursor:
                        break
                    
                    # Pequeno delay para evitar rate limiting
                    time.sleep(0.1)
                    
                except Exception as req_error:
                    error_str = str(req_error).lower()
                    if "timeout" in error_str or "timed out" in error_str:
                        print(f"AVISO: Timeout na itera├º├úo {iteration}. Blocos recuperados at├® agora: {len(all_blocks)}", file=sys.stderr)
                        # Continuar com os blocos j├í recuperados
                        break
                    else:
                        # Outro tipo de erro, tentar novamente uma vez
                        print(f"AVISO: Erro ao recuperar blocos (itera├º├úo {iteration}): {req_error}", file=sys.stderr)
                        if iteration == 1:
                            # Se for a primeira itera├º├úo, tentar novamente
                            time.sleep(1)
                            continue
                        else:
                            # Se j├í recuperou alguns blocos, continuar com o que tem
                            break
            
            if iteration >= max_iterations:
                print(f"AVISO: Limite de itera├º├Áes atingido ({max_iterations}). Blocos recuperados: {len(all_blocks)}", file=sys.stderr)
            
            print(f"Total de blocos recuperados: {len(all_blocks)}", file=sys.stderr)
            
            # Fun├º├úo auxiliar para extrair texto de rich_text
            def extract_rich_text(rich_text_list):
                texts = []
                for text_item in rich_text_list:
                    if isinstance(text_item, dict) and "plain_text" in text_item:
                        texts.append(text_item["plain_text"])
                return "".join(texts)
            
            # Extrair texto dos blocos para facilitar leitura
            content_text = []
            for block in all_blocks:
                block_type = block.get("type", "")
                block_id = block.get("id", "")
                
                if block_type == "paragraph" and "paragraph" in block:
                    rich_text = block["paragraph"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(text)
                        
                elif block_type == "heading_1" and "heading_1" in block:
                    rich_text = block["heading_1"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"# {text}")
                        
                elif block_type == "heading_2" and "heading_2" in block:
                    rich_text = block["heading_2"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"## {text}")
                        
                elif block_type == "heading_3" and "heading_3" in block:
                    rich_text = block["heading_3"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"### {text}")
                        
                elif block_type == "bulleted_list_item" and "bulleted_list_item" in block:
                    rich_text = block["bulleted_list_item"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"- {text}")
                        
                elif block_type == "numbered_list_item" and "numbered_list_item" in block:
                    rich_text = block["numbered_list_item"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"1. {text}")
                        
                elif block_type == "to_do" and "to_do" in block:
                    rich_text = block["to_do"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    checked = block["to_do"].get("checked", False)
                    checkbox = "[x]" if checked else "[ ]"
                    if text:
                        content_text.append(f"{checkbox} {text}")
                        
                elif block_type == "quote" and "quote" in block:
                    rich_text = block["quote"].get("rich_text", [])
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"> {text}")
                        
                elif block_type == "code" and "code" in block:
                    rich_text = block["code"].get("rich_text", [])
                    language = block["code"].get("language", "")
                    text = extract_rich_text(rich_text)
                    if text:
                        content_text.append(f"```{language}\n{text}\n```")
            
            # Adicionar blocos e texto extra├¡do ├á resposta
            page["content_blocks"] = all_blocks
            page["content_text"] = "\n".join(content_text)
            page["has_content"] = len(all_blocks) > 0
            page["content_blocks_count"] = len(all_blocks)
        except Exception as blocks_error:
            # Se n├úo conseguir obter blocos, adicionar informa├º├úo de erro
            page["content_blocks"] = []
            page["content_text"] = ""
            page["has_content"] = False
            page["content_error"] = str(blocks_error)
            print(f"AVISO: N├úo foi poss├¡vel obter blocos da p├ígina {page_id}: {blocks_error}", file=sys.stderr)
        
        return page
    except Exception as e:
        raise Exception(f"Erro ao obter p├ígina: {str(e)}")


def create_page(title: str, content: Optional[str] = None, database_id: Optional[str] = None, 
                properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cria uma nova p├ígina no database 'Notas'"""
    try:
        client = get_notion_client()
        
        if database_id is None:
            database_id = get_notas_database_id()
        
        # Obter estrutura do database para descobrir propriedade de t├¡tulo
        db_info = client.databases.retrieve(database_id=database_id)
        db_properties = db_info.get("properties", {})
        
        # Preparar propriedades da p├ígina
        if properties:
            page_properties = properties.copy()
        else:
            # Encontrar propriedade de t├¡tulo automaticamente
            title_prop_name = None
            for prop_name, prop_info in db_properties.items():
                if prop_info.get("type") == "title":
                    title_prop_name = prop_name
                    break
            
            if title_prop_name:
                page_properties = {
                    title_prop_name: {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                }
            else:
                # Se n├úo encontrar propriedade title, tentar usar "Name" ou primeira propriedade
                first_prop = list(db_properties.keys())[0] if db_properties else "title"
                page_properties = {
                    first_prop: {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                }
        
        # Criar p├ígina
        new_page = {
            "parent": {
                "database_id": database_id
            },
            "properties": page_properties
        }
        
        # Criar p├ígina primeiro
        page = client.pages.create(**new_page)
        
        # Adicionar conte├║do se fornecido
        if content:
            # Dividir conte├║do em par├ígrafos se tiver m├║ltiplas linhas
            content_lines = content.split('\n')
            blocks = []
            for line in content_lines:
                if line.strip():
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": line.strip()
                                    }
                                }
                            ]
                        }
                    })
            
            if blocks:
                # Adicionar conte├║do como blocos filhos
                # Nota: O m├®todo correto ├® append, mas pode precisar de ajustes dependendo da vers├úo da biblioteca
                try:
                    client.blocks.children.append(block_id=page["id"], children=blocks)
                except AttributeError:
                    # Fallback: tentar m├®todo alternativo
                    for block in blocks:
                        client.blocks.children.append(block_id=page["id"], children=[block])
        
        return page
    except Exception as e:
        raise Exception(f"Erro ao criar p├ígina: {str(e)}")


def update_page(page_id: str, title: Optional[str] = None, 
                properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Atualiza uma p├ígina existente"""
    try:
        client = get_notion_client()
        
        update_data = {}
        if properties:
            update_data["properties"] = properties
        elif title:
            # Tentar atualizar t├¡tulo
            update_data["properties"] = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        
        page = client.pages.update(page_id=page_id, **update_data)
        return page
    except Exception as e:
        raise Exception(f"Erro ao atualizar p├ígina: {str(e)}")


def delete_page(page_id: str) -> bool:
    """Arquiva (soft delete) uma p├ígina"""
    try:
        client = get_notion_client()
        client.pages.update(page_id=page_id, archived=True)
        return True
    except Exception as e:
        raise Exception(f"Erro ao deletar p├ígina: {str(e)}")


def set_database_id(database_id: str) -> Dict[str, Any]:
    """Configura o ID do database 'Notas' manualmente"""
    global NOTAS_DATABASE_ID
    NOTAS_DATABASE_ID = database_id
    return {"success": True, "database_id": database_id, "message": "Database ID configurado com sucesso"}


def list_databases() -> List[Dict[str, Any]]:
    """Lista todos os databases dispon├¡veis"""
    try:
        client = get_notion_client()
        # Usar "data_source" em vez de "database" na API atual do Notion
        results = client.search(filter={"property": "object", "value": "data_source"})
        return results.get("results", [])
    except Exception as e:
        raise Exception(f"Erro ao listar databases: {str(e)}")


# Lista de ferramentas do Notion
TOOLS = [
    {
        "name": "notion_search_pages",
        "description": "Busca p├íginas no database 'Notas' por texto",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto para buscar nas p├íginas"
                },
                "database_id": {
                    "type": "string",
                    "description": "ID do database (opcional, usa 'Notas' por padr├úo)"
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "notion_list_pages",
        "description": "Lista todas as p├íginas do database 'Notas'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database_id": {
                    "type": "string",
                    "description": "ID do database (opcional, usa 'Notas' por padr├úo)"
                },
                "page_size": {
                    "type": "number",
                    "description": "N├║mero m├íximo de p├íginas para retornar",
                    "default": 50
                },
            },
        },
    },
    {
        "name": "notion_get_page",
        "description": "Obt├®m detalhes completos de uma p├ígina espec├¡fica incluindo todo o conte├║do (blocos de texto, par├ígrafos, t├¡tulos, listas, etc.). Retorna propriedades da p├ígina e conte├║do extra├¡do em formato texto leg├¡vel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "ID da p├ígina (obtido de notion_list_pages ou notion_search_pages)"
                },
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "notion_create_page",
        "description": "Cria uma nova p├ígina no database 'Notas'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "T├¡tulo da p├ígina"
                },
                "content": {
                    "type": "string",
                    "description": "Conte├║do da p├ígina (texto)"
                },
                "database_id": {
                    "type": "string",
                    "description": "ID do database (opcional, usa 'Notas' por padr├úo)"
                },
                "properties": {
                    "type": "object",
                    "description": "Propriedades customizadas da p├ígina (opcional)"
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "notion_update_page",
        "description": "Atualiza uma p├ígina existente",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "ID da p├ígina a ser atualizada"
                },
                "title": {
                    "type": "string",
                    "description": "Novo t├¡tulo da p├ígina"
                },
                "properties": {
                    "type": "object",
                    "description": "Propriedades a atualizar"
                },
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "notion_delete_page",
        "description": "Arquiva (deleta) uma p├ígina",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "ID da p├ígina a ser deletada"
                },
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "notion_list_databases",
        "description": "Lista todos os databases dispon├¡veis na conta",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "notion_set_database_id",
        "description": "Configura o ID do database 'Notas' manualmente",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database_id": {
                    "type": "string",
                    "description": "ID do database 'Notas'"
                },
            },
            "required": ["database_id"],
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
                        "name": "notion",
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
                
                if tool_name == "notion_search_pages":
                    query = arguments.get("query", "")
                    database_id = arguments.get("database_id")
                    
                    if not query:
                        raise ValueError("query ├® obrigat├│rio")
                    
                    pages = search_pages(query, database_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"pages": pages, "count": len(pages)}, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_list_pages":
                    database_id = arguments.get("database_id")
                    page_size = arguments.get("page_size", 50)
                    
                    result = list_pages(database_id, page_size)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_get_page":
                    page_id = arguments.get("page_id")
                    
                    if not page_id:
                        raise ValueError("page_id ├® obrigat├│rio")
                    
                    page = get_page(page_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(page, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_create_page":
                    title = arguments.get("title", "")
                    content = arguments.get("content")
                    database_id = arguments.get("database_id")
                    properties = arguments.get("properties")
                    
                    if not title:
                        raise ValueError("title ├® obrigat├│rio")
                    
                    page = create_page(title, content, database_id, properties)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(page, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_update_page":
                    page_id = arguments.get("page_id")
                    title = arguments.get("title")
                    properties = arguments.get("properties")
                    
                    if not page_id:
                        raise ValueError("page_id ├® obrigat├│rio")
                    
                    page = update_page(page_id, title, properties)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(page, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_delete_page":
                    page_id = arguments.get("page_id")
                    
                    if not page_id:
                        raise ValueError("page_id ├® obrigat├│rio")
                    
                    success = delete_page(page_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"success": success, "message": "P├ígina arquivada com sucesso"}, ensure_ascii=False),
                        }
                    ]
                
                elif tool_name == "notion_list_databases":
                    databases = list_databases()
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps({"databases": databases, "count": len(databases)}, indent=2, ensure_ascii=False, default=str),
                        }
                    ]
                
                elif tool_name == "notion_set_database_id":
                    database_id = arguments.get("database_id")
                    
                    if not database_id:
                        raise ValueError("database_id ├® obrigat├│rio")
                    
                    result = set_database_id(database_id)
                    result_content = [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, ensure_ascii=False),
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
        
        # M├®todo n├úo implementado
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {
                "code": -32601,
                "message": f"M├®todo n├úo implementado: {message.get('method')}",
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
    """Fun├º├úo principal - l├¬ mensagens do stdin"""
    # Log de inicializa├º├úo para stderr (n├úo quebra o protocolo)
    print("Servidor MCP Notion iniciado", file=sys.stderr)
    print(f"API Key: {NOTION_API_KEY[:10]}...", file=sys.stderr)
    print("Database padr├úo: 'Notas'", file=sys.stderr)
    print("Funcionalidades: Buscar, Listar, Criar, Atualizar, Deletar p├íginas", file=sys.stderr)
    
    # Tentar encontrar database 'Notas' automaticamente
    try:
        db_id = find_notas_database()
        if db_id:
            print(f"Database 'Notas' encontrado automaticamente: {db_id}", file=sys.stderr)
    except:
        print("AVISO: N├úo foi poss├¡vel encontrar database 'Notas' automaticamente.", file=sys.stderr)
        print("Use notion_list_databases para listar databases e notion_set_database_id para configurar.", file=sys.stderr)
    
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

