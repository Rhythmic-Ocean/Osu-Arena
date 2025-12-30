from __future__ import annotations
from typing import Any, TYPE_CHECKING
import discord
import datetime
from discord.ext import commands, tasks
from supabase import AsyncClient
from utils_v2 import (
    ChallengeStatus,
    RivalsColumn,
    TablesRivals,
    RivalsData,
    DiscordOsuColumn,
    Renderer,
)
from load_env import ENV

if TYPE_CHECKING:
    from bot import OsuArena


class Monitor(commands.Cog, name="monitor"):
    def __init__(self, bot: OsuArena, supabase_client: AsyncClient):
        self.bot = bot
        self.supabase_client = supabase_client
        self.log_handler = self.bot.log_handler
        self.db_handler = self.bot.db_handler
        self.osu_client = self.bot.osu_client
        self.renderer = Renderer(self.bot)
        self.logger = self.log_handler.logger

        self.monitor_database.start()

    def cog_unload(self):
        self.monitor_database.cancel()

    @tasks.loop(seconds=10)
    async def monitor_database(self):
        try:
            await self.monitor_new_players()
            await self.monitor_top_plays()
            await self.monitor_rivals()
        except Exception as e:
            await self.log_handler.report_error("Monitor.monitor_database_loop", e)

    @monitor_database.before_loop
    async def before_monitor_database(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = discord.utils.get(member.guild.roles, name="Inactive")
        if role:
            await member.add_roles(role)
        else:
            error = Exception("Unable to handle role.")
            self.log_handler.report_error(
                "Monitor.on_member_join()",
                error,
                f"Error handling <@{member.id}> Inactive role",
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        discord_id = member.id
        user_name = member.name

        self.log_handler.report_info(
            f"User left: {user_name} ({discord_id}). Processing deletion..."
        )

        try:
            response = await (
                self.supabase_client.table("discord_osu")
                .delete()
                .eq("discord_id", discord_id)
                .execute()
            )

            if response.data:
                msg = f"Successfully wiped data for {user_name}."
                self.log_handler.report_info(msg)

                guild = member.guild
                if not guild:
                    self.logger.warning("Sync Error: Guild not found.")
                    return
                channel = guild.get_channel(ENV.BOT_UPDATES)

                if channel:
                    embed = discord.Embed(
                        title="User Left & Data Wiped",
                        description=f"**{user_name}** (`{discord_id}`) left the server.\nDeleted their record from `discord_osu`.",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now(),
                    )
                    await channel.send(embed=embed)
            else:
                self.log_handler.report_info(
                    f"User {user_name} left, but was not in the database."
                )

        except Exception as e:
            await self.log_handler.report_error(
                f"Monitor.on_member_remove({user_name})", e
            )

    async def monitor_new_players(self):
        try:
            new_players = await self.db_handler.new_player_detector()
            if not new_players:
                return
            for player in new_players:
                try:
                    discord_id = player[DiscordOsuColumn.DISCORD_ID]
                    if not await self.db_handler.negate_new_player_announce(discord_id):
                        raise Exception(
                            f"New player announce negation failed! Got False for <@{discord_id}>"
                        )
                    await self.give_role_nickname(player)
                    await self.announce_new_player(player)
                except Exception as error:
                    await self.log_handler.report_error(
                        "Monitor.monitor_new_players() loop", error
                    )
        except Exception as e:
            await self.log_handler.report_error(
                "Monitor.monitor_new_players() outer", e
            )

    async def monitor_top_plays(self):
        try:
            top_plays = await self.db_handler.top_play_detector()
            if not top_plays:
                return
            for play in top_plays:
                try:
                    discord_id = play[DiscordOsuColumn.DISCORD_ID]
                    if not await self.db_handler.negate_top_play(discord_id):
                        raise Exception(
                            f"Top play negation failed! Got False for <@{discord_id}>"
                        )
                    top_play_id = play[DiscordOsuColumn.TOP_PLAY_ID]
                    await self.announce_new_top_play(top_play_id, discord_id)
                except Exception as error:
                    await self.log_handler.report_error(
                        "Monitor.monitor_top_plays() loop", error
                    )
        except Exception as e:
            await self.log_handler.report_error("Monitor.monitor_top_plays() outer", e)

    async def monitor_rivals(self):
        try:
            rivals_table = await self.get_rivals()
            for row in rivals_table:
                try:
                    is_end = await self.check_end(row)
                    if is_end:
                        winner, loser = is_end
                        await self.end_challenge(row, winner, loser)
                        await self.send_announcement(row, winner, loser)
                except Exception as e:
                    await self.log_handler.report_error(
                        "Monitor.monitor_rivals() loop", e
                    )
        except Exception as e:
            await self.log_handler.report_error("Monitor.monitor_rivals() outer", e)

    async def give_role_nickname(self, player: list[dict[str, Any]]) -> None:
        discord_id = player[DiscordOsuColumn.DISCORD_ID]
        player_league = player[DiscordOsuColumn.LEAGUE]
        osu_username = player[DiscordOsuColumn.OSU_USERNAME]
        guild = self.bot.guild
        if not guild:
            return

        try:
            member = await guild.fetch_member(discord_id)
        except discord.NotFound:
            return

        role = discord.utils.get(guild.roles, name=player_league.capitalize())
        role_part = discord.utils.get(guild.roles, name="Participant")

        try:
            for role_m in member.roles:
                if role_m.name == "Inactive":
                    await member.remove_roles(role_m)

            if role:
                await member.add_roles(role)
            if role_part:
                await member.add_roles(role_part)

        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.give_role_nickname()",
                error,
                f"Failed giving roles to <@{discord_id}>",
            )

        try:
            await member.edit(nick=osu_username)
        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.give_role_nickname()",
                error,
                f"Failed to change nickname for <@{discord_id}>",
            )

    async def announce_new_player(self, player: list[dict[str, Any]]) -> None:
        guild = self.bot.guild
        discord_id = player[DiscordOsuColumn.DISCORD_ID]
        player_league = player[DiscordOsuColumn.LEAGUE]

        if not guild:
            error = Exception("Can't find Guild for Monitor.announce_new_player()")
            await self.log_handler.report_error(
                "Monitor.announce_new_player()",
                error,
            )
            return

        channel = guild.get_channel(ENV.WELCOME_ID)
        try:
            if channel:
                await channel.send(
                    f"<@{discord_id}>, you have been assigned to {player_league.capitalize()} league."
                )
        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.announce_new_player()",
                error,
                f"Could not announce <@{discord_id}>'s arrival!",
            )

    async def announce_new_top_play(self, top_play_id: int, discord_id: int):
        top_play = await self.osu_client.get_score_by_id_only(top_play_id)
        embed = await self.renderer.score.render(top_play)
        content_str = (
            f"New Top Play from <@{discord_id}>!" if discord_id else "New Top Play!"
        )
        guild = self.bot.guild
        if not guild:
            error = Exception("Can't find Guild for Monitor.announce_new_top_play()")
            await self.log_handler.report_error(
                "Monitor.announce_new_top_play()", error
            )
            return

        channel = guild.get_channel(ENV.TOP_PLAY_ID)
        try:
            if channel:
                await channel.send(content=content_str, embed=embed)
        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.announce_new_top_play()", error
            )

    async def check_end(self, row: RivalsColumn) -> tuple[str, str] | None:
        for_pp = row[RivalsColumn.FOR_PP]
        challenger_stats = row[RivalsColumn.CHALLENGER_STATS]
        challenged_stats = row[RivalsColumn.CHALLENGED_STATS]
        if challenger_stats >= for_pp:
            return (RivalsColumn.CHALLENGER, RivalsColumn.CHALLENGED)
        elif challenged_stats >= for_pp:
            return (RivalsColumn.CHALLENGED, RivalsColumn.CHALLENGER)
        else:
            return None

    async def get_rivals(self) -> list[RivalsData]:
        REQ_COLUMNS = ", ".join(
            [
                RivalsColumn.CHALLENGER,
                RivalsColumn.CHALLENGED,
                RivalsColumn.CHALLENGE_ID,
                RivalsColumn.FOR_PP,
                RivalsColumn.CHALLENGER_STATS,
                RivalsColumn.CHALLENGED_STATS,
            ]
        )
        try:
            query = (
                await self.supabase_client.table(TablesRivals.RIVALS)
                .select(REQ_COLUMNS)
                .eq(RivalsColumn.CHALLENGE_STATUS, ChallengeStatus.PENDING)
                .execute()
            )
            return query.data if (query and query.data) else []
        except Exception as e:
            print(f"Exception fetching rivals: {e}")
            return []

    async def end_challenge(self, row: RivalsColumn, winner: str, loser: str) -> None:
        winner_uname = row[winner]
        loser_uname = row[loser]
        challenge_id = row[RivalsColumn.CHALLENGE_ID]
        try:
            await (
                self.supabase_client.table(TablesRivals.RIVALS)
                .update(
                    {
                        RivalsColumn.CHALLENGE_STATUS: ChallengeStatus.FINISHED,
                        RivalsColumn.WINNER: winner_uname,
                    }
                )
                .eq(RivalsColumn.CHALLENGE_ID, challenge_id)
                .execute()
            )
            await self.challenge_finish_point_distribution(
                winner_uname, loser_uname, row[RivalsColumn.FOR_PP]
            )
        except Exception as e:
            await self.log_handler.report_error(
                "Monitor.end_challenge()",
                e,
                f"Failed updating Challenge Status for challenge_id {challenge_id}",
            )

    async def send_announcement(
        self, row: RivalsColumn, winner: str, loser: str
    ) -> None:
        winner_uname = row[winner]
        loser_uname = row[loser]
        for_pp = row[RivalsColumn.FOR_PP]
        winner_id = await self.db_handler.get_discord_id(osu_username=winner_uname)
        loser_id = await self.db_handler.get_discord_id(osu_username=loser_uname)

        if not winner_id or not loser_id:
            await self.log_handler.report_error(
                "Monitor.send_announcement()",
                Exception("Could not find winner/loser Discord IDs"),
            )
            return

        msg_id = await self.db_handler.get_msg_id(row[RivalsColumn.CHALLENGE_ID])
        guild = self.bot.guild
        if not guild:
            await self.log_handler.report_error(
                "Monitor.send_announcement()",
                Exception("Guild not found"),
            )
            return

        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)
        if not channel:
            await self.log_handler.report_error(
                "Monitor.send_announcement()", Exception("Rivals Channel not found")
            )
            return

        content = f"<@{winner_id}> vs <@{loser_id}> | {for_pp}PP | Finished. WINNER: <@{winner_id}>"

        try:
            if msg_id is None:
                await channel.send(content)
            else:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(content=content)
                except discord.NotFound:
                    await channel.send(content)
        except Exception as error:
            await self.log_handler.report_error("Monitor.send_announcement", error)

        await self.point_distribution_announcement(winner_id, loser_id, for_pp)

    async def challenge_finish_point_distribution(self, winner, loser, for_pp):
        try:
            response1 = await self.db_handler.add_points(winner, for_pp)
            response2 = await self.db_handler.add_points(loser, -int(round(for_pp / 2)))
            if response1 and response2:
                return True
            raise Exception(
                f"Unable to update rivarly_end points for {winner} and {loser}"
            )
        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.challenge_finish_point_distribution()", error
            )

    async def point_distribution_announcement(self, winner_id, loser_id, for_pp):
        win_points = for_pp
        lose_points = int(round(for_pp / 2))
        guild = self.bot.guild
        if not guild:
            error = Exception(
                "Can't find Guild for Monitor.point_distribution_announcement()"
            )
            await self.log_handler.report_error(
                "Monitor.point_distribution_announcement()",
                error,
            )
            return
        channel = guild.get_channel(ENV.BOT_UPDATES)
        try:
            if channel:
                await channel.send(
                    f"<@{winner_id}> vs <@{loser_id}> | {for_pp}PP | Finished. WINNER: <@{winner_id}>\n"
                    f"<@{winner_id}> +{win_points}\n"
                    f"<@{loser_id}> -{lose_points}\n"
                )
            else:
                raise Exception("Could not find Bot Updates channel!!")
        except Exception as error:
            await self.log_handler.report_error(
                "Monitor.point_distribution_announcement", error
            )


async def setup(bot: OsuArena):
    await bot.add_cog(Monitor(bot, bot.supabase_client))
