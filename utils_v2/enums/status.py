from enum import Enum, StrEnum, auto


class ChallengeStatus(StrEnum):
    PENDING = "Pending"
    DECLINED = "Declined"
    UNFINISHED = "Unfinished"
    FINISHED = "Finished"
    REVOKED = "Revoked"


class SeasonStatus(StrEnum):
    ARCHIVED = "Archived"
    ONGOING = "Ongoing"


class ChallengeFailed(Enum):
    PENDING = auto()
    TOO_EARLY = auto()
    ONGOING = auto()
    BAD_LINK = auto()
    GOOD = auto()
    FAILED = auto()


class FuncStatus(Enum):
    ERROR = auto()
    GOOD = auto()
    EMPTY = auto()
    BAD_REQ = auto()
    TOO_LATE = auto()
