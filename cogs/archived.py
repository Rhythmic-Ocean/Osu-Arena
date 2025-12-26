import discord
from discord import app_commands
from discord.ext import commands
from bot import OsuArena
from utils_v2 import Renderer, ArchivedTable, TablesPoints, ChallengeStatus


class Archives(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = bot.db_handler
        self.renderer = Renderer(bot)

    @app_commands.command(name="archived", description="Shows archived tables")
    @app_commands.describe(
        season="The finished season number", league="The league name"
    )
    async def archived(
        self, interaction: discord.Interaction, season: int, league: str
    ):
        await interaction.response.defer()

        league_name = league.lower()

        # 1. Initial Validation
        if not self._is_valid_league_name(league_name):
            valid_list = ", ".join([t.value.capitalize() for t in ArchivedTable])
            await interaction.followup.send(
                f"❌ Invalid league name. Use one of: {valid_list}", ephemeral=True
            )
            return

        try:
            # 2. Fetch Data (Handles all routing logic)
            # Returns tuple: (headers, rows, error_message)
            headers, rows, error = await self._fetch_archive_data(league_name, season)

            if error:
                await interaction.followup.send(error, ephemeral=True)
                return

            if not rows:
                await interaction.followup.send(
                    "⚠ This table is empty or does not exist."
                )
                return

            # 3. Render & Send
            await self._render_and_send(interaction, league, season, headers, rows)

        except Exception as e:
            self.bot.error_handler.logger.error(f"Archive Error: {e}")
            await interaction.followup.send(
                "⚠️ An unknown error occurred while processing your request."
            )

    # ------------------------------------------------------------------
    # Internal Helper Methods
    # ------------------------------------------------------------------

    def _is_valid_league_name(self, league_name: str) -> bool:
        """Checks if the league exists in the Enum."""
        return league_name in [t.value for t in ArchivedTable]

    async def _fetch_archive_data(self, league: str, season: int):
        """
        Routes the request to the correct DB function based on league type.
        Returns: (headers, rows, error_message)
        """
        # Case A: Rivals
        if league == ArchivedTable.RIVALS.value:
            if season != 0:
                return [], [], "❌ Invalid season for Rivals. Use **season: 0**."

            data = await self.db_handler.get_rivals_table(
                status=ChallengeStatus.FINISHED
            )
            return (*data, None) if data else ([], [], None)

        # Case B: Seasonal Points
        if league in [t.value for t in TablesPoints]:
            if season < 3:
                return (
                    [],
                    [],
                    "❌ Seasonal Points are only archived starting from **Season 3**.",
                )

            data = await self.db_handler.get_archived_points(season=season)
            return (*data, None) if data else ([], [], None)

        # Case C: Standard Leagues (Bronze, Silver, etc.)
        # This requires checking the DB for valid seasons first
        valid_seasons = await self.db_handler.get_archived_season()

        if not valid_seasons:
            return [], [], "⚠ Could not fetch season history. Please try again later."

        if season not in valid_seasons:
            pretty_seasons = ", ".join(map(str, sorted(valid_seasons)))
            return [], [], f"❌ Invalid season. Available seasons: {pretty_seasons}"

        data = await self.db_handler.get_archived_league_table(league, season)
        return (*data, None) if data else ([], [], None)

    async def _render_and_send(
        self, interaction, league_display, season, headers, rows
    ):
        """Generates the image and sends the final embed."""
        image_buf = self.renderer.leaderboard.render_image(headers, rows)

        if not image_buf:
            await interaction.followup.send("⚠ Failed to render image.")
            return

        file = discord.File(fp=image_buf, filename="table.png")
        embed = discord.Embed(title=f"{league_display.capitalize()} - Season {season}")
        embed.set_image(url="attachment://table.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: OsuArena):
    await bot.add_cog(Archives(bot))
