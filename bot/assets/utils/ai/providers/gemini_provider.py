import mimetypes


from google import genai


from . import AIProvider, AIProviderLiteral
from . import AIModel



class GeminiAIProvider(AIProvider):
    def __init__(self, model: AIModel):
        super().__init__(AIProviderLiteral.GEMINI)
        self.client = genai.Client(api_key=self.get_api_key()).aio
        self.model = model.value

    async def ask(self, prompt: str) -> str:
        response = await self.client.models.generate_content(
            model=self.model, contents=[prompt]
        )

        return response.text

    async def ask_about_file(self, file_path: str, prompt: str) -> str:
        mime_type = mimetypes.guess_type(file_path)[0]
        f = await self.client.files.upload(
            file=file_path,
            config={"mime_type": mime_type if mime_type else "audio/ogg"}
        )

        response = await self.client.models.generate_content(
            model=self.model, contents=[f, prompt]
        )

        return response.text
