import discord


class ConfirmDelete(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.value: bool | None = None

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        self.stop()
