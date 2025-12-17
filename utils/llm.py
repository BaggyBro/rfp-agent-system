"""Shared LLM utility using Google Gemini Flash 2.5."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from dotenv import dotenv_values
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

# Load API key from environment
config = dotenv_values(".env")
API_KEY = config.get("API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_llm(temperature: float = 0.3, model: str = "gemini-2.0-flash-exp") -> ChatGoogleGenerativeAI:
    """
    Get a configured Google Gemini LLM instance.
    
    Args:
        temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.
        model: Model name. Defaults to gemini-2.0-flash-exp (or gemini-2.5-flash if available).
    
    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    if not API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not found. Set it in .env file or environment variable."
        )
    
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=API_KEY,
    )


def extract_structured_data(
    text: str,
    schema_description: str,
    llm: Optional[ChatGoogleGenerativeAI] = None,
) -> Dict[str, Any]:
    """
    Use LLM to extract structured data from text according to a schema.
    
    Args:
        text: Input text to extract from
        schema_description: Description of what to extract (e.g., "voltage, insulation, core_count")
        llm: Optional LLM instance (creates one if not provided)
    
    Returns:
        Dictionary with extracted fields
    """
    if llm is None:
        llm = get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting technical specifications from RFP documents.
Extract the requested information and return ONLY a JSON object with the fields specified.
If a field is not found, use null. Be precise and accurate."""),
        ("human", """Extract the following information from this RFP text:
{schema}

RFP Text:
{text}

Return ONLY valid JSON with the extracted fields.""")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"schema": schema_description, "text": text})
        # Parse JSON from response
        import json
        content = response.content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        result = json.loads(content)
        logger.debug(f"[LLM] Extracted structured data: {result}")
        return result
    except Exception as e:
        logger.error(f"[LLM] Failed to extract structured data: {str(e)}")
        return {}


def generate_summary(
    text: str,
    max_words: int = 140,
    llm: Optional[ChatGoogleGenerativeAI] = None,
) -> str:
    """
    Use LLM to generate an intelligent summary of the text.
    
    Args:
        text: Text to summarize
        max_words: Target word count for summary
        llm: Optional LLM instance
    
    Returns:
        Generated summary
    """
    if llm is None:
        llm = get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at summarizing technical documents. Create concise, informative summaries."),
        ("human", """Summarize this RFP document in approximately {max_words} words.
Focus on key requirements, specifications, and procurement needs.

RFP Text:
{text}

Summary:""")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"text": text, "max_words": max_words})
        summary = response.content.strip()
        logger.debug(f"[LLM] Generated summary ({len(summary)} chars)")
        return summary
    except Exception as e:
        logger.error(f"[LLM] Failed to generate summary: {str(e)}")
        # Fallback to simple truncation
        words = text.split()[:max_words]
        return " ".join(words)


def analyze_with_llm(
    prompt_text: str,
    context: Optional[Dict[str, Any]] = None,
    llm: Optional[ChatGoogleGenerativeAI] = None,
) -> str:
    """
    Generic LLM analysis function for agent reasoning.
    
    Args:
        prompt_text: The prompt/question for the LLM
        context: Optional context dictionary to include
        llm: Optional LLM instance
    
    Returns:
        LLM response text
    """
    if llm is None:
        llm = get_llm()
    
    if context:
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        full_prompt = f"{prompt_text}\n\nContext:\n{context_str}"
    else:
        full_prompt = prompt_text
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert AI assistant helping with RFP processing and product matching."),
        ("human", "{prompt}")
    ])
    
    chain = prompt | llm
    try:
        response = chain.invoke({"prompt": full_prompt})
        return response.content.strip()
    except Exception as e:
        logger.error(f"[LLM] Analysis failed: {str(e)}")
        return ""

