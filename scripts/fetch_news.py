#!/usr/bin/env python3
"""
あおのデイリーニュース - ニュース収集スクリプト
RSSフィードからニュースを取得し、Gemini APIで要約・コメントを生成
"""

import os
import json
import re
import random
from html import unescape
from datetime import datetime, timedelta, timezone
from pathlib import Path
import feedparser
import requests
from typing import Optional
from email.utils import parsedate_to_datetime

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

# フォールバックコメント（カテゴリ別）
FALLBACK_COMMENTS = {
    "ai": [
        "AIの進化は目覚ましいですね。民泊やレンタルスペースの運営にも活用できるヒントがあるかもしれません。",
        "この技術、顧客対応の自動化や予約管理に応用できそうです。最新動向は要チェック！",
        "AI活用で業務効率化のチャンス。競合に差をつけるためにも、新しい技術には敏感でいたいですね。",
        "生成AIの活用シーンが広がっています。物件紹介文の作成や多言語対応などに使えそう。",
        "テクノロジーの進歩を味方につけて、より良いサービス提供を目指しましょう！",
        "このニュースは注目。AIを使った集客や運営効率化のアイデアが浮かびます。",
        "時代の流れを掴んでおくことが大切。AI活用は今後ますます重要になりそうです。",
    ],
    "minpaku": [
        "規制動向は常にウォッチしておきましょう。早めの対応が安定運営のカギです。",
        "市場の変化に敏感に。柔軟な戦略で乗り越えていきましょう！",
        "民泊ビジネスは変化が激しい業界。情報収集を怠らないことが成功の秘訣です。",
        "他のオーナーさんの動向も参考に。良い事例は積極的に取り入れましょう。",
        "インバウンド需要の回復に備えて、今から準備を進めておくのがおすすめです。",
        "地域のルールをしっかり確認。法令遵守で長く続けられるビジネスを。",
        "ゲストの安全・安心を第一に。信頼されるホストを目指しましょう。",
    ],
    "rental": [
        "新しいスペース活用のヒントになりそう。トレンドを押さえておきましょう。",
        "レンタルスペース市場は成長中。差別化のアイデアを常に考えていきたいですね。",
        "プラットフォームの動向は要チェック。新機能は積極的に活用しましょう。",
        "ニッチなジャンルにもチャンスあり。ユニークなスペースで勝負するのもアリ。",
        "リピーター獲得が安定収益のカギ。サービス品質を高めていきましょう。",
        "競合との差別化ポイントを明確に。自分のスペースの強みを活かしましょう。",
        "新しい利用シーンの開拓が成長のヒント。柔軟な発想で可能性を広げましょう。",
    ],
}


def parse_published_date(published_str: str) -> str:
    """配信日をパースして日本語形式に変換"""
    if not published_str:
        return ""

    try:
        dt = parsedate_to_datetime(published_str)
        return dt.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        try:
            dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except Exception:
            return published_str[:16] if len(published_str) > 16 else published_str


def parse_published_datetime(published_str: str) -> Optional[datetime]:
    """配信日をdatetimeオブジェクトとしてパース"""
    if not published_str:
        return None

    try:
        return parsedate_to_datetime(published_str)
    except Exception:
        try:
            return datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            return None


def is_published_on_date(published_str: str, target_date: str) -> bool:
    """記事が指定日に公開されたかどうかを判定"""
    dt = parse_published_datetime(published_str)
    if not dt:
        return False
    
    # タイムゾーンを考慮してJSTに変換
    jst = timezone(timedelta(hours=9))
    if dt.tzinfo:
        dt_jst = dt.astimezone(jst)
    else:
        dt_jst = dt.replace(tzinfo=jst)
    
    article_date = dt_jst.strftime("%Y-%m-%d")
    return article_date == target_date


def fetch_article_content(url: str) -> str:
    """元記事のURLから本文を取得"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        
        # メタタグからdescriptionを取得
        og_desc = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not og_desc:
            og_desc = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']', html, re.IGNORECASE)
        
        meta_desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not meta_desc:
            meta_desc = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
        
        # 優先順位: og:description > meta description
        description = ""
        if og_desc:
            description = og_desc.group(1)
        elif meta_desc:
            description = meta_desc.group(1)
        
        # HTMLエンティティをデコード
        description = unescape(description)
        
        # 記事本文を抽出（article, main, .article, .content などから）
        article_content = ""
        
        # <article>タグから抽出
        article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
        if article_match:
            article_content = article_match.group(1)
        else:
            # <main>タグから抽出
            main_match = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
            if main_match:
                article_content = main_match.group(1)
        
        # 本文からテキストを抽出
        if article_content:
            # pタグの内容を抽出
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', article_content, re.DOTALL | re.IGNORECASE)
            if paragraphs:
                # HTMLタグを除去してテキストのみ取得
                text_parts = []
                for p in paragraphs[:5]:  # 最初の5段落
                    clean_p = clean_html_text(p)
                    if len(clean_p) > 30:  # 短すぎる段落は除外
                        text_parts.append(clean_p)
                if text_parts:
                    article_content = " ".join(text_parts)[:1000]
                else:
                    article_content = ""
        
        # 本文が取得できなかった場合はdescriptionを使用
        if not article_content and description:
            return description[:500]
        
        if article_content:
            return article_content[:1000]
        
        return description[:500] if description else ""
        
    except Exception as e:
        print(f"  記事取得エラー ({url[:50]}...): {e}")
        return ""


def clean_html_text(text: str) -> str:
    """HTMLを取り除いて読みやすいテキストに整形"""
    if not text:
        return ""
    # HTMLエンティティを先にデコード
    text = unescape(text)
    # scriptタグとstyleタグの中身を除去
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # HTMLタグを除去
    no_tags = re.sub(r"<[^>]+>", " ", text)
    # URLを除去（要約に含まれるリンクURL）
    no_urls = re.sub(r'https?://\S+', '', no_tags)
    # 連続する空白を正規化
    normalized = re.sub(r"\s+", " ", no_urls).strip()
    return normalized


def extract_entry_summary(entry: dict) -> str:
    """RSSエントリーから本文候補を抽出"""
    raw_summary = entry.get("summary", "")
    if not raw_summary:
        contents = entry.get("content", [])
        if contents and isinstance(contents, list):
            raw_summary = contents[0].get("value", "")
    
    cleaned = clean_html_text(raw_summary)
    
    # Google Newsの場合、summaryがほぼ空になることがあるのでタイトルを使用
    if len(cleaned) < 20:
        return ""
    
    return cleaned


def get_fallback_comment(category: str) -> str:
    """カテゴリに応じたランダムなフォールバックコメントを取得"""
    comments = FALLBACK_COMMENTS.get(category, FALLBACK_COMMENTS["ai"])
    return random.choice(comments)


def fetch_rss_entries(feed_url: str, max_entries: int = 10, target_date: str = None) -> list:
    """RSSフィードからエントリーを取得（日付フィルタリング対応）"""
    try:
        feed = feedparser.parse(feed_url)
        entries = []

        for entry in feed.entries[:max_entries * 3]:  # 多めに取得してフィルタリング
            published_raw = entry.get("published", "")
            
            # 日付フィルタリング（target_dateが指定されている場合）
            if target_date and published_raw:
                if not is_published_on_date(published_raw, target_date):
                    continue
            
            clean_title = clean_html_text(entry.get("title", ""))
            entries.append({
                "title": clean_title,
                "link": entry.get("link", ""),
                "published": published_raw,
                "publishedDate": parse_published_date(published_raw),
                "summary": extract_entry_summary(entry)[:500],
            })
            
            if len(entries) >= max_entries:
                break

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


def generate_ai_summary(entry: dict, article_content: str = "") -> dict:
    """AIニュースの要約とコメントを生成"""
    # 本文情報を追加
    content_info = f"\n本文: {article_content[:800]}" if article_content else ""
    
    prompt = f"""
以下のAI関連ニュースについて、日本語で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}{content_info}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で初心者にもわかりやすく説明",
    "detail": "記事の詳細な内容を3-5文で説明。具体的な数字や事実があれば含める",
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
    fallback_summary = entry['summary'][:200] if entry['summary'] else f"「{entry['title']}」について報じられています。"
    fallback_detail = article_content[:300] if article_content else ""
    return {
        "summary": fallback_summary,
        "detail": fallback_detail,
        "aoComment": get_fallback_comment("ai")
    }


def generate_minpaku_summary(entry: dict, article_content: str = "") -> dict:
    """民泊ニュースの要約とコメントを生成"""
    # 本文情報を追加
    content_info = f"\n本文: {article_content[:800]}" if article_content else ""
    
    prompt = f"""
以下の民泊関連ニュースについて、民泊オーナーの立場で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}{content_info}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で説明",
    "detail": "オーナーが知っておくべき詳細情報を3-5文で。規制内容、影響範囲、時期などがあれば含める",
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

    fallback_summary = entry['summary'][:200] if entry['summary'] else f"「{entry['title']}」について報じられています。"
    fallback_detail = article_content[:300] if article_content else ""
    return {
        "summary": fallback_summary,
        "detail": fallback_detail,
        "aoComment": get_fallback_comment("minpaku")
    }


def generate_rental_summary(entry: dict, article_content: str = "") -> dict:
    """レンタルスペースニュースの要約とコメントを生成"""
    # 本文情報を追加
    content_info = f"\n本文: {article_content[:800]}" if article_content else ""
    
    prompt = f"""
以下のレンタルスペース関連ニュースについて、スペースオーナーの立場で要約とコメントを作成してください。

タイトル: {entry['title']}
概要: {entry['summary']}{content_info}

出力形式（JSON）:
{{
    "summary": "ニュースの要点を2-3文で説明",
    "detail": "オーナーが知っておくべき詳細情報を3-5文で。市場動向、新サービス、利用トレンドなどがあれば含める",
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

    fallback_summary = entry['summary'][:200] if entry['summary'] else f"「{entry['title']}」について報じられています。"
    fallback_detail = article_content[:300] if article_content else ""
    return {
        "summary": fallback_summary,
        "detail": fallback_detail,
        "aoComment": get_fallback_comment("rental")
    }


def process_news_category(category: str, max_articles: int = 5, target_date: str = None) -> list:
    """カテゴリごとにニュースを処理"""
    all_entries = []

    # RSSフィードからエントリーを収集（日付フィルタリング付き）
    for feed in RSS_FEEDS.get(category, []):
        entries = fetch_rss_entries(feed["url"], max_entries=10, target_date=target_date)
        for entry in entries:
            entry["source"] = feed["name"]
        all_entries.extend(entries)
        print(f"    {feed['name']}: {len(entries)}件")

    # 重複除去（タイトルベース）
    seen_titles = set()
    unique_entries = []
    for entry in all_entries:
        title_key = entry["title"].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_entries.append(entry)

    print(f"    重複除去後: {len(unique_entries)}件")

    # 最新のものを選択
    processed = []
    for entry in unique_entries[:max_articles]:
        print(f"    処理中: {entry['title'][:40]}...")
        
        # 元記事から本文を取得
        article_content = fetch_article_content(entry["link"])
        
        # カテゴリに応じた要約生成
        if category == "ai":
            summary_data = generate_ai_summary(entry, article_content)
            tools = detect_ai_tools(entry["title"] + " " + entry.get("summary", "") + " " + article_content)
        elif category == "minpaku":
            summary_data = generate_minpaku_summary(entry, article_content)
            tools = []
        else:  # rental
            summary_data = generate_rental_summary(entry, article_content)
            tools = []

        article = {
            "title": entry["title"],
            "url": entry["link"],
            "source": entry.get("source", ""),
            "publishedDate": entry.get("publishedDate", ""),
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
        articles = process_news_category(category, max_articles=5, target_date=target_date)
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
