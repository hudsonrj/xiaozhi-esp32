"""
Message Handler para validação e formatação de mensagens JSON-RPC 2.0
"""
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handler para processar mensagens JSON-RPC 2.0"""
    
    @staticmethod
    def validate_jsonrpc(message: Dict[str, Any]) -> bool:
        """Valida se a mensagem é um JSON-RPC 2.0 válido"""
        if not isinstance(message, dict):
            return False
        
        if "jsonrpc" not in message or message["jsonrpc"] != "2.0":
            return False
        
        # Request deve ter method e id
        if "method" in message and "id" in message:
            return True
        
        # Response deve ter result ou error, e id
        if ("result" in message or "error" in message) and "id" in message:
            return True
        
        # Notification deve ter apenas method (sem id)
        if "method" in message and "id" not in message:
            return True
        
        return False
    
    @staticmethod
    def parse_message(data: str) -> Optional[Dict[str, Any]]:
        """Parse uma string JSON para dict"""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error("Erro ao fazer parse JSON: %s", e)
            return None
    
    @staticmethod
    def format_message(message: Dict[str, Any]) -> str:
        """Formata um dict para string JSON"""
        try:
            return json.dumps(message, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error("Erro ao formatar mensagem: %s", e)
            return ""
    
    @staticmethod
    def extract_mcp_payload(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrai o payload MCP de uma mensagem do WebSocket xiaozhi.me"""
        if message.get("type") == "mcp" and "payload" in message:
            return message["payload"]
        return None
    
    @staticmethod
    def wrap_mcp_message(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Envolve um payload JSON-RPC em uma mensagem MCP para xiaozhi.me"""
        return {
            "type": "mcp",
            "payload": payload
        }
    
    @staticmethod
    def wrap_mcp_payload(payload: Dict[str, Any], session_id: str = "") -> Dict[str, Any]:
        """Envolve um payload JSON-RPC em uma mensagem MCP para xiaozhi.me com session_id"""
        message = {
            "type": "mcp",
            "payload": payload
        }
        if session_id:
            message["session_id"] = session_id
        return message
    
    @staticmethod
    def is_request(message: Dict[str, Any]) -> bool:
        """Verifica se é uma requisição JSON-RPC"""
        return "method" in message and "id" in message
    
    @staticmethod
    def is_response(message: Dict[str, Any]) -> bool:
        """Verifica se é uma resposta JSON-RPC"""
        return ("result" in message or "error" in message) and "id" in message
    
    @staticmethod
    def is_notification(message: Dict[str, Any]) -> bool:
        """Verifica se é uma notificação JSON-RPC (sem id)"""
        return "method" in message and "id" not in message
    
    @staticmethod
    def create_error_response(request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Cria uma resposta de erro JSON-RPC"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }

