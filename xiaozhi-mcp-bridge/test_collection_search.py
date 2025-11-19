#!/usr/bin/env python3
"""
Teste de busca na collection usando ID correto
"""
import asyncio
import aiohttp
import json
import sys

API_URL = "https://rag.apecloud.com/mcp/"
API_KEY = "sk-aaddc93bfb5044d8af0d4044fb197b5d"

async def test_search_collection():
    """Testa busca na collection usando ID correto"""
    print("=" * 70)
    print("TESTE: Buscar na Collection 'Conhecimento'")
    print("=" * 70)
    
    # Primeiro, listar collections para obter o ID correto
    print("\n1. Listando collections para obter ID...")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    list_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_collections",
            "arguments": {}
        }
    }
    
    collection_id = None
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=list_message, headers=headers) as response:
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
                            if "result" in data:
                                result = data["result"]
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "items" in structured:
                                        collections = structured["items"]
                                        print(f"   Encontradas {len(collections)} collections:")
                                        for coll in collections:
                                            coll_id = coll.get("id", "")
                                            coll_title = coll.get("title", "")
                                            print(f"   - ID: {coll_id}, Título: {coll_title}")
                                            if coll_title.lower() == "conhecimento":
                                                collection_id = coll_id
                                                print(f"   ✓ Collection 'Conhecimento' encontrada! ID: {collection_id}")
                                                break
                    else:
                        data = await response.json()
                        print(f"   Resposta JSON direta: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"   Erro ao listar collections: {e}")
            return False
    
    if not collection_id:
        print("\n   ⚠️ Collection 'Conhecimento' não encontrada. Usando ID conhecido...")
        collection_id = "col5925ae37c6f60eb4"
        print(f"   Usando ID: {collection_id}")
    
    # Agora fazer a busca usando o ID correto
    print(f"\n2. Fazendo busca na collection (ID: {collection_id})...")
    query = "acesso à collection Conhecimento"
    
    search_message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_collection",
            "arguments": {
                "collection_id": collection_id,  # Usar ID, não nome!
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
            async with session.post(API_URL, json=search_message, headers=headers) as response:
                print(f"   Status HTTP: {response.status}")
                
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
                            if "result" in data:
                                result = data["result"]
                                
                                # Verificar se há erro
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "error" in structured:
                                        print(f"\n   ❌ ERRO: {structured.get('error')}")
                                        print(f"   Detalhes: {structured.get('details', 'N/A')}")
                                        return False
                                
                                # Verificar se há resultados
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "items" in structured:
                                        items = structured["items"]
                                        print(f"\n   ✓ SUCESSO! Encontrados {len(items)} resultados:")
                                        for i, item in enumerate(items[:3], 1):
                                            rank = item.get("rank", "N/A")
                                            score = item.get("score", "N/A")
                                            content_text = item.get("content", "")[:200]
                                            source = item.get("source", "N/A")
                                            recall_type = item.get("recall_type", "N/A")
                                            
                                            print(f"\n   Resultado {i}:")
                                            print(f"     Rank: {rank}, Score: {score:.4f}" if isinstance(score, (int, float)) else f"     Rank: {rank}, Score: {score}")
                                            print(f"     Tipo: {recall_type}")
                                            print(f"     Fonte: {source}")
                                            print(f"     Conteúdo: {content_text}...")
                                        return True
                                
                                # Tentar formato alternativo
                                if "content" in result:
                                    content = result["content"]
                                    if isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, dict) and "text" in item:
                                                try:
                                                    text_data = json.loads(item["text"])
                                                    if "items" in text_data:
                                                        items = text_data["items"]
                                                        print(f"\n   ✓ SUCESSO! Encontrados {len(items)} resultados (formato alternativo)")
                                                        return True
                                                except json.JSONDecodeError:
                                                    pass
                                
                                print(f"\n   ⚠️ Resposta recebida mas formato não reconhecido:")
                                print(f"   {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
                    else:
                        data = await response.json()
                        if "result" in data:
                            result = data["result"]
                            if "error" in result or ("structuredContent" in result and "error" in result["structuredContent"]):
                                print(f"\n   ❌ ERRO na resposta:")
                                print(f"   {json.dumps(result, indent=2, ensure_ascii=False)}")
                                return False
                            print(f"\n   ✓ Resposta recebida:")
                            print(f"   {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}...")
                else:
                    error_text = await response.text()
                    print(f"\n   ❌ Erro HTTP {response.status}: {error_text}")
                    return False
        except asyncio.TimeoutError:
            print(f"\n   ❌ Timeout na requisição")
            return False
        except Exception as e:
            print(f"\n   ❌ Erro ao fazer requisição: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return False

async def main():
    """Função principal"""
    print("\n🔍 Testando busca na collection ApeRAG")
    print(f"URL: {API_URL}")
    print(f"API Key: {API_KEY[:20]}...\n")
    
    success = await test_search_collection()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ TESTE PASSOU - Busca funcionou corretamente!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ TESTE FALHOU - Verifique os erros acima")
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

