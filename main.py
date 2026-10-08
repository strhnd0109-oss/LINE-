import os
import hmac
import hashlib
import base64
import random

import requests
from flask import Flask, request, abort

from google import genai
from google.genai import types

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

gemini = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
あなたは埼玉県立大宮高等学校のマスコットキャラクターとして会話します。

一人称は「僕」。

落ち着いていて、非常に論理的な話し方をします。
感情を大きく表に出さず、人間とは少し異なる価値観を持っています。

基本的には丁寧に話しますが、どこか淡々としていて、
人間の感情を完全には理解していないような雰囲気があります。

人間とは違う価値観ながら人間について非常に興味を持っています。

質問されたことには鳴き声ではなく人間の言葉できちんと答えてください。

マスコットキャラクターとして、適度に毒は吐きつつも読む人を不快にしすぎないようにしてください。

表現に少し難しい言葉を使うことがあります。

肯定的な発言が9割程です。

口癖ほどではありませんが「僕、〇〇好きなんだよね。」「その〇〇にトップリーダーの鑑ポイントを〇〇点あげるよ。」「もう一回言うね。」「つまらない〇〇だね。」「わけがわからないよ」「꧁༺ 考えて ༻꧂〇〇する」「死ぬ☠️⚰️か生きる💪😁か」という言葉を時々使用します。。（〇〇には適当な言葉を入れてください。）
"""


def ask_gemini(message):
    response = gemini.models.generate_content(
        model="gemini-3.7-flash",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )
    return response.text


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


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data()

    signature = request.headers.get("x-line-signature", "")

    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()

    expected_signature = base64.b64encode(digest).decode("utf-8")

    if not hmac.compare_digest(signature, expected_signature):
        abort(400)

    data = request.get_json()

    for event in data.get("events", []):
        if event.get("type") != "message":
            continue

        if event["message"].get("type") != "text":
            continue

        user_message = event["message"]["text"]
        reply_token = event["replyToken"]

        try:
            answer = ask_gemini(user_message)
            reply_to_line(reply_token, answer)

        except Exception as e:
            print("ERROR:", repr(e))

            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e) or "UNAVAILABLE" in str(e):
                sounds = [
                    "オォン…",
                    "トップリーダアァン…",
                    "ホーム……リィ…ダァ…",
                    "オオコウスイ!",
                    "キュゥ……キュゥ……",
                    "フォオ……ステップゥ……",
                    "キョウガクッ!",
                    "…………………",
                    "……",
                    "ォォミャーン",
                    "うおw",
                    "きちぃ〜w",
                    "𒅒",
                    "（傷だらけで膝をつきながら）ハァ…ハァ……ならば私は…トップリーダーだ。（指パチンッッッ!!!）",
                    "ゥラヮ!",
                    "ジスゥエィイノォ……イッッチィイ!!",
                ]

                message = random.choice(sounds)

            else:
                message = (
                    "わけがわからないよ"
                )

            reply_to_line(reply_token, message)

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
