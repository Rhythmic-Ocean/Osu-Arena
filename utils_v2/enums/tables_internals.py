from enum import StrEnum
from typing import TypedDict


class LeagueColumn(StrEnum):
    DISCORD_USERNAME = "discord_username"
    OSU_USERNAME = "osu_username"
    INITIAL_PP = "initial_pp"
    CURRENT_PP = "current_pp"
    PP_CHANGE = "pp_change"
    GLOBAL_RANK = "global_rank"
    ID = "id"
    PERCENTAGE_CHANGE = "percentage_change"
    II = "ii"
    DISCORD_ID = "discord_id"


class LeagueData(TypedDict):
    discord_username: str
    osu_username: str
    initial_pp: int
    current_pp: int
    pp_change: int
    global_rank: int
    id: int
    percentage_change: float
    ii: float


class DiscordOsuColumn(StrEnum):
    DISCORD_USERNAME = "discord_username"
    OSU_USERNAME = "osu_username"
    CURRENT_PP = "current_pp"
    OSU_ID = "osu_id"
    LEAGUE = "league"
    GLOBAL_RANK = "global_rank"
    FUTURE_LEAGUE = "future_league"
    DISCORD_ID = "discord_id"
    II = "ii"
    TOP_PLAY_MAP = "top_play_map"
    TOP_PLAY_PP = "top_play_pp"
    TOP_PLAY_DATE = "top_play_date"
    TOP_PLAY_ID = "top_play_id"
    TOP_PLAY_ANNOUNCE = "top_play_announce"
    NEW_PLAYER_ANNOUNCE = "new_player_announce"
    POINTS = "points"
    SEASONAL_POINTS = "seasonal_points"


class DiscordOsuData(TypedDict):
    discord_username: str
    osu_username: str
    current_pp: int
    osu_id: int
    league: str
    global_rank: int
    future_league: str
    discord_id: int
    ii: float
    top_play_map: str
    top_play_pp: int
    top_play_date: str  # Timestamptz comes through as an ISO string
    top_play_id: int
    top_play_announce: bool
    new_player_announce: bool
    points: int
    seasonal_points: int


class MiscColumn(StrEnum):
    ID = "id"
    VARIABLE = "variable"
    STATUS = "status"


class MiscData(TypedDict, total=False):
    id: int
    variable: str
    status: bool


# Historical Points Table
class HistoricalPointsColumn(StrEnum):
    ID = "id"
    DISCORD_USERNAME = "discord_username"
    OSU_USERNAME = "osu_username"
    DISCORD_ID = "discord_id"


class HistoricalPointsData(TypedDict, total=False):
    id: int
    discord_username: str
    osu_username: str


class ChallengeUserColumn(StrEnum):
    ID = "id"
    DISCORD_USERNAME = "discord_username"
    OSU_USERNAME = "osu_username"
    CHALLENGE_ID = "challenge_id"
    INITIAL_PP = "initial_pp"
    CURRENT_PP = "current_pp"
    DISCORD_ID = "discord_id"


class ChallengeUserData(TypedDict, total=False):
    id: int
    discord_username: str
    osu_username: str
    challenge_id: int
    initial_pp: int
    current_pp: int


class MessageIdColumn(StrEnum):
    ID = "id"
    MSG_ID = "msg_id"
    CHALLENGE_ID = "challenge_id"


class MessageIdData(TypedDict, total=False):
    id: int
    msg_id: int
    challenge_id: int


class SeasonColumn(StrEnum):
    ID = "id"
    STATUS = "status"
    SEASON = "season"


class SeasonData(TypedDict, total=False):
    id: int
    status: str
    season: int


class RivalsColumn(StrEnum):
    CHALLENGE_ID = "challenge_id"
    LEAGUE = "league"
    CHALLENGER = "challenger"
    CHALLENGED = "challenged"
    CHALLENGER_INITIAL_PP = "challenger_initial_pp"
    CHALLENGER_FINAL_PP = "challenger_final_pp"
    CHALLENGED_INITIAL_PP = "challenged_initial_pp"
    CHALLENGED_FINAL_PP = "challenged_final_pp"
    ISSUED_AT = "issued_at"
    CHALLENGE_STATUS = "challenge_status"
    FOR_PP = "for_pp"
    CHALLENGED_STATS = "challenged_stats"
    CHALLENGER_STATS = "challenger_stats"
    WINNER = "winner"


class RivalsData(TypedDict, total=False):
    challenge_id: int
    league: str
    challenger: str
    challenged: str
    challenger_initial_pp: int
    challenger_final_pp: int
    challenged_initial_pp: int
    challenged_final_pp: int
    issued_at: str
    challenge_status: str
    for_pp: int
    challenged_stats: float
    challenger_stats: float
    winner: str
