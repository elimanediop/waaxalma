from dataclasses import dataclass
from app.security.client_identity import ClientIdentity


@dataclass(frozen=True)
class SecurityContext:
    identity: ClientIdentity
