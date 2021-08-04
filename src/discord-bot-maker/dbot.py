import discord

from discord.ext import commands

PACKAGENAME = "DiscordBotMaker"
color = discord.Color.dark_red()
FATHER = "<@!781547664079847464>"
owner = FATHER

class DBot:
    def __init__(self, 
    bTOKEN : str,
    bPrefix : tuple = ".", 
    owner : str = FATHER, 
    helpCommand : bool = True, 
    baseCode : bool = True,
    ):
        self.bPrefix = bPrefix
        self.bot = None
        self.commDict = {}
        self.bTOKEN = bTOKEN


        if baseCode:
            self.baseCode()

        if helpCommand:
            self.commandHelp()

    def __add__(self, t : tuple):
        self.createCommand(*t)
    
    def __call__(self):
        self.bRun()
    
    def __len__(self):
        return len(self.commDict)
    
    def __enter__(self):
        return self

    def __exit__(self, *args):
        print(args)
        self.bRun()
    









    def baseCode(self):
        self.bot = commands.Bot(command_prefix = self.bPrefix)

        @self.bot.event
        async def on_ready():
            await self.bot.change_presence(status = discord.Status.idle, activity = discord.Game(name = (f"{self.bPrefix[0]}help" if type(self.bPrefix) == tuple else f"{self.bPrefix}help")))
            print(f'{self.bot.user.name} has connected to Discord!')
    
    def bRun(self):
        self.bot.run(self.bTOKEN)
    
    def getBotInstance(self):
        return self.bot
    







    def createCommand(self, trigger : str, reply : str, reply2 : str = None, emoji : str = "😃", image : str = None, help : str = "Not Defined"):
        self.commDict[trigger] = (reply, reply2, emoji, image, help)
        self.createCommands(self.commDict)

    def createCommands(self, commDict : dict):
        for element in commDict:
            self.commDict[element] = commDict[element]


        @self.bot.event
        async def on_message(message):
            for trigger in self.commDict:
                emoji = "😃"
                reply = self.commDict[trigger][0]
                reply2 = self.commDict[trigger][1]
                emoji = self.commDict[trigger][2]
                image = self.commDict[trigger][3]

                
                varlist = [
                    ("<author name>", message.author.name),
                    ("<author mention>", message.author.mention),
                    ("<author display name>", message.author.display_name),
                    ("<author discriminator>", message.author.discriminator),

                    ("<message time>", message.created_at),
                    ("<message content>", message.content),
                    ("<message clean content>", message.clean_content),

                    ("<channel name>", message.channel.name),
                    ("<channel topic>", message.channel.topic),
                    # ("<channel last message>", message.channel.last_message),
                    ("<channel category>", message.channel.category.name),
                    ("<channel mention>", message.channel.mention),

                    ("<guild name>", message.guild.name),
                    # ("<guild owner name>", message.guild.owner.name),
                    # ("<guild owner mention>", message.guild.owner.mention),
                    # ("<guild owner nickname>", message.guild.owner.nick),
                    ("<guild member count>", message.guild.member_count),
                    # ("<guild icon url>", await message.guild.icon_url.read()),
                    # ("<guild channels>", (channel.name for channel in message.guild.channels)),
                    ("<guild description>", message.guild.description),
                    # ("<guild rules channel>", message.guild.rules_channel.mention),
                    ("<guild features>", message.guild.features),
                ]


                for var in varlist:
                    if var[0] in reply:
                        reply = reply.replace(var[0], f"{var[1]}")
                    if reply2:
                        if var[0] in reply2:
                            reply2 = reply2.replace(var[0], f"{var[1]}")
                    



                if type(self.bPrefix) == tuple:
                    for prefix in self.bPrefix:
                        if message.content.startswith(f"{prefix}{trigger}"):
                            embed = discord.Embed(title = reply, description = reply2 if reply2 else "", color = color)

                            embed.add_field(name = "‎", value = emoji, inline = False)
                            embed.set_thumbnail(url = message.author.avatar_url)
                            
                            if image:
                                embed.set_image(url = image)
                            
                            embed.add_field(name = f"{PACKAGENAME}", value = f"\n{self.bot.user.name} is using {PACKAGENAME}", inline = False)
                            await message.channel.send(embed = embed)
                            
                            print(f"command{trigger.capitalize()} was used")
                            return
                else:
                    if message.content.startswith(f"{self.bPrefix}{trigger}"):
                        embed = discord.Embed(title = reply, description = reply2 if reply2 else "", color = color)

                        embed.add_field(name = "‎", value = emoji, inline = False)
                        embed.set_thumbnail(url = message.author.avatar_url)
                        
                        if image:
                            embed.set_image(url = image)
                        
                        embed.add_field(name = f"{PACKAGENAME}", value = f"\n{self.bot.user.name} is using {PACKAGENAME}", inline = False)
                        await message.channel.send(embed = embed)
                        
                        print(f"command{trigger.capitalize()} was used")
                        return


            @self.bot.event
            async def on_command_error(ctx, error):
                if isinstance(error, commands.CommandNotFound):
                    return
            await self.bot.process_commands(message)
    











    def commandHi(self, aliases : list = [], help : str = "Says hi back", message : str = "Hey!", description : str = "uwu", gif : str = "https://c.tenor.com/lGBkMdCSr-EAAAAj/bye-smile.gif"):
        self.hiAliases = aliases
        self.hiHelp = help
        self.hiTitle = message
        self.hiDescription = description
        self.hiImage = gif

        @self.bot.command(aliases = self.hiAliases, help = self.hiHelp)
        async def hi(ctx):
            embed = discord.Embed(title = self.hiTitle, description = self.hiDescription, color = color)
            embed.set_image(url = self.hiImage)
            embed.add_field(name = f"{PACKAGENAME}", value = f"\n{self.bot.user.name} is using {PACKAGENAME} by {FATHER}")

            await ctx.send(embed = embed)
            print("commandHi was used")
    
    def commandHelp(self, title : str = "HELP", description : str = f"By {owner}"):
        self.helpTitle = title
        self.helpDescription = description
        self.bot.remove_command('help')

        @self.bot.command(help = "Shows this message")
        async def help(ctx):
            tempPrefixList = ""
            if type(self.bPrefix) == tuple:
                for prefix in self.bPrefix:
                    tempPrefixList += f"{prefix}\n"
            else:
                tempPrefixList += f"{self.bPrefix}\n"
            embed = discord.Embed(title = self.helpTitle, description = self.helpDescription, color = color)
            embed.add_field(name = "Prefix :", value = tempPrefixList)
            commandsHelpVar = ""
            for command in self.bot.walk_commands():
                commandsHelpVar += f"{command.name} : {command.help}\n"
            for command in self.commDict:
                commandsHelpVar += f"{command} : {self.commDict[command][4]}\n"
            embed.add_field(name = "Commands", value = commandsHelpVar, inline = False)
            embed.add_field(name = f"{PACKAGENAME}", value = f"\n{self.bot.user.name} is using {PACKAGENAME} by {FATHER}")

            await ctx.send(embed = embed)
            print("commandHelp was used")