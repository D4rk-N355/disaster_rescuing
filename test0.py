from google import genai
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def list_available_models():
    try:
        # 初始化 Gemini Client
        client = genai.Client()

        # 列出模型
        response = client.models.list_models()
        print("可用模型：", response)
    except Exception as e:
        print("列出模型失敗！")
        print("錯誤訊息：", e)

# 呼叫列出模型函數
list_available_models()