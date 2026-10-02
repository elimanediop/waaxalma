from typing import Any


class ProviderRegistry:
    """
    Registry for provider implementations.

    Providers are identified by:
        capability + provider name

    Examples:
        translation + openai
        speech + openai
        speech_to_text + openai
    """

    def __init__(self) -> None:
        self._providers: dict[
            tuple[str, str],
            Any,
        ] = {}

    def register(
        self,
        *,
        capability: str,
        name: str,
        provider: Any,
    ) -> None:
        key = (
            capability,
            name,
        )

        if key in self._providers:
            raise ValueError(
                f"Provider '{name}' is already registered "
                f"for capability '{capability}'."
            )

        self._providers[key] = provider

    def get(
        self,
        *,
        capability: str,
        name: str,
    ) -> Any:
        key = (
            capability,
            name,
        )

        provider = self._providers.get(key)

        if provider is None:
            raise KeyError(
                f"Provider '{name}' is not registered "
                f"for capability '{capability}'."
            )

        return provider

    def contains(
        self,
        *,
        capability: str,
        name: str,
    ) -> bool:
        return (
            capability,
            name,
        ) in self._providers

    def names_for(
        self,
        capability: str,
    ) -> list[str]:
        return sorted(
            name
            for registered_capability, name
            in self._providers
            if registered_capability == capability
        )