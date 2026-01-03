from __future__ import annotations
import asyncio
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
    TablesLeagues,
)
from zoneinfo import ZoneInfo
from load_env import ENV
from utils_v2.enums.status import FuncStatus

if TYPE_CHECKING:
    from bot import OsuArena

MAX_TRIES = 3

weekly_time = datetime.time(hour=15, minute=12, tzinfo=ZoneInfo("America/Chicago"))


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
        self.weekly_point_update.start()

    def cog_unload(self):
        self.monitor_database.cancel()
        self.weekly_point_update.cancel()

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

    @tasks.loop(time=weekly_time)
    async def weekly_point_update(self):
        naw = datetime.datetime.now(ZoneInfo("America/Chicago"))
        if naw.weekday() != 5:
            return

        guild = self.bot.guild
        channel = guild.get_channel(ENV.BOT_UPDATES)

        for a_league in TablesLeagues:
            try:
                await self.supabase_client.rpc(
                    "sync_table_pp", {"tbl_name": a_league}
                ).execute()
            except Exception as error:
                await self.log_handler.report_error(
                    "Monitor.weekly_point_update()",
                    error,
                    f"Error syncing {a_league.capitalize()}",
                )
                continue

            try:
                response = await self.supabase_client.rpc(
                    "award_weekly_winner", {"league_table_name": a_league}
                ).execute()
            except Exception as error:
                await self.log_handler.report_error(
                    "Monitor.weekly_point_update()",
                    error,
                    "Error at function rpc function awark weekly winner()",
                )
                return

            datas = response.data

            if datas and channel:
                for row in datas:
                    # 1. Parse the dictionary keys returned by Postgres
                    discord_id = row["discord_id"]
                    total_points = row["new_points"]
                    seasonal_points = row["new_seasonal_points"]

                    # 2. Create a nice formatted message
                    message = (
                        f"🏆 **Weekly Winner: {a_league}**\n"
                        f"Congratulations <@{discord_id}>! You've been awarded **+100 points**.\n"
                        f"> **Total Points:** {total_points}\n"
                        f"> **Seasonal Points:** {seasonal_points}"
                    )

                    try:
                        await channel.send(content=message)
                    except Exception as error:
                        await self.log_handler.report_error(
                            "Monitor.weekly_point_update()",
                            error,
                            "Error sending message to channel.",
                        )

    @weekly_point_update.before_loop
    async def before_weekly_point_update(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        role = discord.utils.get(member.guild.roles, name="Inactive")
        if role:
            await member.add_roles(role)
        else:
            error = Exception("Unable to handle role.")
            await self.log_handler.report_error(
                "Monitor.on_member_join()",
                error,
                f"Error handling <@{member.id}> Inactive role",
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        discord_id = member.id
        user_name = member.name

        await self.log_handler.report_info(
            f"User left: {user_name} (<@{discord_id}>). Processing deletion..."
        )
        # to use  later to revoke rivals, fails silently if no such user exists
        osu_username = await self.db_handler.get_username(discord_id)

        try:
            response = await (
                self.supabase_client.table("discord_osu")
                .delete()
                .eq("discord_id", discord_id)
                .execute()
            )

            if response.data:
                msg = f"Successfully wiped data for {user_name}."
                await self.log_handler.report_info(msg)

                guild = member.guild
                if not guild:
                    await self.logger.warning("Sync Error: Guild not found.")
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
                await self.log_handler.report_info(
                    f"User {user_name} left, but was not in the database."
                )
            if osu_username:
                challenges = await self.db_handler.get_active_challenges(
                    discord_id, osu_username
                )
                if challenges == FuncStatus.ERROR:
                    error = Exception(f"Error when {user_name} left.")
                    await self.log_handler.report_error(
                        "Monitor.on_member_remove()",
                        error,
                        f"⚠️ Failed retriving any existing challenges for <@{discord_id}>. Please delete any of their existing challenges manually.",
                    )
                    return

                if not len(challenges):
                    await self.log_handler.report_info(
                        f"⚠️ No existing challenges for {user_name} <@{discord_id}>."
                    )
                    return

                total_revoked_challenges = 0
                for challenge in challenges:
                    if await self.revoke_challenge(challenge):
                        total_revoked_challenges += 1
                await self.log_handler.report_info(
                    f"⚠️{total_revoked_challenges}/{len(challenges)} challenges revoked."
                )

        except Exception as e:
            await self.log_handler.report_error(
                f"Monitor.on_member_remove({user_name})", e
            )

    async def monitor_new_players(self):
        for tries in range(MAX_TRIES):
            try:
                new_players = await self.db_handler.new_player_detector()
                if not new_players:
                    return
                for player in new_players:
                    try:
                        discord_id = player[DiscordOsuColumn.DISCORD_ID]
                        if not await self.db_handler.negate_new_player_announce(
                            discord_id
                        ):
                            raise Exception(
                                f"New player announce negation failed! Got False for <@{discord_id}>"
                            )
                        await self.give_role_nickname(player)
                        await self.announce_new_player(player)
                    except Exception as error:
                        await self.log_handler.report_error(
                            "Monitor.monitor_new_players() loop", error
                        )
                return
            except Exception as e:
                if tries == MAX_TRIES - 1:
                    await self.log_handler.report_error(
                        "Monitor.monitor_new_players() outer", e
                    )
                await self.log_handler.report_info(
                    f"Failed running Monitor.monitor_new_players(). Current tries : {tries + 1}/{MAX_TRIES}.\nThis process will sleep for 5 extra seconds before trying again."
                )
                await asyncio.sleep(5)

    async def monitor_top_plays(self):
        if not self.osu_client:
            raise Exception()
            self.log_handler.report_error()
        for tries in range(MAX_TRIES):
            try:
                top_plays = await self.db_handler.top_play_detector()

                if not top_plays:
                    return

                for play in top_plays:
                    for tries in range(MAX_TRIES):
                        try:
                            discord_id = play[DiscordOsuColumn.DISCORD_ID]
                            top_play_id = play[DiscordOsuColumn.TOP_PLAY_ID]
                            await self.announce_new_top_play(top_play_id, discord_id)
                            if not await self.db_handler.negate_top_play(discord_id):
                                raise Exception(
                                    f"Top play negation failed! Got False for <@{discord_id}>"
                                )
                            break
                        except Exception as error:
                            if tries == MAX_TRIES - 1:
                                await self.log_handler.report_error(
                                    "Monitor.monitor_top_plays() loop",
                                    error,
                                    f"Error for top_play: {top_play_id}, error announcing for <@{discord_id}>",
                                )
                            await self.log_handler.report_info(
                                f"Failed running Monitor.monitor_top_plays() loop . Current tries : {tries + 1}/{MAX_TRIES}.\nThis process will sleep for 5 seconds before trying again.\n Error announcing top play for player <@{discord_id}>."
                            )
                            await asyncio.sleep(5)
                return

            except Exception as e:
                if tries == MAX_TRIES - 1:
                    await self.log_handler.report_error(
                        "Monitor.monitor_top_plays() outer", e
                    )

                await self.log_handler.report_info(
                    f"Failed running Monitor.monitor_top_plays(). Current tries : {tries + 1}/{MAX_TRIES}.\nThis process will sleep for 5 seconds before trying again."
                )
                await asyncio.sleep(5)

    async def monitor_rivals(self):
        for tries in range(MAX_TRIES):
            try:
                rivals_table = await self.get_rivals()

                if not rivals_table:
                    return

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
                return

            except Exception as e:
                if tries == MAX_TRIES - 1:
                    await self.log_handler.report_error(
                        "Monitor.monitor_rivals() outer", e
                    )

                await self.log_handler.report_info(
                    f"Failed running Monitor.monitor_rivals(). Current tries : {tries + 1}/{MAX_TRIES}.\nThis process will sleep for 5 seconds before trying again."
                )
                await asyncio.sleep(5)

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
            else:
                raise Exception(
                    f"Could not find top play channel. Failed to announce top play for <@{discord_id}>"
                )
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
                .eq(RivalsColumn.CHALLENGE_STATUS, ChallengeStatus.UNFINISHED)
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
            response1 = await self.db_handler.add_points(for_pp, osu_username=winner)
            response2 = await self.db_handler.add_points(
                -int(round(for_pp / 2)), osu_username=loser
            )
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

    async def revoke_challenge(self, challenge: dict[str, Any]):
        challenger = challenge[RivalsColumn.CHALLENGER]
        challenged = challenge[RivalsColumn.CHALLENGED]
        challenge_id = challenge[RivalsColumn.CHALLENGE_ID]

        revoke_success = await self.db_handler.revoke_challenge(challenge_id)
        if not revoke_success:
            error = Exception(
                f"Failed to revoke challenge, challenge_id : {challenge_id}. {challenger} vs {challenged}"
            )
            await self.log_handler.report_error(
                "PlayerManagement.revoke_challenge()",
                error,
            )
            return False

        msg_id = await self.db_handler.get_msg_id(challenge_id)
        guild = self.bot.guild
        channel = guild.get_channel(ENV.RIVAL_RESULTS_ID)

        if not channel:
            return True
        new_content = f"{challenger} vs {challenged} | Revoked"
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                if msg:
                    await msg.edit(content=new_content)
            except discord.NotFound:
                await channel.send(content=new_content)
        return True


async def setup(bot: OsuArena):
    await bot.add_cog(Monitor(bot, bot.supabase_client))
