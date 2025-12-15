from flask import Flask, request
from pybit.unified_trading import HTTP
import re
from datetime import datetime
import os

app = Flask(__name__)

# ✅ Bybit API 設定
session = HTTP(
    api_key="Qi3ZcjuY4WnPuqi5rK",
    api_secret="5KpWwkeoYsGp6r17tgBTNFNAcqtEzO8QGG1G",
    testnet=True  # 若你用正式帳戶請改成 False
)

DEFAULT_MAX_LOSS = 5  # 預設最大虧損 USDT

# ✅ 訊號解析函式
def parse_signal(text):
    if "小多單" in text:
        side = "Buy"
        signal_type = "小多單"
    elif "多單" in text:
        side = "Buy"
        signal_type = "多單"
    elif "小空單" in text:
        side = "Sell"
        signal_type = "小空單"
    elif "空單" in text:
        side = "Sell"
        signal_type = "空單"
    else:
        return None, None, None, None, None, None

    entry = re.search(r"進場[:：]?\s*([\d.]+)", text)
    sl = re.search(r"SL[:：]?\s*([\d.]+)", text)
    tp1 = re.search(r"TP1[:：]?\s*([\d.]+)", text)
    risk = re.search(r"(風險|risk)[:：]?\s*([\d.]+)", text, re.IGNORECASE)

    entry_price = float(entry.group(1)) if entry else None
    stop_loss = float(sl.group(1)) if sl else None
    take_profit = float(tp1.group(1)) if tp1 else None
    max_loss = float(risk.group(2)) if risk else DEFAULT_MAX_LOSS

    return signal_type, side, entry_price, stop_loss, take_profit, max_loss

# ✅ 首頁測試用
@app.route('/')
def home():
    return '✅ Flask 伺服器已啟動'

# ✅ webhook 接收訊號
@app.route('/webhook', methods=['POST'])
def webhook():
    print("🚨 webhook 被呼叫了")
    data = request.get_data(as_text=True).strip()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n📩 [{timestamp}] 收到訊號：{data}")

    signal_type, side, entry, sl, tp, max_loss = parse_signal(data)
    if not signal_type or not entry or not sl or not tp:
        print("⚠️ 無法解析訊號")
        return 'Parse error'

    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        print("⚠️ 風險點數為 0，無法計算")
        return 'Invalid SL'

    qty = round(max_loss / risk_per_unit, 3)
    rr_ratio = round(abs(tp - entry) / risk_per_unit, 2)
    print(f"📊 盈虧比：{rr_ratio}（TP1: {tp}, SL: {sl}）")
    print(f"📐 自動計算倉位：{qty} 張（最大虧損 {max_loss} USDT）")

    try:
        response = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side=side,
            order_type="Limit",
            price=str(entry),
            qty=str(qty),
            take_profit=str(round(tp, 2)),
            stop_loss=str(round(sl, 2)),
            time_in_force="GoodTillCancel"
        )
        print(f"✅ [{signal_type}] 下單成功：{response}")
    except Exception as e:
        print("❌ 下單失敗：", e)
        if hasattr(e, 'args') and len(e.args) > 0:
            print("🔍 錯誤細節：", e.args[0])

    return 'OK'

# ✅ 啟動伺服器
if __name__ == '__main__':
    public_url = os.environ.get("REPLIT_WEB_URL")
    if public_url:
        print(f"🌐 公開 webhook 網址：{public_url}webhook")
    else:
        print("⚠️ 無法取得公開網址，請手動點右上角的 Open in a new tab")
    app.run(host='0.0.0.0', port=3000)
