"""Localization of Bot messages (not embeds)"""

import discord

class BotInfo():
    def ping(language: str, bot: discord.Bot):
        if language == "ru":
            return f"Понг! Текущий пинг - `{int(bot.latency * 1000)}ms`"
        else:
            return f"Pong! Current ping - `{int(bot.latency * 1000)}ms`"