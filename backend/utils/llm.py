"""
LLM factory — returns configured LLM instances based on available API keys or local Ollama.
Supports Gemini Pro, Groq, and local Ollama (Llama 3.1 / Qwen / DeepSeek-R1).
"""
from typing import Optional
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import get_settings

_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_ollama_llm(model: Optional[str] = None, base_url: Optional[str] = None):
    """
    Returns ChatOllama instance for local offline inference.
    """
    s = _get_settings()
    from langchain_ollama import ChatOllama
    target_model = model or s.ollama_model
    target_url = base_url or s.ollama_base_url
    return ChatOllama(
        base_url=target_url,
        model=target_model,
        temperature=0.2,
    )


def get_supervisor_llm():
    """
    Gemini Pro or Groq for Supervisor, DFM, Engineering, Cost, Safety agents.
    Falls back to local Ollama if no cloud API keys are provided.
    """
    s = _get_settings()
    if s.gemini_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=s.gemini_api_key,
                temperature=0.1,
            )
        except ImportError:
            pass

    if s.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=s.groq_api_key,
                temperature=0.1,
            )
        except ImportError:
            pass

    # Fallback to local Ollama
    return get_ollama_llm(model=s.ollama_model)


def get_design_llm():
    """
    Groq/DeepSeek or Gemini Flash for Design Agent code generation.
    Falls back to local Ollama if no cloud API keys are provided.
    """
    s = _get_settings()
    if s.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="deepseek-r1-distill-llama-70b",
                groq_api_key=s.groq_api_key,
                temperature=0.2,
            )
        except ImportError:
            pass

    if s.gemini_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=s.gemini_api_key,
                temperature=0.2,
            )
        except ImportError:
            pass

    # Fallback to local Ollama
    return get_ollama_llm(model=s.ollama_model)
