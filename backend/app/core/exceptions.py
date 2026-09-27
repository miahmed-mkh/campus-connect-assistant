class UnsafeInputError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason

        super().__init__(
            f"Entrée utilisateur refusée : {reason}"
        )

class RateLimitExceededError(RuntimeError):
    def __init__(
        self,
        limit: int,
        retry_after_seconds: int,
    ) -> None:
        self.limit = limit
        self.retry_after_seconds = retry_after_seconds

        super().__init__(
            "Limite de requêtes dépassée : "
            f"{limit} requêtes par minute"
        )
