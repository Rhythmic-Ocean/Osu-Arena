import discord


class ChallengeView(discord.ui.View):
    def __init__(self, challenged: discord.Member, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.challenged = challenged
        self.response = None
        self.message = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message(
                "This challenge is not for you.", ephemeral=True
            )
            return

        self.response = True
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"✅ {self.challenged.mention} accepted the challenge!", view=self
        )
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.challenged:
            await interaction.response.send_message(
                "This challenge is not for you.", ephemeral=True
            )
            return

        self.response = False
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"🚫 {self.challenged.mention} declined the challenge.", view=self
        )
        self.stop()

    async def on_timeout(self):
        """Called automatically when the timer expires."""
        self.response = None

        for child in self.children:
            child.disabled = True

        if self.message:
            try:
                await self.message.edit(content="⏱️ Challenge expired.", view=self)
            except (discord.NotFound, discord.Forbidden):
                pass
