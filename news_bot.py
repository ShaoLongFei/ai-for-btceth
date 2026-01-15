import os
import json
import feedparser  # 引入新库
import requests
import google.generativeai as genai
from datetime import datetime

# --- 配置 ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
PUSHPLUS_TOKEN_LIYAN = os.getenv("PUSHPLUS_TOKEN_LIYAN")
MODEL_NAME = 'gemini-2.5-flash' 

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def get_crypto_news():
    """从 CoinTelegraph RSS 获取最新新闻 (比 yfinance 更稳定)"""
    print("正在连接 CoinTelegraph RSS 源...")
    news_summary = ""
    
    # CoinTelegraph 的 RSS 地址
    rss_url = "https://cointelegraph.com/rss"
    
    try:
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            return "RSS源暂时无法连接或无更新。"
            
        print(f"成功获取 {len(feed.entries)} 条新闻")
        
        # 取前 8 条新闻，信息量更足
        for i, entry in enumerate(feed.entries[:8]):
            title = entry.title
            # 这里的 published 通常格式比较乱，我们只取标题即可，AI 自己知道时效性
            news_summary += f"{i+1}. {title}\n"
            
    except Exception as e:
        news_summary = f"RSS抓取失败: {e}"
        
    return news_summary

def analyze_sentiment(news_text):
    """AI 分析大盘情绪"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        你是一个加密货币市场情报官。请根据以下来自 CoinTelegraph 的最新新闻标题，分析今日市场情绪：
        
        {news_text}
        
        【任务】
        1. **情绪倾向**：Bullish (看涨) / Bearish (看跌) / Neutral (中性)。
        2. **恐慌贪婪分**：-10 (极度恐慌/利空) 到 +10 (极度贪婪/利好)。
        3. **一句话日报**：用中文总结市场正在发生的大事（20字以内）。
        
        请严格返回 JSON:
        {{
            "sentiment": "Bullish",
            "score": 6,
            "summary": "SEC批准新ETF申请，市场普遍看涨"
        }}
        """
        
        generation_config = {"response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"舆情分析出错: {e}")
        return {"sentiment": "Neutral", "score": 0, "summary": "AI分析服务暂时繁忙"}

def send_pushplus(html_content):
    if not PUSHPLUS_TOKEN: return
    requests.post('http://www.pushplus.plus/send', 
                  json={"token": PUSHPLUS_TOKEN, "title": "📢 每日币圈风向", "content": html_content, "template": "html"})
    if not PUSHPLUS_TOKEN_LIYAN: return
    requests.post('http://www.pushplus.plus/send', 
                  json={"token": PUSHPLUS_TOKEN_LIYAN, "title": "📢 每日币圈风向", "content": html_content, "template": "html"})

def main():
    news_text = get_crypto_news()
    
    # 如果抓取失败，直接发报错
    if "RSS抓取失败" in news_text:
        send_pushplus(f"<h3>❌ 系统报错</h3><p>{news_text}</p>")
        return

    result = analyze_sentiment(news_text)
    
    score = result.get('score', 0)
    sentiment = result.get('sentiment', 'Neutral')
    summary = result.get('summary', '无总结')
    
    # 颜色逻辑：利好是红(国内习惯)或绿，这里用 Emoji 增强
    color = "#333"
    icon = "⚖️"
    if score >= 3: 
        color = "#d93025" # 红 (利好)
        icon = "🔥"
    elif score <= -3: 
        color = "#188038" # 绿 (利空)
        icon = "❄️"
    
    html = f"""
    <div style="padding: 10px; border-left: 4px solid {color}; background-color: #f9f9f9;">
        <h2 style='color:{color}; margin:0;'>{icon} {sentiment} ({score})</h2>
        <p style="font-size: 16px; font-weight: bold; margin-top: 10px;">{summary}</p>
    </div>
    <hr>
    <h4>🌍 CoinTelegraph 头条:</h4>
    <pre style='white-space: pre-wrap; font-family: sans-serif; color: #555;'>{news_text}</pre>
    <br>
    <small>Powered by {MODEL_NAME} & RSS</small>
    """
    
    print(f"分析完成: {sentiment} ({score})")
    send_pushplus(html)

if __name__ == "__main__":
    main()
