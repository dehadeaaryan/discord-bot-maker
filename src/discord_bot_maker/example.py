from discord_bot_maker import DBot

d = DBot(TOKEN)

d.createCommand(trigger = "jump", reply = "whoop!", reply2 = "I just jumped", emoji = "😄", image = "jumping.gif", help = "jumps")

d()