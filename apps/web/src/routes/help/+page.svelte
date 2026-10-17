<svelte:head><title>Setup guide — Discord Bot Maker</title></svelte:head>
<main id="main" class="guide glass"><h1>Setup guide</h1><h2>1. Make a command</h2><p>Open the builder and choose a template. Select a block to edit it. Connect the trigger to a reply, or add a role/channel condition with True and False paths. The list view lets you do the same work without dragging.</p><h2>2. Preview your reply</h2><p>Pick a command and set the sample user, server, channel and role IDs. Preview uses the same Python interpreter as the exported bot. It never sends messages to Discord.</p><h2>3. Connect to Discord</h2><p>Follow the <a href="#discord-setup">Discord setup steps</a> below to create your bot, get its token, and add it to your server.</p><h2>4. Export or publish</h2><p>Export downloads bot.json and a Python launcher. Run it on your own machine or server. Hosted publishing is available only to the configured owner during the pilot. Signing in with Discord authenticates you; it does not supply your bot token.</p><section aria-labelledby="python">
<h2 id="python">Run with Python</h2>
<p>Install the package from <a href="https://pypi.org/project/discord-bot-maker/" target="_blank" rel="noreferrer">PyPI ↗</a>. The library works independently of this website.</p>
<h3 id="discord-setup">Create a bot and get its token</h3>
<ol>
  <li>Open the <a href="https://discord.com/developers/applications" target="_blank" rel="noreferrer">Discord Developer Portal</a>, choose <strong>New Application</strong>, and enter a name.</li>
  <li>Open <strong>Bot</strong>. Add a bot user if prompted, then choose <strong>Reset Token</strong> and copy the bot token.</li>
  <li>Open <strong>Installation</strong> and enable <strong>Guild Install</strong>. Under <strong>Default Install Settings</strong>, select <code>bot</code> and <code>applications.commands</code>.</li>
  <li>Select <strong>View Channels</strong>, <strong>Send Messages</strong>, and <strong>Embed Links</strong>, then save.</li>
  <li>Open the <strong>Discord Provided Link</strong>, choose <strong>Add to Server</strong>, and authorize it in a server you can manage.</li>
</ol>
<p>Keep the token private. It is different from the application ID, public key, and OAuth client secret. Reset it if exposed. These Python bots use the Gateway, so leave <strong>Interactions Endpoint URL</strong> empty.</p>
<p>Slash commands need no privileged intents. Enable <strong>Message Content Intent</strong> only for prefix commands; enable <strong>Server Members Intent</strong> if your Python bot uses member welcomes.</p>
<h3>Install and run</h3>
<p>Export your bot and extract the ZIP. In that folder, create a virtual environment and install the requirements:</p>
<pre><code>python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt</code></pre>
<p>Set the token in your terminal. The exported launcher and CLI read environment variables; they do not load a <code>.env</code> file automatically.</p>
<pre><code># macOS / Linux
export DISCORD_BOT_TOKEN='your-bot-token'
# Windows PowerShell
$env:DISCORD_BOT_TOKEN='your-bot-token'</code></pre>
<p>For a test server, enable <strong>User Settings → Advanced → Developer Mode</strong> in Discord, right-click the server, and choose <strong>Copy Server ID</strong>. Replace <code>YOUR_SERVER_ID</code> below:</p>
<pre><code>discord-bot-maker validate bot.json
discord-bot-maker preview bot.json --command hello
discord-bot-maker run bot.json --sync --guild-id YOUR_SERVER_ID</code></pre>
<p>Replace <code>hello</code> with your command name. Use <code>--sync</code> on the first run and after changing commands. Omit <code>--guild-id</code> to register commands globally. Keep the process running, then try your command in Discord.</p>
<p>Writing your bot in Python instead? Install with <code>python -m pip install discord-bot-maker</code>. <code>Bot.from_env()</code> can also read a local <code>.env</code> file next to your script; add that file to <code>.gitignore</code>.</p>
</section><h2>Save, publish, and rollback</h2><p>Your browser keeps your current local draft. Sign in to save projects across devices. Saving changes the draft; publishing creates a separate immutable version. Rollback selects an earlier published version without overwriting your draft. Stop disconnects a hosted bot; deleting credentials also stops it.</p><a class="button primary" href="/builder">Open the builder →</a></main>
