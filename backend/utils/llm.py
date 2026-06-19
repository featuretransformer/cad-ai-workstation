"""
LLM factory — returns configured LLM instances based on available API keys.
"""
from config import get_settings

_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_supervisor_llm():
    """Gemini Pro for Supervisor, DFM, Engineering, Cost, Safety agents."""
    s = _get_settings()
    if s.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=s.gemini_api_key,
            temperature=0.1,
        )
    if s.groq_api_key:
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=s.groq_api_key, temperature=0.1)
    raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env")


def get_design_llm():
    """Groq/DeepSeek for Design Agent — fast code generation."""
    s = _get_settings()
    if s.groq_api_key:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="deepseek-r1-distill-llama-70b",
            groq_api_key=s.groq_api_key,
            temperature=0.2,
        )
    if s.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=s.gemini_api_key,
            temperature=0.2,
        )
    raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env")
