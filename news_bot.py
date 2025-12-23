import os
import json
import yfinance as yf
import requests
import google.generativeai as genai

# --- 配置 ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
MODEL_NAME = 'gemini-2.5-flash' # 保持一致

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def get_crypto_news():
    """从 Yahoo Finance 获取最新 BTC 新闻"""
    print("正在搜集全网新闻...")
    news_summary = ""
    try:
        btc = yf.Ticker("BTC-USD")
        news_list = btc.news
        if news_list:
            for i, item in enumerate(news_list[:5]): # 取前5条
                title = item.get('title', 'No Title')
                # 尝试获取发布时间
                news_summary += f"{i+1}. {title}\n"
        else:
            news_summary = "今日雅虎财经未返回特定新闻。"
    except Exception as e:
        news_summary = f"新闻获取失败: {e}"
        
    return news_summary

def analyze_sentiment(news_text):
    """AI 分析大盘情绪"""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = f"""
        你是一个加密货币舆情分析师。请阅读以下今日新闻标题：
        {news_text}
        
        任务：
        1. 判断今日大盘情绪：Bullish(看涨), Bearish(看跌), Neutral(中性)。
        2. 情绪打分：-10(极度恐慌) 到 +10(极度贪婪)。
        3. 用中文写一句话日报总结。
        
        请返回 JSON:
        {{
            "sentiment": "Bullish",
            "score": 5,
            "summary": "机构ETF买入强劲，市场情绪回暖"
        }}
        """
        
        generation_config = {"response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"舆情分析出错: {e}")
        return {"sentiment": "Neutral", "score": 0, "summary": "AI分析暂时不可用"}

def send_pushplus(html_content):
    if not PUSHPLUS_TOKEN: return
    requests.post('http://www.pushplus.plus/send', 
                  json={"token": PUSHPLUS_TOKEN, "title": "📢 每日币圈早报", "content": html_content, "template": "html"})

def main():
    news_text = get_crypto_news()
    print(f"获取到的新闻:\n{news_text}")
    
    result = analyze_sentiment(news_text)
    
    score = result.get('score', 0)
    sentiment = result.get('sentiment', 'Neutral')
    
    # 颜色逻辑
    color = "#333"
    if score > 0: color = "#d93025" # 红色看涨
    elif score < 0: color = "#188038" # 绿色看跌
    
    html = f"""
    <h2 style='color:{color}'>{sentiment} (情绪分: {score})</h2>
    <p><b>日报总结:</b> {result.get('summary', '')}</p>
    <hr>
    <h4>News Source:</h4>
    <pre style='white-space: pre-wrap;'>{news_text}</pre>
    <br>
    <small>Powered by {MODEL_NAME}</small>
    """
    
    send_pushplus(html)

if __name__ == "__main__":
    main()
