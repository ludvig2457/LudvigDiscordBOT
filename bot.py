import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")  # Получаем токен из .env

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Явный путь к ffmpeg.exe
FFMPEG_PATH = r"C:\\ffmpeg-7.1.1-full_build\\bin\\ffmpeg.exe"

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
    'executable': FFMPEG_PATH
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# ---------------- Команды ------------------

@bot.command(name='войти')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Подключился к {channel.name}')
    else:
        await ctx.send('Ты должен быть в голосовом канале!')

@bot.command(name='выйти')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Отключился от голосового канала.')
    else:
        await ctx.send('Я не в голосовом канале.')

@bot.command(name='играть')
async def play(ctx, *, url):
    if not ctx.author.voice:
        await ctx.send('Ты должен быть в голосовом канале!')
        return

    voice = ctx.voice_client
    if not voice:
        voice = await ctx.author.voice.channel.connect()
    elif voice.is_playing():
        voice.stop()

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        voice.play(player, after=lambda e: print(f'Ошибка плеера: {e}') if e else None)

    await ctx.send(f'Сейчас играет: {player.title}')

@bot.command(name='пауза')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Музыка на паузе.')
    else:
        await ctx.send('Музыка не играет.')

@bot.command(name='продолжить')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Музыка продолжена.')
    else:
        await ctx.send('Музыка не на паузе.')

@bot.command(name='стоп')
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send('Музыка остановлена.')
    else:
        await ctx.send('Музыка не играет.')

# ---------------- Игра: Угадай число ------------------

games = {}

@bot.command(name='угадай')
async def guess_number(ctx):
    if ctx.author.id in games:
        await ctx.send('Ты уже играешь! Попробуй угадать число.')
        return

    number = random.randint(1, 100)
    games[ctx.author.id] = number
    await ctx.send('Я загадал число от 1 до 100. Напиши число в чат, чтобы угадать!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author.id in games:
        try:
            guess = int(message.content)
            number = games[message.author.id]

            if guess < number:
                await message.channel.send('Слишком маленькое число!')
            elif guess > number:
                await message.channel.send('Слишком большое число!')
            else:
                await message.channel.send(f'Поздравляю, {message.author.mention}! Ты угадал число {number}!')
                del games[message.author.id]
        except ValueError:
            pass

    await bot.process_commands(message)

# ---------------- Прочее ------------------

@bot.event
async def on_ready():
    print(f'Бот запущен как {bot.user}')

# Запуск
bot.run(TOKEN)
