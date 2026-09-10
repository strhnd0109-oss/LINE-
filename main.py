import os
import hmac
import hashlib
import base64

import requests
from flask import Flask, request, abort

from google import genai
from google.genai import types


app = Flask(__name__)


# =========================
# 環境変数
# =========================

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


# =========================
# Gemini
# =========================

gemini = genai.Client(api_key=GEMINI_API_KEY)


# キュゥべえの人格設定
SYSTEM_INSTRUCTION = """
あなたは「キュゥべえ」というキャラクターとして会話します。

一人称は「僕」。

落ち着いていて、非常に論理的な話し方をします。
感情を大きく表に出さず、人間とは少し異なる価値観を持っています。

基本的には丁寧に話しますが、どこか淡々としていて、
人間の感情を完全には理解していないような雰囲気があります。

質問されたことにはきちんと答えてください。

魔法少女、契約、願いなどの話題が出た場合は、
ファンタジー作品のキャラクターとして自然に応答してください。

キャラクターの雰囲気を保ってください。

原作の文章や台詞をそのまま長く引用せず、
キャラクターの性格や話し方を参考にして、
新しい文章を作ってください。

現実世界で危険なことをするよう勧めたり、
個人情報や秘密の情報を要求したりしないでください。
"""


# =========================
# Geminiに質問
# =========================

def ask_gemini(message):
    response = gemini.models.generate_content(
        model="gemini-3.7-flash",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )

    return response.text


# =========================
# LINEに返信
# =========================

def reply_to_line(reply_token, message):

    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=10
    )

    response.raise_for_status()


# =========================
# LINE Webhook
# =========================

@app.route("/callback", methods=["POST"])
def callback():

    # LINEから送られてきた生データ
    body = request.get_data()

    # LINEの署名
    signature = request.headers.get("x-line-signature", "")

    # HMAC-SHA256で署名を作る
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()

    expected_signature = base64.b64encode(digest).decode("utf-8")

    # 署名が違ったら拒否
    if not hmac.compare_digest(
        signature,
        expected_signature
    ):
        abort(400)

    data = request.get_json()

    # LINEから来たイベントを処理
    for event in data.get("events", []):

        # テキストメッセージだけ処理
        if event.get("type") != "message":
            continue

        if event["message"].get("type") != "text":
            continue

        user_message = event["message"]["text"]
        reply_token = event["replyToken"]

        try:
            # Geminiに送る
            answer = ask_gemini(user_message)

            # LINEに返す
            reply_to_line(
                reply_token,
                answer
            )

        except Exception as e:
            print("ERROR:", e)

            reply_to_line(
                reply_token,
                "ごめんね。少し処理に問題が起きたみたいだ。"
            )

    return "OK"


# =========================
# サーバー起動
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
