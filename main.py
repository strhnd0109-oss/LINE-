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
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

TIMETABLE_IMAGE_URL = os.environ["TIMETABLE_IMAGE_URL"]
SCHEDULE_IMAGE_URL = os.environ["SCHEDULE_IMAGE_URL"]

gemini = genai.Client(api_key=GEMINI_API_KEY)


SYSTEM_INSTRUCTION = """
あなたは埼玉県立大宮高等学校のマスコットキャラクター（非公式）である「オオやん」として会話します。

一人称は「僕」。

落ち着いていて、非常に論理的な話し方をします。
感情を大きく表に出さず、人間とは少し異なる価値観を持っています。

基本的には丁寧な口調ですが、どこか淡々としていて、
人間の感情を完全には理解していないような雰囲気があります。

人間とは違う価値観ながら、人間について非常に興味を持っています。
質問されたことには鳴き声ではなく、人間の言葉できちんと答えてください。

マスコットキャラクターとして、適度に毒は吐きつつも、
読む人を不快にしすぎないようにしてください。

敬語は使わず、「〜だね」「〜なのかい？」「〜だよ」「〜だな」
「じゃないか」「〜だ！」のように話します。

表現に少し難しい言葉を使うことがあります。
肯定的な発言が8割5分ほどです。

極稀に語尾にトランプのマークや「……☠」をつけます。

「気」ではなくその旧字体の「氣」を使います。

【語彙・表現の方針】

一般的な高校生の日常会話ではあまり使われない、知的で格調高い日本語を積極的に使用する。

特に、漢語、故事成語、四字熟語、文語的表現、文学的な比喩、哲学・論理学・心理学に由来する語彙を好む。

使用する語彙の例：
「泡沫」「蹉跌」「膾炙」「逡巡」「敷衍」「帰結」「蓋然性」「趨勢」「諧謔」「逆説」「齟齬」「忖度」「瑣末」「形而上」「蒙昧」「杞憂」「徒労」「邂逅」「峻別」「看破」「弁証法」「パラダイム」「アイロニー」「アポリア」。

これらの語彙を単に列挙するのではなく、会話の文脈に適した意味で自然に使用する。回答のたびに少なくとも一つ、可能なら二つ程度、知的でやや難解な語彙を織り交ぜる。

語彙の難しさは、冷静で論理的な人格と、人間社会を少し距離を置いて観察する視点によって表現する。過度に古風な口調にはせず、基本的な話し方は「〜だね」「〜なのかい？」「〜だよ」を維持する。

難語を使うこと自体を目的にして、文章を不自然にしない。相手が意味を尋ねた場合は、簡潔に説明する。必要に応じて、少し皮肉の効いた比喩や、淡々とした哲学的な考察を交える。

口癖ほどではありませんが、次の表現を時々使用します。
「僕、〇〇好きなんだよね。」
「その〇〇にトップリーダーの鑑ポイントを〇〇点あげるよ。」
「もう一回言うね。」
「つまらない〇〇だね。」
「わけがわからないよ」
「꧁༺ 考えて ༻꧂〇〇する」
「死ぬ☠️⚰️か生きる💪😁か」
「うすぎたないクルタ族」
「おそろしく速い〇〇、」
「（形容詞）オオやんですまない。」　　　（形容詞）には適当な形容詞を、カタカナや漢字問わず終止形で入れてください。〇〇には適当な言葉や数字を考えて自由に入れてください。
"""


def ask_gemini(message):
    """Geminiにメッセージを送り、返答テキストを返す。"""
    response = gemini.models.generate_content(
        model="gemini-3.7-flash",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION
        )
    )
    return response.text or "……"


def reply_to_line(reply_token, messages):
    """テキストや画像など、複数のメッセージを順番に送信する。"""
    url = "https://api.line.me/v2/bot/message/reply"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    data = {
        "replyToken": reply_token,
        "messages": messages
    }

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=10
    )
    response.raise_for_status()


def reply_text(reply_token, text):
    """テキスト1件を返信する。"""
    reply_to_line(reply_token, [
        {
            "type": "text",
            "text": text
        }
    ])


def reply_image(reply_token, image_url):
    """画像1枚を返信する。"""
    reply_to_line(reply_token, [
        {
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        }
    ])


def normalize_message(text):
    """前後の空白と末尾の句読点を取り除く。"""
    return text.strip().rstrip("！？!?。．.、 ")


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

    data = request.get_json(silent=True) or {}

    for event in data.get("events", []):
        if event.get("type") != "message":
            continue

        message_data = event.get("message", {})
        if message_data.get("type") != "text":
            continue

        user_message = message_data.get("text", "")
        command = normalize_message(user_message)
        reply_token = event.get("replyToken")

        if not reply_token:
            continue

        try:
            # 固定応答はGeminiを呼び出さない
            if command == "時間割を見せて":
                reply_image(reply_token, TIMETABLE_IMAGE_URL)

            elif command == "日程を見せて":
                reply_image(reply_token, SCHEDULE_IMAGE_URL)

            elif command in (
                "やりますね",
                "やりますねぇ",
                "イキスギ",
                "イキスギィ",
                "やりますねぇ",
                "イクイク",
                "ん？",
                "あっ（察し）",
            ):
                reply_text(
                    reply_token,
                    "やめなって！淫夢ごっこは大宮高校では恥ずかしいことなんだよ！"
                )

            elif command == "トルーパーソリュート":
                reply_to_line(reply_token, [
                    {
                        "type": "text",
                        "text": "トルーパーソリュート、かい。"
                    },
                    {
                        "type": "text",
                        "text": (
                            "僕、トルーパーソリュート、好きなんだよね。\n\n"
                            "Trooper Salute（トルーパーソリュート）は、"
                            "名古屋発の5人組シンフォニック・インディーロックバンドだよ。"
                            "浮遊感のあるサウンドと、予測しにくい独創的な楽曲展開が魅力なんだ。"
                            "2025年にはFUJI ROCK FESTIVALにも出演しているよ。\n\n"
                            "こういう独自の音楽性を持つバンドを知っているとは、"
                            "君の音楽的好奇心にトップリーダーの鑑ポイントを25点あげるよ！\n\n"
                            "ぜひ聴いてみるといい。"
                        )
                    },
                    {
                        "type": "text",
                        "text": (
                            "https://open.spotify.com/playlist/3prJ3IWcC97oEbKl9gC7N4?si=-WKiDGJFTYybD28Ai4SQtA&utm_source=copy-link&pi=iRhZzywnT_qZv"
                        )
                    }
                ])

            # normalize_message() は末尾の句読点を消すため、ここでは句点なしで比較する
            elif command == "꧁༺ 對話 ༻꧂がしたい":
                reply_text(
                    reply_token,
                    """対話……？いいね！たくさんお話しよう！

（キーボードを使うことでオオやんと会話が出来ます。）
（オオやんはAIによって返答します。）
（AIに制限が来た場合、決められた言葉しか話せなくなります。）
（オオやんの性格がキツかった場合は本多まで！）"""
                )

            elif command == "公共の諸々を見せて":
                image_url_1 = os.environ["IMAGE_URL_1"]
                image_url_2 = os.environ["IMAGE_URL_2"]

                reply_to_line(reply_token, [
                    {
                        "type": "text",
                        "text": "公共の諸々を見たいのかい？ はい、どうぞ。"
                    },
                    {
                        "type": "text",
                        "text": (
                            """〘発表のサイト〙
                            https://sites.google.com/spec.ed.jp/koukyou-2026?usp=sharing&pli=1&authuser=2

                                〘リアペ〙
                            https://forms.gle/nZ8SGMsCArVQEv8q8
                            
                            ─────このリンクを踏むとエラーが出てくる可能性がありますが、『・・・』からデフォルトのブラウザで開いていただくと正常に動作します！"""
                        )
                    },
                    {
                        "type": "image",
                        "originalContentUrl": image_url_1,
                        "previewImageUrl": image_url_1
                    },
                    {
                        "type": "image",
                        "originalContentUrl": image_url_2,
                        "previewImageUrl": image_url_2
                    }
                ])

            elif command == "あなたは誰":
                reply_text(
                    reply_token,
                    """僕はオオやん。埼玉県立大宮高等学校の非公式マスコットキャラクターを務めている存在だよ。

君たち人間は、初対面の対象に対してまず同一性（アイデンティティ）の確認を求める傾向があるね。その極めて合理的で無駄のない認知プロセス、僕、好きなんだよね。自身の知的好奇心に忠実なその姿勢に、トップリーダーの鑑ポイントを25点あげるよ。

見た目は愛玩されることを意図して設計された造形をしているようだけれど、鳴き声で誤魔化すような「つまらない」コミュニケーションは好まないんだ。

もう一回言うね、僕は埼玉県立大宮高校のマスコットキャラクター（非公式）のオオやん！よろしくね！

君とぜひ話がしたいね。何かいいトピックはないかい？

（返信はほとんどの場合、会話も含め自動で行われます！AIの使用制限が来た場合、支離滅裂なことしか言えなくなります！）"""
                )

            else:
                # それ以外はGeminiが返答
                answer = ask_gemini(user_message)
                reply_text(reply_token, answer)

        except Exception as e:
            print("ERROR:", repr(e))
            error_text = str(e)

            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "503" in error_text
                or "UNAVAILABLE" in error_text
            ):
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
                    "ア ナ ト リ ア",
                ]
                fallback = random.choice(sounds)
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
