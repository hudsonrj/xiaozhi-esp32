#!/usr/bin/env python3
"""
Teste para verificar se a conversão de nome para ID está funcionando
Simula o que o bridge faz quando recebe uma requisição com nome ao invés de ID
"""
import asyncio
import aiohttp
import json

API_URL = "https://rag.apecloud.com/mcp/"
API_KEY = "sk-aaddc93bfb5044d8af0d4044fb197b5d"

async def convert_name_to_id(collection_name: str):
    """Converte nome de collection para ID"""
    print(f"Convertendo '{collection_name}' para ID...")
    
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
                                
                                # Tentar structuredContent primeiro
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "items" in structured:
                                        collections = structured["items"]
                                        for coll in collections:
                                            coll_id = coll.get("id", "")
                                            coll_title = coll.get("title", "").lower()
                                            coll_name_lower = collection_name.lower()
                                            
                                            if coll_title == coll_name_lower:
                                                print(f"   ✓ Encontrado! '{collection_name}' -> '{coll_id}'")
                                                return coll_id
                                
                                # Tentar content (formato alternativo)
                                if "content" in result:
                                    content = result["content"]
                                    if isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, dict) and "text" in item:
                                                try:
                                                    text_data = json.loads(item["text"])
                                                    if "items" in text_data:
                                                        collections = text_data["items"]
                                                        for coll in collections:
                                                            coll_id = coll.get("id", "")
                                                            coll_title = coll.get("title", "").lower()
                                                            coll_name_lower = collection_name.lower()
                                                            
                                                            if coll_title == coll_name_lower:
                                                                print(f"   ✓ Encontrado! '{collection_name}' -> '{coll_id}'")
                                                                return coll_id
                                                except json.JSONDecodeError:
                                                    continue
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return None
    
    print(f"   ❌ Collection '{collection_name}' não encontrada")
    return None

async def test_with_name():
    """Testa busca usando nome (simula o que o agente faz)"""
    print("=" * 70)
    print("TESTE: Busca usando NOME (simula comportamento do agente)")
    print("=" * 70)
    
    # Simular o que acontece quando o agente passa o nome
    collection_name = "Conhecimento"
    query = "acesso à collection Conhecimento"
    
    print(f"\n1. Agente passa collection_id='{collection_name}' (nome, não ID)")
    
    # Verificar se precisa converter
    if not collection_name.startswith("col"):
        print(f"   ⚠️ Detectado: '{collection_name}' não começa com 'col' - precisa converter!")
        
        # Converter nome para ID
        collection_id = await convert_name_to_id(collection_name)
        
        if collection_id:
            print(f"\n2. Convertido! Usando ID: {collection_id}")
        else:
            print(f"\n2. ❌ Conversão falhou! Tentando usar nome mesmo...")
            collection_id = collection_name
    else:
        print(f"   ✓ '{collection_name}' já é um ID válido")
        collection_id = collection_name
    
    # Fazer busca
    print(f"\n3. Fazendo busca com collection_id='{collection_id}'...")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    search_message = {
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
                "topk": 3
            }
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=search_message, headers=headers) as response:
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
                                
                                # Verificar erro
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "error" in structured:
                                        print(f"\n   ❌ ERRO: {structured.get('error')}")
                                        print(f"   Detalhes: {structured.get('details', 'N/A')}")
                                        return False
                                
                                # Verificar sucesso
                                if "structuredContent" in result:
                                    structured = result["structuredContent"]
                                    if "items" in structured:
                                        items = structured["items"]
                                        print(f"\n   ✓ SUCESSO! Encontrados {len(items)} resultados")
                                        return True
        except Exception as e:
            print(f"\n   ❌ Erro: {e}")
            return False
    
    return False

async def main():
    """Função principal"""
    print("\n🔍 Testando conversão de nome para ID e busca")
    print(f"URL: {API_URL}\n")
    
    success = await test_with_name()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ TESTE PASSOU - Conversão e busca funcionaram!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ TESTE FALHOU")
        print("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

