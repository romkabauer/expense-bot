import os
from abc import ABC, abstractmethod
from enum import Enum


class AIProviderLiteral(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"


class AIProvider(ABC):
    BASE_URLS = {
        AIProviderLiteral.GEMINI: "https://generativelanguage.googleapis.com",
        AIProviderLiteral.OPENAI: "https://api.openai.com",
    }

    ENV_KEYS = {
        AIProviderLiteral.GEMINI: "GEMINI_API_KEY",
        AIProviderLiteral.OPENAI: "OPENAI_API_KEY",
    }

    def __init__(self, provider: AIProviderLiteral):
        self.provider = provider

    def get_base_url(self) -> str:
        """Return the base URL for the current AI provider."""
        return self.BASE_URLS.get(self.provider)

    def get_api_key(self) -> str:
        """Return the API key for the current AI provider from environment variables.
        Raises an error if not set.
        """
        env_var = self.ENV_KEYS.get(self.provider)
        api_key = os.getenv(env_var)

        if not api_key:
            raise EnvironmentError(
                f"Missing API key for {self.provider.name}. "
                f"Set the environment variable {env_var}."
            )
        return api_key

    @abstractmethod
    async def ask(self, prompt: str) -> str:
        """Provider-specific response generation method."""
        raise NotImplementedError

    @abstractmethod
    async def ask_about_file(self, file_path: str, prompt: str) -> str:
        """Provider-specific response generation method with the file in context."""
        raise NotImplementedError
