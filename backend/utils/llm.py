"""
LLM factory — returns configured LLM instances based on available API keys or local Ollama.
Supports Gemini Pro, Groq, and local Ollama (Llama 3.1 / Qwen / DeepSeek-R1).
"""
from typing import Optional
from pathlib import Path
import sys
import socket

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import get_settings


def _google_api_reachable(timeout: float = 2.0) -> bool:
    """Fast DNS probe — returns False if Google APIs are unreachable."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo("generativelanguage.googleapis.com", 443)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False
    finally:
        socket.setdefaulttimeout(None)

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
    Supervisor, DFM, Engineering, Cost, Safety agents.
    Provides resilient failover: Gemini (fast attempt) -> Groq (Qwen) -> Ollama (local).
    """
    s = _get_settings()
    gemini_llm = None
    groq_llm = None

    if s.gemini_api_key and _google_api_reachable():
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_llm = ChatGoogleGenerativeAI(
                model="gemini-3.8-flash",
                google_api_key=s.gemini_api_key,
                temperature=0.1,
                max_retries=0,
            )
        except Exception:
            pass

    if s.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            groq_llm = ChatGroq(
                model="qwen/qwen3.8-27b",
                groq_api_key=s.groq_api_key,
                temperature=0.1,
            )
        except Exception:
            pass

    if gemini_llm and groq_llm:
        return gemini_llm.with_fallbacks([groq_llm])
    elif gemini_llm:
        return gemini_llm
    elif groq_llm:
        return groq_llm

    # Fallback to local Ollama
    return get_ollama_llm(model=s.ollama_model)


def get_design_llm():
    """
    Design Agent code generation.
    Provides resilient failover: Gemini (fast attempt) -> Groq (Qwen) -> Ollama (local).
    """
    s = _get_settings()
    gemini_llm = None
    groq_llm = None

    if s.gemini_api_key and _google_api_reachable():
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_llm = ChatGoogleGenerativeAI(
                model="gemini-3.8-flash",
                google_api_key=s.gemini_api_key,
                temperature=0.2,
                max_retries=0,
            )
        except Exception:
            pass

    if s.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            groq_llm = ChatGroq(
                model="qwen/qwen3.8-27b",
                groq_api_key=s.groq_api_key,
                temperature=0.2,
            )
        except Exception:
            pass

    if gemini_llm and groq_llm:
        return gemini_llm.with_fallbacks([groq_llm])
    elif gemini_llm:
        return gemini_llm
    elif groq_llm:
        return groq_llm

    # Fallback to local Ollama
    return get_ollama_llm(model=s.ollama_model)
