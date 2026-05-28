from dotenv import load_dotenv
import os

load_dotenv()

print("=== Ollama 配置驗證 ===")
print(f"✓ OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL')}")
print(f"✓ OLLAMA_MODEL_DISPATCH: {os.getenv('OLLAMA_MODEL_DISPATCH')}")
print(f"✓ OLLAMA_MODEL_DEBUG: {os.getenv('OLLAMA_MODEL_DEBUG')}")

import requests
base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
print(f"\n=== 連線測試 ===")
print(f"📍 嘗試連線到: {base_url}")

try:
    response = requests.get(f"{base_url}/api/tags", timeout=5)
    if response.status_code == 200:
        print(f"✅ 成功連線到 Ollama")
        models = response.json().get('models', [])
        print(f"📊 可用模型數: {len(models)}")
        for model in models:
            print(f"   - {model.get('name', 'Unknown')}")
    else:
        print(f"⚠️ 伺服器狀態碼: {response.status_code}")
except requests.exceptions.ConnectionError as e:
    print(f"❌ 無法連線: {e}")
    print(f"   請檢查:")
    print(f"   1. Tailscale VPN 是否已連線")
    print(f"   2. Ollama 伺服器 ({base_url}) 是否在運行")
    print(f"   3. 防火牆是否允許連線到端口 11434")
except Exception as e:
    print(f"❌ 錯誤: {e}")
