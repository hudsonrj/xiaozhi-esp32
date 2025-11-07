#!/usr/bin/env python3
"""
Testes básicos para validar componentes da bridge
"""
import sys
import os
import asyncio
import json

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from message_handler import MessageHandler


def test_message_handler():
    """Testa MessageHandler"""
    print("Testando MessageHandler...")
    handler = MessageHandler()
    
    # Teste 1: Validar requisição JSON-RPC válida
    valid_request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    assert handler.validate_jsonrpc(valid_request), "Requisição válida falhou"
    print("✓ Requisição válida validada")
    
    # Teste 2: Validar resposta JSON-RPC válida
    valid_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"tools": []}
    }
    assert handler.validate_jsonrpc(valid_response), "Resposta válida falhou"
    print("✓ Resposta válida validada")
    
    # Teste 3: Validar notificação JSON-RPC válida
    valid_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/message"
    }
    assert handler.validate_jsonrpc(valid_notification), "Notificação válida falhou"
    print("✓ Notificação válida validada")
    
    # Teste 4: Rejeitar mensagem inválida
    invalid_message = {
        "jsonrpc": "1.0",  # Versão errada
        "method": "test"
    }
    assert not handler.validate_jsonrpc(invalid_message), "Mensagem inválida aceita incorretamente"
    print("✓ Mensagem inválida rejeitada")
    
    # Teste 5: Parse e format
    message_str = json.dumps(valid_request)
    parsed = handler.parse_message(message_str)
    assert parsed == valid_request, "Parse falhou"
    print("✓ Parse JSON funcionando")
    
    formatted = handler.format_message(valid_request)
    assert formatted == message_str, "Format falhou"
    print("✓ Format JSON funcionando")
    
    # Teste 6: Extrair payload MCP
    mcp_message = {
        "type": "mcp",
        "payload": valid_request
    }
    extracted = handler.extract_mcp_payload(mcp_message)
    assert extracted == valid_request, "Extração de payload falhou"
    print("✓ Extração de payload MCP funcionando")
    
    # Teste 7: Envolver mensagem MCP
    wrapped = handler.wrap_mcp_message(valid_request)
    assert wrapped["type"] == "mcp", "Wrap MCP falhou"
    assert wrapped["payload"] == valid_request, "Wrap MCP payload falhou"
    print("✓ Wrap mensagem MCP funcionando")
    
    # Teste 8: Criar erro response
    error_response = handler.create_error_response(1, -32601, "Method not found")
    assert error_response["jsonrpc"] == "2.0", "Erro response JSON-RPC falhou"
    assert error_response["id"] == 1, "Erro response ID falhou"
    assert "error" in error_response, "Erro response error falhou"
    print("✓ Criação de erro response funcionando")
    
    print("\n✅ Todos os testes do MessageHandler passaram!\n")


def test_message_types():
    """Testa detecção de tipos de mensagem"""
    print("Testando detecção de tipos de mensagem...")
    handler = MessageHandler()
    
    request = {
        "jsonrpc": "2.0",
        "method": "test",
        "id": 1
    }
    assert handler.is_request(request), "Request não detectado"
    assert not handler.is_response(request), "Request detectado como response"
    assert not handler.is_notification(request), "Request detectado como notification"
    print("✓ Request detectado corretamente")
    
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {}
    }
    assert handler.is_response(response), "Response não detectado"
    assert not handler.is_request(response), "Response detectado como request"
    assert not handler.is_notification(response), "Response detectado como notification"
    print("✓ Response detectado corretamente")
    
    notification = {
        "jsonrpc": "2.0",
        "method": "test"
    }
    assert handler.is_notification(notification), "Notification não detectado"
    assert not handler.is_request(notification), "Notification detectado como request"
    assert not handler.is_response(notification), "Notification detectado como response"
    print("✓ Notification detectado corretamente")
    
    print("\n✅ Todos os testes de tipos de mensagem passaram!\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Testes Básicos - Xiaozhi MCP Bridge")
    print("=" * 60)
    print()
    
    try:
        test_message_handler()
        test_message_types()
        
        print("=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

