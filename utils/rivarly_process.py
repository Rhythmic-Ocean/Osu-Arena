"""
Rivalry Processing & UI Interaction.

This module handles the creation of new challenges and the user interaction
components (Buttons) for accepting or declining challenges. It acts as the
bridge between the Discord UI and the database transactions for new matches.
"""

from .db_getter import get_osu_uname, get_pp
from .core_v2 import create_supabase, CHALLENGE_STATUS
import logging
import discord
from discord.ui import View, Button
from typing import Optional

"""
Classes and Functions in this module:
1. class ChallengeView(View)
2. log_rivals(leag: str, challenger: str, challenged: str, pp: float) -> int | None
3. store_msg_id(challenge_id: int, msg_id: int) -> None
"""

logging.basicConfig(filename="rivalry_process.log", level=logging.DEBUG, filemode="w")


class ChallengeView(View):
    """
    A Discord UI View containing 'Accept' and 'Decline' buttons for a challenge.

    Attributes:
        challenged (discord.Member): The user who is allowed to interact with the buttons.
        response (bool | None): The result of the interaction.
                                True = Accepted, False = Declined, None = No action.
    """

    def __init__(self, challenged: discord.Member, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.challenged = challenged
        self.response = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        """Callback for the Accept button."""
        if interaction.user != self.challenged:
            await interaction.response.send_message(
                "This challenge is not for you.", ephemeral=True
            )
            return
        self.response = True
        await interaction.response.send_message(
            f"{self.challenged.mention} has accepted the challenge!"
        )
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        """Callback for the Decline button."""
        if interaction.user != self.challenged:
            await interaction.response.send_message(
                "This challenge is not for you.", ephemeral=True
            )
            return
        self.response = False
        await interaction.response.send_message(
            f"{self.challenged.mention} has declined the challenge."
        )
        self.stop()


async def log_rivals(
    leag: str, challenger: str, challenged: str, pp: float
) -> Optional[int]:
    """
    Logs a new challenge into the database.

    This function performs the following steps:
    1. Fetches osu! usernames and current PP for both users.
    2. Inserts a new record into the 'rivals' table with status 'Pending'.
    3. Inserts linked records into the 'challenger' and 'challenged' reference tables.

    Args:
        leag (str): The league name (e.g., 'gold').
        challenger (str): Discord username of the challenger.
        challenged (str): Discord username of the challenged.
        pp (float): The PP threshold for the challenge.

    Returns:
        int | None: The unique 'challenge_id' if successful, None otherwise.
    """
    supabase = await create_supabase()
    league = leag.lower()

    try:
        challenger_uname = await get_osu_uname(challenger)
        challenged_uname = await get_osu_uname(challenged)

        if not challenger_uname or not challenged_uname:
            logging.warning(
                f"Missing osu username for challenger ({challenger}) or challenged ({challenged})."
            )
            return None

        challenger_pp = await get_pp(discord_username=challenger)
        challenged_pp = await get_pp(discord_username=challenged)

        if challenger_pp is None or challenged_pp is None:
            logging.warning(
                f"Missing PP data for challenger ({challenger}) or challenged ({challenged})."
            )
            return None

        # Insert main challenge record
        response = (
            await supabase.table("rivals")
            .insert(
                {
                    "league": league,
                    "challenger": challenger_uname,
                    "challenged": challenged_uname,
                    "for_pp": pp,
                    "challenger_initial_pp": challenger_pp,
                    "challenged_initial_pp": challenged_pp,
                    "challenge_status": CHALLENGE_STATUS[1],  # Pending
                }
            )
            .execute()
        )

        if not response.data or "challenge_id" not in response.data[0]:
            logging.error("Failed to insert into 'rivals' or missing 'challenge_id'")
            return None

        challenge_id = response.data[0]["challenge_id"]

        # Insert related table records
        try:
            await (
                supabase.table("challenged")
                .insert(
                    {
                        "challenge_id": challenge_id,
                        "discord_username": challenged,
                        "osu_username": challenged_uname,
                        "initial_pp": challenged_pp,
                    }
                )
                .execute()
            )

            await (
                supabase.table("challenger")
                .insert(
                    {
                        "challenge_id": challenge_id,
                        "discord_username": challenger,
                        "osu_username": challenger_uname,
                        "initial_pp": challenger_pp,
                    }
                )
                .execute()
            )

        except Exception as e:
            logging.error(
                f"Error inserting into sub-tables (challenger/challenged): {e}"
            )
            # Note: We might want to handle rollback here if strict consistency is required
            pass

        return challenge_id

    except Exception as e:
        logging.error(f"Error in log_rivals(): {e}")
        return None


async def store_msg_id(challenge_id: int, msg_id: int) -> None:
    """
    Links a Discord Message ID to a Challenge ID.

    This allows the bot to find and edit the original challenge announcement
    later (e.g., when the challenge is finished).

    Args:
        challenge_id (int): The unique challenge identifier.
        msg_id (int): The Discord message ID of the announcement.
    """
    supabase = await create_supabase()
    try:
        await (
            supabase.table("mesg_id")
            .insert({"msg_id": msg_id, "challenge_id": challenge_id})
            .execute()
        )
    except Exception as e:
        logging.error(f"Error when storing mesg_id: {e}")

