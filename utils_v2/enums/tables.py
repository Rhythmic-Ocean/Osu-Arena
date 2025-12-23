from enum import StrEnum


class TablesLeagues(StrEnum):
    NOVICE = "novice"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    ELITE = "elite"
    MASTER = "master"


class TablesLeaguesDeprecated(StrEnum):
    RANKER = "ranker"


class TablesRivals(StrEnum):
    RIVALS = "rivals"
    CHALLENGED = "challenged"
    CHALLENGER = "challenger"


class TablesPoints(StrEnum):
    POINTS = "points"
    S_POINTS = "s_points"
    HISTORICAL_POINTS = "historical_points"


class TableMiscellaneous(StrEnum):
    MESG_ID = "mesg_id"
    SEASONS = "seasons"
