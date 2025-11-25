from flask_ngrok import run_with_ngrok
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage

app = Flask(__name__)

@app.route("/")
def home():
  line_bot_api = LineBotApi('k/FQS6Bj4Jqr3EmwngcjfthUYj4yhKOeUFbxcTfJjZz+S8Z4N8J8gghijsPLFx/qTU5Xld0ws6KgbpoPUIbfTryYNAkRBaZ+O/zcXJgLMkclJLj2LTnjbeT2ui/RhcChi+QQh411p2ouZ3cnQoxZkAdB04t89/1O/w1cDnyilFU=')
  try:
    # 網址被執行時，等同使用 GET 方法發送 request，觸發 LINE Message API 的 push_message 方法
    line_bot_api.push_message('yummy_corn1117', TextSendMessage(text='Hello World!!!'))
    return 'OK'
  except:
    print('error')

if __name__ == "__main__":
    run_with_ngrok(app)
    app.run()
