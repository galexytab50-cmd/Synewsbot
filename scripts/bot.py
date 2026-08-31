#!/usr/bin/env python3
"""
ربات خوندن فیدهای اینوریدر، ترجمه و خلاصه‌سازی با DeepSeek،
و ارسال پست‌های جدید به کانال تلگرام.

این اسکریپت:
1. با استفاده از refresh_token یک access_token جدید از اینوریدر می‌گیرد.
2. آیتم‌های خوانده‌شده (reading list) را می‌خواند.
3. هر آیتم جدید را با DeepSeek ترجمه، خلاصه و دسته‌بندی می‌کند.
4. پیام را با قالب مشخص (هشتگ، تیتر، خلاصه، منبع لینک‌دار) به تلگرام می‌فرستد.
5. زمان آخرین آیتم پردازش‌شده را در فایل state.json ذخیره می‌کند.
"""

import json
import os
import re
import sys
import time
import html
import requests

# ---------- تنظیمات از طریق متغیرهای محیطی (Secrets) ----------
INOREADER_APP_ID = os.environ["INOREADER_APP_ID"]
INOREADER_APP_KEY = os.environ["INOREADER_APP_KEY"]
INOREADER_REFRESH_TOKEN = os.environ["INOREADER_REFRESH_TOKEN"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# اگر می‌خوای فقط یک پوشه/تگ خاص از اینوریدر رو بخونی، این رو ست کن
# مثال: "user/-/label/MyFolder"  یا خالی بذار برای کل reading list
INOREADER_STREAM_ID = os.environ.get("INOREADER_STREAM_ID", "user/-/state/com.google/reading-list")

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state.json")
MAX_ITEMS_PER_RUN = 20  # حداکثر تعداد پستی که در هر اجرا فرستاده می‌شه (جلوگیری از اسپم)
SUMMARY_MAX_LEN_SOURCE = 1500  # قبل از فرستادن به DeepSeek، متن منبع تا این حد کوتاه می‌شه

INOREADER_TOKEN_URL = "https://www.inoreader.com/oauth2/token"
INOREADER_STREAM_URL = "https://www.inoreader.com/reader/api/0/stream/contents/{stream_id}"
TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

CATEGORIES = ["سیاسی", "اجتماعی", "فرهنگی", "ورزشی", "نظامی"]


def get_access_token():
    """با refresh_token یک access_token تازه می‌گیرد."""
    resp = requests.post(
        INOREADER_TOKEN_URL,
        data={
            "client_id": INOREADER_APP_ID,
            "client_secret": INOREADER_APP_KEY,
            "refresh_token": INOREADER_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_published": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_items(access_token):
    url = INOREADER_STREAM_URL.format(stream_id=INOREADER_STREAM_ID)
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"n": 50},  # آخرین ۵۰ آیتم
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def translate_and_categorize(title, summary):
    """
    متن انگلیسی (یا هر زبان دیگه) رو با DeepSeek ترجمه، خلاصه و دسته‌بندی می‌کنه.
    خروجی: dict با کلیدهای title, summary, category
    """
    source_text = f"عنوان: {title}\n\nمتن: {summary}"[:SUMMARY_MAX_LEN_SOURCE]

    system_prompt = (
        "تو یک مترجم و خبرنگار حرفه‌ای فارسی‌زبان هستی. متن خبری (که ممکنه به "
        "انگلیسی یا هر زبان دیگه‌ای باشه) در ادامه داده می‌شه. وظیفه تو:\n"
        "۱. عنوان خبر رو به فارسیِ روان و رسمی ترجمه کن (نه بازنویسی، ترجمه دقیق).\n"
        "۲. یک خلاصه‌ی ۳ تا ۴ جمله‌ای از متن خبر، به زبان فارسی، بنویس.\n"
        "۳. دقیقاً یکی از این پنج دسته رو بر اساس موضوع خبر انتخاب کن: "
        f"{', '.join(CATEGORIES)}\n\n"
        "مهم: title و summary باید هر دو کاملاً به زبان فارسی نوشته بشن، حتی اگه "
        "متن ورودی انگلیسی باشه. هیچ کلمه‌ی انگلیسی (به‌جز اسم خاص) نباید توشون باشه.\n\n"
        "خروجی رو فقط و فقط به‌صورت یک JSON معتبر و دقیقاً با همین سه کلید بده، "
        "بدون هیچ توضیح یا متن اضافه قبل یا بعدش:\n"
        '{"title": "عنوان فارسی اینجا", "summary": "خلاصه فارسی اینجا", "category": "یکی از پنج دسته"}'
    )

    resp = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": source_text},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    if not resp.ok:
        print(f"خطای DeepSeek API: {resp.status_code} {resp.text}", file=sys.stderr)
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]
    print(f"--- پاسخ خام DeepSeek ---\n{content}\n------------------------")

    # بعضی مدل‌ها با وجود response_format، متن رو تو ```json ... ``` می‌پیچن
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?", "", cleaned).rsplit("```", 1)[0].strip()

    data = json.loads(cleaned)

    fa_title = (data.get("title") or "").strip()
    fa_summary = (data.get("summary") or "").strip()
    category = (data.get("category") or "").strip()

    if not fa_title or not fa_summary:
        raise ValueError(f"پاسخ DeepSeek کلیدهای لازم رو نداشت: {data}")

    if category not in CATEGORIES:
        category = "اجتماعی"  # دسته‌ی پیش‌فرض اگه مدل چیز عجیبی برگردوند

    return {
        "title": fa_title,
        "summary": fa_summary,
        "category": category,
    }


def build_message(item, translated):
    link = ""
    if item.get("canonical"):
        link = item["canonical"][0].get("href", "")
    elif item.get("alternate"):
        link = item["alternate"][0].get("href", "")

    feed_title = item.get("origin", {}).get("title", "") or "منبع خبر"

    hashtag = f"#{translated['category']}"
    title = html.escape(translated["title"])
    summary = html.escape(translated["summary"])

    parts = [hashtag, f"<b>{title}</b>", summary]

    if link:
        source_line = f'منبع: <a href="{html.escape(link)}">{html.escape(feed_title)}</a>'
        parts.append(source_line)

    return "\n\n".join(parts)


def send_to_telegram(text):
    resp = requests.post(
        TELEGRAM_SEND_URL.format(token=TELEGRAM_BOT_TOKEN),
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"خطا در ارسال به تلگرام: {resp.status_code} {resp.text}", file=sys.stderr)
    resp.raise_for_status()


def main():
    state = load_state()
    last_published = state.get("last_published", 0)

    access_token = get_access_token()
    items = fetch_items(access_token)

    # آیتم‌های جدیدتر از آخرین published، مرتب‌شده از قدیم به جدید
    new_items = [it for it in items if it.get("published", 0) > last_published]
    new_items.sort(key=lambda it: it.get("published", 0))

    if not new_items:
        print("هیچ آیتم جدیدی نیست.")
        return

    new_items = new_items[:MAX_ITEMS_PER_RUN]

    max_published = last_published
    for item in new_items:
        try:
            title = strip_html(item.get("title", "بدون عنوان"))
            summary_html = item.get("summary", {}).get("content", "")
            summary = strip_html(summary_html)

            translated = translate_and_categorize(title, summary)
            message = build_message(item, translated)
            send_to_telegram(message)

            print(f"ارسال شد: {translated['title'][:60]}")
            max_published = max(max_published, item.get("published", 0))
            time.sleep(2)  # جلوگیری از rate-limit تلگرام و دیپ‌سیک
        except Exception as e:
            print(f"خطا در پردازش آیتم: {e}", file=sys.stderr)

    state["last_published"] = max_published
    save_state(state)


if __name__ == "__main__":
    main()
