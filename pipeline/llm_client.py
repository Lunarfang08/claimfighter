"""LLM client for Ollama via OpenAI-compatible endpoint.

This wrapper handles:
- JSON mode structured output
- Retry with repair on parse failures
- Defensive parsing (strips markdown code fences)
"""

import json
import os
import re
from typing import TypeVar, Type, Optional

from openai import OpenAI
from pydantic import BaseModel, ValidationError, field_validator

from schemas import ExtractedFields, DocumentType


T = TypeVar("T", bound=BaseModel)


class OllamaClient:
    """Thin wrapper around OpenAI client pointed at Ollama."""
    
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        # Ollama ignores the key; Groq/OpenAI-compatible APIs need OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "ollama"
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        self.model = model
    
    def _call_with_json_mode(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        max_retries: int = 2,
    ) -> T:
        """Call LLM with JSON mode and parse response into pydantic model.
        
        Args:
            system_prompt: System instructions
            user_prompt: User input/question
            response_model: Pydantic model class to parse response into
            max_retries: Number of retries on parse failure
            
        Returns:
            Parsed pydantic model instance
            
        Raises:
            ValueError: If parsing fails after all retries
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,  # Low temperature for structured extraction
                    response_format={"type": "json_object"},
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM")
                
                # Defensive parsing: strip markdown code fences if present
                content = self._clean_json_response(content)
                
                # Parse JSON
                data = json.loads(content)
                
                # Validate against pydantic model
                return response_model.model_validate(data)
                
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt < max_retries:
                    # Retry with more explicit instructions
                    user_prompt += f"\n\nPrevious attempt failed to parse. Error: {str(e)}\nPlease respond with ONLY valid JSON matching the schema, no markdown formatting, no explanation text."
                    continue
                else:
                    raise ValueError(
                        f"Failed to parse LLM response after {max_retries + 1} attempts. "
                        f"Last error: {e}\nLast response: {content}"
                    )
    
    @staticmethod
    def _clean_json_response(content: str) -> str:
        """Remove markdown code fences and extra whitespace."""
        # Remove ```json ... ``` or ```...```
        content = re.sub(r'^```(?:json)?\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
        return content.strip()
    
    def classify_document(self, text: str) -> DocumentType:
        """Classify the type of medical document.
        
        Args:
            text: Raw extracted text from document
            
        Returns:
            DocumentType enum value
        """
        system_prompt = """You are a medical billing document classifier.
Given text extracted from a medical/insurance document, classify it into one of these types:
- "eob": Explanation of Benefits from insurance company
- "denial_letter": Letter denying or partially denying a claim
- "itemized_bill": Itemized bill from healthcare provider
- "unknown": If you cannot determine the type

Respond with ONLY a JSON object: {"document_type": "eob|denial_letter|itemized_bill|unknown"}"""

        user_prompt = f"""Classify this document text:

{text[:2000]}"""  # First 2000 chars should be enough

        result = self._call_with_json_mode(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=DocumentTypeResponse,
        )
        
        return result.document_type
    
    def extract_fields(self, text: str, document_type: DocumentType) -> ExtractedFields:
        """Extract structured fields from document text.
        
        Args:
            text: Raw extracted text from document
            document_type: Pre-classified document type
            
        Returns:
            ExtractedFields with all extracted information
        """
        system_prompt = f"""You are a medical billing document parser.
Extract structured information from the following {document_type.value} document.

Extract these fields (use null for missing values):
- patient_name: string
- patient_id: string (member/patient ID)
- insurer_name: string
- provider_name: string (hospital/clinic name)
- service_date: ISO date string (YYYY-MM-DD)
- service_date_end: ISO date string if range, else null
- cpt_codes: array of CPT procedure codes (5-digit codes like "99285")
- icd_codes: array of ICD diagnosis codes (like "R51.9")
- billed_amount: decimal string (total amount billed)
- allowed_amount: decimal string (insurance allowed amount)
- paid_amount: decimal string (amount insurance paid)
- patient_responsibility: decimal string (patient owes)
- denial_reason_code: string (like "CO-50", "CO-11")
- denial_reason_text: string (human explanation of denial)
- in_network: boolean (true if in-network, false if out-of-network, null if unknown)
- raw_denial_context: string (snippet of text explaining the denial)

CRITICAL: Respond with ONLY valid JSON. No markdown, no explanation."""

        user_prompt = f"""Document text:

{text}

Respond with JSON only."""

        # Build a minimal response model for the LLM output, then map to ExtractedFields
        result = self._call_with_json_mode(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ExtractedFieldsResponse,
        )
        
        # Map to full ExtractedFields (adding document_type which LLM doesn't output)
        return ExtractedFields(
            document_type=document_type,
            **result.model_dump(exclude_none=False)
        )


# Response models for LLM (these match the JSON schemas we ask for)

class DocumentTypeResponse(BaseModel):
    """LLM response for document classification."""
    document_type: DocumentType


class ExtractedFieldsResponse(BaseModel):
    """LLM response for field extraction (without document_type)."""
    # Copy all fields from ExtractedFields except document_type
    patient_name: str | None = None
    patient_id: str | None = None
    insurer_name: str | None = None
    provider_name: str | None = None
    service_date: str | None = None  # LLM outputs as string, we'll parse
    service_date_end: str | None = None
    cpt_codes: Optional[list[str]] = None
    icd_codes: Optional[list[str]] = None
    billed_amount: str | None = None  # LLM outputs as string
    allowed_amount: str | None = None
    paid_amount: str | None = None
    patient_responsibility: str | None = None
    denial_reason_code: str | None = None
    denial_reason_text: str | None = None
    in_network: bool | None = None
    raw_denial_context: str | None = None

    @field_validator("cpt_codes", "icd_codes", mode="before")
    @classmethod
    def coerce_null_to_empty_list(cls, v):
        """LLM sometimes returns null for list fields — treat as empty list."""
        if v is None:
            return []
        return v
