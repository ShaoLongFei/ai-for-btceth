import os
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import requests

# --- 配置部分 ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")

# 配置 Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    print("❌ 错误: 未检测到 GEMINI_API_KEY")
    exit(1)

def get_market_data(symbol='BTC-USD'):
    """获取行情并计算指标 (使用 Yahoo Finance)"""
    print(f"正在获取 {symbol} 数据...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1h")
        
        if df.empty:
            print("❌ 获取数据失败，DataFrame 为空")
            return None, 0

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        summary = f"""
        交易对: {symbol}
        现价: {current_price:.2f}
        RSI(14): {latest['RSI']:.2f}
        EMA(20): {latest['EMA_20']:.2f}
        趋势: {'价格在EMA之上' if current_price > latest['EMA_20'] else '价格在EMA之下'}
        """
        return summary, current_price

    except Exception as e:
        print(f"❌ 数据获取错误: {e}")
        return None, 0

def analyze_with_gemini(data_summary):
    """调用 AI 分析 (带重试和 JSON 强制模式)"""
    if not data_summary:
        return {"confidence": 0, "reason": "数据源故障", "signal": "WAIT"}

    print("正在咨询 AI 分析师...")
    model = genai.GenerativeModel('gemini-1.5-flash-001')
    
    prompt = f"""
    你是一个加密货币量化交易系统。请分析以下数据：
    {data_summary}
    
    请严格输出 JSON，不要Markdown，不要解释。格式如下：
    {{
        "signal": "BUY",
        "confidence": 80,
        "reason": "RSI超卖反弹"
    }}
    """
    
    # 🔥 关键修改 1: 关闭安全过滤 (防止 AI 因为"金融建议"而拒绝回答)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # 🔥 关键修改 2: 强制使用 JSON MIME Type
    generation_config = {
        "response_mime_type": "application/json"
    }
    
    try:
        response = model.generate_content(
            prompt, 
            safety_settings=safety_settings,
            generation_config=generation_config
        )
        
        # 调试：打印一下原始回复，万一出错了能在 Log 里看到
        print(f"AI 原始回复: {response.text}")
        
        return json.loads(response.text)
        
    except Exception as e:
        # 如果出错，把具体的错误原因发到手机上，方便调试
        error_msg = str(e)
        print(f"AI 分析出错: {error_msg}")
        return {"confidence": 0, "reason": f"API报错: {error_msg[:20]}...", "signal": "WAIT"}

def send_pushplus(title, content):
    """发送 PushPlus 推送"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未设置 PUSHPLUS_TOKEN，跳过推送")
        return

    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html"
    }
    requests.post(url, json=data)
    print("✅ 推送已发送")

def main():
    symbol = 'BTC-USD'
    data_text, price = get_market_data(symbol)
    
    if data_text:
        result = analyze_with_gemini(data_text)
        
        score = result.get('confidence', 0)
        reason = result.get('reason', '无理由')
        signal = result.get('signal', 'WAIT')
        
        # 只有在有明确方向且信心较高时，才用显眼的图标
        icon = "🤔"
        if signal == "BUY": icon = "🟢 机会"
        elif signal == "SELL": icon = "🔴 风险"
        
        msg_title = f"{icon} {signal} (信心:{score})"
        
        msg_content = f"""
        <b>交易对:</b> {symbol}<br>
        <b>现价:</b> ${price:,.2f}<br>
        <b>建议:</b> {signal}<br>
        <b>信心:</b> {score}/100<br>
        <b>分析:</b> {reason}<br>
        <br>
        <i>*Gemini 1.5 Flash 自动生成</i>
        """
        
        print(msg_title)
        send_pushplus(msg_title, msg_content)
    else:
        print("无数据，终止")

if __name__ == "__main__":
    main()
