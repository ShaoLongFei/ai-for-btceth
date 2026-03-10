AI for Btc/eth/any
🤖 AI Crypto Signal Bot (AI 加密货币信号机器人)

这是一个基于 Google Gemini AI + Yahoo Finance 的自动化量化分析工具。它完全免费，利用 GitHub Actions 每天定时分析市场行情，并将买卖建议推送到你的微信。
✳️ 痛点：
不想分析：上班无法看数据，但是又想进行投资。
信息获取能力弱：可能是加密/投资市场新人，不懂得如何看k线or其它杂七杂八内容
✨ 特点：

    0 成本：使用免费的 GitHub Actions 和 Gemini 免费 API。

    全自动：无需服务器，云端自动运行。

    智能分析：AI 根据 RSI、EMA 等技术指标给出行情分析和信心分数。

    即时推送：通过 PushPlus 推送到微信。

🚀 快速开始 (3步部署)
第一步：Fork 项目

点击右上角的 Fork 按钮，将本仓库复制到你自己的 GitHub 账号下。
第二步：准备密钥 (Secrets)

你需要获取两个免费的密钥，用于驱动机器人和接收消息。

    获取 Gemini API Key (AI 大脑)

        访问 Google AI Studio。

        登录 Google 账号，点击 "Get API key" -> "Create API key"。

        复制以 AIza 开头的密钥。

    获取 PushPlus Token (消息推送)

        访问 PushPlus 官网。

        微信扫码登录，复制你的 "Token"。

第三步：配置 GitHub 仓库

回到你 Fork 好的 GitHub 仓库页面：

    点击顶部菜单栏的 Settings (设置)。

    在左侧栏找到 Secrets and variables -> 点击 Actions。

    点击绿色的 New repository secret 按钮，依次添加以下两个变量：

Name (变量名)	Secret (值)	说明
GEMINI_API_KEY	你的 AIza... 密钥	必填，用于调用 AI
PUSHPLUS_TOKEN	你的 PushPlus Token	必填，用于微信推送
▶️ 如何运行

配置好密钥后，机器人已经准备就绪！

    点击仓库顶部的 Actions 标签页。

    如果看到绿色按钮提示 "I understand my workflows, go ahead and enable them"，请点击它（Fork 的项目默认会禁用工作流）。

    在左侧点击 Crypto AI Analysis。

    点击右侧的 Run workflow -> 再次点击绿色的 Run workflow 按钮。

    等待约 30 秒，如果显示绿色对勾 ✅，请检查你的微信，应该已经收到推送了！

以后，它会在每天北京时间早上 8:00 (UTC 0:00) 自动运行，无需人工干预。
🛠️ 高级设置 (可选)

如果你想修改配置，可以编辑仓库中的文件：
1. 修改运行频率

编辑 .github/workflows/crypto_bot.yml 文件中的 cron 字段：
YAML

on:
  schedule:
    - cron: '0 */4 * * *'  # 改为每4小时运行一次

2. 修改交易对

编辑 main.py 文件：
Python

def main():
    symbol = 'ETH-USD'  # 改为以太坊，注意格式是 币种-USD

3. 修改 AI 模型

如果报错或想用更新的模型，编辑 main.py：
Python

# 例如改为 gemini-2.0-flash-exp 或其他可用模型
model = genai.GenerativeModel('gemini-2.5-flash') 

❓ 常见问题

Q: 运行报错 404 models/gemini-xxxx 怎么办？ A: 说明 Google 更新了模型名称。请在 main.py 中将模型名称修改为最新的版本号（如 gemini-1.5-flash-001 或 gemini-2.0-flash）。

Q: 为什么没有收到微信推送？ A: 请检查 GitHub Secrets 中的 PUSHPLUS_TOKEN 是否填写正确，或者检查 PushPlus 官网是否额度耗尽。

免责声明： 本项目仅供学习和技术研究使用，AI 生成的投资建议仅供参考，不构成任何财务指导。市场有风险，投资需谨慎。
修改文档，以防工作流被禁用
