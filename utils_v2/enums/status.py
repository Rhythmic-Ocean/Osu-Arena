from enum import StrEnum


class ChallengeStatus(StrEnum):
    PENDING = "Pending"
    DECLINED = "Declined"
    UNFINISHED = "Unfinished"
    FINISHED = "Finished"
    REVOKED = "Revoked"
