#!/usr/bin/env python3
"""
این اسکریپت رو فقط یک‌بار، روی کامپیوتر خودت (نه گیت‌هاب) اجرا کن
تا refresh_token بگیری. بعدش دیگه لازمش نداری.

مراحل:
1. برو تو https://www.inoreader.com/developers/ یک اپلیکیشن بساز
   و مقدار Redirect URI رو دقیقاً بذار: http://localhost
   (App ID و App Key رو یادداشت کن)

2. این اسکریپت رو اجرا کن:
   pip install requests
   python get_refresh_token.py

3. طبق راهنمایی که چاپ می‌شه، لینک رو تو مرورگر باز کن، وارد اینوریدر شو
   و اجازه بده. مرورگر تو رو به یه آدرس مثل این می‌بره که خطای
   "این سایت در دسترس نیست" می‌ده - عیبی نداره:
   http://localhost/?code=XXXXXXXX

4. مقدار بعد از code= رو کپی کن و تو ترمینال بهش بده.

5. اسکریپت refresh_token رو چاپ می‌کنه. اون رو تو GitHub Secrets
   با اسم INOREADER_REFRESH_TOKEN ذخیره کن.
"""

import requests

AUTH_URL = "https://www.inoreader.com/oauth2/auth"
TOKEN_URL = "https://www.inoreader.com/oauth2/token"
REDIRECT_URI = "http://localhost"


def main():
    app_id = input("App ID رو وارد کن: ").strip()
    app_key = input("App Key رو وارد کن: ").strip()

    auth_link = (
        f"{AUTH_URL}?client_id={app_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=read"
        f"&state=xyz"
    )

    print("\nاین لینک رو تو مرورگر باز کن و اجازه دسترسی بده:\n")
    print(auth_link)
    print("\nبعد از تایید، از آدرس بار مرورگر، مقدار بعد از code= رو کپی کن.")

    code = input("\ncode رو اینجا وارد کن: ").strip()

    resp = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": app_id,
            "client_secret": app_key,
            "scope": "read",
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    print("\n✅ موفق شد! این مقادیر رو تو GitHub Secrets ذخیره کن:\n")
    print(f"INOREADER_APP_ID = {app_id}")
    print(f"INOREADER_APP_KEY = {app_key}")
    print(f"INOREADER_REFRESH_TOKEN = {data['refresh_token']}")


if __name__ == "__main__":
    main()
