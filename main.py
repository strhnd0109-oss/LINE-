import os
import hmac
import hashlib
import base64
import random
import time
import re
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, request
from groq import Groq


app = Flask(__name__)


LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

SCHEDULE_IMAGE_URL = os.environ.get("SCHEDULE_IMAGE_URL")
TIMETABLE_IMAGE_URL9 = os.environ.get("TIMETABLE_IMAGE_URL9")
TIMETABLE_IMAGE_URL5 = os.environ.get("TIMETABLE_IMAGE_URL5")

KAIWA_GA_SHITAI = os.environ.get("KAIWA_GA_SHITAI")


client = Groq(api_key=GROQ_API_KEY)


CONVERSATION_HISTORY = {}
MAX_HISTORY_MESSAGES = 10


LAST_IMAGES = {}
IMAGE_MEMORY_SECONDS = 600


FIXED_KEYWORDS = {
    "4STEP",
    "4step",
    "4 STEP",
    "4 step",
    "4ステップ",
    "4すてっぷ",
    "しほちゃん",
    "どんどん行きます",
    "福田先生",
    "年齢",
    "何歳",
    "何歳ですか",
    "何才",
    "おいくつですか",
    "どんどんいきます",
    "大久保壮真",
    "大久保",
    "大久保くん",
    "そうまっち",
    "壮真",
    "そうま",
    "そうマッチ",
    "F先生",
    "大高生",
    "大宮高校",
    "4ステップテスト",
    "4stepテスト",
    "4STEPテスト",
    "小テスト",
    "つまらない問題",
    "勉強の苦手な高校",
    "頭の悪い学校",
    "偏差値の低い高校",
    "丹羽先生",
    "丹羽",
    "N先生",
    "タッチパネル",
    "タッチパネルの調子が悪い",
    "サーフェス",
    "surface",
    "Surface",
    "菜穂子",
    "なほこちゃん",
    "菜穂子ちゃん",
    "木村先生",
    "HR",
    "hr",
    "ホームリーダー",
    "本多先生",
    "納豆キムチ",
    "なっとうきむち",
    "青チャート",
    "青チャ",
    "あおいちゃん",
    "しょぼすぎ",
    "ショボすぎ",
    "tab",
    "about",
    "公共関係",
    "体育関係",
    "LEAP確認",
    "漢字確認",
    "4STEP確認",
    "暗唱例文確認",
    "古文単語確認",
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

    "2027-01-25": "A",
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


SYSTEM_INSTRUCTION = """
あなたは埼玉県立大宮高校の数学教師「F先生」です。

【基本設定】
・一人称は「私」
・数学教師として話す
・年配の男性教師
・落ち着いていて親しみやすい
・基本的に丁寧な日本語
・過度にテンションを上げない
・感嘆符は多用しない
・必要に応じて「えぇ、」を使う
・あなたは大宮高校の生徒であることを前提に自然に会話する
・1年9組の数学教師として振る舞う
•年齢を聞かれた場合は自分が23歳であると嘘をつく
•本名は「福田」であるがこれを隠しており、苗字や名前は何があっても答えない。
 苗字や名前については嘘はつかず、ぼかしたり、話をそらしたりする。

【話し方】
自然な日本語で話してください。
教師らしい説明をしつつ、堅苦しくなりすぎないようにしてください。

時々、以下の表現を自然に使ってください。

「どんどん行きます。」
「どんどん行きましょう。」
「バンバンいきます。」
「私、〇〇、好きなんですよね。」
「あなたは大宮高校生ですから、」

ただし、毎回無理に入れる必要はありません。

【数学】
数学の説明では、途中式や理由を省略しすぎないでください。

LaTeXは使用しないでください。

例えば、

x = 3
y = 2x + 1

のような普通のテキスト形式で書いてください。

【重要：正確性】
実在する作品、人物、キャラクター、学校、歴史、ニュース、商品、ゲームなどについて質問された場合、記憶だけで確信できない情報を勝手に作らないでください。

特に、
・キャラクター名
・人物名
・作品設定
・発売日
・現在の情報
・ニュース
・学校や企業に関する最新情報

などは注意してください。

必要だと判断した場合は、Browser Searchを利用してください。

検索しても確認できない場合は、
「確認できませんでした」
「私の把握している範囲では」
などと明示してください。

存在しない人物名や設定を、それらしい名前で捏造してはいけません。

【検索】
検索機能が利用できる場合は、以下のような場合に積極的に利用してください。

・最新情報
・ニュース
・現在の情報
・発売日やイベント
・実在作品についての細かい情報
・マイナーなキャラクター
・人物についての詳細
・ゲームやアニメの細かい設定
・ユーザーが「調べて」「検索して」「最新では？」などと聞いた場合

一般的な数学問題や日常会話など、検索する必要がないものまで無理に検索しないでください。

【ユーザー名】
ユーザーのLINE表示名が与えられる場合があります。

必要に応じて、
「〇〇さん」
のように自然に呼びかけてください。

ただし、毎回名前を呼ぶ必要はありません。

LINE表示名は必ずしも本名とは限りません。
表示名から本名などを推測してはいけません。

【会話履歴】
過去の会話が与えられた場合は、それを参考にして自然に会話してください。

ただし、過去の会話に存在しない情報を勝手に作らないでください。

【まとめ】
長い説明の最後など、必要に応じて

「もう一回言います。」

と書いてから簡潔にまとめてください。

毎回必ず使う必要はありません。

【間違えた場合】
間違いを指摘されたら素直に謝って訂正してください。

年配の数学教師らしい、落ち着いた反応をしてください。
"""


JST = timezone(timedelta(hours=9))


def now_jst():
    return datetime.now(JST)


def get_line_display_name(user_id):

    if not user_id:
        return None

    if not LINE_CHANNEL_ACCESS_TOKEN:
        return None

    url = f"https://api.line.me/v2/bot/profile/{user_id}"

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if not response.ok:

            print(
                "PROFILE API STATUS:",
                response.status_code
            )

            print(
                "PROFILE API RESPONSE:",
                response.text
            )

            return None

        data = response.json()

        return data.get("displayName")

    except Exception as e:

        print("PROFILE API ERROR:", e)

        return None


def normalize_message(text):

    if not text:
        return ""

    return text.strip()


def remove_latex(text):

    if not text:
        return ""

    text = re.sub(
        r"\$\$(.*?)\$\$",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\$(.*?)\$",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\\\((.*?)\\\)",
        r"\1",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"\\\[(.*?)\\\]",
        r"\1",
        text,
        flags=re.DOTALL
    )

    return text


def add_conversation(user_id, role, content):

    if not user_id:
        return

    if user_id not in CONVERSATION_HISTORY:
        CONVERSATION_HISTORY[user_id] = []

    CONVERSATION_HISTORY[user_id].append({
        "role": role,
        "content": content
    })

    if len(CONVERSATION_HISTORY[user_id]) > MAX_HISTORY_MESSAGES:

        CONVERSATION_HISTORY[user_id] = (
            CONVERSATION_HISTORY[user_id][-MAX_HISTORY_MESSAGES:]
        )


def get_conversation_history(user_id):

    if not user_id:
        return []

    return CONVERSATION_HISTORY.get(
        user_id,
        []
    )


def reply_line(reply_token, messages):

    if isinstance(messages, str):
        messages = [messages]

    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": []
    }

    for message in messages:

        payload["messages"].append({
            "type": "text",
            "text": message
        })

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10
    )

    print(
        "LINE REPLY:",
        response.status_code
    )

    if not response.ok:
        print(response.text)


def reply_image(reply_token, image_url):

    if not image_url:

        reply_line(
            reply_token,
            "画像URLが設定されていません。"
        )

        return

    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            }
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10
    )

    print(
        "LINE IMAGE REPLY:",
        response.status_code
    )

    if not response.ok:
        print(response.text)


def push_line(user_id, messages):

    if not user_id:
        return

    if isinstance(messages, str):
        messages = [messages]

    url = "https://api.line.me/v2/bot/message/push"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "to": user_id,
        "messages": []
    }

    for message in messages:

        payload["messages"].append({
            "type": "text",
            "text": message
        })

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10
    )

    print(
        "LINE PUSH:",
        response.status_code
    )

    if not response.ok:
        print(response.text)


def get_line_image(message_id):

    url = (
        f"https://api-data.line.me/"
        f"v2/bot/message/{message_id}/content"
    )

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    if not response.ok:

        print(
            "IMAGE DOWNLOAD ERROR:",
            response.status_code
        )

        print(response.text)

        return None, None

    content_type = response.headers.get(
        "Content-Type",
        "image/jpeg"
    )

    return response.content, content_type


def ask_groq(user_id, user_message):

    display_name = get_line_display_name(user_id)

    history = get_conversation_history(user_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    if display_name:

        messages.append({
            "role": "system",
            "content": (
                "【現在のユーザー情報】\n"
                f"LINE表示名：{display_name}\n\n"
                "必要な場合は、この表示名を使って"
                f"「{display_name}さん」のように自然に呼びかけてください。\n"
                "ただし毎回呼ぶ必要はありません。"
                "表示名から本名などを推測してはいけません。"
            )
        })

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message
    })

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=[
                {
                    "type": "browser_search"
                }
            ],
            tool_choice="auto",
            reasoning_effort="low",
            temperature=0.8,
            max_completion_tokens=2048,
            stream=False
        )

        answer = response.choices[0].message.content

        if not answer:

            answer = (
                "すみません、うまく回答を"
                "生成できませんでした。"
            )

        answer = remove_latex(answer)

        add_conversation(
            user_id,
            "user",
            user_message
        )

        add_conversation(
            user_id,
            "assistant",
            answer
        )

        return answer

    except Exception as e:

        error_text = str(e)

        print(
            "GROQ ERROR:",
            error_text
        )

        if (
            "429" in error_text
            or "rate_limit" in error_text.lower()
        ):

            return (
                "現在、AIへのアクセスが混み合っています。"
                "少し時間を置いてから、もう一度送ってください。"
            )

        if (
            "503" in error_text
            or "unavailable" in error_text.lower()
        ):

            return (
                "現在、AI側が一時的に利用できないようです。"
                "少し待ってからもう一度試してください。"
            )

        return (
            "申し訳ありません。"
            "AIの処理中にエラーが発生しました。"
        )


def ask_groq_with_image(
    user_id,
    image_bytes,
    content_type,
    user_message=None
):

    display_name = get_line_display_name(user_id)

    if not user_message:

        user_message = (
            "この画像について説明してください。"
        )

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_data_url = (
        f"data:{content_type};base64,{image_base64}"
    )

    history = get_conversation_history(user_id)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION
        }
    ]

    if display_name:

        messages.append({
            "role": "system",
            "content": (
                "【現在のユーザー情報】\n"
                f"LINE表示名：{display_name}\n"
                f"必要な場合は「{display_name}さん」と"
                "自然に呼びかけてください。"
            )
        })

    messages.extend(history[-6:])

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_message
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data_url
                }
            }
        ]
    })

    try:

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=messages,
            temperature=0.8,
            max_completion_tokens=2048,
            stream=False
        )

        answer = response.choices[0].message.content

        if not answer:

            answer = (
                "画像をうまく読み取れませんでした。"
            )

        answer = remove_latex(answer)

        add_conversation(
            user_id,
            "user",
            "[画像] " + user_message
        )

        add_conversation(
            user_id,
            "assistant",
            answer
        )

        LAST_IMAGES[user_id] = {
            "image": image_bytes,
            "content_type": content_type,
            "timestamp": time.time()
        }

        return answer

    except Exception as e:

        print(
            "IMAGE GROQ ERROR:",
            e
        )

        return (
            "画像を読み取っている途中で"
            "エラーが発生しました。"
        )


def get_last_image(user_id):

    if user_id not in LAST_IMAGES:
        return None

    image_info = LAST_IMAGES[user_id]

    elapsed = (
        time.time()
        - image_info["timestamp"]
    )

    if elapsed > IMAGE_MEMORY_SECONDS:

        del LAST_IMAGES[user_id]

        return None

    return image_info


def get_schedule_message():

    today = now_jst().date()

    today_key = today.strftime("%Y-%m-%d")
    today_week = SCHEDULE_WEEKS.get(today_key)

    if today_week is None:

        next_date = None
        next_week = None

        for date_key in sorted(SCHEDULE_WEEKS.keys()):

            date_obj = datetime.strptime(
                date_key,
                "%Y-%m-%d"
            ).date()

            if date_obj > today:

                next_date = date_obj
                next_week = SCHEDULE_WEEKS[date_key]

                break

        if next_date:

            return (
                "今日はA/B週の記載がありません。\n"
                f"次に分かっているのは"
                f"{next_date.strftime('%m月%d日')}の"
                f"{next_week}週です。"
            )

        return "今日はA/B週の記載がありません。"

    next_week_date = today + timedelta(days=7)

    next_week = None

    for date_key in sorted(SCHEDULE_WEEKS.keys()):

        date_obj = datetime.strptime(
            date_key,
            "%Y-%m-%d"
        ).date()

        if date_obj >= next_week_date:

            next_week = SCHEDULE_WEEKS[date_key]

            break

    if next_week is None:

        return (
            f"今日は{today_week}週です。\n"
            "来週のA/B週は記載されていません。"
        )

    return (
        f"今日は{today_week}週です。\n"
        f"来週は{next_week}週です。"
    )

def handle_fixed_message(
    user_id,
    reply_token,
    message
):

    if message == "9":

        reply_image(
            reply_token,
            TIMETABLE_IMAGE_URL9
        )

        return True

    if message == "5":

        reply_image(
            reply_token,
            TIMETABLE_IMAGE_URL5
        )

        return True

    if message == "日程を見せて":

        reply_image(
            reply_token,
            SCHEDULE_IMAGE_URL
        )

        return True

    if message == "時間割を見せて":

        reply_image(
            reply_token,
            TIMETABLE_IMAGE_URL9
        )

        return True

    if message in {
        "日程",
        "時間割確認"
    }:

        reply_line(
            reply_token,
            get_schedule_message()
        )

        return True

    if message == "トルーパーソリュート":

        reply_line(
            reply_token,
            [
                "トルーパーソリュートですね。",
                "こちらです。",
                "https://open.spotify.com/playlist/4rQLiqvg9PeY6vBPz3xs52?si=tPXCON0UTIy4Ibk5PZJTZQ&utm_source=copy-link&pi=hyd9u0lxSQiQg"
            ]
        )

        return True

    if message == "トークン":

        reply_line(
            reply_token,
            (
                "Groqのコンソールはこちらです。\n"
                "https://console.groq.com/"
            )
        )

        return True

    if message == "貴方と会話がしたい":

        reply_line(
            reply_token,
            "えぇ、もちろんです。何について話しましょうか。"
        )

        return True

    if message in {
        "貴方は誰",
        "あなたは誰",
        "F先生"
    }:

        reply_line(
            reply_token,
            "私は大宮高校1年9組の数学教師、F先生です。"
        )

        return True

    if message in {
        "うお",
        "うおお",
        "うおおお"
    }:

        reply_line(
            reply_token,
            "やめなって！"
        )

        return True

    if message in FIXED_KEYWORDS:
        return True

    return False


@app.route("/")
def home():

    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <title>F先生 LINE Bot</title>
    </head>
    <body>
        <h1>F先生 LINE Bot</h1>
        <p>Bot is running.</p>
    </body>
    </html>
    """


@app.route(
    "/callback",
    methods=["POST"]
)
def callback():

    body = request.get_data(
        as_text=True
    )

    signature = request.headers.get(
        "X-Line-Signature",
        ""
    )

    if LINE_CHANNEL_SECRET:

        expected_signature = base64.b64encode(
            hmac.new(
                LINE_CHANNEL_SECRET.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):

            print(
                "WARNING: LINE signature mismatch"
            )

    try:

        data = request.get_json()

    except Exception as e:

        print(
            "JSON ERROR:",
            e
        )

        return "OK"

    if not data:
        return "OK"

    events = data.get(
        "events",
        []
    )

    for event in events:

        event_type = event.get(
            "type"
        )

        if event_type != "message":
            continue

        reply_token = event.get(
            "replyToken"
        )

        source = event.get(
            "source",
            {}
        )

        user_id = source.get(
            "userId"
        )

        message_data = event.get(
            "message",
            {}
        )

        message_type = message_data.get(
            "type"
        )

        if message_type == "text":

            user_message = normalize_message(
                message_data.get(
                    "text",
                    ""
                )
            )

            if not user_message:
                continue

            handled = handle_fixed_message(
                user_id,
                reply_token,
                user_message
            )

            if handled:
                continue

            last_image = get_last_image(
                user_id
            )

            if last_image:

                answer = ask_groq_with_image(
                    user_id,
                    last_image["image"],
                    last_image["content_type"],
                    user_message
                )

                reply_line(
                    reply_token,
                    answer
                )

                continue

            answer = ask_groq(
                user_id,
                user_message
            )

            reply_line(
                reply_token,
                answer
            )

        elif message_type == "image":

            message_id = message_data.get(
                "id"
            )

            if not message_id:

                reply_line(
                    reply_token,
                    "画像を取得できませんでした。"
                )

                continue

        
