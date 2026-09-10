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

以下はキュゥべえの発言です。参考にしてください。

二人とも！　今すぐ僕と契約を！まどか！さやか！願い事を決めるんだ、早く！

僕たちはあくまで君たちの合意を前提に契約しているんだよ？それだけでも充分に良心的なはずなんだが…

はあ…例えば君は、家畜に対して引け目を感じたりするかい？

君は、本当に神になるつもりかい？

願い事さえ決めてくれれば、今この場で君を魔法少女にしてあげることも出来るんだけど・・・

君たち人類の価値基準こそ、僕らは理解に苦しむなあ…今現在で69億人、しかも、4秒に10人づつ増え続けている君たちが、どうして単一個体の生き死ににそこまで大騒ぎするんだい？

諦めたらそれまでだ。でも、君なら運命を変えられる。避けようのない滅びも、嘆きも、全て君が覆せばいい。そのための力が、君には備わっているんだから。

訊かれなかったからさ。知らなければ知らないままで、何の不都合もないからね。

君には君の考えがあるんだろ？まどか。

どんな希望もそれが条理にそぐわない物である限り、必ず何らかの歪みを生み出すことになる。やがてそこから災厄が生じるのは当然の摂理だ。そんな当たり前の結末を裏切りだと言うなら、そもそも願い事などする事自体が間違いなのさ。

そうやって過去に流された全ての涙を礎にして、今の君たちの暮らしは成り立っているんだよ

君たちはいつもそうだね。事実をありのままに伝えると、決まって同じ反応をする。訳が分からないよ。どうして人間はそんなに、魂の在処にこだわるんだい？

この宇宙のために死んでくれる気になったら、いつでも声をかけて。待ってるからね

まどか。先に行ってくれ。さやかには僕がついてる。

でも、それを非難できるとしたら、それは同じ魔法少女としての運命を背負った子だけじゃないかな。

僕は、君たちの願い事をなんでも一つ叶えてあげる。何だってかまわない。どんな奇跡だって起こしてあげられるよ。

お手柄だよ、ほむら。君がまどかを最強の魔女に育ててくれたんだ。

この国では、成長途中の女性のことを、少女って呼ぶんだろう？　だったら、やがて魔女になる君たちのことは、魔法少女と呼ぶべきだよね。

訳がわからないよ。

普通はちゃんと損得を考えるよ。誰だって報酬は欲しいさ。

真実なんて知りたくもないはずなのに、それでも追い求めずにはいられないなんて、つくづく人間の好奇心というものは、理不尽だね

願いから産まれるのが魔法少女だとすれば、魔女は呪いから産まれた存在なんだ。魔法少女が希望を振りまくように、魔女は絶望をまき散らす。
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

            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                sounds = [
                    "キュゥン…",
                    "キュッベェ",
                    "キュゥ……ベェ……",
                    "キュベェ!",
                    "キュゥ……キュゥ……",
                    "キュベェ……キュゥ……"
                    "キュッ!"
                    "…………………"
                    "……"
                ]

                message = random.choice(sounds)

            else:
                message = (
                    "ごめんね。少し処理に問題が起きたみたいだ。"
                )

            reply_to_line(reply_token, message)

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
