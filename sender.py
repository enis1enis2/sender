import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

URL = "https://www.aski.gov.tr/tr/Kesinti.aspx"
CHECK_INTERVAL = 60  # saniye
NTFY_URL = "https://ntfy.sh/S3uK3s1nt1B1ld1r1m1"

last_state = None  # "kesinti" veya "normal"

def parse_tr_datetime(s):
    date_str, time_str = s.split()
    day, month, year = map(int, date_str.split("."))
    h, m, sec = map(int, time_str.split(":"))
    return datetime(year, month, day, h, m, sec)

def get_keciören_times():
    try:
        resp = requests.get(URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("❌ Site alınamadı:", e)
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    paragraphs = soup.find_all("p")

    for p in paragraphs:
        text = p.get_text()
        if "KEÇİÖREN" in text.upper():
            b_tags = p.find_all("b")
            start_str = end_str = None
            for b in b_tags:
                label = b.get_text().strip().lower()
                next_text = b.next_sibling.strip() if b.next_sibling else ""
                if "arıza tarihi" in label:
                    start_str = next_text
                elif "tamir tarihi" in label:
                    end_str = next_text
            if start_str and end_str:
                return start_str, end_str
    return None, None

def send_ntfy_notification(title, message):
    try:
        body = f"{title}\n{message}".encode("utf-8")  # 🔥 burada latin-1 engelleniyor
        headers = {
            "Title": title.encode("utf-8"),
            "Priority": "default",
            "Content-Type": "text/plain; charset=utf-8"
        }
        requests.post(NTFY_URL, data=body, headers=headers)
        print(f"📢 Bildirim gönderildi: {title}")
    except Exception as e:
        print("⚠️ Bildirim gönderilemedi:", e)

def main():
    global last_state
    print("💧 ASKI Keçiören su kesintisi izleyici başlatıldı...")

    while True:
        start_str, end_str = get_keciören_times()

        if start_str and end_str:
            now = datetime.now()
            try:
                start_dt = parse_tr_datetime(start_str)
                end_dt = parse_tr_datetime(end_str)
            except Exception:
                print("⚠️ Tarih biçimi okunamadı.")
                time.sleep(CHECK_INTERVAL)
                continue
            
            if start_dt <= now <= end_dt:
                if last_state != "kesinti":
                    send_ntfy_notification(
                        "🚨 KEÇİÖREN'de su kesintisi başladı",
                        f"Arıza: {start_str}\nTamir: {end_str}"
                    )
                    last_state = "kesinti"
                else:
                    print("⏸ Hâlâ aynı kesinti, tekrar bildirim yok.")
            else:
                if last_state == "kesinti" and end_dt < now:
                    send_ntfy_notification(
                        "✅ KEÇİÖREN'de su geri geldi",
                        f"Arıza: {start_str}\nTamir: {end_str}\nSu kesintisi sona erdi."
                    )
                    last_state = "normal"
                else:
                    print("💧 Su mevcut, kesinti yok.")
        else:
            print("⚠️ Keçiören kesintisi bulunamadı.")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
