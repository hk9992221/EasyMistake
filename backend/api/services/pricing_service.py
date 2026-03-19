"""Pricing calculation service."""

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Dict


class PricingService:
    """Calculate API costs from token usage."""

    # Fallback prices, expressed as "currency per 1,000,000 tokens".
    PRICING_FALLBACK: Dict[str, Dict[str, float | str]] = {
        "qwen-vl-max": {"input": 20, "output": 60, "currency": "CNY"},
        "qwen-vl-plus": {"input": 8, "output": 20, "currency": "CNY"},
        "qwen-vl-v1": {"input": 8, "output": 20, "currency": "CNY"},
        "gpt-4": {"input": 30, "output": 60, "currency": "USD"},
        "gpt-4-vision-preview": {"input": 10, "output": 30, "currency": "USD"},
        "gpt-4o": {"input": 5, "output": 15, "currency": "USD"},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6, "currency": "USD"},
        "default": {"input": 0.0, "output": 0.0, "currency": "USD"},
    }

    USD_TO_CNY = Decimal("7.2")
    TOKENS_PER_UNIT = Decimal("1000000")
    _ALIYUN_PRICING_CACHE: Dict[str, Dict[str, float | str]] | None = None

    @classmethod
    def _normalize_model_key(cls, model_name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", model_name.lower()).strip("_")

    @classmethod
    def _load_aliyun_pricing(cls) -> Dict[str, Dict[str, float | str]]:
        if cls._ALIYUN_PRICING_CACHE is not None:
            return cls._ALIYUN_PRICING_CACHE

        pricing: Dict[str, Dict[str, float | str]] = {}
        json_path = Path(__file__).resolve().parents[1] / "aliyun.json"
        if not json_path.exists():
            cls._ALIYUN_PRICING_CACHE = pricing
            return pricing

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            models = payload.get("model", [])
            if isinstance(models, list):
                for item in models:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name")
                    if not name:
                        continue
                    key = cls._normalize_model_key(str(name))
                    pricing[key] = {
                        "input": float(item.get("input_price_pm") or 0),
                        "output": float(item.get("output_price_pm") or 0),
                        "currency": "CNY",
                    }
        except Exception:
            pricing = {}

        cls._ALIYUN_PRICING_CACHE = pricing
        return pricing

    @classmethod
    def get_model_pricing(cls, model_name: str) -> Dict[str, float | str]:
        model_key = cls._normalize_model_key(model_name)
        aliyun = cls._load_aliyun_pricing()

        if model_key in aliyun:
            return aliyun[model_key]

        for key, pricing in aliyun.items():
            if key and key in model_key:
                return pricing

        if model_key in cls.PRICING_FALLBACK:
            return cls.PRICING_FALLBACK[model_key]

        for key, pricing in cls.PRICING_FALLBACK.items():
            if key != "default" and key in model_key:
                return pricing

        return cls.PRICING_FALLBACK["default"]

    @classmethod
    def calculate_cost(
        cls,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        target_currency: str = "USD",
    ) -> Decimal:
        pricing = cls.get_model_pricing(model_name)

        input_cost = Decimal(str(prompt_tokens)) / cls.TOKENS_PER_UNIT * Decimal(str(pricing["input"]))
        output_cost = Decimal(str(completion_tokens)) / cls.TOKENS_PER_UNIT * Decimal(str(pricing["output"]))
        total_cost = input_cost + output_cost

        if pricing["currency"] != target_currency:
            if pricing["currency"] == "CNY" and target_currency == "USD":
                total_cost = total_cost / cls.USD_TO_CNY
            elif pricing["currency"] == "USD" and target_currency == "CNY":
                total_cost = total_cost * cls.USD_TO_CNY

        return total_cost.quantize(Decimal("0.00000001"))

    @classmethod
    def calculate_cost_from_usage(
        cls,
        model_name: str,
        usage: Dict,
        target_currency: str = "USD",
    ) -> Decimal:
        if not usage:
            return Decimal("0")

        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        return cls.calculate_cost(model_name, prompt_tokens, completion_tokens, target_currency)


pricing_service = PricingService()
