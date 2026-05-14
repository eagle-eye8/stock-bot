import datetime
import os
import sys
import traceback
# from dotenv import load_dotenv
import feedparser
import yfinance as yf
from google import genai
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)
# load_dotenv()
# ==========================================
# 環境変数チェック
# ==========================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

print("=" * 60)
print("🔍 Environment Check")
print("=" * 60)

print("GEMINI_API_KEY exists:", bool(GEMINI_API_KEY))
print("LINE_CHANNEL_ACCESS_TOKEN exists:", bool(LINE_CHANNEL_ACCESS_TOKEN))
print("LINE_USER_ID exists:", bool(LINE_USER_ID))

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY が設定されていません")

if not LINE_CHANNEL_ACCESS_TOKEN:
    raise ValueError("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")

if not LINE_USER_ID:
    raise ValueError("❌ LINE_USER_ID が設定されていません")

# ==========================================
# クライアント初期化
# ==========================================

client = genai.Client(api_key=GEMINI_API_KEY)

line_config = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)

# ==========================================
# データ収集
# ==========================================

def get_japan_stock_data():
    """日本株データ取得"""

    SCAN_LIST = {
        "285A": "キオクシア",
        "6857": "アドバンテスト",
        "6920": "レーザーテック",
        "4004": "レゾナック",
        "8035": "東京エレクトロン",
        "6146": "ディスコ",
        "6723": "ルネサス",
        "5016": "JX金属",
        "9984": "ソフトバンクG",
        "5803": "フジクラ",
        "8306": "三菱UFJ",
        "7203": "トヨタ",
        "9107": "川崎汽船",
        "9104": "商船三井",
        "7011": "三菱重工",
        "8058": "三菱商事",
        "4523": "エーザイ",
        "5802": "住友電工",
        "6501": "日立",
        "5401": "日本製鉄",
    }

    results = []

    print("=" * 60)
    print("🇯🇵 日本株データ取得開始")
    print("=" * 60)

    for code, name in SCAN_LIST.items():
        try:
            print(f"取得中: {name} ({code})")

            df = yf.Ticker(f"{code}.T").history(period="5d")

            if len(df) < 2:
                print(f"⚠️ データ不足: {name}")
                continue

            last = df["Close"].iloc[-1]
            chg = (last / df["Close"].iloc[-2] - 1) * 100

            volat = (
                (df["High"].iloc[-1] - df["Low"].iloc[-1])
                / df["Open"].iloc[-1]
                * 100
            )

            val = (last * df["Volume"].iloc[-1]) / 10**8

            results.append(
                f"【{name}】"
                f"{last:.0f}円"
                f"({chg:+.1f}%) "
                f"ボラ:{volat:.1f}% "
                f"代金:{val:.0f}億"
            )

        except Exception as e:
            print(f"❌ 日本株取得エラー: {name}")
            print(e)

    return "\n".join(results)


def get_us_stock_data():
    """米国株データ取得"""

    US_WATCH = {
        "NVDA": "エヌビディア",
        "TSLA": "テスラ",
        "AAPL": "アップル",
        "MSFT": "マイクロソフト",
        "AVGO": "ブロードコム",
        "SOXL": "SOXレバ",
    }

    results = []

    print("=" * 60)
    print("🇺🇸 米国株データ取得開始")
    print("=" * 60)

    for ticker, name in US_WATCH.items():
        try:
            print(f"取得中: {ticker}")

            df = yf.Ticker(ticker).history(period="5d")

            if len(df) < 2:
                print(f"⚠️ データ不足: {ticker}")
                continue

            last = df["Close"].iloc[-1]
            chg = (last / df["Close"].iloc[-2] - 1) * 100

            results.append(
                f"{name}({ticker}): "
                f"${last:.1f} "
                f"({chg:+.1f}%)"
            )

        except Exception as e:
            print(f"❌ 米国株取得エラー: {ticker}")
            print(e)

    return "\n".join(results)


def get_weekend_news():
    """Google News RSS取得"""

    print("=" * 60)
    print("📰 ニュース取得開始")
    print("=" * 60)

    try:
        url = (
            "https://news.google.com/rss/search?"
            "q=政治+経済+日本+半導体&hl=ja&gl=JP&ceid=JP:ja"
        )

        feed = feedparser.parse(url)

        news = [
            f"・{e.title}"
            for e in feed.entries[:10]
        ]

        return "【最新トピック】\n" + "\n".join(news)

    except Exception as e:
        print("❌ ニュース取得失敗")
        print(e)
        raise


# ==========================================
# AI解析
# ==========================================

def run_analysis(mode_name, ctx, details):

    print("=" * 60)
    print("🤖 Gemini解析開始")
    print("=" * 60)

    prompt = f"""
# Role
あなたは伝説的なデイトレーダー兼テクニカルアナリストです。

提供された情報を元に、
{mode_name}の戦略について
深く推論し、
勝利のためのロードマップを提示してください。

# Input Data

【市場概況】
{ctx}

【詳細データ】
{details}

# 指示

1. 絵文字を多用
2. 米国市場と日本市場の連動性を分析
3. 個別銘柄を深掘り
4. デイトレ・スイング戦略を提示

# 出力構成

1. 【🔥相場熱感】
2. 【🌍米日連動分析】
3. 【💎個別ピックアップ】
4. 【🎯今日の勝ち筋】
"""

    try:
        print("📝 Prompt length:", len(prompt))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        print("✅ Gemini API成功")

        print("=" * 60)
        print("📦 RAW RESPONSE")
        print("=" * 60)

        print(response)

        text = getattr(response, "text", None)

        if not text:
            print("❌ response.text が空")

            if hasattr(response, "candidates"):
                print("candidates:")
                print(response.candidates)

            raise ValueError("Gemini response.text が空です")

        print("✅ response.text 取得成功")
        print("文字数:", len(text))

        return text

    except Exception as e:

        print("=" * 60)
        print("❌ Gemini解析エラー")
        print("=" * 60)

        traceback.print_exc()

        print("エラー内容:")
        print(type(e))
        print(e)

        raise


# ==========================================
# LINE送信
# ==========================================

def send_line(msg):

    print("=" * 60)
    print("📤 LINE送信開始")
    print("=" * 60)

    try:

        print("message length:", len(msg))

        # LINE制限対策
        if len(msg) > 4500:
            print("⚠️ メッセージ長すぎるためカット")

            msg = msg[:4500] + "\n\n...(省略)"

        with ApiClient(line_config) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.push_message(
                PushMessageRequest(
                    to=LINE_USER_ID,
                    messages=[
                        TextMessage(text=msg)
                    ]
                )
            )

        print("✅ LINE送信完了")

    except Exception as e:

        print("=" * 60)
        print("❌ LINE送信エラー")
        print("=" * 60)

        traceback.print_exc()

        raise


# ==========================================
# メイン処理
# ==========================================

def main():

    print("=" * 60)
    print("🚀 START")
    print("=" * 60)

    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "JP"

    jst_now = datetime.datetime.now(
        datetime.timezone(
            datetime.timedelta(hours=9)
        )
    )

    now_str = jst_now.strftime("%Y/%m/%d %H:%M")

    print(f"🕒 JST Time: {now_str}")
    print(f"📌 Mode: {mode_arg}")

    # ==========================================
    # 市場指数
    # ==========================================

    indices = {
        "日経": "^N225",
        "TOPIX": "1306.T",
        "ダウ": "^DJI",
        "SOX": "^SOX",
        "ナス": "^IXIC",
        "円": "JPY=X",
    }

    ctx = ""

    print("=" * 60)
    print("📊 市場指数取得")
    print("=" * 60)

    for name, ticker in indices.items():

        try:
            print(f"取得中: {name}")

            d = yf.Ticker(ticker).history(period="5d")

            if len(d) < 2:
                print(f"⚠️ データ不足: {name}")
                continue

            pct = (
                d["Close"].iloc[-1]
                / d["Close"].iloc[-2]
                - 1
            ) * 100

            ctx += f"{name}:{pct:+.1f}% "

        except Exception as e:
            print(f"❌ 指数取得失敗: {name}")
            print(e)

    print("市場概況:", ctx)

    # ==========================================
    # モード分岐
    # ==========================================

    if mode_arg == "JP":

        title = "🇯🇵 日本株・朝の戦略"

        details = get_japan_stock_data()

    elif mode_arg == "US":

        title = "🇺🇸 米国株・夜の分析"

        details = get_us_stock_data()

    else:

        title = "📰 週末トピック分析"

        details = get_weekend_news()

    print("=" * 60)
    print("📋 details")
    print("=" * 60)

    print(details)

    # ==========================================
    # AI解析
    # ==========================================

    analysis = run_analysis(
        title,
        ctx,
        details,
    )

    # ==========================================
    # LINE送信
    # ==========================================

    full_msg = (
        f"【{title}】\n"
        f"配信時刻: {now_str}(JST)\n\n"
        f"{analysis}"
    )

    send_line(full_msg)

    print("=" * 60)
    print("✅ ALL DONE")
    print("=" * 60)


# ==========================================
# エントリーポイント
# ==========================================

if __name__ == "__main__":

    try:
        main()

    except Exception as e:

        print("=" * 60)
        print("💥 FATAL ERROR")
        print("=" * 60)

        traceback.print_exc()

        sys.exit(1)
