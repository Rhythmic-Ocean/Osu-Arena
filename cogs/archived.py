import discord
from discord import app_commands
from discord.ext import commands
from bot import OsuArena
from utils_v2 import Renderer, ArchivedTable, ChallengeStatus


class Archives(commands.Cog):
    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.db_handler = bot.db_handler
        self.renderer = Renderer(bot)

    @app_commands.command(name="archived", description="View archived league tables")
    @app_commands.describe(
        season="The finished season number (or 0 for Rivals)", league="The league name"
    )
    async def archived(
        self, interaction: discord.Interaction, season: int, league: str
    ):
        league_name = league.lower()
        await interaction.response.defer()

        if not await self._validate_args(interaction, season, league_name):
            return

        try:
            headers, rows, title = await self._fetch_archive_data(league_name, season)

            if not rows:
                await interaction.followup.send(
                    "📂 **No Data Found:** This table is empty or the archive does not exist."
                )
                return

            await self._render_and_send(interaction, headers, rows, title)

        except Exception as e:
            self.bot.error_handler.logger.error(f"Archive Error: {e}")
            await interaction.followup.send(
                "⚠️ **System Error:** An unexpected error occurred while processing the archive."
            )

    async def _validate_args(
        self, interaction: discord.Interaction, season: int, league_name: str
    ) -> bool:
        """Returns True if arguments are valid, False (and sends error) otherwise."""

        if league_name not in [t.value for t in ArchivedTable]:
            valid_list = ", ".join([f"`{t.value.capitalize()}`" for t in ArchivedTable])
            await interaction.followup.send(
                f"❌ **Invalid League:** Please choose one of: {valid_list}",
                ephemeral=True,
            )
            return False

        if league_name == ArchivedTable.RIVALS.value:
            if season != 0:
                await interaction.followup.send(
                    "❌ **Incorrect Season:** Rivals archives do not use season numbers.\n"
                    "👉 Please use **0** to view finished Rival Challenges.",
                    ephemeral=True,
                )
                return False
            return True

        valid_seasons = await self.db_handler.get_archived_season()
        if not valid_seasons:
            await interaction.followup.send(
                "⚠️ **Database Error:** Could not fetch season history. Please try again later."
            )
            return False

        if season not in valid_seasons:
            pretty_seasons = ", ".join([f"`{s}`" for s in sorted(valid_seasons)])
            await interaction.followup.send(
                f"❌ **Invalid Season:** That season is not in the archives.\n"
                f"📅 **Available Seasons:** {pretty_seasons}",
                ephemeral=True,
            )
            return False

        if league_name == ArchivedTable.NOVICE.value and season == 1:
            await interaction.followup.send(
                "❌ **Unavailable:** The Novice League archive starts from **Season 2**.",
                ephemeral=True,
            )
            return False

        if league_name == ArchivedTable.RANKER.value and season != 1:
            await interaction.followup.send(
                "❌ **Unavailable:** Ranker League is deprecated and only exists for **Season 1**.",
                ephemeral=True,
            )
            return False

        if league_name == ArchivedTable.S_POINTS.value and season < 3:
            await interaction.followup.send(
                "❌ **Unavailable:** Seasonal Points are only archived starting from **Season 3**.",
                ephemeral=True,
            )
            return False

        return True

    async def _fetch_archive_data(self, league: str, season: int):
        if league == ArchivedTable.RIVALS.value:
            data = await self.db_handler.get_rivals_table(
                status=ChallengeStatus.FINISHED
            )
            title = "⚔️ Rivals - Finished Challenges"
            return (*data, title) if data else ([], [], title)

        if league == ArchivedTable.S_POINTS.value:
            data = await self.db_handler.get_archived_points(season=season)
            title = f"🏆 Seasonal Points - Season {season}"
            return (*data, title) if data else ([], [], title)

        data = await self.db_handler.get_archived_league_table(league, season)
        title = f"📜 {league.capitalize()} League - Season {season}"
        return (*data, title) if data else ([], [], title)

    async def _render_and_send(self, interaction, headers, rows, title):
        image_buf = await self.renderer.leaderboard.render_image(headers, rows)

        if not image_buf:
            await interaction.followup.send(
                "⚠️ **Render Error:** Failed to generate image."
            )
            return

        file = discord.File(fp=image_buf, filename="archive_table.png")
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.set_image(url="attachment://archive_table.png")

        await interaction.followup.send(embed=embed, file=file)


async def setup(bot: OsuArena):
    await bot.add_cog(Archives(bot))
    print("Archives cog loaded")
