#!/usr/bin/env python3
"""
Teste de queries vetoriais no ApeRAG para verificar se está retornando informações dos documentos
"""
import asyncio
import aiohttp
import json
import sys
import time

API_URL = "https://rag.apecloud.com/mcp/"
API_KEY = "sk-aaddc93bfb5044d8af0d4044fb197b5d"
COLLECTION_ID = "col5925ae37c6f60eb4"

async def test_vector_search(collection_id: str, query: str, test_name: str):
    """Testa busca vetorial com diferentes configurações"""
    print("\n" + "=" * 70)
    print(f"TESTE: {test_name}")
    print(f"Query: '{query}'")
    print("=" * 70)
    
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
            "name": "search_collection",
            "arguments": {
                "collection_id": collection_id,
                "query": query,
                "use_vector_index": True,
                "use_fulltext_index": True,
                "use_graph_index": True,
                "use_summary_index": True,
                "use_vision_index": False,
                "rerank": True,
                "topk": 5
            }
        }
    }
    
    start_time = time.time()
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        try:
            async with session.post(API_URL, json=message, headers=headers) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'text/event-stream' in content_type:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        json_str = None
                        for line in lines:
                            if line.startswith('data: '):
                                json_str = line[6:]
                                break
                        if json_str:
                            data = json.loads(json_str)
                        else:
                            data = json.loads(text)
                    else:
                        data = await response.json()
                    
                    print(f"⏱️  Tempo de resposta: {elapsed_time:.2f} segundos")
                    print(f"📊 Status: {response.status}")
                    
                    if "result" in data:
                        result = data["result"]
                        if "content" in result:
                            content = result["content"]
                            if content and len(content) > 0:
                                text_content = content[0].get("text", "")
                                try:
                                    search_data = json.loads(text_content)
                                    
                                    if "error" in search_data:
                                        print(f"❌ Erro: {search_data['error']}")
                                        return False
                                    
                                    if "items" in search_data and search_data["items"]:
                                        items = search_data["items"]
                                        print(f"\n✅ Encontrados {len(items)} resultados:\n")
                                        
                                        for i, item in enumerate(items[:5], 1):
                                            rank = item.get("rank", "N/A")
                                            score = item.get("score", "N/A")
                                            content_text = item.get("content", "")[:300]
                                            source = item.get("source", "N/A")
                                            recall_type = item.get("recall_type", "N/A")
                                            metadata = item.get("metadata", {})
                                            
                                            print(f"  📄 Resultado {i}:")
                                            print(f"     Rank: {rank}, Score: {score:.4f}" if isinstance(score, (int, float)) else f"     Rank: {rank}, Score: {score}")
                                            print(f"     Tipo: {recall_type}")
                                            print(f"     Fonte: {source}")
                                            if metadata.get("page_idx") is not None:
                                                print(f"     Página: {metadata['page_idx'] + 1}")
                                            print(f"     Conteúdo: {content_text}...")
                                            print()
                                        
                                        return True
                                    else:
                                        print("\n⚠️ Nenhum resultado encontrado")
                                        return False
                                except json.JSONDecodeError as e:
                                    print(f"\n⚠️ Erro ao parsear JSON: {e}")
                                    print(f"Resposta: {text_content[:500]}")
                                    return False
                    else:
                        print(f"\n⚠️ Formato de resposta inesperado")
                        print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ Erro HTTP {response.status}: {error_text}")
                    return False
        except asyncio.TimeoutError:
            print(f"❌ Timeout após {elapsed_time:.2f} segundos")
            return False
        except Exception as e:
            print(f"❌ Erro ao fazer requisição: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return False

async def main():
    """Função principal"""
    print("\n🔍 Testando Queries Vetoriais no ApeRAG")
    print(f"Collection ID: {COLLECTION_ID}")
    print(f"URL: {API_URL}\n")
    
    # Queries de teste para verificar busca vetorial
    queries = [
        ("Machiavelli e poder", "Busca sobre Maquiavel"),
        ("Napoleon Hill e riqueza", "Busca sobre Napoleon Hill"),
        ("Kant e razão pura", "Busca sobre filosofia de Kant"),
        ("Bauman e sociedade líquida", "Busca sobre Bauman"),
        ("48 leis do poder", "Busca sobre livro específico"),
        ("como pensar e enriquecer", "Busca semântica sobre desenvolvimento pessoal"),
    ]
    
    success_count = 0
    total_count = len(queries)
    
    for query, test_name in queries:
        success = await test_vector_search(COLLECTION_ID, query, test_name)
        if success:
            success_count += 1
        print("\n" + "-" * 70)
        await asyncio.sleep(1)  # Pequeno delay entre requisições
    
    print("\n" + "=" * 70)
    print(f"RESUMO: {success_count}/{total_count} testes bem-sucedidos")
    print("=" * 70)

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

