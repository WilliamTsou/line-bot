import requests
from bs4 import BeautifulSoup
import sys
import io

# 確保 stdout 使用 UTF-8 編碼，避免 Windows (cp950) 無法輸出某些字元
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

url = "https://tw.stock.yahoo.com/quote/NZDTWD=X"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
print("成功取得資料！" if response.status_code == 200 else "失敗")

soup = BeautifulSoup(response.text, "html.parser")

# 兼容不同情況：先找 trend-down；若找不到就找 trend-up
price_tag = soup.find(
    "span",
    attrs={
        "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-down)"
    },
)

if not price_tag:
    price_tag = soup.find(
        "span",
        attrs={
            "class": "Fz(32px) Fw(b) Lh(1) Mend(4px) D(f) Ai(c) C($c-trend-up)"
        },
    )

if price_tag:
    print(f"目前的紐西蘭幣對台幣匯率是：{price_tag.text}")
else:
    print("找不到匯率資料 QQ")
