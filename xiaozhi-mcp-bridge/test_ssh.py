#!/usr/bin/env python3
"""
Teste simples de conexão SSH
"""
import subprocess
import sys

host = "100.124.250.21"
user = "allied"
command = "echo 'SSH Test OK'"

print(f"Testando SSH para {user}@{host}...")
print(f"Comando: ssh {user}@{host} '{command}'")

try:
    result = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", f"{user}@{host}", command],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print(f"\nExit code: {result.returncode}")
    print(f"\nSTDOUT:\n{result.stdout}")
    print(f"\nSTDERR:\n{result.stderr}")
    
    if result.returncode == 0:
        print("\n✅ SSH funcionando!")
    else:
        print("\n❌ SSH falhou")
        
except subprocess.TimeoutExpired:
    print("\n❌ Timeout na conexão SSH")
except FileNotFoundError:
    print("\n❌ Comando SSH não encontrado")
except Exception as e:
    print(f"\n❌ Erro: {e}")

