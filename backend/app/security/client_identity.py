from dataclasses import dataclass
import re


class ClientIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class ClientIdentity:
    client_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", self.client_id
        ):
            raise ClientIdentityError("Invalid X-Client-Id.")
