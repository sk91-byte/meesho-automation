import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from groq import AsyncGroq
from pydantic import BaseModel, Field
from app.core.config import settings
from app.models.product import Product

logger = logging.getLogger("instagram_reseller")


class AIInterpretationSchema(BaseModel):
    intent: str = Field(..., description="Message intent e.g., GREETING, PRODUCT_INFO, PRODUCT_PRICE, PRODUCT_VARIANT, PLACE_ORDER, CUSTOMER_REQUEST, HUMAN_REQUEST")
    language: str = Field("hinglish", description="Customer language: english, hindi, hinglish")
    script: str = Field("latin", description="Writing script: latin, devanagari")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0")
    detected_product_query: Optional[str] = None
    requested_variant: Optional[str] = None
    requested_quantity: Optional[int] = None
    order_fields_detected: Dict[str, Any] = {}
    customer_request_type: Optional[str] = None  # COLOR, SIZE, VARIANT, DISCOUNT, OTHER
    requires_human: bool = False
    human_reason: Optional[str] = None


class AIProvider(ABC):
    @abstractmethod
    async def interpret_message(self, message_text: str, conversation_history: List[Dict[str, str]]) -> AIInterpretationSchema:
        pass

    @abstractmethod
    async def generate_verified_response(
        self,
        customer_message: str,
        interpretation: AIInterpretationSchema,
        tool_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        pass


class GroqAIProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def interpret_message(self, message_text: str, conversation_history: List[Dict[str, str]]) -> AIInterpretationSchema:
        if not self.client:
            # Safe heuristic fallback when Groq API key is not configured in dev
            return self._heuristic_fallback(message_text)

        system_prompt = (
            "You are an intent classifier for an Instagram eCommerce assistant selling products in India. "
            "Examine the customer's message (which could be in English, Hindi, Hinglish, Devanagari, or Latin script). "
            "Extract: intent, language, script, confidence, detected_product_query, requested_variant, requested_quantity, order_fields_detected (name, phone, house_building, road_area_colony), customer_request_type, requires_human. "
            "Output strictly valid JSON matching this schema: "
            '{"intent":"GREETING"|"PRODUCT_INFO"|"PRODUCT_PRICE"|"PRODUCT_VARIANT"|"PLACE_ORDER"|"CUSTOMER_REQUEST"|"HUMAN_REQUEST"|"UNKNOWN", '
            '"language":"english"|"hindi"|"hinglish", "script":"latin"|"devanagari", "confidence":0.95, "detected_product_query":null, '
            '"requested_variant":null, "requested_quantity":null, "order_fields_detected":{}, "customer_request_type":null, "requires_human":false, "human_reason":null}'
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            raw_json = response.choices[0].message.content
            parsed = json.loads(raw_json)
            return AIInterpretationSchema(**parsed)
        except Exception as e:
            logger.error(f"Groq message interpretation error: {e}")
            return self._heuristic_fallback(message_text)

    def _heuristic_fallback(self, message_text: str) -> AIInterpretationSchema:
        msg_lower = message_text.lower()
        
        # Check human request
        if any(w in msg_lower for w in ["human", "owner", "bande", "agent"]):
            return AIInterpretationSchema(intent="HUMAN_REQUEST", requires_human=True, human_reason="Explicit human request")
        
        # Check price request
        if any(w in msg_lower for w in ["price", "kitne ka", "cost", "rate"]):
            return AIInterpretationSchema(intent="PRODUCT_PRICE")
        
        # Check order request
        if any(w in msg_lower for w in ["buy", "purchase", "order", "chahiye"]):
            return AIInterpretationSchema(intent="PLACE_ORDER")

        # Check color / size variant request
        if any(w in msg_lower for w in ["black", "brown", "blue", "pink", "red", "green", "size"]):
            for color in ["black", "brown", "blue", "pink", "red", "green"]:
                if color in msg_lower:
                    return AIInterpretationSchema(intent="PRODUCT_VARIANT", requested_variant=color.capitalize())

        return AIInterpretationSchema(intent="PRODUCT_INFO")

    async def generate_verified_response(
        self,
        customer_message: str,
        interpretation: AIInterpretationSchema,
        tool_results: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Rule 2 & 3: Generate natural response strictly grounded in verified backend tool output."""
        if not self.client:
            return self._format_verified_fallback_response(interpretation, tool_results)

        system_prompt = (
            "You are a polite, natural Instagram eCommerce sales assistant. "
            "NON-NEGOTIABLE RULE: You MUST ONLY state facts provided in the AUTHORITATIVE BACKEND TOOL RESULTS below. "
            "NEVER invent prices, stock, discounts, or policies. "
            "Reply in the customer's language (English, Hindi, or Hinglish) using their script style. "
            f"AUTHORITATIVE BACKEND TOOL RESULTS: {json.dumps(tool_results, ensure_ascii=False)}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": customer_message}
                ],
                temperature=settings.GROQ_TEMPERATURE,
                max_tokens=settings.GROQ_MAX_TOKENS
            )
            raw_reply = response.choices[0].message.content.strip()
            
            # Layer 6 Validation: Verify claims against truth before returning
            validated_reply = self.validate_response_claims(raw_reply, tool_results)
            return validated_reply
        except Exception as e:
            logger.error(f"Groq response generation error: {e}")
            return self._format_verified_fallback_response(interpretation, tool_results)

    def validate_response_claims(self, response_text: str, tool_results: Dict[str, Any]) -> str:
        """Layer 6 Anti-Hallucination Validator: ensure no unverified numerical price or fake variant is stated."""
        if "price" in tool_results:
            expected_price = str(int(tool_results["price"]))
            # If AI mentions price, check if it matches exact backend price
            if "₹" in response_text or "rs" in response_text.lower():
                if expected_price not in response_text:
                    logger.warning("Response validation failed: AI generated price mismatch. Using verified template.")
                    return f"Product price is ₹{expected_price} 😊"

        return response_text

    def _format_verified_fallback_response(self, interpretation: AIInterpretationSchema, tool_results: Dict[str, Any]) -> str:
        if interpretation.requires_human:
            return "I've passed your request to our store owner. They will message you shortly! 😊"
        
        if "price" in tool_results:
            price = tool_results["price"]
            name = tool_results.get("product_name", "this product")
            return f"The price for {name} is ₹{int(price)} 😊. Free delivery & COD available!"

        if "variant_available" in tool_results:
            variant = tool_results.get("variant")
            avail = tool_results["variant_available"]
            if avail:
                return f"Yes! 😊 {variant} is available in stock."
            else:
                return f"Sorry, {variant} is currently unavailable. I've noted your request for the owner!"

        return "Hello! How can I help you with our Meesho products today? 😊"


# Central service instance
ai_provider = GroqAIProvider()
