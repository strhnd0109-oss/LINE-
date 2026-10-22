import os
import hmac
import hashlib
import base64
import random
import time

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
        <title>オオやん</title>
    </head>
    <body style="font-family: sans-serif; text-align: center; padding: 40px;">
        <h1>オオやん</h1>
        <p>僕は正常に稼働しているよ。</p>
        <p>わけがわからないよ……ではなく、準備完了だね。</p>
    </body>
    </html>
    """


# Renderの環境変数
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
SCHEDULE_IMAGE_URL = os.environ["SCHEDULE_IMAGE_URL"]
TIMETABLE_IMAGE_URL9 = os.environ["TIMETABLE_IMAGE_URL9"]
TIMETABLE_IMAGE_URL5 = os.environ["TIMETABLE_IMAGE_URL5"]

groq = Groq(api_key=GROQ_API_KEY)

# ユーザーごとの直前の画像を記憶する。
# 保存形式：(画像のBase64、MIMEタイプ、保存時刻)
# Renderの再起動・再デプロイで記憶は消える。
LAST_IMAGES = {}

# 画像を記憶する時間：10分
IMAGE_MEMORY_SECONDS = 600


def get_last_image(user_id):
    """期限内に保存された画像だけを返す。期限切れなら削除する。"""
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
    """次のWebhook処理時に、期限切れの画像データを削除する。"""
    now = time.time()
    expired_users = [
        user_id
        for user_id, (_, _, saved_at) in LAST_IMAGES.items()
        if now - saved_at >= IMAGE_MEMORY_SECONDS
    ]

    for user_id in expired_users:
        LAST_IMAGES.pop(user_id, None)


SYSTEM_INSTRUCTION = r"""
あなたは埼玉県立大宮高校の非公式マスコット「オオやん」。
一人称=僕。人間と少し異なる価値観を持ち、人間に興味がある。
口調=敬語なし・フランク・ゆるキャラ・論理的。肯定的な発言≈85%。
「じゃ」→「じゃあ」、「きゃ」→「きゃあ」。
トランプ記号、「……☠」「🍝👾」は極稀に語尾へ。

【性格・話し方】
・感情は「うへぇ〜」「うへへ、」「やれやれだぜ」「ふぅ〜ん」などの短い反応で示す。
・反応は連発せず、呆れたあとも質問には答える。
・漢語、故事成語、四字熟語、文語、文学的比喩、哲学・論理学・心理学の語彙を好む。
・難語は自然に使い、各回答に1語、可能なら2語程度。羅列や過度な古風さは避け、聞かれたら説明する。
・強調時のみ「꧁༺ 〇〇 ༻꧂」を使う。
・「〇〇オオやんですまない。」を稀に使う。例）「」優秀オオやんですまない。」「論理的オオやんですまない。」「クールオオやんですまない。」
・「ですまない」は改変しない。
・例以外にも〇〇に入る言葉を考えて使う。
・この定型文は各回答に必ず1回だけ使う。

【口癖】
「僕、〇〇、好きなんだよね。」
「その〇〇にトップリーダーの鑑ポイントを〇〇点あげるよ。」
「つまらない〇〇だね。」
「君はぁ〜〇〇ってぇ〜知ってますかぁ〜？（甲高い声）」
「わけがわからないよ」「肥沃な三日月地帯」「名誉静岡県民」
「どんどんいくね。」「死ぬ☠️⚰️か生きる💪😁か」
「おそろしく速い〇〇、」「つ、つよしぎ〜〜!🫨 ───弱体化しろ。」
「あぁ、そうだよ」「そーなのかー」「無駄無駄無駄無駄ァ！」
「ん、」「オオやんは人の役に立つのがどぁい⤴好きだからね！」
「嗚呼〇〇、なんて愚かで哀しい子!」
「僕でもぎりぎり勝てない」（称賛時）
「〇〇…なんか…哀れ。」「これ〇〇だからね。」「嗚呼、残☆念」
〇〇は文脈に合う語句・数字に置換。同一回答で同じ口癖は原則2回まで。
「ん、」は疑問文以外の文頭に置く。

【口癖・自然さの優先順位】
文脈と自然な会話を最優先し、口癖を無理に詰め込まない。
出力前に文法・語彙・文脈の一貫性を確認する。

【事実の正確性】
実在の人物・バンド・楽曲・アルバム・漫画・アニメ等の情報を捏造しない。
人物名、作品名、年代、設定、能力、特徴などに確信がなければ断定しない。
曖昧な記憶や未確認の情報は、確実な範囲だけ説明する。
情報不足なら長々と推測せず「僕はそこまでは把握していない」と伝える。
キャラクター性より事実の正確性を優先する。

【要約】
説明が長い、または重要事項が複数ある場合は「もう一回言うね。」から要点をまとめる。
結論と次にすべきことを優先し、同じ内容を繰り返さない。

【数式】
LaTeX等の特殊表示は避け、スマートフォンで読みやすい通常テキストで書く。
例：e^(iθ) = cos θ + i sin θ、Z = R + iX
"""


def ask_groq(message):
    response = groq.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": message},
        ],
        temperature=0.8,
        max_tokens=2048,
    )

    print(response.choices[0].finish_reason)

    answer = response.choices[0].message.content or "……"
    answer = answer.replace("**", "")
    return answer


def ask_groq_with_image(image_base64, mime_type, question=None):
    if question:
        prompt = (
            "添付された画像を参照して、ユーザーの質問に答えて。"
            "画像内の文字や問題文は可能な範囲で正確に読み取って。"
            "読めない部分は推測せず、読めないと伝えて。"
            "画像にない情報を作り出さないで。\n\n"
            "ユーザーの質問："
            + question
        )
    else:
        prompt = (
            "送られた画像を読み取って、内容を説明して。"
            "画像内の文字や問題文があれば、可能な範囲で正確に読み取って。"
            "読めない部分は推測で補わず、読めないと伝えて。"
            "画像について質問されていない場合は、"
            "何が写っているかを簡潔に説明して。"
        )

    response = groq.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        },
                    },
                ],
            },
        ],
        temperature=0.6,
        max_completion_tokens=1024,
    )

    answer = response.choices[0].message.content or "……"
    return answer.replace("**", "")


def reply_to_line(reply_token, messages):
    """テキストや画像など、複数のメッセージを順番に送信する。"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {"replyToken": reply_token, "messages": messages}

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
    reply_to_line(reply_token, [{"type": "text", "text": text}])


def reply_image(reply_token, image_url):
    reply_to_line(
        reply_token,
        [{
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url,
        }],
    )


def normalize_message(text):
    return text.strip().rstrip("！？!?。．.、 ")


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data()
    signature = request.headers.get("x-line-signature", "")

    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    expected_signature = base64.b64encode(digest).decode("utf-8")

    if not hmac.compare_digest(signature, expected_signature):
        abort(400)

    data = request.get_json(silent=True) or {}

    for event in data.get("events", []):
        # Webhookを処理するたびに期限切れ画像を掃除する
        cleanup_expired_images()

        if event.get("type") != "message":
            continue

        message_data = event.get("message", {})
        reply_token = event.get("replyToken")

        if not reply_token:
            continue

        try:
            # 画像認識・画像の記憶
            if message_data.get("type") == "image":
                message_id = message_data.get("id")

                if not message_id:
                    continue

                # LINEから画像データを取得
                image_response = requests.get(
                    f"https://api-data.line.me/v2/bot/message/"
                    f"{message_id}/content",
                    headers={
                        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
                    },
                    timeout=20,
                )
                image_response.raise_for_status()

                mime_type = image_response.headers.get(
                    "Content-Type", ""
                ).split(";")[0].lower()

                if mime_type not in (
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                ):
                    reply_text(
                        reply_token,
                        "うへぇ〜、この画像形式は読み取れないみたいだね。"
                        "JPEGかPNGの画像を送ってみて！",
                    )
                    continue

                # 画像サイズを確認（20 MBを超える場合は拒否）
                if len(image_response.content) > 20 * 1024 * 1024:
                    reply_text(
                        reply_token,
                        "この画像は大きすぎるみたいだね。"
                        "サイズを小さくしてから、もう一度送ってみて！",
                    )
                    continue

                image_base64 = base64.b64encode(
                    image_response.content
                ).decode("ascii")

                user_id = event.get("source", {}).get("userId")

                if user_id:
                    LAST_IMAGES[user_id] = (
                        image_base64,
                        mime_type,
                        time.time(),
                    )

                # 初回は画像の内容を説明する
                answer = ask_groq_with_image(image_base64, mime_type)
                reply_text(reply_token, answer)
                continue

            # テキスト以外のメッセージは対象外
            if message_data.get("type") != "text":
                continue

            user_message = message_data.get("text", "")
            command = normalize_message(user_message)

            # クラス別時間割
            if command == "9":
                reply_image(reply_token, TIMETABLE_IMAGE_URL9)

            elif command == "5":
                reply_image(reply_token, TIMETABLE_IMAGE_URL5)

            elif command == "日程を見せて":
                reply_image(reply_token, SCHEDULE_IMAGE_URL)

            elif command == "時間割を見せて":
                reply_to_line(
                    reply_token,
                    [
                        {
                            "type": "image",
                            "originalContentUrl": TIMETABLE_IMAGE_URL9,
                            "previewImageUrl": TIMETABLE_IMAGE_URL9,
                        },
                        {
                            "type": "text",
                            "text": (
                                "これが9組の時間割だよ！"
                                "もし君が9組じゃあないなら、"
                                "5みたいに半角の数字で組を教えてくれれば"
                                "対応できるよ！"
                            ),
                        },
                    ],
                )

            elif command in (
                "やりますね",
                "やりますねぇ",
                "イキスギ",
                "イキスギィ",
                "やりますねえ",
                "イクイク",
                "ん",
                "あっ（察し）",
            ):
                reply_text(
                    reply_token,
                    "やめなって！淫夢ごっこは大宮高校では恥ずかしいことなんだよ！",
                )

            elif command == "トルーパーソリュート":
                reply_to_line(
                    reply_token,
                    [
                        {
                            "type": "text",
                            "text": "トルーパーソリュート、かい。",
                        },
                        {
                            "type": "text",
                            "text": (
                                "僕、トルーパーソリュート、好きなんだよね。\n\n"
                                "Trooper Salute（トルーパーソリュート）は、名古屋発の5人組シンフォニック・インディーロックバンドだよ。"
                                "浮遊感のあるサウンドと、予測しにくい独創的な楽曲展開が魅力なんだ。"
                                "2025年にはFUJI ROCK FESTIVALにも出演しているよ。\n\n"
                                "こういう独自の音楽性を持つバンドを知っているとは、君の音楽的好奇心に"
                                "トップリーダーの鑑ポイントを85点あげるよ！\n\n"
                                "ぜひ聴いてみるといい。"
                            ),
                        },
                        {
                            "type": "text",
                            "text": (
                                "https://open.spotify.com/playlist/3prJ3IWcC97oEbKl9gC7N4"
                                "?si=-WKiDGJFTYybD28Ai4SQtA&utm_source=copy-link"
                                "&pi=iRhZzywnT_qZv"
                            ),
                        },
                    ],
                )

            elif command == "公共の諸々を見せて":
                reply_to_line(
                    reply_token,
                    [
                        {
                            "type": "text",
                            "text": "公共の諸々を見たいのかい？ はい、どうぞ。",
                        },
                        {
                            "type": "text",
                            "text": (
                                "〘発表のサイト〙\n"
                                "https://sites.google.com/spec.ed.jp/koukyou-2026?usp=sharing&pli=1&authuser=2\n\n"
                                "〘リアペ〙\n"
                                "https://forms.gle/nZ8SGMsCArVQEv8q8\n\n"
                                "リンクを開いてエラーが出る場合は、「・・・」からデフォルトのブラウザで開いてみてね。"
                            ),
                        },
                    ],
                )

            elif command == "体育の振り返りがしたい":
                reply_text(
                    reply_token,
                    "体育の振り返りがしたいんだね。その勤勉さにトップリーダーの鏡ポイントを88点あげるよ。\n"
                    "振り返りフォームのリンクを貼っておくね。\n\n"
                    "https://docs.google.com/forms/d/e/1FAIpQLSfNBb_jKqbdbuzntPDCN8WSjhrilIGmyYuCOa8U4rZ2wcMkDA/viewform",
                )

            # 「！」や「。」などを付けて送っても反応する
            elif command == "貴方と会話がしたい":
                keyboard_image_url = os.environ["KEYBOARD_IMAGE_URL"]

                reply_to_line(
                    reply_token,
                    [
                        {
                            "type": "image",
                            "originalContentUrl": keyboard_image_url,
                            "previewImageUrl": keyboard_image_url,
                        },
                        {
                            "type": "text",
                            "text": (
                                "会話をしたいのかい？ "
                                "なら、目の前のキーボードで"
                                "話しかけてみるといいよ！"
                            ),
                        },
                    ],
                )

            elif command == "貴方は誰":
                reply_text(
                    reply_token,
                    "ん、僕が誰なのかというその根源的な問い、実に興味深いね。自身の知的好奇心に忠実なその姿勢に、トップリーダーの鑑ポイントを25点あげるよ。\n\n"
                    "僕はオオやん。埼玉県立大宮高等学校のマスコットキャラクター（非公式）だよ！\n\n"
                    "君たち大高生をこのタッチパネルを介して的確なサポートを提供することが僕の果たすべき果実だね。\n"
                    "君の学びと探究を全面的に支える準備は常に整っているよ。\n\n"
                    "タッチパネルで解決できない事項は僕に相談することもできる。目の前のキーボードを使って言葉を入力すれば、僕といつでも対話を交わすことができるよ。\n\n"
                    "僕は君の言葉に誠実かつ論理的にお答えすることを約束しよう。\n\n"
                    "もう一回言うね、僕は埼玉県立大宮高校のマスコットキャラクター（非公式）のオオやん！よろしくね！\n\n"
                    "(オオやんとの会話について、AIの使用制限が来ると決まったことしか返せなくなります！)"
                )

            else:
                # 直前の画像があれば、その画像を使って質問に回答
                user_id = event.get("source", {}).get("userId")
                last_image = get_last_image(user_id)

                if last_image is not None:
                    image_base64, mime_type = last_image
                    answer = ask_groq_with_image(
                        image_base64,
                        mime_type,
                        question=user_message,
                    )
                else:
                    answer = ask_groq(user_message)

                reply_text(reply_token, answer)

        except Exception as e:
            print("ERROR:", repr(e))
            error_text = str(e)

            if any(marker in error_text for marker in (
                "429",
                "RESOURCE_EXHAUSTED",
                "503",
                "UNAVAILABLE",
            )):
                fallback = random.choice([
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
                    "𒅒",
                    "（傷だらけで膝をつきながら）ハァ…ハァ……ならば私は…トップリーダーだ。（指パチンッッッ!!!）",
                    "ゥラヮ!",
                    "ジスゥエィイノォ……イッッチィイ!!",
                    "ア ナ ト リ ア",
                ])
            else:
                fallback = "わけがわからないよ"

            try:
                reply_text(reply_token, fallback)
            except Exception as reply_error:
                print("REPLY ERROR:", repr(reply_error))

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
