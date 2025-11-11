#!/usr/bin/env python3
"""
Script de teste para ApeRAG MCP - Listar collections e fazer busca
"""
import asyncio
import aiohttp
import json
import sys

API_URL = "https://rag.apecloud.com/mcp/"
API_KEY = "sk-aaddc93bfb5044d8af0d4044fb197b5d"

async def test_list_collections():
    """Testa listagem de collections"""
    print("=" * 60)
    print("TESTE 1: Listar Collections")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_collections",
            "arguments": {}
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=message, headers=headers) as response:
                if response.status == 200:
                    # Verificar tipo de conteúdo
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'text/event-stream' in content_type:
                        # Processar SSE
                        text = await response.text()
                        # Extrair JSON do SSE
                        lines = text.strip().split('\n')
                        json_str = None
                        for line in lines:
                            if line.startswith('data: '):
                                json_str = line[6:]  # Remove "data: "
                                break
                        if json_str:
                            data = json.loads(json_str)
                        else:
                            # Tentar parsear como JSON direto
                            data = json.loads(text)
                    else:
                        data = await response.json()
                    
                    print(f"Status: {response.status}")
                    print(f"Content-Type: {content_type}")
                    print(f"Resposta completa:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if "result" in data:
                        result = data["result"]
                        # Verificar structuredContent primeiro (mais fácil de processar)
                        if "structuredContent" in result:
                            structured = result["structuredContent"]
                            if "items" in structured:
                                collections = structured["items"]
                                print(f"\n✅ Encontradas {len(collections)} collections:")
                                for i, coll in enumerate(collections, 1):
                                    coll_id = coll.get("id", "N/A")
                                    title = coll.get("title", "N/A")
                                    desc = coll.get("description", "N/A")
                                    print(f"\n  {i}. ID: {coll_id}")
                                    print(f"     Título: {title}")
                                    print(f"     Descrição: {desc[:100]}..." if len(desc) > 100 else f"     Descrição: {desc}")
                                return collections
                        
                        # Fallback: tentar processar content text
                        if "content" in result:
                            content = result["content"]
                            if content and len(content) > 0:
                                text_content = content[0].get("text", "")
                                try:
                                    collections_data = json.loads(text_content)
                                    if "items" in collections_data:
                                        collections = collections_data["items"]
                                        print(f"\n✅ Encontradas {len(collections)} collections:")
                                        for i, coll in enumerate(collections, 1):
                                            coll_id = coll.get("id", "N/A")
                                            title = coll.get("title", "N/A")
                                            desc = coll.get("description", "N/A")
                                            print(f"\n  {i}. ID: {coll_id}")
                                            print(f"     Título: {title}")
                                            print(f"     Descrição: {desc[:100]}..." if len(desc) > 100 else f"     Descrição: {desc}")
                                        return collections
                                except json.JSONDecodeError:
                                    print(f"\n⚠️ Resposta não é JSON válido: {text_content}")
                        
                        print("\n⚠️ Nenhuma collection encontrada")
                    else:
                        print("\n⚠️ Formato de resposta inesperado")
                else:
                    error_text = await response.text()
                    print(f"❌ Erro HTTP {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Erro ao fazer requisição: {e}")
    
    return None

async def test_search_collection(collection_id: str, query: str):
    """Testa busca em uma collection"""
    print("\n" + "=" * 60)
    print(f"TESTE 2: Buscar na Collection '{collection_id}'")
    print(f"Query: '{query}'")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_collection",
            "arguments": {
                "collection_id": collection_id,
                "query": query,
                "use_vector_index": True,
                "use_fulltext_index": True,
                "use_graph_index": True,
                "use_summary_index": True,
                "rerank": True,
                "topk": 5
            }
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=message, headers=headers) as response:
                if response.status == 200:
                    # Verificar tipo de conteúdo
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'text/event-stream' in content_type:
                        # Processar SSE
                        text = await response.text()
                        # Extrair JSON do SSE
                        lines = text.strip().split('\n')
                        json_str = None
                        for line in lines:
                            if line.startswith('data: '):
                                json_str = line[6:]  # Remove "data: "
                                break
                        if json_str:
                            data = json.loads(json_str)
                        else:
                            # Tentar parsear como JSON direto
                            data = json.loads(text)
                    else:
                        data = await response.json()
                    
                    print(f"Status: {response.status}")
                    print(f"Content-Type: {content_type}")
                    
                    if "result" in data:
                        result = data["result"]
                        if "content" in result:
                            content = result["content"]
                            if content and len(content) > 0:
                                text_content = content[0].get("text", "")
                                try:
                                    search_data = json.loads(text_content)
                                    
                                    # Verificar se há erro
                                    if "error" in search_data:
                                        print(f"❌ Erro: {search_data['error']}")
                                        if "details" in search_data:
                                            print(f"   Detalhes: {search_data['details']}")
                                        return False
                                    
                                    # Verificar se há resultados
                                    if "items" in search_data and search_data["items"]:
                                        items = search_data["items"]
                                        print(f"\n✅ Encontrados {len(items)} resultados:")
                                        for i, item in enumerate(items[:5], 1):
                                            rank = item.get("rank", "N/A")
                                            score = item.get("score", "N/A")
                                            content_text = item.get("content", "")[:200]
                                            source = item.get("source", "N/A")
                                            recall_type = item.get("recall_type", "N/A")
                                            
                                            print(f"\n  Resultado {i}:")
                                            print(f"    Rank: {rank}, Score: {score:.4f}" if isinstance(score, (int, float)) else f"    Rank: {rank}, Score: {score}")
                                            print(f"    Tipo: {recall_type}")
                                            print(f"    Fonte: {source}")
                                            print(f"    Conteúdo: {content_text}...")
                                        return True
                                    else:
                                        print("\n⚠️ Nenhum resultado encontrado")
                                        print(f"Resposta completa: {json.dumps(search_data, indent=2, ensure_ascii=False)}")
                                except json.JSONDecodeError:
                                    print(f"\n⚠️ Resposta não é JSON válido: {text_content}")
                                    print(f"Resposta completa: {text_content}")
                        else:
                            print(f"\n⚠️ Formato de resposta inesperado")
                            print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    print(f"❌ Erro HTTP {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Erro ao fazer requisição: {e}")
            import traceback
            traceback.print_exc()
    
    return False

async def main():
    """Função principal"""
    print("\n🔍 Testando ApeRAG MCP API")
    print(f"URL: {API_URL}")
    print(f"API Key: {API_KEY[:20]}...\n")
    
    # Teste 1: Listar collections
    collections = await test_list_collections()
    
    if collections and len(collections) > 0:
        # Pegar a primeira collection disponível
        first_collection = collections[0]
        collection_id = first_collection.get("id", "")
        
        print(f"\n📚 Usando collection: {collection_id}")
        
        # Teste 2: Buscar sobre um livro
        queries = [
            "livro",
            "pense e enriqueça",
            "machiliano"
        ]
        
        for query in queries:
            success = await test_search_collection(collection_id, query)
            if success:
                break
            print(f"\n⚠️ Tentando próxima query...")
    else:
        print("\n⚠️ Não foi possível listar collections. Tentando busca direta com ID conhecido...")
        # Tentar com o ID que encontramos
        await test_search_collection("col5925ae37c6f60eb4", "livro")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

