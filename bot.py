import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime

with open("config.json") as f:
    config = json.loads(f.read())
bot = commands.Bot(command_prefix="!")
cogs = ['cogs.remind']


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(bot.command_prefix)
    print('------')
    for cog in cogs:
        bot.load_extension(cog)


# @bot.event
# async def on_message(msg):
#     prefix = "!"
#     if msg.content[0] == (prefix):
#         msg.content = msg.content[1:]
#     if (msg.content == "ping"):
#         await msg.channel.send("pong")


@bot.command()
async def ping(msg):
    print("HEII")
    await msg.channel.send(datetime.now().strftime("%A %d. %B %Y -> %H:%M:%S"))
    return (await msg.channel.send("pong"))


@bot.command()
async def date(msg, d):
    try:
        a = datetime.strptime(d, '%Y:%H:%M')
        print(a.ctime())
    except ValueError:
        return (await msg.channel.
                send("{} is wrong format or out of range"
                     .format(d)))


bot.run(config["token"])
