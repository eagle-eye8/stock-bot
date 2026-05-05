import datetime  # 実行時刻の表示に使用
import os
import sys

import feedparser
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
line_config = Configuration(access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ==========================================
# データ収集セクション
# ==========================================
def get_japan_stock_data():
    """日本株：主要銘柄のスキャン"""
    SCAN_LIST = {
        # ユーザー指定
        # 半導体・ハイテク
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
        # 出来高・売買代金常連
        "8306": "三菱UFJ",
        "7203": "トヨタ",
        "9107": "川崎汽船",
        "9104": "商船三井",
        "7011": "三菱重工",
        "8058": "三菱商事",
        "9983": "ファーストリテイリング",
        "4523": "エーザイ",
        "5802": "住友電工",
        "6501": "日立",
        "5401": "日本製鉄",
    }

    results = []
    for code, name in SCAN_LIST.items():
        try:
            df = yf.Ticker(f"{code}.T").history(period="5d")
            if len(df) < 2:
                continue
            last = df["Close"].iloc[-1]
            chg = (last / df["Close"].iloc[-2] - 1) * 100
            volat = (
                (df["High"].iloc[-1] - df["Low"].iloc[-1]) / df["Open"].iloc[-1] * 100
            )
            val = (last * df["Volume"].iloc[-1]) / 10**8
            results.append(
                f"【{name}】{last:.0f}円({chg:+.1f}%) ボラ:{volat:.1f}% 代金:{val:.0f}億"
            )
        except:
            continue
    return "\n".join(results)


def get_us_stock_data():
    """米国株：主要銘柄のスキャン"""
    US_WATCH = {
        "NVDA": "エヌビディア",
        "TSLA": "テスラ",
        "AAPL": "アップル",
        "MSFT": "マイクロソフト",
        "AVGO": "ブロードコム",
        "SOXL": "SOXレバ",
    }
    results = []
    for ticker, name in US_WATCH.items():
        try:
            df = yf.Ticker(ticker).history(period="5d")
            last = df["Close"].iloc[-1]
            chg = (last / df["Close"].iloc[-2] - 1) * 100
            results.append(f"{name}({ticker}): ${last:.1f} ({chg:+.1f}%)")
        except:
            continue
    return "\n".join(results)


def get_weekend_news():
    """週末：GoogleニュースRSS"""
    url = "https://news.google.com/rss/search?q=政治+経済+日本+半導体&hl=ja&gl=JP&ceid=JP:ja"
    feed = feedparser.parse(url)
    news = [f"・{e.title}" for e in feed.entries[:10]]
    return "【最新トピック】\n" + "\n".join(news)


# ==========================================
# 解析 & 送信
# ==========================================
def run_analysis(mode_name, ctx, details):
    prompt = f"""
# Role
あなたは伝説的なデイトレーダー兼テクニカルアナリストです。
提供された情報を元に、{mode_name}の戦略について深く推論し、勝利のためのロードマップを提示してください。

# Input Data
【市場概況（Context）】
{ctx}

【詳細データ（Indices/Stocks/News）】
{details}

# 指示・制約事項
1. **視覚的判断**: 📈🚀📉⚠️などの絵文字を多用し、一目で強気・弱気・警戒がわかる直感的な投資判断を下すこと。
2. **市場の相関分析**: 米国市場（SOX指数、NVDA等）と日本市場（日経先物、為替）の連動性を踏まえ、今日の地合いを定義すること。
3. **個別銘柄の深掘り**: 以下の銘柄については、データとニュースから具体的な値動きを予測すること。
   - **アドバンテスト(6857)**：半導体セクターの牽引役としての動向
   - **レゾナック(4004)**：パワー半導体・材料面での材料視
   - **フジクラ(5803)**：電線・AIデータセンター関連としての需給
   - **キオクシア**：IPO動向およびメモリ市況への波及
   - **JX金属(ENEOS:5020)**：銅価格などの商品市況とグループ動向
4. **アクションプラン**: デイトレ・スイングの視点で「今日（週明け）の勝ち筋」を、エントリー・利確・損切りの考え方を含めて具体的に提示すること。

# 出力構成
1. 【🔥相場熱感】全体的なセンチメント
2. 【🌍米日連動分析】外部環境からの影響
3. 【💎個別ピックアップ】指定5社の戦略（📈/📉判断付き）
4. 【🎯今日の勝ち筋】具体的シナリオと狙い目の価格帯
"""
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="high")
            ),
        )
        return response.text
    except Exception as e:
        return f"AI解析エラー。データのみ表示：\n{details}"


def send_line(msg):
    try:
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(to=LINE_USER_ID, messages=[TextMessage(text=msg)])
            )
        print("✅ LINE送信完了")
    except Exception as e:
        print(f"❌ LINEエラー: {e}")


# ==========================================
# メイン
# ==========================================


def main():
    mode_arg = sys.argv[1] if len(sys.argv) > 1 else "JP"

    # --- datetimeの使用: 日本時間の現在時刻を取得 ---
    # GitHub Actions(UTC)でも日本時間で表示されるように +9時間調整
    jst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    now_str = jst_now.strftime("%Y/%m/%d %H:%M")

    print(f"=== 実行モード: {mode_arg} ({now_str}) ===")

    # 市場指数 (TOPIXはETF 1306.Tで安定取得)
    indices = {
        "日経": "^N225",
        "TOPIX": "1306.T",
        "ダウ": "^DJI",
        "SOX": "^SOX",
        "ナス": "^IXIC",
        "円": "JPY=X",
    }
    ctx = ""
    for name, t in indices.items():
        try:
            d = yf.Ticker(t).history(period="5d")
            pct = (d["Close"].iloc[-1] / d["Close"].iloc[-2] - 1) * 100
            ctx += f"{name}:{pct:+.1f}% "
        except:
            pass

    # モード切り替え
    if mode_arg == "JP":
        title = "🇯🇵 日本株・朝の戦略"
        details = get_japan_stock_data()
    elif mode_arg == "US":
        title = "🇺🇸 米国株・夜の分析"
        details = get_us_stock_data()
    else:
        title = "📰 週末トピック分析"
        details = get_weekend_news()

    # 解析実行
    analysis = run_analysis(title, ctx, details)

    # --- 送信メッセージの組み立て (時刻を挿入) ---
    full_msg = f"【{title}】\n配信時刻: {now_str}(JST)\n\n{analysis}"
    send_line(full_msg)


if __name__ == "__main__":
    main()
