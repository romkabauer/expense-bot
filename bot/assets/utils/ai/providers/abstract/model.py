from enum import Enum


class AIModel(Enum):
    GEMINI_2_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_FLASH_LITE_LATEST = "gemini-flash-lite-latest"

    def __str__(self):
        return self.value
