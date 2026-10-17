# Discord Bot Maker repository

Read [AGENTS.md](AGENTS.md) for repository instructions, checks, packaging and
contributor conventions. Read [the package authoring guide](src/discord_bot_maker/AGENTS.md)
for the Python API before implementing bot features.

Use the public facade for examples. Keep Sponge separate from the library and
never expose secrets or run live Discord operations as part of offline tests.
