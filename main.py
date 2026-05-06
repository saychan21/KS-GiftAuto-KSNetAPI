import requests
import time
import random
import os
import csv
import cloudscraper
from playwright.sync_api import sync_playwright

CSV_URL = "https://docs.google.com/spreadsheets/d/1c2QmtlaBNsQ32j7JWly-ayigbkmfireBUisUEzxaJTY/export?format=csv&gid=561406276"
USED_FILE = "used_pairs.txt"

PARALLEL_PAGES = 3


# -----------------------
# used_pairs 관리
# -----------------------
def load_used_pairs():
    if not os.path.exists(USED_FILE):
        return set()
    with open(USED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)


def save_used_pair(code, player):
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{code}|{player}\n")


# -----------------------
# giftcode (API)
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

    print("Giftcodes(API):", codes)
    return codes


# -----------------------
# player (Google Sheet B열)
# -----------------------
def get_players():
    try:
        res = requests.get(CSV_URL, timeout=10)

        if res.status_code != 200:
            print("❌ CSV 요청 실패")
            return []

        content = res.content.decode("utf-8", errors="ignore")
        reader = csv.reader(content.splitlines())

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

        print("Players:", players)
        return players

    except Exception as e:
        print("❌ CSV 처리 실패:", e)
        return []


# -----------------------
# 딜레이
# -----------------------
def human_delay(a=1.0, b=2.0):
    time.sleep(random.uniform(a, b))


# -----------------------
# 클릭
# -----------------------
def js_click_by_text(page, text):
    page.evaluate(f"""
        [...document.querySelectorAll('button')]
        .find(btn => btn.innerText.includes('{text}'))?.click();
    """)


def safe_click(page, text):
    try:
        page.click(f"text={text}", timeout=5000)
    except:
        js_click_by_text(page, text)


# -----------------------
# Redeem
# -----------------------
def redeem(page, player_id, giftcode, step_id):
    base = f"screenshots/{step_id}_{player_id}_{giftcode}"

    page.goto("https://ks-giftcode.centurygame.com/")
    page.screenshot(path=f"{base}_1_home.png")

    page.wait_for_selector("input")
    page.fill("input", player_id)
    page.screenshot(path=f"{base}_2_player.png")

    human_delay()

    safe_click(page, "Login")
    human_delay()
    page.screenshot(path=f"{base}_3_login.png")

    page.wait_for_selector("input[placeholder='Enter Gift Code']")
    page.fill("input[placeholder='Enter Gift Code']", giftcode)
    page.screenshot(path=f"{base}_4_code.png")

    human_delay()

    safe_click(page, "Confirm")
    human_delay()
    page.screenshot(path=f"{base}_5_done.png")


# -----------------------
# 실행
# -----------------------
def run():
    giftcodes = get_active_codes()
    players = get_players()

    if not giftcodes or not players:
        print("❌ 데이터 없음")
        return

    used_pairs = load_used_pairs()
    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        pages = [browser.new_page() for _ in range(PARALLEL_PAGES)]

        step = 0
        page_index = 0

        for code in giftcodes:
            for player in players:

                pair_key = f"{code}|{player}"

                if pair_key in used_pairs:
                    print(f"[SKIP] {pair_key}")
                    continue

                step += 1

                page = pages[page_index]
                page_index = (page_index + 1) % PARALLEL_PAGES

                for retry in range(3):
                    try:
                        print(f"[TRY] {code} -> {player}")

                        redeem(page, player, code, step)

                        print(f"[SUCCESS] {code} -> {player}")
                        save_used_pair(code, player)
                        break

                    except Exception as e:
                        print(f"[ERROR] {e}")
                        time.sleep(2)
                else:
                    print(f"[FAIL] {code} -> {player}")

                human_delay()

        browser.close()


if __name__ == "__main__":
    run()
