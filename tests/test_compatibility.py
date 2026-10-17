import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from discord_bot_maker import Bot, Command, DBot


class CompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_discord_client_initializes(self):
        bot = DBot("unused")
        self.assertTrue(bot.bot.intents.message_content)
        self.assertIsNotNone(bot.bot.get_command("help"))
        await bot.bot.close()

    async def test_named_api_and_legacy_definition_mapping(self):
        bot = Bot("unused", prefix=("!", "."))
        command = bot.add_command(
            "hello", "Hello", description="Welcome", image_url="https://example.com/image.png",
            help_text="A greeting",
        )
        self.assertIsInstance(command, Command)
        bot.createCommand("legacy", "Hi", "Description", "✨", None, "Legacy help")
        self.assertEqual(bot.command_definitions["legacy"].description, "Description")
        self.assertEqual(bot.commDict["hello"], ("Hello", "Welcome", "😃", "https://example.com/image.png", "A greeting"))
        self.assertEqual(len(bot), 2)
        self.assertIs(bot.client, bot.getBotInstance())
        with self.assertRaises(ValueError):
            bot.add_command("help", "Conflicts with help")
        with self.assertRaises(ValueError):
            bot.add_command("two words", "Invalid")
        await bot.client.close()

    async def test_complete_command_name_and_multiple_prefixes(self):
        bot = Bot("unused", prefix=("!", "."), help_command=False)
        bot.add_command("hello", "Hello")
        bot.client.process_commands = AsyncMock()
        message = SimpleNamespace(
            author=SimpleNamespace(
                bot=False, name="Aaryan", mention="@Aaryan", display_name="Aaryan",
                discriminator="0", display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
            ),
            channel=SimpleNamespace(send=AsyncMock()), guild=None,
            content="!helloworld", clean_content="!helloworld", created_at="now",
        )
        await bot.client.on_message(message)
        message.channel.send.assert_not_awaited()
        bot.client.process_commands.assert_awaited_once_with(message)
        for content in ("!hello", ".hello there"):
            message.content = content
            await bot.client.on_message(message)
        self.assertEqual(message.channel.send.await_count, 2)
        await bot.client.close()

    async def test_explicit_run_and_legacy_constructor(self):
        bot = DBot(bTOKEN="unused", bPrefix="!", helpCommand=False, baseCode=False)
        self.assertIsNone(bot.client)
        with self.assertRaises(RuntimeError):
            bot.run()
        bot.baseCode()
        bot.client.run = Mock()
        bot.bRun()
        bot.client.run.assert_called_once_with("unused")
        await bot.client.close()

    async def test_direct_message_without_guild_or_avatar(self):
        bot = DBot("unused", helpCommand=False)
        bot.bot._connection.user = SimpleNamespace(name="Test bot")
        bot.createCommand("hello", "Hello <author name>", "<guild name><channel category>")
        bot.bot.process_commands = AsyncMock()
        channel = SimpleNamespace(send=AsyncMock())
        author = SimpleNamespace(
            bot=False, name="Aaryan", mention="@Aaryan", display_name="Aaryan",
            discriminator="0", display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
        )
        message = SimpleNamespace(
            author=author, channel=channel, guild=None, content=".hello",
            clean_content=".hello", created_at="now",
        )
        await bot.bot.on_message(message)
        embed = channel.send.call_args.kwargs["embed"]
        self.assertEqual(embed.title, "Hello Aaryan")
        self.assertEqual(embed.thumbnail.url, author.display_avatar.url)
        author.bot = True
        channel.send.reset_mock()
        await bot.bot.on_message(message)
        channel.send.assert_not_awaited()
        await bot.bot.close()

    async def test_context_exception_does_not_start_bot(self):
        bot = DBot("unused")
        bot.bRun = Mock()
        with self.assertRaises(ValueError):
            with bot:
                raise ValueError("invalid config")
        bot.bRun.assert_not_called()
        await bot.bot.close()
