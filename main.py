from discord.ext import commands
import discord
import os

import Settings

activity = discord.Activity(type=discord.ActivityType.watching, name="Kush Services | .gg/Kushboost")

class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        for file in os.listdir("./Cogs"):
            if file.endswith(".py"):
                try:
                    await self.load_extension(f"Cogs.{file[:-3]}")
                except Exception as error:
                    print(f"Failed to load extension {file[:-3]}")
                    print(error)

bot = Bot(command_prefix=commands.when_mentioned, intents=discord.Intents.default())

@bot.event
async def on_ready():
    print("done")
    activity = discord.Game(name=".gg/Kushhh", type=2)
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Activity(type=discord.ActivityType.watching, name=".gg/jxmes "))

@bot.command()
async def sync(ctx, args = None):
    if not args:
        args = str(ctx.guild.id)
    synced = None
    if args == "~":
        synced = await bot.tree.sync()
    elif args.isdigit():
        if bot.get_guild(int(args)):
            try:
                bot.tree.copy_global_to(guild=discord.Object(int(args)))
                synced = await bot.tree.sync(guild=discord.Object(int(args)))
            except Exception as error:
                return await ctx.send(f"There was a issue with syncing the tree with the specified guild.\n```py\n{error}```")
        else: return await ctx.send("That's not a guild or I'm not in it")
    else: return
    await ctx.send(f"Tree synced {'to guild with the id `{}`'.format(args) if not args == '~' else 'globally'}!\n```py\n{synced}```")


bot.run(token=Settings.Token, reconnect=True)
