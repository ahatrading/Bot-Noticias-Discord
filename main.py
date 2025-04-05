import discord
from discord.ext import tasks, commands
import feedparser
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

RSS_FEEDS = {
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Valor Econômico": "https://valor.globo.com/rss/",
    "BeInCrypto": "https://br.beincrypto.com/feed/"
}

noticias_postadas = set()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    checar_noticias.start()


@tasks.loop(minutes=30)
async def checar_noticias():
    print("⏰ Executando checagem de notícias...")
    canal = bot.get_channel(CHANNEL_ID)

    if not canal:
        print("❌ Canal não encontrado.")
        return
    else:
        print(f"✅ Canal encontrado: {canal.name}")

    for nome, url in RSS_FEEDS.items():
        print(f"🔎 Verificando feed: {nome}")
        feed = feedparser.parse(url)
        for noticia in feed.entries[:3]:
            print(f"📄 Título da notícia: {noticia.title}")
            if noticia.link not in noticias_postadas:
                embed = discord.Embed(title=noticia.title,
                                      url=noticia.link,
                                      description=noticia.summary[:200] +
                                      "...",
                                      color=0x00ff99)
                embed.set_author(name=nome)
                await canal.send(embed=embed)
                noticias_postadas.add(noticia.link)
                print(f"✅ Notícia enviada: {noticia.title}")
            else:
                print(f"🔁 Já postado: {noticia.title}")


from keep_alive import keep_alive

keep_alive()  # Inicia o servidor web
bot.run(TOKEN)
