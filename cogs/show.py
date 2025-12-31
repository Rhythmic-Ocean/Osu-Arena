import discord
from discord import app_commands
from discord.ext import commands
from bot import OsuArena
from utils_v2 import ShowTable
from utils_v2.enums.status import ChallengeStatus
from utils_v2.enums.tables import TablesLeagues, TablesPoints
from utils_v2.enums.tables_internals import DiscordOsuColumn
from utils_v2.renderer import Renderer


class Show(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = self.bot.db_handler
        self.log_handler = self.bot.log_handler
        self.renderer = Renderer(self.bot)

    @app_commands.command(name="show", description="Show the league table")
    @app_commands.describe(league="The name of the league to display")
    async def show(self, interaction: discord.Interaction, league: str):
        league_name = league.lower()
        await interaction.response.defer()

        if not await self._validate_args(interaction, league_name):
            return

        try:
            headers, rows, title = await self._fetch_table_data(league_name)

            if not rows:
                await interaction.followup.send("⚠️ This table is empty.")
                return

            await self._render_and_send(interaction, headers, rows, title)

        except Exception as e:
            print(f"CRITICAL: /show command crashed: {e}")
            await interaction.followup.send(
                "⚠️ An unknown error occurred while loading the table."
            )

    @show.autocomplete("league")
    async def show_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [t.value for t in ShowTable]
        return [
            app_commands.Choice(name=choice.capitalize(), value=choice)
            for choice in choices
            if current.lower() in choice.lower()
        ][:25]

    async def _validate_args(
        self, interaction: discord.Interaction, league_name: str
    ) -> bool:
        if league_name not in [t.value for t in ShowTable]:
            valid_list = ", ".join([f"`{t.value.capitalize()}`" for t in ShowTable])
            await interaction.followup.send(
                f"❌ **Invalid League:** Please choose one of: {valid_list}",
                ephemeral=True,
            )
            return False

        if league_name == ShowTable.RANKER:
            await interaction.followup.send(
                "⚠ **Deprecated:** The Ranker league is no longer available.",
                ephemeral=True,
            )
            return False

        return True

    async def _fetch_table_data(self, league_name: str):
        if league_name in [t.value for t in TablesLeagues]:
            data = await self.db_handler.get_current_league_table(league_name)
            title = f"{league_name.capitalize()}"
            return (*data, title) if data else ([], [], title)

        elif league_name in [t.value for t in TablesPoints]:
            if league_name == TablesPoints.S_POINTS:
                league_name = DiscordOsuColumn.SEASONAL_POINTS
            data = await self.db_handler.get_current_points(league_name)
            if league_name == TablesPoints.POINTS:
                title = "Universal Points"
            else:
                title = "Seasonal Points"
            return (*data, title) if data else ([], [], title)

        else:
            data = await self.db_handler.get_rivals_table(ChallengeStatus.UNFINISHED)
            title = "Rivals"
            return (*data, title) if data else ([], [], title)

    async def _render_and_send(self, interaction, headers, rows, title):
        """Handles image generation and embed construction."""
        try:
            image_buf = await self.renderer.leaderboard.render_image(headers, rows)

            if not image_buf:
                await interaction.followup.send("⚠️ Failed to generate table image.")
                return

            file = discord.File(fp=image_buf, filename="table.png")

            embed = discord.Embed(title=title, color=discord.Color.blue())
            embed.set_image(url="attachment://table.png")

            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            print(f"Error in _render_and_send: {e}")
            await interaction.followup.send("⚠️ Failed to send the leaderboard.")


async def setup(bot):
    await bot.add_cog(Show(bot))
    print("LeagueTable cog loaded")
