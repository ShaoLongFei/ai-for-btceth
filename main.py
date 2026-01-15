import os
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import requests

# --- 配置部分 ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
PUSHPLUS_TOKEN_LIYAN = os.getenv("PUSHPLUS_TOKEN_LIYAN")
# 🔥 锁定你测试成功的 2.5 版本
MODEL_NAME = 'gemini-2.5-flash' 

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
else:
    print("❌ 错误: 未检测到 GEMINI_API_KEY")
    exit(1)

def get_market_data(symbol='BTC-USD'):
    """获取行情并计算指标"""
    print(f"正在获取 {symbol} 数据...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="7d", interval="1h")
        
        if df.empty: return None, 0

        # 计算指标
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) # ATR用于计算止损距离
        
        # MACD
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        latest = df.iloc[-1]
        
        # 自动获取MACD列名
        macd_col = [c for c in df.columns if c.startswith('MACD_')][0]
        macds_col = [c for c in df.columns if c.startswith('MACDs_')][0]
        
        summary = f"""
        标的: {symbol}
        现价: {latest['Close']:.2f}
        ATR(波动率): {latest['ATR']:.2f}
        
        [技术指标]
        RSI(14): {latest['RSI']:.2f}
        EMA20: {latest['EMA_20']:.2f} | EMA50: {latest['EMA_50']:.2f}
        MACD: {latest[macd_col]:.2f} | 信号线: {latest[macds_col]:.2f}
        """
        return summary, latest['Close']

    except Exception as e:
        print(f"❌ 数据错误: {e}")
        return None, 0

def analyze_with_gemini(data_summary, current_price):
    """AI 分析师 (支持做空 + 止盈止损计算)"""
    if not data_summary: return None

    print(f"🧠 正在调用 {MODEL_NAME} 进行策略计算...")
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        你是一个专业的加密货币量化交易员。请分析以下数据：
        {data_summary}
        
        任务：
        1. 决策方向：做多(LONG)、做空(SHORT) 或 观望(WAIT)。
        2. 信心分数：0-100。
        3. **关键任务**：如果开仓，请根据 ATR 和技术支撑/压力位，计算具体的止盈(TP)和止损(SL)价格。
           - 做多(LONG): TP > 现价, SL < 现价。
           - 做空(SHORT): TP < 现价, SL > 现价。
           - 观望(WAIT): TP和SL填 0。
        
        请严格返回 JSON 格式：
        {{
            "signal": "LONG",
            "confidence": 85,
            "entry_price": {current_price},
            "tp_price": 92500.00,
            "sl_price": 88000.00,
            "reason": "RSI突破50，MACD金叉，看涨"
        }}
        """
        
        # 强制 JSON 输出
        generation_config = {"response_mime_type": "application/json"}
        
        response = model.generate_content(prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"AI 思考出错: {e}")
        # 出错时返回默认安全值
        return {"signal": "WAIT", "confidence": 0, "reason": f"API Error: {str(e)[:20]}"}

def send_pushplus(title, content):
    if not PUSHPLUS_TOKEN: return
    requests.post('http://www.pushplus.plus/send', 
                  json={"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "html"})
    if not PUSHPLUS_TOKEN_LIYAN: return
    requests.post('http://www.pushplus.plus/send', 
                  json={"token": PUSHPLUS_TOKEN_LIYAN, "title": title, "content": content, "template": "html"})
    print("✅ 推送发送成功")

def main():
    symbol = 'BTC-USD'
    data_text, price = get_market_data(symbol)
    
    if data_text:
        result = analyze_with_gemini(data_text, price)
        
        signal = result.get('signal', 'WAIT')
        score = result.get('confidence', 0)
        tp = result.get('tp_price', 0)
        sl = result.get('sl_price', 0)
        reason = result.get('reason', '')
        
        # 装饰图标
        icon = "☕"
        if signal == "LONG": icon = "🟢 做多"
        elif signal == "SHORT": icon = "🔴 做空"
        
        # 计算盈亏比 (RR Ratio)
        rr_info = ""
        if signal != "WAIT" and tp != 0 and sl != 0:
            diff_profit = abs(tp - price)
            diff_loss = abs(price - sl)
            if diff_loss > 0:
                rr = diff_profit / diff_loss
                rr_info = f" | 盈亏比 1:{rr:.1f}"

        msg_title = f"{icon} {symbol} ({score}分)"
        msg_content = f"""
        <b>决策:</b> {signal} {rr_info}<br>
        <b>现价:</b> ${price:,.2f}<br>
        <hr>
        <b>🎯 止盈 (TP):</b> ${tp:,.2f}<br>
        <b>🛡️ 止损 (SL):</b> ${sl:,.2f}<br>
        <hr>
        <b>AI 逻辑:</b> {reason}<br>
        <br>
        <small>Model: {MODEL_NAME}</small>
        """
        
        print(msg_title)
        send_pushplus(msg_title, msg_content)

if __name__ == "__main__":
    main()
