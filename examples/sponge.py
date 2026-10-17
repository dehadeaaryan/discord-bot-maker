"""Sponge: a real bot authored entirely with Discord Bot Maker's public API.

Run: .venv/bin/python examples/sponge.py --sync
"""

import argparse

from discord_bot_maker import Bot, Button, CommandContext, Embed, Message


def configure(bot: Bot) -> Bot:
    bot.reply("hello", Embed("Hello, {{user.display_name}}! 🧽", "I’m Sponge. Ready to soak up some tasks."), description="Meet Sponge")
    bot.reply("ping", "Pong! 🏓 All pores operational.", description="Check Sponge is awake")
    bot.reply("rules", Embed("The lair’s house rules", "Be kind. No spam. Be nice to the duck."), description="Read the server rules")
    bot.random_reply("wisdom", [
        "Stay absorbent. You never know when knowledge might spill.",
        "If life gets messy, that sounds like job security to me.",
        "My duck has reviewed your proposal. He says quack.",
    ], description="Questionable wisdom from Sponge", cooldown=5)
    bot.reply("duck", Message("The duck demands attention.", buttons=[Button("Pet the duck 🦆", reply="Quack. Your affection has been accepted.")]), description="Visit Sponge’s pet duck")

    @bot.command(description="Feed the duck and see your personal total", cooldown=3)
    def feed(ctx: CommandContext):
        total = ctx.user_store.increment("duck_snacks")
        return f"🦆 Quack! You’ve fed the duck {total} time(s)."

    @bot.command(description="Set your server’s duck motto", permission="manage_guild", private=True)
    def motto(ctx: CommandContext, text: str):
        ctx.store.set("duck_motto", text[:200])
        return "The duck’s new motto is saved."

    @bot.command(description="Read this server’s duck motto")
    def duck_motto(ctx: CommandContext):
        return ctx.store.get("duck_motto", "Stay curious. Stay quacky.")

    bot.poll()
    bot.reminders()
    return bot


def main():
    parser = argparse.ArgumentParser(description="Run Sponge using Discord Bot Maker.")
    parser.add_argument("--sync", action="store_true", help="Register commands on first run or after changes.")
    args = parser.parse_args()
    try:
        bot = configure(Bot.from_env(storage="data/sponge.sqlite3"))
    except ValueError as error:
        parser.error(str(error))
    bot.run(sync=args.sync)


if __name__ == "__main__":
    main()
