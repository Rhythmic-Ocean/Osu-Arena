from __future__ import annotations
import discord
import pandas as pd
import matplotlib.pyplot as plt

from datetime import datetime
from io import BytesIO
from typing import List, Tuple, Any, Optional

from plottable import Table, ColumnDefinition

from osu import LegacyScore, SoloScore

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import OsuArena


class BaseRenderer:
    FLAG_BASE = 127397
    MAIN_COLOR = 0x2ECC71
    ERROR_COLOR = 0xE74C3C
    HEADER_COLOR = "#FF69B4"

    def __init__(self, bot: OsuArena):
        self.bot = bot
        self.osu_client = bot.osu_client

    def get_flag(self, country_code: str) -> str:
        if not country_code:
            return "🏳️"
        return "".join(chr(self.FLAG_BASE + ord(c)) for c in country_code.upper())

    def format_relative_time(self, date: datetime) -> str:
        ts = int(date.timestamp())
        return f"<t:{ts}:R>"

    def format_duration(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def format_mods(self, mod_list: list[str]) -> str:
        return "+" + "".join(mod_list) if mod_list else "+NM"

    async def ensure_full_user(self, user):
        if user.statistics is None or user.country_code is None:
            try:
                return await self.osu_client.get_user(user.id, mode="osu")
            except Exception as e:
                print(f"Renderer Error: Could not fetch full user: {e}")
                return user
        return user


class Renderer(BaseRenderer):
    def __init__(self, bot: OsuArena):
        super().__init__(bot)
        self.score = ScoreRenderer(bot)
        self.leaderboard = LeaderboardRenderer(bot)


class ScoreRenderer(BaseRenderer):
    GRADE_EMOJIS = {
        "XH": "<:XH:1449232200368259265>",
        "X": "<:X_:1449232164771332096>",
        "SH": "<:SH:1449232118751297670>",
        "S": "<:S_:1449232073779974194>",
        "A": "<:A_:1449231818392998030>",
        "B": "<:B_:1449231894368485528>",
        "C": "<:C_:1449231970126135438>",
        "D": "<:D_:1449232012341674085>",
        "F": "💔",
    }

    async def render(self, play: SoloScore | LegacyScore) -> discord.Embed:
        user = await self.ensure_full_user(play.user)
        stats = self._normalize_stats(play)

        embed = discord.Embed(color=self.MAIN_COLOR)
        self._build_author(embed, user)
        self._build_header(embed, play.beatmapset, play.beatmap)
        self._build_description(embed, play.beatmap, stats)
        self._build_footer(embed, play.beatmapset)

        return embed

    def _normalize_stats(self, play: SoloScore | LegacyScore) -> dict:
        """Unifies Lazer (SoloScore) and Stable (LegacyScore) data structures."""
        is_lazer = isinstance(play, SoloScore)

        if is_lazer:
            return {
                "date": play.ended_at,
                "score": play.total_score,
                "accuracy": play.accuracy * 100,
                "mods": [m.mod.value for m in play.mods],
                "combo": play.max_combo,
                "pp": play.pp if play.pp else 0,
                "misses": getattr(play.statistics, "miss", 0),
                "rank": play.rank.name,
            }
        else:
            return {
                "date": play.created_at,
                "score": play.score,
                "accuracy": play.accuracy * 100,
                "mods": [m.value for m in play.mods],
                "combo": play.max_combo,
                "pp": play.pp if play.pp else 0,
                "misses": play.statistics.count_miss,
                "rank": play.rank.name,
            }

    def _build_author(self, embed: discord.Embed, user):
        try:
            total_pp = user.statistics.pp
            g_rank = (
                f"#{user.statistics.global_rank}"
                if user.statistics.global_rank
                else "-"
            )
            c_code = user.country_code
            c_rank = user.statistics.country_rank
            flag = self.get_flag(c_code)
        except AttributeError:
            total_pp, g_rank, c_code, c_rank, flag = 0, "-", "??", 0, "🏳️"

        text = f"{flag} {user.username}: {total_pp:,.0f}pp ({g_rank} {c_code}{c_rank})"
        embed.set_author(
            name=text, url=f"https://osu.ppy.sh/u/{user.id}", icon_url=user.avatar_url
        )

    def _build_header(self, embed: discord.Embed, beatmapset, beatmap):
        embed.title = f"{beatmapset.artist} - {beatmapset.title} [{beatmap.version}] [{beatmap.difficulty_rating:.2f}★]"
        embed.url = f"https://osu.ppy.sh/b/{beatmap.id}"
        if beatmapset.covers.list_2x:
            embed.set_thumbnail(url=beatmapset.covers.list_2x)

    def _build_description(self, embed: discord.Embed, beatmap, stats: dict):
        grade = self.GRADE_EMOJIS.get(stats["rank"], "❓")
        mods = self.format_mods(stats["mods"])
        time = self.format_relative_time(stats["date"])
        length = self.format_duration(beatmap.total_length)

        desc = (
            f"__**New Top Play**__\n"
            f"{grade} **{mods}** • {stats['score']:,} • **{stats['accuracy']:.2f}%** • {time}\n"
            f"**{stats['pp']:.2f}**pp • **{stats['combo']}x**/{beatmap.max_combo}x • {stats['misses']} ❌\n"
            f"`{length}` • BPM: `{beatmap.bpm}` • CS: `{beatmap.cs}` AR: `{beatmap.ar}` OD: `{beatmap.accuracy}` HP: `{beatmap.drain}`"
        )
        embed.description = desc

    def _build_footer(self, embed: discord.Embed, beatmapset):
        embed.set_footer(
            text=f"Mapset by {beatmapset.creator} • Status: {beatmapset.status.name.capitalize()}"
        )


class LeaderboardRenderer(BaseRenderer):
    ODD_ROW_COLOR = "#000000"
    EVEN_ROW_COLOR = "#222222"
    TEXT_COLOR = "white"
    FONT_SIZE = 14

    async def render_image(
        self, headers: List[str], rows: List[Tuple[Any, ...]]
    ) -> Optional[BytesIO]:
        if not rows:
            return None

        df = pd.DataFrame(rows, columns=headers)
        first_col_name = df.columns[0]
        n_rows, n_cols = df.shape

        fig_width = n_cols * 3
        fig_height = n_rows * 0.6 + 1

        fig = None

        try:
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            fig.set_facecolor("black")
            ax.axis("off")

            Table(
                df,
                ax=ax,
                index_col=first_col_name,
                textprops={
                    "fontsize": self.FONT_SIZE,
                    "color": self.TEXT_COLOR,
                    "ha": "center",
                    "family": "sans-serif",
                },
                column_definitions=self._get_column_defs(),
                col_label_cell_kw={
                    "facecolor": self.HEADER_COLOR,
                    "edgecolor": "white",
                    "linewidth": 1.5,
                },
                cell_kw={"edgecolor": "white", "linewidth": 1.5},
                odd_row_color=self.ODD_ROW_COLOR,
                even_row_color=self.EVEN_ROW_COLOR,
            )

            buf = BytesIO()
            plt.savefig(
                buf,
                format="png",
                bbox_inches="tight",
                dpi=250,
                facecolor=fig.get_facecolor(),
            )
            buf.seek(0)
            return buf

        except Exception as e:
            print(f"LeaderboardRenderer Error: {e}")
            return None
        finally:
            if fig:
                plt.close(fig)

    def _get_column_defs(self) -> List[ColumnDefinition]:
        return [
            ColumnDefinition(
                name="osu_username",
                textprops={"weight": "bold", "ha": "left"},
                width=1.2,
            ),
            ColumnDefinition(
                name="challenger", textprops={"weight": "bold", "ha": "left"}, width=1.2
            ),
            ColumnDefinition(
                name="challenged", textprops={"weight": "bold", "ha": "left"}, width=1.2
            ),
        ]
