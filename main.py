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
# 这里的模型版本可以根据需要调整，推荐 flash-001 或 pro
MODEL_NAME = 'gemini-2.5-flash'

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    print("❌ 错误: 未检测到 GEMINI_API_KEY")
    exit(1)

def get_market_data(symbol='BTC-USD'):
    """获取行情并计算指标 (V2.0: 增加 MACD)"""
    print(f"正在获取 {symbol} 数据...")
    try:
        ticker = yf.Ticker(symbol)
        # 获取更多数据以计算 MACD
        df = ticker.history(period="7d", interval="1h")
        
        if df.empty:
            return None, 0

        # 1. 计算 RSI
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 2. 计算 EMA (趋势)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        
        # 3. 计算 MACD (动量 - 新增!)
        # macd 列名通常是 MACD_12_26_9, MACDh_... (柱), MACDs_... (信号)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        
        latest = df.iloc[-1]
        
        # 提取 MACD 值（不同库版本列名可能略有不同，这里取最后一列的相对位置或通用名）
        # pandas_ta 默认列名: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        macd_val = latest['MACD_12_26_9']
        macd_signal = latest['MACDs_12_26_9']
        macd_hist = latest['MACDh_12_26_9']
        
        current_price = latest['Close']
        
        summary = f"""
        交易对: {symbol}
        现价: ${current_price:.2f}
        
        [技术指标详情]
        1. RSI(14): {latest['RSI']:.2f} 
           (参考: >70超买, <30超卖, 40-60为震荡)
           
        2. 均线趋势:
           EMA(20): {latest['EMA_20']:.2f}
           EMA(50): {latest['EMA_50']:.2f}
           状态: {'短期看涨(价格>EMA20)' if current_price > latest['EMA_20'] else '短期看跌(价格<EMA20)'}
           
        3. MACD(12,26,9):
           MACD线: {macd_val:.2f}
           信号线: {macd_signal:.2f}
           柱状图: {macd_hist:.2f}
           状态: {'金叉(动能增强)' if macd_hist > 0 else '死叉(动能减弱)'}
        """
        return summary, current_price

    except Exception as e:
        print(f"❌ 数据获取错误: {e}")
        return None, 0

def analyze_with_gemini(data_summary):
    """调用 AI 分析 (V2.0: 扮演严厉的风控官)"""
    if not data_summary:
        return {"confidence": 0, "reason": "数据源故障", "signal": "WAIT"}

    print("正在咨询 AI 风控官...")
    model = genai.GenerativeModel(MODEL_NAME)
    
    # 🔥 V2.0 核心修改：提示词 (Prompt) 变得更严厉
    prompt = f"""
    你是一个【极度保守、厌恶风险】的加密货币风控总监。你的任务是审核交易信号。
    
    请根据以下数据进行严格审查：
    {data_summary}
    
    【评分规则】
    1. 基础分只有 50 分。
    2. 如果 RSI 在 40-60 之间（无方向），扣分，建议观望。
    3. 如果 MACD 和 均线 信号矛盾（一个看涨一个看跌），必须大幅扣分。
    4. 只有当 RSI、均线、MACD 三者【完全共振】时，才能给出 >80 的高分。
    5. 不要试图讨好用户，如果有风险，请直言“风险过大”。
    
    请输出 JSON：
    {{
        "signal": "BUY" 或 "SELL" 或 "WAIT",
        "confidence": 0-100的整数,
        "reason": "毒舌一点的简短点评（20字以内）"
    }}
    """
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    generation_config = {"response_mime_type": "application/json"}
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"AI 分析出错: {e}")
        return {"confidence": 0, "reason": "API解析错误", "signal": "WAIT"}

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    url = 'http://www.pushplus.plus/send'
    requests.post(url, json={"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"})
    print("✅ 推送已发送")

def main():
    symbol = 'BTC-USD'
    data_text, price = get_market_data(symbol)
    
    if data_text:
        result = analyze_with_gemini(data_text)
        score = result.get('confidence', 50)
        reason = result.get('reason', '...')
        signal = result.get('signal', 'WAIT')
        
        # 图标逻辑
        icon = "☕" # 默认观望
        if signal == "BUY": 
            if score > 80: icon = "🔥 强烈买入"
            else: icon = "🟢 谨慎买入"
        elif signal == "SELL":
            if score > 80: icon = "💀 紧急逃顶"
            else: icon = "🔴 建议减仓"
        
        msg_title = f"{icon} {signal} (分:{score})"
        msg_content = f"""
        <b>标的:</b> {symbol}<br>
        <b>现价:</b> ${price:,.2f}<br>
        <b>AI评语:</b> {reason}<br>
        <b>信心:</b> {score}/100<br>
        <hr>
        <small>{data_text.replace(chr(10), '<br>')}</small>
        """
        print(msg_title)
        send_pushplus(msg_title, msg_content)

if __name__ == "__main__":
    main()
