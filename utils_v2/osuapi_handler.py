from __future__ import annotations
from osu import AsynchronousClient
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import OsuArena


class OsuAPI_Handler:
    def __init__(self, bot: OsuArena, osu_client: AsynchronousClient) -> None:
        self.bot = bot
        self.osu_client = osu_client
