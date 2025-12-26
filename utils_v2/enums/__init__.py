from .tables import (
    TableMiscellaneous,
    TablesLeagues,
    TablesLeaguesDeprecated,
    TablesPoints,
    TablesRivals,
    ArchivedTable,
)

from .tables_internals import (
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
from .status import ChallengeStatus, SeasonStatus

__all__ = [
    # Table Namespaces
    "TableAll",
    "TablesLeagues",
    "TablesRivals",
    "TableMiscellaneous",
    "TablesLeaguesDeprecated",
    "TablesPoints",
    "ArchivedTable",
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
    # Status
    "ChallengeStatus",
    "SeasonStatus",
]


class TableAll:
    LEAGUES = TablesLeagues
    LEAGUES_DEPRECATED = TablesLeaguesDeprecated
    RIVALS = TablesRivals
    POINTS = TablesPoints
    MISC = TableMiscellaneous
