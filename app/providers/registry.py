from app.providers.base import Provider


class ProviderRegistry:
    def __init__(self, openai: Provider) -> None:
        self.openai = openai

    def resolve(self, model: str) -> Provider:
        # All model IDs are forwarded to the sole configured, trusted provider.
        return self.openai
