from pydantic import BaseModel

from dspy_constants import (
    MODEL_NAME_GEMINI_2_0_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH_LITE,
    MODEL_NAME_GEMINI_2_5_PRO,
)

class CostStatistics(BaseModel):
    input_cost: float
    output_cost: float
    total_cost: float
    total_cost_llm_api_usd: float | None = None
    currency: str


class PricingTier(BaseModel):
    input_price_per_million: float
    output_price_per_million: float 
    context_cache_price_per_million: float
    context_storage_price_per_million_per_hour: float
    currency: str = "USD"

class PricingConfig(BaseModel):
    standard_tier: PricingTier
    long_context_tier: PricingTier
    long_context_threshold: int
    currency: str = "USD"

class PricingConfigGemini20Flash(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,
        output_price_per_million=0.40,
        context_cache_price_per_million=0.025,
        context_storage_price_per_million_per_hour=1.00
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,  # Same as standard since no long context pricing specified
        output_price_per_million=0.40,
        context_cache_price_per_million=0.025,
        context_storage_price_per_million_per_hour=1.00
    )

    long_context_threshold: int = 1_000_000  # 1M token context window - now differentiation per context

class PricingConfigGemini25Flash(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.30,
        output_price_per_million=2.50,
        context_cache_price_per_million=0.0,  # Not available yet ("Coming soon!")
        context_storage_price_per_million_per_hour=0.0  # Not available yet ("Coming soon!")
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.30,  # Same as standard since no long context pricing specified
        output_price_per_million=2.50,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )

    long_context_threshold: int = 1_000_000  # 1M token context window

class PricingConfigGemini25Pro(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=1.25,
        output_price_per_million=10.00,
        context_cache_price_per_million=0.0,  # Not available
        context_storage_price_per_million_per_hour=0.0  # Not available
    )

    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=2.50,
        output_price_per_million=15.00,
        context_cache_price_per_million=0.0,  # Not available
        context_storage_price_per_million_per_hour=0.0  # Not available
    )

    long_context_threshold: int = 200_000  # 200k tokens threshold for long context pricing

class PricingConfigGemini25FlashLite(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,
        output_price_per_million=0.40,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,  # Same as standard since no long context pricing specified
        output_price_per_million=0.40,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )

    long_context_threshold: int = 1_000_000  # 1M token context window

class PricingService:
    model_pricing_map: dict[str, PricingConfig] = {
        MODEL_NAME_GEMINI_2_0_FLASH: PricingConfigGemini20Flash(), # reusing for simplicity
        MODEL_NAME_GEMINI_2_5_FLASH: PricingConfigGemini25Flash(),
        MODEL_NAME_GEMINI_2_5_FLASH_LITE: PricingConfigGemini25FlashLite(),
        MODEL_NAME_GEMINI_2_5_PRO: PricingConfigGemini25Pro()
    }

    def get_pricing_config(self, model_name: str) -> PricingConfig | None:
        return self.model_pricing_map.get(model_name, None)

    def get_registered_model_names(self) -> list[str]:
        return list(self.model_pricing_map.keys())

class SingleModelPricingService:
    def __init__(self, model_name: str, pricing_service: PricingService):
        self.model_name = model_name
        self.pricing_service = pricing_service

    def get_cost_statistics_for(self, input_tokens: int, output_tokens: int) -> CostStatistics | None:
        pricing_tier = self._get_pricing_tier(input_tokens)
        if pricing_tier is None:
            print(f"No pricing tier for model: {self.model_name}")
            return None
        input_cost = round(pricing_tier.input_price_per_million * input_tokens / 1_000_000, 3)
        output_cost = round(pricing_tier.output_price_per_million * output_tokens / 1_000_000, 3)
        total_cost = input_cost + output_cost
        return CostStatistics(input_cost=input_cost, output_cost=output_cost, total_cost=total_cost, currency=pricing_tier.currency)    

    def _get_pricing_tier(self, input_tokens: int) -> PricingTier | None: 
        pricing_config = self.pricing_service.get_pricing_config(self.model_name)
        if pricing_config is None:
            return None
        if input_tokens > pricing_config.long_context_threshold:
            return pricing_config.long_context_tier
        return pricing_config.standard_tier
    
    def get_model_name(self) -> str:
        return self.model_name