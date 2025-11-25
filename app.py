from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
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
    LocationAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent
)

import os

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        if text == 'quick_reply':
            postback_icon = request.url_root + 'static/postback.png'
            postback_icon = postback_icon.replace("http", "https")
            message_icon = request.url_root + 'static/message.png'
            message_icon = message_icon.replace("http", "https")
            datetime_icon = request.url_root + 'static/calendar.png'
            datetime_icon = datetime_icon.replace("http", "https")
            date_icon = request.url_root + 'static/calendar.png'
            date_icon = date_icon.replace("http", "https")
            time_icon = request.url_root + 'static/time.png'
            time_icon = time_icon.replace("http", "https")

            quickReply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=PostbackAction(
                            label="Postback",
                            data="postback",
                            display_text="postback"
                        ),
                        image_url=postback_icon
                    ),
                    QuickReplyItem(
                        action=MessageAction(
                            label="Message",
                            text="message"
                        ),
                        image_url=message_icon
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Date",
                            data="date",
                            mode="date"
                        ),
                        image_url=date_icon
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Time",
                            data="time",
                            mode="time"
                        ),
                        image_url=time_icon
                    ),
                    QuickReplyItem(
                        action=DatetimePickerAction(
                            label="Datetime",
                            data="datetime",
                            mode="datetime",
                            initial="2024-01-01T00:00",
                            max="2025-01-01T00:00",
                            min="2023-01-01T00:00"
                        ),
                        image_url=datetime_icon
                    ),
                    QuickReplyItem(
                        action=CameraAction(label="Camera")
                    ),
                    QuickReplyItem(
                        action=CameraRollAction(label="Camera Roll")
                    ),
                    QuickReplyItem(
                        action=LocationAction(label="Location")
                    )
                ]
            )
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text='請選擇項目',
                        quick_reply=quickReply
                    )]
                )
            )

@line_handler.add(PostbackEvent)
def handle_postback(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        postback_data = event.postback.data
        if postback_data == 'postback':
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text='Postback')]
                )
            )
        elif postback_data == 'date':
            date = event.postback.params['date']
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=date)]
                )
            )
        elif postback_data == 'time':
            time = event.postback.params['time']
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=time)]
                )
            )
        elif postback_data == 'datetime':
            datetime = event.postback.params['datetime']
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=datetime)]
                )
            )

if __name__ == "__main__":
    app.run()