import feedparser
import requests
import json
import os
import re
import html
from html.parser import HTMLParser
from datetime import datetime

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
POSTED_FILE = "posted_links.json"

RSS_FEEDS = {
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Valor Econômico": "https://valor.globo.com/rss/",
    "BeInCrypto": "https://br.beincrypto.com/feed/"
}

# Cores por fonte
CORES = {
    "InfoMoney":      0x2ecc71,  # verde
    "CoinDesk":       0xf39c12,  # laranja
    "Valor Econômico": 0xe74c3c, # vermelho
    "BeInCrypto":     0x9b59b6,  # roxo
}


class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts).strip()


def strip_html(raw: str) -> str:
    """Remove todas as tags HTML, decodifica entidades e limpa boilerplate."""
    raw = html.unescape(raw or "")
    parser = _TagStripper()
    parser.feed(raw)
    text = parser.get_text()
    # Colapsa espaços múltiplos
    text = re.sub(r"\s+", " ", text).strip()
    # Remove boilerplate PT: "O artigo X apareceu primeiro em Y."
    text = re.sub(r"\s*O artigo .+? apareceu primeiro em .+?\.", "", text, flags=re.DOTALL).strip()
    # Remove boilerplate EN: "The post X appeared first on Y."
    text = re.sub(r"\s*The post .+? appeared first on .+?\.", "", text, flags=re.DOTALL).strip()
    # Remove boilerplate BeInCrypto PT: "X foi visto pela primeira vez em Y."
    text = re.sub(r"\s*\S.+? foi visto pela primeira vez em .+?\.", "", text, flags=re.DOTALL).strip()
    return text


def extract_image(entry) -> str | None:
    """Tenta extrair URL de imagem de diferentes campos do RSS."""
    # 1. media:thumbnail (YouTube, BeInCrypto, etc.)
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url", "")
        if url:
            return html.unescape(url)

    # 2. media:content com tipo imagem
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            if m.get("type", "").startswith("image"):
                url = m.get("url", "")
                if url:
                    return html.unescape(url)

    # 3. Enclosure (podcasts/feeds antigos)
    for link in getattr(entry, "links", []):
        if link.get("type", "").startswith("image"):
            return html.unescape(link.get("href", ""))

    # 4. Extrai src da primeira <img> no summary (InfoMoney, Valor, etc.)
    summary_raw = getattr(entry, "summary", "") or ""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary_raw, re.IGNORECASE)
    if match:
        url = html.unescape(match.group(1))
        # Ignora imagens de rastreamento (< 5px)
        if "1x1" not in url and "pixel" not in url.lower():
            return url

    return None


# Carrega links já postados (persiste entre execuções via git)
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r") as f:
        postados = set(json.load(f))
else:
    postados = set()

novos_count = 0

for nome, url in RSS_FEEDS.items():
    feed = feedparser.parse(url)
    for entry in feed.entries[:3]:
        link = entry.get("link", "")
        if not link or link in postados:
            continue

        titulo = (entry.get("title") or "Sem título")[:256]
        descricao_raw = entry.get("summary") or entry.get("content", [{}])[0].get("value", "")
        descricao = strip_html(descricao_raw)[:300]
        if descricao:
            descricao += "..."

        image_url = extract_image(entry)

        embed = {
            "title": titulo,
            "url": link,
            "description": descricao or None,
            "color": CORES.get(nome, 0x3498db),
            "author": {"name": nome},
            "footer": {"text": f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')} BRT"},
        }

        if image_url:
            embed["image"] = {"url": image_url}

        payload = {"embeds": [embed]}
        r = requests.post(WEBHOOK_URL, json=payload)

        if r.status_code in (200, 204):
            print(f"✅ [{nome}] {titulo[:60]}")
            postados.add(link)
            novos_count += 1
        else:
            print(f"❌ [{nome}] erro {r.status_code}: {titulo[:60]}")

if novos_count == 0:
    print("Nenhuma notícia nova encontrada.")
else:
    print(f"\n✅ {novos_count} notícias postadas.")

# Salva links atualizados para o próximo commit
with open(POSTED_FILE, "w") as f:
    json.dump(list(postados), f, indent=2)
