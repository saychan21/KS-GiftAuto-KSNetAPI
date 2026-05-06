import requests
import cloudscraper
import csv
import os
import time
import random
import shutil
from io import StringIO
from playwright.sync_api import sync_playwright

CSV_URL = "https://docs.google.com/spreadsheets/d/1c2QmtlaBNsQ32j7JWly-ayigbkmfireBUisUEzxaJTY/export?format=csv&gid=561406276"
USED_FILE = "used_pairs.txt"

# -----------------------
# 1. giftcode (API)
# -----------------------
def get_active_codes():
    scraper = cloudscraper.create_scraper()
    res = scraper.get("https://kingshot.net/api/gift-codes")
    data = res.json()

    codes = [
        item["code"]
        for item in data["data"]["giftCodes"]
        if item["expiresAt"] is None
    ]

    print("🎁 GiftCodes:", codes)
    return codes


# -----------------------
# 2. player_id (B열)
# -----------------------
def get_players():
    res = requests.get(CSV_URL)
    f = StringIO(res.text)
    reader = csv.reader(f)

    players = set()

    for i, row in enumerate(reader):
        if i < 1:
            continue
        if len(row) < 2:
            continue

        player = row[1].strip()

        if player and player.isdigit():
            players.add(player)

    players = list(players)
    print("👤 Players:", players)
    return players


# -----------------------
# 3. 중복 관리
# -----------------------
def load_used():
    if not os.path.exists(USED_FILE):
        return set()
    with open(USED_FILE, "r") as f:
        return set(f.read().splitlines())


def save_used(pair):
    with open(USED_FILE, "a") as f:
        f.write(pair + "\n")


# -----------------------
# 4. 딜레이
# -----------------------
def delay():
    time.sleep(random.uniform(1.0, 2.0))


# -----------------------
# 5. redeem + 캡처
# -----------------------
def redeem(page, player, code, step):
    base = f"screenshots/{step}_{player}_{code}"

    page.goto("https://ks-giftcode.centurygame.com/")
    page.screenshot(path=f"{base}_1_home.png")

    page.fill("input", player)
    page.screenshot(path=f"{base}_2_player.png")

    delay()

    page.click("text=Login")
    page.screenshot(path=f"{base}_3_login.png")

    page.wait_for_selector("input[placeholder='Enter Gift Code']")
    page.fill("input[placeholder='Enter Gift Code']", code)
    page.screenshot(path=f"{base}_4_code.png")

    delay()

    page.click("text=Confirm")
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{base}_5_done.png")


# -----------------------
# 6. ZIP 생성
# -----------------------
def zip_screenshots():
    if os.path.exists("screenshots"):
        shutil.make_archive("screenshots_backup", "zip", "screenshots")
        print("📦 screenshots_backup.zip 생성 완료")


# -----------------------
# 7. 실행
# -----------------------
def run():
    codes = get_active_codes()
    players = get_players()
    used = load_used()

    if not codes or not players:
        print("❌ 데이터 없음")
        return

    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        step = 0

        for code in codes:
            for player in players:

                key = f"{code}|{player}"

                if key in used:
                    print(f"[SKIP] {key}")
                    continue

                step += 1

                try:
                    print(f"[TRY] {key}")

                    redeem(page, player, code, step)

                    print(f"[SUCCESS] {key}")
                    save_used(key)

                except Exception as e:
                    print(f"[ERROR] {key} → {e}")

                delay()

        browser.close()

    # 🔥 실행 끝나면 ZIP 생성
    zip_screenshots()


if __name__ == "__main__":
    run()
