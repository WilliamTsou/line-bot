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

# 從環境變數讀取 Channel Access Token / Channel Secret
configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))


@app.route("/callback", methods=["POST"])
def callback():
    # 取得 X-Line-Signature header
    signature = request.headers.get("X-Line-Signature", "")

    # 取得 request body
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)

    # 驗證與處理 webhook
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return "OK"


# ---------- 匯率爬蟲函式 ----------
def get_nzd_twd_rate():
    url = "https://tw.stock.yahoo.com/quote/NZDTWD=X"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=5)
    except Exception as e:
        print("request error:", e)
        return None

    if res.status_code != 200:
        print("status_code:", res.status_code)
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # Yahoo 版面常改，一次試幾種 class
    possible_classes = [
        "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-down)",
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
        line_bot_api = MessagingApi(api_client)

        # 1️⃣ 匯率功能
        if text == "給我匯率":
            rate = get_nzd_twd_rate()
            if rate:
                reply_text = (
                    "目前紐西蘭幣（NZD）對台幣（TWD）的匯率是：\n"
                    f"👉 {rate}"
                )
            else:
                reply_text = "目前無法取得匯率 QQ（可能是 Yahoo 改版或暫時無法連線）"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
            return

        # 2️⃣ quick_reply 功能
        if text == "quick_reply":
            base_url = request.url_root  # e.g. https://line-bot-self.vercel.app/

            postback_icon = urljoin(base_url, "static/postback.png")
            message_icon = urljoin(base_url, "static/message.png")
            datetime_icon = urljoin(base_url, "static/calendar.png")
            date_icon = urljoin(base_url, "static/calendar.png")
            time_icon = urljoin(base_url, "static/time.png")

            quick_reply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(
                            label="Postback",
                            data="postback",
                            display_text="postback",
                        ),
                        image_url=postback_icon,
                    ),
                    QuickReplyItem(
                        action=MessageAction(
                            label="Message",
                            text="message",
                        ),
                        image_url=message_icon,
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Date",
                            data="date",
                            mode="date",
                        ),
                        image_url=date_icon,
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Time",
                            data="time",
                            mode="time",
                        ),
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
                    QuickReplyItem(
                        action=CameraAction(label="Camera"),
                    ),
                    QuickReplyItem(
                        action=CameraRollAction(label="Camera Roll"),
                    ),
                    QuickReplyItem(
                        action=LocationAction(label="Location"),
                    ),
                ]
            )

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="請選擇項目",
                            quick_reply=quick_reply,
                        )
                    ],
                )
            )
            return

        # 3️⃣ 其他訊息：echo 回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)],
            )
        )


@line_handler.add(PostbackEvent)
def handle_postback(event):
    postback_data = event.postback.data

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if postback_data == "postback":
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="Postback")],
                )
            )
        elif postback_data == "date":
            date = event.postback.params.get("date", "")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=date)],
                )
            )
        elif postback_data == "time":
            time = event.postback.params.get("time", "")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=time)],
                )
            )
        elif postback_data == "datetime":
            dt = event.postback.params.get("datetime", "")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=dt)],
                )
            )


if __name__ == "__main__":
    # 本機測試用；在 Vercel 上會忽略這一段，直接使用 app 物件
    app.run(port=5000)

