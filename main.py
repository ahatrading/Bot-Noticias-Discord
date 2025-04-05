import discord
from discord.ext import commands
import feedparser
import os
from datetime import datetime, time, timedelta
import asyncio
from keep_alive import keep_alive

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

# Horários fixos (horário de Brasília)
horarios_envio = [
    time(21, 0),   # Sessão Ásia
    time(4, 0),    # Londres Abertura
    time(10, 0),   # NY Abertura
    time(12, 0),   # Londres Fechamento
    time(17, 0),   # NY Fechamento
    time(20, 30),  # Pós-CBDC
]

@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")
    bot.loop.create_task(agendar_envios())

async def agendar_envios():
    while True:
        agora = datetime.now()
        proximo_horario = min(
            [datetime.combine(agora.date(), h) for h in horarios_envio if datetime.combine(agora.date(), h) > agora] +
            [datetime.combine(agora.date() + timedelta(days=1), horarios_envio[0])]
        )
        tempo_espera = (proximo_horario - agora).total_seconds()
        print(f"⏳ Próximo envio agendado para: {proximo_horario.strftime('%d/%m/%Y %H:%M')}")
        await asyncio.sleep(tempo_espera)
        await checar_noticias()

async def checar_noticias():
    canal = bot.get_channel(CHANNEL_ID)
    if not canal:
        print("❌ Canal não encontrado.")
        return

    for nome, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for noticia in feed.entries[:3]:
            if noticia.link not in noticias_postadas:
                embed = discord.Embed(
                    title=noticia.title,
                    url=noticia.link,
                    description=noticia.summary[:200] + "...",
                    color=0x3498db
                )
                embed.set_author(name=nome)
                embed.set_footer(text=f"🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                await canal.send(embed=embed)
                noticias_postadas.add(noticia.link)

keep_alive()
bot.run(TOKEN)
