from enum import StrEnum


class Role(StrEnum):
    VISITOR = "visitor"
    PARTICIPANT = "participant"
    JUDGE = "judge"
    ORGANIZER = "organizer"
    ADMIN = "admin"


AUTHENTICATED_ROLES = frozenset(Role) - {Role.VISITOR}
