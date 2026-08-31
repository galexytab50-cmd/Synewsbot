# Inoreader → Telegram Bot

هر ۱ ساعت یک‌بار اجرا می‌شه، آیتم‌های جدید فید اینوریدرت رو می‌خونه و به‌شکل
«عنوان + خلاصه کوتاه + لینک» تو کانال تلگرامت پست می‌کنه. کاملاً روی
GitHub Actions اجرا می‌شه، نیازی به سرور نداری.

## مرحله ۱ — ساخت اپلیکیشن در اینوریدر

1. برو به: https://www.inoreader.com/developers/
2. یک اپلیکیشن جدید بساز.
3. مقدار **Redirect URI** رو دقیقاً بذار: `http://localhost`
4. مقادیر **App ID** و **App Key** رو یادداشت کن.

## مرحله ۲ — گرفتن Refresh Token (فقط یک‌بار)

روی کامپیوتر خودت (نه گیت‌هاب):

```bash
pip install requests
python scripts/get_refresh_token.py
```

طبق راهنمای اسکریپت پیش برو. در آخر سه مقدار بهت می‌ده:
`INOREADER_APP_ID`, `INOREADER_APP_KEY`, `INOREADER_REFRESH_TOKEN`

## مرحله ۳ — ساخت ربات تلگرام

1. تو تلگرام برو پیش [@BotFather](https://t.me/BotFather) و دستور `/newbot` رو بزن.
2. توکن ربات رو یادداشت کن (`TELEGRAM_BOT_TOKEN`).
3. ربات رو به کانالت اضافه کن و **ادمین** کن (با دسترسی ارسال پیام).
4. برای گرفتن `TELEGRAM_CHAT_ID`:
   - اگه کانالت **پابلیک** هست: از همون یوزرنیم استفاده کن، مثلاً `@my_channel`
   - اگه **پرایوت** هست: یک پیام تو کانال بفرست، بعد این آدرس رو باز کن
     (به‌جای `<TOKEN>` توکن ربات رو بذار):
     `https://api.telegram.org/bot<TOKEN>/getUpdates`
     و مقدار `"chat":{"id": ...}` رو (یه عدد منفی بزرگ) بردار.

## مرحله ۴ — تنظیم Secrets تو گیت‌هاب

تو ریپازیتوری برو به:
**Settings → Secrets and variables → Actions → New repository secret**

این ۵ مقدار رو اضافه کن:

| Name | مقدار |
|---|---|
| `INOREADER_APP_ID` | از مرحله ۱ |
| `INOREADER_APP_KEY` | از مرحله ۱ |
| `INOREADER_REFRESH_TOKEN` | از مرحله ۲ |
| `TELEGRAM_BOT_TOKEN` | از مرحله ۳ |
| `TELEGRAM_CHAT_ID` | از مرحله ۳ |

## مرحله ۵ — فعال‌سازی

1. این پوشه رو تو یه ریپازیتوری جدید گیت‌هاب push کن.
2. برو به تب **Actions** و اگه لازم بود workflow رو Enable کن.
3. می‌تونی از همون‌جا با دکمه‌ی **Run workflow** یک بار دستی اجراش کنی تا تست بشه.
4. بعد از اون، خودش هر ساعت (دقیقه‌ی صفر) اجرا می‌شه.

⚠️ **نکته مهم:** چون `state.json` مقدارش صفره، در اولین اجرا ربات جدیدترین
آیتم‌های موجود (حداکثر ۲۰ تا) رو به‌عنوان بک‌فیل می‌فرسته. اگه نمی‌خوای این
اتفاق بیفته، قبل از اولین اجرا مقدار `last_published` تو `state.json` رو
به زمان الان (Unix timestamp) تغییر بده.

## تنظیمات قابل تغییر (داخل `scripts/bot.py`)

- `INOREADER_STREAM_ID`: اگه می‌خوای فقط یه پوشه/تگ خاص از اینوریدر خونده
  بشه (نه کل reading list)، این متغیر محیطی رو تو workflow اضافه کن،
  مثلاً: `user/-/label/AI News`
- `MAX_ITEMS_PER_RUN`: حداکثر تعداد پست در هر اجرا (پیش‌فرض ۲۰)
- `SUMMARY_MAX_LEN`: طول خلاصه (پیش‌فرض ۴۰۰ کاراکتر)
- بازه‌ی زمانی اجرا: خط `cron` تو فایل
  `.github/workflows/inoreader-to-telegram.yml`
