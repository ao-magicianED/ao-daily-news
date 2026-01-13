#!/usr/bin/env python3
"""
あおのデイリーニュース - ニュース収集スクリプト
RSSフィードからニュースを取得し、Gemini APIで要約・コメントを生成
"""

import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import feedparser
import requests
from typing import Optional

# 設定
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = DATA_DIR / "archive"

# Gemini API設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# RSSフィード一覧
RSS_FEEDS = {
    "ai": [
        # AI関連ニュース
        {"url": "https://news.google.com/rss/search?q=AI+ChatGPT+Claude+Gemini&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News AI"},
        {"url": "https://news.google.com/rss/search?q=生成AI+人工知能&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News 生成AI"},
        {"url": "https://news.google.com/rss/search?q=OpenAI+Anthropic+Google+AI&hl=en&gl=US&ceid=US:en", "name": "Google News AI (Global)"},
    ],
    "minpaku": [
        # 民泊関連ニュース
        {"url": "https://news.google.com/rss/search?q=民泊+規制&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News 民泊規制"},
        {"url": "https://news.google.com/rss/search?q=民泊+Airbnb&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News 民泊"},
        {"url": "https://news.google.com/rss/search?q=vacation+rental+regulation&hl=en&gl=US&ceid=US:en", "name": "Global Vacation Rental"},
    ],
    "rental": [
        # レンタルスペース関連ニュース
        {"url": "https://news.google.com/rss/search?q=レンタルスペース+シェアスペース&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News レンタルスペース"},
        {"url": "https://news.google.com/rss/search?q=インスタベース+スペースマーケット&hl=ja&gl=JP&ceid=JP:ja", "name": "Google News スペースプラットフォーム"},
        {"url": "https://news.google.com/rss/search?q=coworking+space+sharing&hl=en&gl=US&ceid=US:en", "name": "Global Space Sharing"},
    ]
}

# AIツール検出キーワード
AI_TOOLS = {
    "ChatGPT": ["chatgpt", "chat gpt", "openai", "gpt-4", "gpt-5", "gpt4", "gpt5"],
    "Claude": ["claude", "anthropic"],
    "Gemini": ["gemini", "google ai", "bard"],
    "Manus": ["manus"],
    "Genspark": ["genspark"],
}


def fetch_rss_entries(feed_url: str, max_entries: int = 10) -> list:
    """RSSフィードからエントリーを取得"""
    try:
        feed = feedparser.parse(feed_url)
        entries = []

        for entry in feed.entries[:max_entries]:
            entries.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")[:500] if entry.get("summary") else "",
            })

        return entries
    except Exception as e:
        print(f"RSS fetch error: {e}")
        return []


def detect_ai_tools(text: str) -> list:
    """テキストから関連するAIツールを検出"""
    text_lower = text.lower()
    detected = []

    for tool, keywords in AI_TOOLS.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(tool)

    return detected if detected else ["Other"]


def call_gemini_api(prompt: str) -> Optional[str]:
    """Gemini APIを呼び出してテキストを生成"""
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set")
        return None

    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }

        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"Gemini API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return None


def generate_ai_summary(entry: dict) -> dict:
    """AIニュースの要約とコメントを生成"""
    prompt = f"""
以下のAI関連ニュースについて、日本語で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で初心者にもわかりやすく説明",
    "detail": "もう少し詳しい解説（あれば）",
    "aoComment": "このAI技術を民泊やレンタルスペースビジネスに活用するとしたら、どんなことができるか？という視点でのアイデアや発想のヒントを1-2文で"
}}

JSONのみを出力してください。
"""

    result = call_gemini_api(prompt)

    if result:
        try:
            # JSONを抽出
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # フォールバック
    return {
        "summary": entry['summary'][:200] if entry['summary'] else entry['title'],
        "detail": "",
        "aoComment": "このニュースの続報に注目です。AIの進化は民泊・レンタルスペース業界にも新しい可能性をもたらすかもしれません。"
    }


def generate_minpaku_summary(entry: dict) -> dict:
    """民泊ニュースの要約とコメントを生成"""
    prompt = f"""
以下の民泊関連ニュースについて、民泊オーナーの立場で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で説明",
    "detail": "オーナーが知っておくべき詳細情報（あれば）",
    "aoComment": "民泊オーナーとして、このニュースをどう活かすか、どう対応すべきかのアドバイスを1-2文で"
}}

JSONのみを出力してください。
"""

    result = call_gemini_api(prompt)

    if result:
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {
        "summary": entry['summary'][:200] if entry['summary'] else entry['title'],
        "detail": "",
        "aoComment": "民泊オーナーとして、規制動向や市場トレンドは常にチェックしておきましょう。"
    }


def generate_rental_summary(entry: dict) -> dict:
    """レンタルスペースニュースの要約とコメントを生成"""
    prompt = f"""
以下のレンタルスペース関連ニュースについて、スペースオーナーの立場で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で説明",
    "detail": "オーナーが知っておくべき詳細情報（あれば）",
    "aoComment": "レンタルスペースオーナーとして、このニュースをどう活かすか、新しいスペースジャンルのアイデアなどを1-2文で"
}}

JSONのみを出力してください。
"""

    result = call_gemini_api(prompt)

    if result:
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {
        "summary": entry['summary'][:200] if entry['summary'] else entry['title'],
        "detail": "",
        "aoComment": "インスタベースやスペースマーケットの新機能はこまめにチェック。新しいスペースジャンルにもアンテナを張りましょう。"
    }


def process_news_category(category: str, max_articles: int = 5) -> list:
    """カテゴリごとにニュースを処理"""
    all_entries = []

    # RSSフィードからエントリーを収集
    for feed in RSS_FEEDS.get(category, []):
        entries = fetch_rss_entries(feed["url"], max_entries=5)
        for entry in entries:
            entry["source"] = feed["name"]
        all_entries.extend(entries)

    # 重複除去（タイトルベース）
    seen_titles = set()
    unique_entries = []
    for entry in all_entries:
        title_key = entry["title"].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_entries.append(entry)

    # 最新のものを選択
    processed = []
    for entry in unique_entries[:max_articles]:
        # カテゴリに応じた要約生成
        if category == "ai":
            summary_data = generate_ai_summary(entry)
            tools = detect_ai_tools(entry["title"] + " " + entry.get("summary", ""))
        elif category == "minpaku":
            summary_data = generate_minpaku_summary(entry)
            tools = []
        else:  # rental
            summary_data = generate_rental_summary(entry)
            tools = []

        article = {
            "title": entry["title"],
            "url": entry["link"],
            "source": entry.get("source", ""),
            "summary": summary_data.get("summary", ""),
            "detail": summary_data.get("detail", ""),
            "aoComment": summary_data.get("aoComment", ""),
        }

        if tools:
            article["tools"] = tools

        processed.append(article)

    return processed


def update_archive_index(date_str: str):
    """アーカイブインデックスを更新"""
    index_path = ARCHIVE_DIR / "index.json"

    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = []

    if date_str not in index:
        index.insert(0, date_str)
        # 最大100件保持
        index = index[:100]

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def main():
    """メイン処理"""
    print("=" * 50)
    print("あおのデイリーニュース - ニュース収集開始")
    print("=" * 50)

    # ディレクトリ作成
    DATA_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    # 日付（前日のニュースをまとめる）
    today = datetime.now()
    target_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n対象日: {target_date}")
    print(f"Gemini API: {'設定済み' if GEMINI_API_KEY else '未設定（フォールバックモード）'}")

    # 各カテゴリのニュースを処理
    news_data = {
        "date": target_date,
        "generated_at": today.isoformat(),
        "ai": [],
        "minpaku": [],
        "rental": []
    }

    for category in ["ai", "minpaku", "rental"]:
        print(f"\n[{category.upper()}] ニュースを収集中...")
        articles = process_news_category(category, max_articles=5)
        news_data[category] = articles
        print(f"  → {len(articles)}件の記事を処理しました")

    # 最新データとして保存
    news_path = DATA_DIR / "news.json"
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    print(f"\n最新ニュースを保存: {news_path}")

    # アーカイブとして保存
    archive_path = ARCHIVE_DIR / f"{target_date}.json"
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    print(f"アーカイブを保存: {archive_path}")

    # アーカイブインデックス更新
    update_archive_index(target_date)
    print("アーカイブインデックスを更新しました")

    print("\n" + "=" * 50)
    print("ニュース収集完了！")
    print("=" * 50)


if __name__ == "__main__":
    main()
