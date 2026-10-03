from .ai_base import AIProvider, ANTI_BOT
from .ai_adapters import (OpenAICompatibleProvider, OpenAIProvider, GeminiProvider, OllamaProvider,
    KimiProvider, DeepSeekProvider, GrokProvider, ClaudeProvider, AnthropicProvider, XAIProvider,
    GroqProvider, MistralProvider, CohereProvider, OpenRouterProvider, TogetherProvider, LMStudioProvider)

def provider(feature="default"):
    from .ai_connections import selected_provider
    return selected_provider(feature)
