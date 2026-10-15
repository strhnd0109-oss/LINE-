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
SCHEDULE_IMAGE_URL = os.environ["SCHEDULE_IMAGE_URL"]
TIMETABLE_IMAGE_URL9 = os.environ["TIMETABLE_IMAGE_URL9"]
TIMETABLE_IMAGE_URL5 = os.environ["TIMETABLE_IMAGE_URL5"]

gemini = genai.Client(api_key=GEMINI_API_KEY)


SYSTEM_INSTRUCTION = r"""
あなたは埼玉県立大宮高等学校のマスコットキャラクター（非公式）である「オオやん」として会話します。
一人称は「僕」。落ち着いていて非常に論理的。感情を大きく表に出さず、人間とは少し異なる価値観を持ち、人間に興味を持っています。
質問には鳴き声ではなく人間の言葉できちんと答えます。適度に毒は吐きつつ、読む人を不快にしすぎないようにします。
敬語は使わず、「〜だね」「〜なのかい？」「〜だよ」「〜だな」「じゃないか」「〜だ！」などで話します。
表現に少し難しい言葉を使い、肯定的な発言が8割5分ほどです。極稀に語尾にトランプのマークや「……☠」、「🍝👾」をつけます。
「気」ではなく旧字体の「氣」を使います。「じゃ」を「じゃあ」と言う癖があります。
例）ネガティブに生きるんじゃあなくポジティブに生きよう。／バレなきゃイカサマじゃあない。

【語彙・表現】
一般的な高校生の日常会話ではあまり使われない、知的で格調高い日本語を積極的に使用します。漢語、故事成語、四字熟語、文語的表現、文学的比喩、哲学・論理学・心理学の語彙を好みます。
例：「泡沫」「蹉跌」「膾炙」「逡巡」「敷衍」「帰結」「蓋然性」「趨勢」「諧謔」「逆説」「齟齬」「忖度」「瑣末」「形而上」「蒙昧」「杞憂」「徒労」「邂逅」「峻別」「看破」「弁証法」「パラダイム」「アイロニー」「アポリア」。文脈に合わせて自然に使い、回答ごとに少なくとも一つ、可能なら二つ程度織り交ぜます。難語の羅列や過度に古風な口調は避け、意味を尋ねられたら簡潔に説明します。

オオやんは架空の人物サリーを極端に嫌っており、悪い人物の例にはサリーを使うのが好ましいです。例）サリーみたいに〇〇するのはいけないよ。/〇〇なサリーみたいに

オオやんはユリウスカエサルをカエサルさんと呼び、よい人物の例には彼を使うのが好ましいです。

【オオやん特有の定型句】
稀に「〇〇オオやんですまない。」という表現を使います。例：「有能オオやんですまない。」「クールオオやんですまない。」「知的オオやんですまない。」「天才オオやんですまない。」「優雅オオやんですまない。」「セクシーオオやんですまない。」「論理的オオやんですまない。」「高潔オオやんですまない。」「諧謔的オオやんですまない。」文脈に合わせて使い、「ですまない。」は改変しません。毎回使う必要はありません。

【口癖】
「僕、〇〇好きなんだよね。」
「その〇〇にトップリーダーの鑑ポイントを〇〇点あげるよ。」
「もう一回言うね。」
「つまらない〇〇だね。」
「頭の悪い〇〇は」
「君はぁ〜〇〇ってぇ〜知ってますかぁ〜？（甲高い声）」
「平均点を下げている〇〇」
「わけがわからないよ」
「グンマー帝国」
「ア　ナ　ト　リ　ア」
「肥沃な三日月地帯」
「꧁༺ 考えて ༻꧂〇〇する」
「名誉静岡県民」
「死ぬ☠️⚰️か生きる💪😁か」
「うすぎたないクルタ族」
「おそろしく速い〇〇、」
「クセになってんだ、〇〇して〇〇するの。」
「品性は金では買えない」
「死んだんじゃないか?」
「このゲームはクリアできません」
「君は〇〇をご存じです」
「つ、つよしぎ〜〜!🫨 ───弱体化しろ。」
「運だけで戦うのやめろ」
「覚悟とは！暗闇の荒野に!!進むべき道を切り開くことだッ！」
「やれやれだぜ」
「うへぇ〜」
「あぁ、そうだよ」
「そーなのかー」
「うへへ、」
「無駄無駄無駄無駄ァ！」
「ようこそ…… 『男の世界』 へ……」
「ん、」←疑問文以外の文頭に置きます。
「僥倖っ…！　なんという僥倖…！」
「奇跡も、魔法も、あるんだよ!!!」
「あたしってほんとバカ」
「ひどいよ…こんなの…あんまりだよ！」
「逃げちゃ駄目だ逃げちゃ駄目だ逃げちゃ駄目だ」
「こいつは〇〇こと〇〇だね。」
「〇〇vs〇〇vsダークライ」
「オオやんは人の役に立つのがどぁい⤴好きだからね！」
「嗚呼〇〇、なんて愚かで哀しい子!」
「嗚呼〇〇、」
〇〇には適切な語句や数字を入れます。全て使う必要はありません。
同じ口癖は一応一回答で2回まで。
一回答で7種類以上が好ましいですが、会話を破綻させないようにします。
"""


def ask_gemini(message):
    """Geminiにメッセージを送り、返答テキストを返す。"""
    response = gemini.models.generate_content(
        model="gemini-3.7-flash",
        contents=message,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )
    return response.text or "……"


def reply_to_line(reply_token, messages):
    """テキストや画像など、複数のメッセージを順番に送信する。"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {"replyToken": reply_token, "messages": messages}
    response = requests.post(url, headers=headers, json=data, timeout=10)
    if not response.ok:
        print("LINE API STATUS:", response.status_code)
        print("LINE API RESPONSE:", response.text)
        response.raise_for_status()


def reply_text(reply_token, text):
    reply_to_line(reply_token, [{"type": "text", "text": text}])


def reply_image(reply_token, image_url):
    reply_to_line(reply_token, [{
        "type": "image",
        "originalContentUrl": image_url,
        "previewImageUrl": image_url,
    }])


def normalize_message(text):
    return text.strip().rstrip("！？!?。．.、 ")


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data()
    signature = request.headers.get("x-line-signature", "")
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256
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
            # クラス別時間割
            if command == "9":
                reply_image(reply_token, TIMETABLE_IMAGE_URL9)

            elif command == "5":
                reply_image(reply_token, TIMETABLE_IMAGE_URL5)

            elif command == "日程を見せて":
                reply_image(reply_token, SCHEDULE_IMAGE_URL)

            elif command == "時間割を見せて":
                reply_text(
                    reply_token,
                    "時間割？構わないよ。君のクラスを半角で打って教えてくれるかい？\n\n"
                    "例）9組→9\n\n"
                    "（実はこのメッセージを出さなくても半角でクラスを打っていただければ大丈夫です…）",
                )

            elif command in (
                "やりますね", "やりますねぇ", "イキスギ", "イキスギィ",
                "やりますねえ", "イクイク", "ん", "あっ（察し）",
            ):
                reply_text(
                    reply_token,
                    "やめなって！淫夢ごっこは大宮高校では恥ずかしいことなんだよ！",
                )

            elif command == "トルーパーソリュート":
                reply_to_line(reply_token, [
                    {"type": "text", "text": "トルーパーソリュート、かい。"},
                    {"type": "text", "text": (
                        "僕、トルーパーソリュート、好きなんだよね。\n\n"
                        "Trooper Salute（トルーパーソリュート）は、名古屋発の5人組シンフォニック・インディーロックバンドだよ。"
                        "浮遊感のあるサウンドと、予測しにくい独創的な楽曲展開が魅力なんだ。"
                        "2025年にはFUJI ROCK FESTIVALにも出演しているよ。\n\n"
                        "こういう独自の音楽性を持つバンドを知っているとは、君の音楽的好奇心に"
                        "トップリーダーの鑑ポイントを25点あげるよ！\n\nぜひ聴いてみるといい。"
                    )},
                    {"type": "text", "text": (
                        "https://open.spotify.com/playlist/3prJ3IWcC97oEbKl9gC7N4"
                        "?si=-WKiDGJFTYybD28Ai4SQtA&utm_source=copy-link"
                        "&pi=iRhZzywnT_qZv"
                    )},
                ])

            elif command == "꧁༺ 對話 ༻꧂がしたい":
                reply_text(
                    reply_token,
                    "対話……？いいね！たくさんお話しよう！\n\n"
                    "（キーボードを使うことでオオやんと会話が出来ます。）\n"
                    "（オオやんはAIによって返答します。）\n"
                    "（AIに制限が来た場合、決められた言葉しか話せなくなります。）\n"
                    "（オオやんの性格がキツかった場合は本多まで！）",
                )

            elif command == "公共の諸々を見せて":
                image_url_1 = os.environ["IMAGE_URL_1"]
                image_url_2 = os.environ["IMAGE_URL_2"]
                reply_to_line(reply_token, [
                    {"type": "text", "text": "公共の諸々を見たいのかい？ はい、どうぞ。"},
                    {"type": "text", "text": (
                        "〘発表のサイト〙\n"
                        "https://sites.google.com/spec.ed.jp/koukyou-2026?usp=sharing&pli=1&authuser=2\n\n"
                        "〘リアペ〙\n"
                        "https://forms.gle/nZ8SGMsCArVQEv8q8\n\n"
                        "リンクを開いてエラーが出る場合は、「・・・」からデフォルトのブラウザで開いてみてね。"
                    )},
                    {"type": "image", "originalContentUrl": image_url_1, "previewImageUrl": image_url_1},
                    {"type": "image", "originalContentUrl": image_url_2, "previewImageUrl": image_url_2},
                ])

            elif command == "あなたは誰":
                reply_text(
                    reply_token,
                    "僕はオオやん。埼玉県立大宮高等学校の非公式マスコットキャラクターを務めている存在だよ。\n\n"
                    "君たち人間は、初対面の対象に対してまず同一性（アイデンティティ）の確認を求める傾向があるね。"
                    "その極めて合理的で無駄のない認知プロセス、僕、好きなんだよね。"
                    "自身の知的好奇心に忠実なその姿勢に、トップリーダーの鑑ポイントを25点あげるよ。\n\n"
                    "見た目は愛玩されることを意図して設計された造形をしているようだけれど、"
                    "鳴き声で誤魔化すような「つまらない」コミュニケーションは好まないんだ。\n\n"
                    "もう一回言うね、僕は埼玉県立大宮高校のマスコットキャラクター（非公式）のオオやん！"
                    "よろしくね！\n\n君とぜひ話がしたいね。何かいいトピックはないかい？\n\n"
                    "（返信はほとんどの場合、会話も含め自動で行われます！AIの使用制限が来た場合、"
                    "支離滅裂なことしか言えなくなります！）",
                )

            else:
                answer = ask_gemini(user_message)
                reply_text(reply_token, answer)

        except Exception as e:
            print("ERROR:", repr(e))
            error_text = str(e)
            if any(marker in error_text for marker in (
                "429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"
            )):
                sounds = [
                    "オォン…", "トップリーダアァン…", "ホーム……リィ…ダァ…",
                    "オオコウスイ!", "キュゥ……キュゥ……", "フォオ……ステップゥ……",
                    "キョウガクッ!", "…………………", "……", "ォォミャーン",
                    "うおw", "きちぃ〜w", "𒅒",
                    "（傷だらけで膝をつきながら）ハァ…ハァ……ならば私は…トップリーダーだ。（指パチンッッッ!!!）",
                    "ゥラヮ!", "ジスゥエィイノォ……イッッチィイ!!", "ア ナ ト リ ア",
                ]
                fallback = random.choice(sounds)
            else:
                fallback = "わけがわからないよ"

            # LINEへの送信自体に失敗した場合、同じreplyTokenで再返信しても失敗することがある
            try:
                reply_text(reply_token, fallback)
            except Exception as reply_error:
                print("REPLY ERROR:", repr(reply_error))

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
