# Run your first Discord bot

The runnable example provides **/hello**, **/ping**, and **/rules**. It runs on
this computer using the standalone Python package. No web app or database is
needed. The project environment uses Python 3.15.0.

## 1. Create your bot

1. Open https://discord.com/developers/applications and select **New Application**.
2. Give it a name, such as “My Server Helper”.
3. Open **Bot**, add a bot user if the portal asks, then use **Reset Token** to
   obtain the bot token. Keep it private. The example asks for it with hidden
   input; you do not need to paste it into a file or chat.
4. Leave the privileged gateway intents off. This example uses slash commands
   and does not need Message Content Intent, Server Members Intent, or Presence Intent.

## 2. Add it to your server

Bots are installed to a **server** first, then channel permissions decide where
members can use them. You need permission to manage the server, or a server
admin must install it for you.

1. Open the application's **Installation** page.
2. Enable **Guild Install** (server installation).
3. Under **Default Install Settings → Guild Install**, add the `bot` and
   `applications.commands` scopes. Choose **View Channels**, **Send Messages**,
   and **Embed Links** permissions, then save.
4. Select **Discord Provided Link**, copy the install link, open it, choose
   **Add to Server**, select your server, and authorize it.

If the portal uses **OAuth2 → URL Generator**, select `bot` and
`applications.commands`, the same permissions, then open its generated URL.
A permissions integer of **19456** represents View Channels + Send Messages +
Embed Links. Administrator permission is unnecessary.

## 3. Pick your server and channel

1. In Discord, open **User Settings → Advanced → Developer Mode**.
2. Right-click your server's icon and choose **Copy Server ID**.
3. Optionally right-click the text channel you want and choose **Copy Channel ID**.

Use an ordinary text channel for this first test. The optional channel flag
makes commands invoked elsewhere return a private pointer to the selected channel.
It does not hide the commands in Discord's picker. To also limit their visibility,
use **Server Settings → Integrations → your app** to restrict command access to
that channel. Make sure channel overrides allow the bot to view the channel,
send messages, and embed links, and allow members to use application commands.

## 4. Run it from this repository

The virtual environment is already installed in this checkout. From the project
folder, run (replace the numeric IDs with yours):

You can also fill in `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` in the root `.env`
file, optionally set `DISCORD_CHANNEL_ID`, then run
`.venv/bin/python examples/bot.py --sync`. The example loads these three settings
from `.env` in the current directory. Existing environment variables take priority,
and command-line flags override IDs. The file is excluded from Git.

```sh
.venv/bin/python examples/bot.py --guild-id YOUR_SERVER_ID --channel-id YOUR_CHANNEL_ID --sync
```

Omit `--channel-id YOUR_CHANNEL_ID` to allow responses throughout your server.
The script prompts for your bot token with hidden input. It is not saved.
`DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, and `DISCORD_CHANNEL_ID` environment
variables are also supported if you already manage secrets that way.

`--sync` registers this example's slash commands in that specific server. Use it
on the first run and after changing commands. Prefer a dedicated test application:
sync replaces that application's server-specific command list with the example's
commands. Subsequent runs can omit `--sync`.

Once the terminal prints **Connected as ...**, type `/hello`, `/ping`, or `/rules`
in the selected Discord channel. Keep the terminal running. Press **Ctrl+C** to
stop it; closing the terminal or sleeping the computer takes the bot offline.

## Test without a token

```sh
.venv/bin/python examples/bot.py --preview hello
.venv/bin/python examples/bot.py --preview ping
.venv/bin/python examples/bot.py --preview rules
```

## Customize it

Edit `build_definition()` in `src/discord_bot_maker/example.py` to change the
command names, replies, rules, and embed colors. The example uses the same
validated definition and interpreter as the standalone library.

The equivalent installed-package command is:

```sh
.venv/bin/python -m discord_bot_maker.example --guild-id YOUR_SERVER_ID --sync
```

For a fresh checkout:

```sh
uv venv --python 3.15 .venv
uv pip install -e .
```

## If something does not work

- **No commands:** confirm the application was installed to this server with
  `applications.commands`, check the server ID, and run with `--sync` once. Try
  reopening Discord's command picker.
- **Missing Access / forbidden:** verify the bot is a member of that server and
  your channel overrides allow it access.
- **Token rejected:** reset the **bot token** in the Bot page. The application
  ID, public key, and OAuth client secret are different values.
- **Replies redirect you:** use the channel passed with `--channel-id`, or omit
  that flag and restart to allow the whole server.

Portal setup follows Discord's [installation documentation](https://discord.com/developers/resources/application#install-links).
Server-specific registration uses discord.py's [application-command guidance](https://discordpy.readthedocs.io/en/stable/faq.html#application-commands).
