import requests

url = "https://discord.com/api/webhooks/1492518777651204238/TPbzx_u5vH1d8j7dN0cdF88f1nlRgkGXkefXr2dip1Qm0k51b0hubFVID39-bPQmDWwH"

# Тест 1: Простое сообщение
r = requests.post(url, json={"content": "MMFLIP Webhook Test"}, timeout=10)
print(f"Simple message — Status: {r.status_code}, Body: {r.text[:200]}")

# Тест 2: Embed как в игре
payload = {
    "username": "MMFLIP",
    "embeds": [{
        "title": "Game #999 — Test",
        "description": "**Winner:** TestPlayer\n**Loser:** TestPlayer2\n**Total Pot:** 100 SV",
        "color": 0x00ff9d,
        "fields": [
            {"name": "Player 1", "value": "TestPlayer — 50 SV", "inline": True},
            {"name": "Player 2", "value": "TestPlayer2 — 50 SV", "inline": True},
        ],
        "footer": {"text": "MMFLIP | Provably Fair"}
    }]
}
r2 = requests.post(url, json=payload, timeout=10)
print(f"Embed message — Status: {r2.status_code}, Body: {r2.text[:200]}")
