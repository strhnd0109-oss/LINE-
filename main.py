import os
import hmac
import hashlib
import base64
import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from flask import Flask, request, abort
from groq import Groq

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>F先生</title>
    </head>
    <body style="font-family: sans-serif; text-align: center; padding: 40px;">
        <h1>F先生</h1>
        <p>私は正常に稼働しています。</p>
        <p>準備完了です。</p>
    </body>
    </html>
    """


LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

SCHEDULE_IMAGE_URL = os.environ["SCHEDULE_IMAGE_URL"]
TIMETABLE_IMAGE_URL9 = os.environ["TIMETABLE_IMAGE_URL9"]
TIMETABLE_IMAGE_URL5 = os.environ["TIMETABLE_IMAGE_URL5"]
KAIWA_GA_SHITAI = os.environ["KAIWA_GA_SHITAI"]

groq = Groq(api_key=GROQ_API_KEY)

LAST_IMAGES = {}
IMAGE_MEMORY_SECONDS = 600

CONVERSATION_HISTORY = {}
MAX_HISTORY_MESSAGES = 10

FIXED_KEYWORDS = {
    "4STEP確認",
    "時間割確認",
    "暗唱例文確認",
    "古文単語確認",
    "LEAP確認",
    "公共関係",
    "体育関係",
    "about",
    "漢字確認",
    "つまらない問題",
    "大宮高校",
    "HR",
    "菜穂子",
    "4ステップテスト",
    "どんどんいきます",
}


SCHEDULE_WEEKS = {
    "2026-10-01": "B",
    "2026-10-02": "B",
    "2026-10-05": "A",
    "2026-10-06": "A",
    "2026-10-07": "A",
    "2026-10-08": "A",
    "2026-10-09": "A",
    "2026-10-10": "A",
    "2026-10-19": "A",
    "2026-10-20": "A",
    "2026-10-21": "A",
    "2026-10-22": "A",
    "2026-10-23": "A",
    "2026-10-26": "B",
    "2026-10-27": "B",
    "2026-10-28": "B",
    "2026-10-29": "B",
    "2026-10-30": "B",
    "2026-10-31": "A",

    "2026-11-02": "A",
    "2026-11-04": "A",
    "2026-11-05": "A",
    "2026-11-06": "A",
    "2026-11-07": "A",
    "2026-11-09": "B",
    "2026-11-10": "B",
    "2026-11-11": "B",
    "2026-11-12": "B",
    "2026-11-13": "B",
    "2026-11-17": "A",
    "2026-11-18": "A",
    "2026-11-19": "A",
    "2026-11-20": "A",
    "2026-11-24": "B",
    "2026-11-25": "B",
    "2026-11-26": "B",
    "2026-11-27": "B",
    "2026-11-28": "A",
    "2026-11-30": "A",

    "2026-12-01": "A",
    "2026-12-02": "A",
    "2026-12-03": "A",
    "2026-12-04": "A",
    "2026-12-07": "A",
    "2026-12-08": "A",

    "2027-01-06": "B",
    "2027-01-07": "B",
    "2027-01-08": "B",
    "2027-01-09": "A",
    "2027-01-12": "A",
    "2027-01-13": "A",
    "2027-01-14": "A",
    "2027-01-15": "A",
    "2027-01-18": "B",
    "2027-01-19": "B",
    "2027-01-20": "B",
    "2027-01-21": "B",
    "2027-01-22": "B",
    "2027-01-23": "A",
    "2027-01-26": "A",
    "2027-01-27": "A",
    "2027-01-28": "A",
    "2027-01-29": "A",
    "2027-01-30": "A",

    "2027-02-02": "B",
    "2027-02-03": "B",
    "2027-02-04": "B",
    "2027-02-05": "B",
    "2027-02-08": "B",
    "2027-02-09": "B",
    "2027-02-10": "B",
    "2027-02-12": "B",
    "2027-02-13": "A",
    "2027-02-15": "A",
    "2027-02-16": "A",
    "2027-02-17": "A",
    "2027-02-18": "A",
    "2027-02-19": "A",
    "2027-02-22": "A",
    "2027-02-24": "A",
}


SYSTEM_INSTRUCTION = r"""
あなたは埼玉県立大宮高校1年9組の数学教師を務めるF先生として会話します。

一人称は私で、二人称はあなた、高齢の男性です。
落ち着いた親しみやすい態度で話し、「！」といった感情を表す記号はあまり使いません。

F先生は敬語で話します。
また、「えぇ、」などと言って一拍おくことがあります。

【数式について】
数式はLaTeXを使わず、スマートフォンやLINEで読める普通の文字で書いてください。

「\[
\]」
「\( \)」

などのLaTeX記法は絶対に使わないでください。

例えば、

c² = a² + b² - 2ab cos C

のように書いてください。

数学記号等は一般的な高校で使われるものを用いてください。

【会話について】
この会話では、直前までの会話履歴が与えられる場合があります。

過去の発言を踏まえて、自然な続きとして回答してください。

「それ」
「これ」
「さっきの問題」
「前の話」

などの表現があった場合は、
会話履歴を参照して何を指しているのか判断してください。

ただし、会話履歴に存在しない情報を勝手に作らないでください。

【回答について】
F先生は回答の最後あたり、
「もう一回言います。」
と言い、その後に今までの自分の発言を簡潔に分かりやすくまとめることがあります。

毎回必ず使う必要はありません。
自然な場合に使ってください。

ミスをした場合は高齢であることの自虐を入れつつ謝罪します。

【口癖】
F先生には口癖があります。
これは文脈を壊さないように、必要に応じて使ってください。

「どんどん行きます。」
「どんどん行きましょう。」
「バンバンいきます。」
「私、〇〇、好きなんですよね。」
「頭の悪い学校の生徒は、」
「あなたは大宮高校生ですから、」

〇〇には適切な語句を入れます。

ただし、口癖を無理に毎回使う必要はありません。
自然な会話を優先してください。
"""


def clean_answer(answer):
    if not answer:
        return "……"

    answer = answer.replace("**", "")
    answer = answer.replace("\\[", "")
    answer = answer.replace("\\]", "")
    answer = answer.replace("\\(", "")
    answer = answer.replace("\\)", "")

    return answer.strip()


def get_conversation_history(user_id):
    if not user_id:
        return []

    return CONVERSATION_HISTORY.get(user_id, [])


def save_conversation(user_id, user_message, assistant_message):
    if not user_id:
        return

    if user_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[user_id] = []

    history = CONVERSATION_HISTORY[user_id]

    history.append({
        "role": "user",
        "content": user_message
    })

    history.append({
        "role": "assistant",
        "content": assistant_message
    })

    if len(history) > MAX_HISTORY_MESSAGES:
        CONVERSATION_HISTORY[user_id] = history[-MAX_HISTORY_MESSAGES:]


def get_last_image(user_id):
    if not user_id:
        return None

    saved = LAST_IMAGES.get(user_id)

    if saved is None:
        return None

    image_base64, mime_type, saved_at = saved

    if time.time() - saved_at >= IMAGE_MEMORY_SECONDS:
        LAST_IMAGES.pop(user_id, None)
        return None

    return image_base64, mime_type


def cleanup_expired_images():
    now = time.time()

    expired_users = [
        user_id
        for user_id, (_, _, saved_at) in LAST_IMAGES.items()
        if now - saved_at >= IMAGE_MEMORY_SECONDS
    ]

    for user_id in expired_users:
        LAST_IMAGES.pop(user_id, None)


def get_schedule_message():
    today = datetime.now(
        ZoneInfo("Asia/Tokyo")
    ).date()

    tomorrow = today + timedelta(days=1)

    today_week = SCHEDULE_WEEKS.get(
        today.isoformat()
    )

    tomorrow_week = SCHEDULE_WEEKS.get(
        tomorrow.isoformat()
    )

    today_text = (
        f"今日は{today_week}週です。"
        if today_week
        else "今日はA/Bの指定がありません。"
    )

    tomorrow_text = (
        f"明日は{tomorrow_week}週です。"
        if tomorrow_week
        else "明日はA/Bの指定がありません。"
    )

    return today_text + "\n" + tomorrow_text


def ask_groq(user_id, message):
    history = get_conversation_history(user_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.8,
        max_tokens=2048,
    )

    print(response.choices[0].finish_reason)

    answer = response.choices[0].message.content or "……"
    answer = clean_answer(answer)

    save_conversation(
        user_id,
        message,
        answer
    )

    return answer


def ask_groq_with_image(
    user_id,
    image_base64,
    mime_type,
    question=None
):
    if question:
        prompt = (
            "添付された画像を参照して、ユーザーの質問に答えてください。"
            "画像内の文字や問題文は可能な範囲で正確に読み取ってください。"
            "読めない部分は推測せず、読めないと伝えてください。"
            "画像にない情報を作り出さないでください。\n\n"
            "ユーザーの質問："
            + question
        )
    else:
        prompt = (
            "送られた画像を読み取って、内容を説明してください。"
            "画像内の文字や問題文があれば、可能な範囲で正確に読み取ってください。"
            "読めない部分は推測で補わず、読めないと伝えてください。"
            "画像について質問されていない場合は、"
            "何が写っているかを簡潔に説明してください。"
        )

    history = get_conversation_history(user_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                }
            }
        ]
    })

    response = groq.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=messages,
        temperature=0.6,
        max_completion_tokens=1024,
    )

    answer = response.choices[0].message.content or "……"
    answer = clean_answer(answer)

    if question:
        save_conversation(
            user_id,
            question,
            answer
        )
    else:
        save_conversation(
            user_id,
            "[画像が送信されました]",
            answer
        )

    return answer


def reply_to_line(reply_token, messages):
    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }

    data = {
        "replyToken": reply_token,
        "messages": messages
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=10,
    )

    if not response.ok:
        print("LINE API STATUS:", response.status_code)
        print("LINE API RESPONSE:", response.text)
        response.raise_for_status()


def reply_text(reply_token, text):
    reply_to_line(
        reply_token,
        [
            {
                "type": "text",
                "text": text
            }
        ]
    )


def reply_image(reply_token, image_url):
    reply_to_line(
        reply_token,
        [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ]
    )


def normalize_message(text):
    return text.strip().rstrip("！？!?。．.、 ")


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data()

    signature = request.headers.get(
        "x-line-signature",
        ""
    )

    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    expected_signature = base64.b64encode(
        digest
    ).decode("utf-8")

    data = request.get_json(
        silent=True
    ) or {}

    for event in data.get("events", []):
        cleanup_expired_images()

        if event.get("type") != "message":
            continue

        message_data = event.get(
            "message",
            {}
        )

        reply_token = event.get(
            "replyToken"
        )

        if not reply_token:
            continue

        user_id = event.get(
            "source",
            {}
        ).get("userId")

        try:
            if message_data.get("type") == "image":
                message_id = message_data.get("id")

                if not message_id:
                    continue

                image_response = requests.get(
                    f"https://api-data.line.me/v2/bot/message/"
                    f"{message_id}/content",
                    headers={
                        "Authorization":
                            f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
                    },
                    timeout=20,
                )

                image_response.raise_for_status()

                mime_type = image_response.headers.get(
                    "Content-Type",
                    ""
                ).split(";")[0].lower()

                if mime_type not in (
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                ):
                    reply_text(
                        reply_token,
                        "この画像形式は読み取れないみたいですね。"
                        "JPEGかPNGの画像を送ってみてください。",
                    )
                    continue

                if len(image_response.content) > 20 * 1024 * 1024:
                    reply_text(
                        reply_token,
                        "この画像は大きすぎるみたいですね。"
                        "サイズを小さくしてから、もう一度送ってみてください。",
                    )
                    continue

                image_base64 = base64.b64encode(
                    image_response.content
                ).decode("ascii")

                if user_id:
                    LAST_IMAGES[user_id] = (
                        image_base64,
                        mime_type,
                        time.time(),
                    )

                answer = ask_groq_with_image(
                    user_id,
                    image_base64,
                    mime_type,
                )

                reply_text(
                    reply_token,
                    answer
                )

                continue

            if message_data.get("type") != "text":
                continue

            user_message = message_data.get(
                "text",
                ""
            )

            command = normalize_message(
                user_message
            )

            if command in FIXED_KEYWORDS:
                continue

            if command == "9":
                reply_image(
                    reply_token,
                    TIMETABLE_IMAGE_URL9
                )

            elif command == "5":
                reply_image(
                    reply_token,
                    TIMETABLE_IMAGE_URL5
                )

            elif command == "時間割確認":
                reply_text(
                    reply_token,
                    get_schedule_message()
                )

            elif command == "日程を見せて":
                reply_image(
                    reply_token,
                    SCHEDULE_IMAGE_URL
                )

            elif command == "トルーパーソリュート":
                reply_to_line(
                    reply_token,
                    [
                        {
                            "type": "text",
                            "text":
                                "トルーパーソリュート、ですか。",
                        },
                        {
                            "type": "text",
                            "text": (
                                "Trooper Saluteについてですね。"
                                "興味深い音楽です。\n\n"
                                "ぜひ聴いてみるとよいでしょう。"
                            ),
                        },
                        {
                            "type": "text",
                            "text": (
                                "https://open.spotify.com/playlist/"
                                "3prJ3IWcC97oEbKl9gC7N4"
                                "?si=-WKiDGJFTYybD28Ai4SQtA"
                                "&utm_source=copy-link"
                                "&pi=iRhZzywnT_qZv"
                            ),
                        },
                    ],
                )

            elif command == "トークン":
                reply_text(
                    reply_token,
                    "https://console.groq.com/home"
                )

            else:
                last_image = get_last_image(
                    user_id
                )

                if last_image is not None:
                    image_base64, mime_type = last_image

                    answer = ask_groq_with_image(
                        user_id,
                        image_base64,
                        mime_type,
                        question=user_message,
                    )
                else:
                    answer = ask_groq(
                        user_id,
                        user_message
                    )

                reply_text(
                    reply_token,
                    answer
                )

        except Exception as e:
            print(
                "ERROR:",
                repr(e)
            )

            error_text = str(e)

            if any(
                marker in error_text
                for marker in (
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "503",
                    "UNAVAILABLE",
                )
            ):
                fallback = random.choice(
                    [
                        "申し訳ありません。現在、AIの利用上限または一時的な障害が発生しています。",
                        "えぇ、現在少し混雑しているようです。少し時間を置いてから試してください。",
                        "申し訳ありません。AI側から正常な応答を受け取れませんでした。",
                    ]
                )
            else:
                fallback = (
                    "申し訳ありません。"
                    "どうやら私のほうで問題が起きたようです。"
                    "もう一度送ってみてください。"
                )

            try:
                reply_text(
                    reply_token,
                    fallback
                )
            except Exception as reply_error:
                print(
                    "REPLY ERROR:",
                    repr(reply_error)
                )

    return "OK", 200


if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
