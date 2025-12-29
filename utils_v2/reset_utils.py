import discord


class ResetConfirmView(discord.ui.View):
    def __init__(self, interaction=discord.Interaction):
        super().__init__(timeout=30)
        self.value = None
        self.original_user = interaction.user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            await interaction.response.send_message(
                "⛔ This is not your command!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Yes, Restart the season.", style=discord.ButtonStyle.green
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        await interaction.response.defer()
        await interaction.edit_original_response(
            "✅ Confirmation received. Starting restart sequence..."
        )
        self.stop()

    @discord.ui.button(label="Cancel restart.", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        await interaction.edit_original_response("❌ **Operation cancelled** by user..")
        self.stop()
