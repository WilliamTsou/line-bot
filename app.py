from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
)
import random
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

# 從環境變數讀取 Channel Access Token / Channel Secret
configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

# 訂閱者清單檔案（儲存 userId 的 JSON 陣列）
SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")


def load_subscribers():
    try:
        import json

        if not os.path.exists(SUBSCRIBERS_FILE):
            return []
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_subscribers(subs):
    import json

    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        app.logger.warning("Failed to save subscribers: %s", e)


# 支援的幣別對映：key = 使用者輸入的國家/幣別名稱（中文或英文），value = Yahoo 金融的符號
RATE_SYMBOLS = {
    "紐西蘭": "NZDTWD=X",
    "NZD": "NZDTWD=X",
    "美金": "USDTWD=X",
    "USD": "USDTWD=X",
    "歐元": "EURTWD=X",
    "EUR": "EURTWD=X",
    "日圓": "JPYTWD=X",
    "JPY": "JPYTWD=X",
    "人民幣": "CNHTWD=X",
    "CNY": "CNHTWD=X",
}


def get_rate(symbol):
    """泛用的匯率抓取（symbol 例如 'NZDTWD=X'）若抓不到回傳 None。"""
    url = f"https://tw.stock.yahoo.com/quote/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=6)
    except Exception as e:
        app.logger.warning("request error: %s", e)
        return None
    if res.status_code != 200:
        app.logger.warning("status_code: %s for %s", res.status_code, symbol)
        return None
    soup = BeautifulSoup(res.text, "html.parser")
    # same heuristic as before: try trend-down then trend-up
    price_tag = soup.find(
        "span",
        attrs={
            "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-down)"
        },
    )
    if not price_tag:
        price_tag = soup.find(
            "span",
            attrs={
                "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-up)"
            },
        )
    if price_tag and price_tag.text.strip():
        return price_tag.text.strip()
    return None


def send_rate_to_subscribers():
    """排程呼叫：抓取每個訂閱者的匯率並推播。"""
    subs = load_subscribers()
    if not subs:
        app.logger.info("No subscribers to send rates to.")
        return
    # 準備一段簡短的匯率摘要，這裡示範幾個幣別
    summary_lines = []
    for name, sym in [("紐西蘭(NZD)", "NZDTWD=X"), ("美金(USD)", "USDTWD=X"), ("歐元(EUR)", "EURTWD=X")]:
        rate = get_rate(sym)
        if rate:
            summary_lines.append(f"{name}：{rate}")
        else:
            summary_lines.append(f"{name}：無法取得")
    message_text = "每日匯率提醒（08:00）：\n" + "\n".join(summary_lines)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for user_id in subs:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(to=user_id, messages=[TextMessage(text=message_text)])
                )
            except Exception as e:
                app.logger.warning("Failed to push to %s: %s", user_id, e)


# 啟動背景排程（只在當前進程中啟動一次）
scheduler = None
try:
    scheduler = BackgroundScheduler()
    # 每天 08:00（伺服器時區）觸發
    scheduler.add_job(send_rate_to_subscribers, CronTrigger(hour=8, minute=0))
    scheduler.start()
    app.logger.info("Scheduler started")
except Exception as e:
    app.logger.warning("Scheduler not started: %s", e)


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

    # 先找「跌」的樣式（你本機測試的版本）
    price_tag = soup.find(
        "span",
        attrs={
            "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-down)"
        },
    )

    # 如果現在是漲，就會是 trend-up，再試一次
    if not price_tag:
        price_tag = soup.find(
            "span",
            attrs={
                "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-up)"
            },
        )

    if price_tag and price_tag.text.strip():
        return price_tag.text.strip()

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

        # 列出支援的匯率（簡單清單）
        if text == "匯率清單":
            supported = ["紐西蘭", "美金", "歐元", "日圓", "人民幣"]
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="我們支援的匯率：\n" + "\n".join(supported))],
                )
            )
            return

        # 使用者輸入幣別名稱時回傳該幣別匯率（支援中文或英文縮寫）
        if text in RATE_SYMBOLS:
            sym = RATE_SYMBOLS[text]
            rate = get_rate(sym)
            if rate:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=f"{text} 匯率：{rate}")],
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="無法取得匯率，請稍後再試。")],
                    )
                )
            return

        # 訂閱 / 取消訂閱 每日匯率推播
        if text in ("訂閱匯率", "訂閱"):
            user_id = getattr(event.source, "userId", None) or getattr(event.source, "user_id", None)
            if not user_id:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="無法取得你的 user id，無法完成訂閱。")],
                    )
                )
                return
            subs = load_subscribers()
            if user_id in subs:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="你已經訂閱過每日匯率通知。")],
                    )
                )
                return
            subs.append(user_id)
            save_subscribers(subs)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="已訂閱每日匯率（每天 08:00）。")],
                )
            )
            return

        if text in ("取消訂閱", "取消訂閱匯率"):
            user_id = getattr(event.source, "userId", None) or getattr(event.source, "user_id", None)
            if not user_id:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="無法取得你的 user id，無法完成取消訂閱。")],
                    )
                )
                return
            subs = load_subscribers()
            if user_id in subs:
                subs.remove(user_id)
                save_subscribers(subs)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="已取消訂閱每日匯率。")],
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="你尚未訂閱每日匯率。")],
                    )
                )
            return

        # 3️⃣ 德德喜歡誰
        if text == "德德喜歡誰":
            people = [
                '威威', '伯伯', '小鄒', '錢錢', '小菜', 'toby', 'ㄈㄈ'
            ]
            person = random.choice(people)
            reply_text = f"德德喜歡{person}！"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
            return

        # # 其他訊息：echo 回覆
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


