from enum import StrEnum


class ChallengeStatus(StrEnum):
    PENDING = "pending"
    ONGOING = "ongoing"
    FINISHED = "finished"


# Standard loop
for status in ChallengeStatus:
    print(f"Member: {status}")  # ChallengeStatus.PENDING
