class RealtimeTranslationException(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        provider: str,
        retryable: bool,
        status_code: int = 502,
    ) -> None:
        super().__init__(message)

        self.code = code
        self.message = message
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code