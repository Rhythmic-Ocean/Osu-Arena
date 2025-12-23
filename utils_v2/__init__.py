from . import enums

from .enums import (
    TableAll,
    ChallengeStatus,
    TablesLeagues,
    TablesRivals,
    TableMiscellaneous,
    TablesLeaguesDeprecated,
    TablesPoints,
    LeagueColumn,
    DiscordOsuColumn,
    MiscColumn,
    HistoricalPointsColumn,
    RivalsColumn,
    ChallengeUserColumn,
    MessageIdColumn,
    SeasonColumn,
    LeagueData,
    DiscordOsuData,
    MiscData,
    HistoricalPointsData,
    RivalsData,
    ChallengeUserData,
    MessageIdData,
    SeasonData,
)

from .error_handler import ErrorHandler

__all__ = [
    # Table Namespaces
    "TableAll",
    "ChallengeStatus",
    "TablesLeagues",
    "TablesRivals",
    "TableMiscellaneous",
    "TablesLeaguesDeprecated",
    "TablesPoints",
    # Column Enums (For Writing/Queries)
    "LeagueColumn",
    "DiscordOsuColumn",
    "MiscColumn",
    "HistoricalPointsColumn",
    "RivalsColumn",
    "ChallengeUserColumn",
    "MessageIdColumn",
    "SeasonColumn",
    # Data Models (For Reading/Autocomplete)
    "LeagueData",
    "DiscordOsuData",
    "MiscData",
    "HistoricalPointsData",
    "RivalsData",
    "ChallengeUserData",
    "MessageIdData",
    "SeasonData",
    # ErrorHandler
    "ErrorHandler",
]
