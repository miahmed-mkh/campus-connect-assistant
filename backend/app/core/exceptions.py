class UnsafeInputError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason

        super().__init__(
            f"Entrée utilisateur refusée : {reason}"
        )
