from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
    MessageAction,
    DatetimePickerAction,
    CameraAction,
    CameraRollAction,
    LocationAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
)

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# ⭐⭐⭐ 匯率爬蟲函式 ⭐⭐⭐
def get_nzd_twd_rate():
    url = "https://tw.stock.yahoo.com/quote/NZDTWD=X"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=5)
    except:
        return None

    if res.status_code != 200:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # Yahoo STOCK class 常常變，一次抓多個可能的 class 比較穩
    possible_classes = [
        "Fz(32px) Fw(b) Lh(1) Mend(4px)", 
        "Fz(32px) Fw(b) Lh(1)",
        "Fz(24px) Fw(b)",
    ]

    for cls in possible_classes:
        tag = soup.find("span", class_=cls)
        if tag and tag.text.strip():
            return tag.text.strip()

    return None


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()
    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)

        # =============================
        # 🇳🇿 匯率功能：給我匯率
        # =============================
        if text == "給我匯率":
            rate = get_nzd_twd_rate()

            if rate:
                reply = f"目前紐西蘭幣（NZD）對台幣（TWD）的匯率是：\n👉 {rate}"
            else:
                reply = "無法取得匯率 QQ\n（Yahoo 可能改版或阻擋爬蟲）"

            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply)]
                )
            )
            return  # 結束，不進 QuickReply/Echo
            
        # =============================
        # 🔘 quick_reply 功能
        # =============================
        if text == "quick_reply":
            base_url = request.url_root

            postback_icon = urljoin(base_url, "static/postback.png")
            message_icon  = urljoin(base_url, "static/message.png")
            datetime_icon = urljoin(base_url, "static/calendar.png")
            date_icon     = urljoin(base_url, "static/calendar.png")
            time_icon     = urljoin(base_url, "static/time.png")

            quick_reply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(
                            label="Postback", data="postback", display_text="postback"
                        ),
                        image_url=postback_icon,
                    ),
                    QuickReplyItem(
                        action=MessageAction(label="Message", text="message"),
                        image_url=message_icon,
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(label="Date", data="date", mode="date"),
                        image_url=date_icon,
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(label="Time", data="time", mode="time"),
                        image_url=time_icon,
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Datetime",
                            data="datetime",
                            mode="datetime",
                            initial="2024-01-01T00:00",
                            max="2025-01-01T00:00",
                            min="2023-01-01T00:00",
                        ),
                        image_url=datetime_icon,
                    ),
                    QuickReplyItem(action=CameraAction(label="Camera")),
                    QuickReplyItem(action=CameraRollAction(label="Camera Roll")),
                    QuickReplyItem(action=LocationAction(label="Location")),
                ]
            )

            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請選擇項目", quick_reply=quick_reply)
                    ],
                )
            )
            return

        # =============================
        # 📝 其他訊息 — echo 回覆
        # =============================
        bot.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)],
            )
        )


# Postback Event handler
@line_handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data

    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)

        if data == "postback":
            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Postback")]
                )
            )
        elif data == "date":
            value = event.postback.params["date"]
            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=value)]
                )
            )
        elif data == "time":
            value = event.postback.params["time"]
            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=value)]
                )
            )
        elif data == "datetime":
            value = event.postback.params["datetime"]
            bot.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=value)]
                )
            )


if __name__ == "__main__":
    app.run(port=5000)
