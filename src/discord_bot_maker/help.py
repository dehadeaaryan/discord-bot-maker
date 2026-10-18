"""Temporary interactive help; every navigation rechecks caller permissions."""
from dataclasses import dataclass
import discord
from .interactions import _ExpiringView, private_reply


@dataclass(frozen=True)
class Help:
    query: str = ""
    page_size: int = 6


class HelpView(_ExpiringView):
    def __init__(self, context, definition):
        super().__init__(context, 180)
        self.definition = definition
        self.page = 0
        self.category = None
        self._rebuild(context.interaction)

    def entries(self, interaction):
        query = self.definition.query.casefold()
        return [item for item in self.context.bot._commands.values() if not self.context.bot._policy_failure(interaction, **item["policy"]) and (not self.category or item["category"] == self.category) and query in f'{item["name"]} {item["description"]} {item["category"]}'.casefold()]

    def _rebuild(self, interaction):
        self.clear_items()
        entries = self.entries(interaction)
        pages = max(1, (len(entries) + self.definition.page_size - 1) // self.definition.page_size)
        self.page = min(self.page, pages - 1)
        for label, step in (("Previous", -1), ("Next", 1)):
            button = discord.ui.Button(label=label, disabled=(self.page == 0 if step < 0 else self.page == pages - 1))
            async def callback(click, step=step):
                if await self.allowed(click):
                    self.page = max(0, self.page + step)
                    self._rebuild(click)
                    await click.response.edit_message(embed=self.embed(click), view=self)
            button.callback = callback
            self.add_item(button)
        categories = sorted({item["category"] for item in self.context.bot._commands.values() if not self.context.bot._policy_failure(interaction, **item["policy"])})
        select = discord.ui.Select(placeholder="Choose category", options=[discord.SelectOption(label="All categories", value="__all__"), *[discord.SelectOption(label=category, value=str(index)) for index, category in enumerate(categories[:24])]])
        async def choose(click):
            if await self.allowed(click):
                value = select.values[0]
                self.category = None if value == "__all__" else categories[int(value)]
                self.page = 0
                self._rebuild(click)
                await click.response.edit_message(embed=self.embed(click), view=self)
        select.callback = choose
        self.add_item(select)

    async def allowed(self, interaction):
        if self.is_finished():
            await private_reply(interaction, "This help menu has expired.")
            return False
        if interaction.user.id != self.context.user.id:
            await private_reply(interaction, "This help menu belongs to the person who opened it.")
            return False
        return await self.context.bot._authorize(interaction, **self.context._policy)

    def embed(self, interaction):
        entries = self.entries(interaction)
        start = self.page * self.definition.page_size
        lines = []
        for item in entries[start:start + self.definition.page_size]:
            args = " ".join(f'<{p.name}>' if p.default is p.empty else f'[{p.name}]' for p in item["parameters"])
            prefix = "/" if item["mode"] != "prefix" else (self.context.bot.prefix if isinstance(self.context.bot.prefix, str) else self.context.bot.prefix[0])
            lines.append(f'**{prefix}{item["name"]} {args}** — {item["description"]}\n{item["category"]}'[:380])
        pages = max(1, (len(entries) + self.definition.page_size - 1) // self.definition.page_size)
        return discord.Embed(title="Command help", description="\n\n".join(lines) or "No matching commands.", color=0xFF7A30).set_footer(text=f"Page {self.page + 1}/{pages}")
