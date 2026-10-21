"""
LLM Factory & Resilient Multi-Key Failover Engine.
Provides high-availability inference across Groq and Gemini API key pools:
- Round-robin key rotation across multiple accounts/keys.
- Dynamic 429 RateLimit quarantine (cooldown-aware).
- Per-model token diversification (qwen/qwen3.8-27b -> openai/gpt-oss-120b).
- Cross-provider failover (Groq -> Gemini -> local Ollama).
- Token budget optimization (300 tokens for planning vs 750 for CAD synthesis).
"""
from typing import Optional, List, Any
from pathlib import Path
import sys
import socket
import time

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import get_settings
from utils.key_pool import APIKeyPool
from langchain_core.messages import AIMessage

# Patch IPv4 resolution for Google APIs to avoid IPv6 getaddrinfo hangs on Windows
_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host and "googleapis.com" in str(host):
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _patched_getaddrinfo


def _google_api_reachable(timeout: float = 2.0) -> bool:
    """Fast IPv4 probe — returns False if Google APIs are unreachable."""
    try:
        socket.setdefaulttimeout(timeout)
        res = socket.getaddrinfo("generativelanguage.googleapis.com", 443, socket.AF_INET)
        ip = res[0][4][0]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((ip, 443)) == 0
    except Exception:
        return False
    finally:
        socket.setdefaulttimeout(None)


_settings = None
_groq_pool: Optional[APIKeyPool] = None
_gemini_pool: Optional[APIKeyPool] = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def get_groq_pool() -> APIKeyPool:
    global _groq_pool
    if _groq_pool is None:
        s = _get_settings()
        _groq_pool = APIKeyPool("groq", s.get_groq_keys())
    return _groq_pool


def get_gemini_pool() -> APIKeyPool:
    global _gemini_pool
    if _gemini_pool is None:
        s = _get_settings()
        _gemini_pool = APIKeyPool("gemini", s.get_gemini_keys())
    return _gemini_pool


def get_ollama_llm(model: Optional[str] = None, base_url: Optional[str] = None):
    """Returns ChatOllama instance for local offline inference."""
    s = _get_settings()
    try:
        from langchain_ollama import ChatOllama
        target_model = model or s.ollama_model
        target_url = base_url or s.ollama_base_url
        return ChatOllama(
            base_url=target_url,
            model=target_model,
            temperature=0.2,
        )
    except Exception:
        return None


class ResilientChatModel:
    """
    High-availability Chat Model wrapper.
    Executes calls through multi-key pools and automatic cross-provider failover.
    """

    def __init__(self, agent_type: str = "design", temperature: float = 0.15, default_max_tokens: int = 750):
        self.agent_type = agent_type
        self.temperature = temperature
        self.default_max_tokens = default_max_tokens

    def invoke(self, messages: Any, **kwargs) -> AIMessage:
        """
        Executes inference with cascading failover:
        1. Groq Key Pool (Primary: qwen/qwen3.8-27b)
        2. Groq Key Pool (Secondary: openai/gpt-oss-120b - separate token bucket)
        3. Gemini Key Pool (gemini-3.1-flash-lite / gemini-3.8-flash)
        4. Local Ollama (if running)
        5. Raise error to trigger deterministic fallback cleanly
        """
        s = _get_settings()
        groq_pool = get_groq_pool()
        gemini_pool = get_gemini_pool()

        # Token budget tuning: lightweight planning needs far fewer tokens than full CADIR
        if self.agent_type in ("supervisor", "classifier", "planner"):
            max_tokens = min(kwargs.get("max_tokens", 300), 300)
        else:
            max_tokens = kwargs.get("max_tokens", self.default_max_tokens)

        # -------------------------------------------------------------
        # TIER 1: Groq Multi-Key Pool (qwen/qwen3.8-27b)
        # -------------------------------------------------------------
        if groq_pool.has_keys():
            attempted_keys = set()
            while len(attempted_keys) < len(groq_pool.keys):
                key = groq_pool.get_next_key()
                if not key or key in attempted_keys:
                    break
                attempted_keys.add(key)

                try:
                    from langchain_groq import ChatGroq
                    client = ChatGroq(
                        model="qwen/qwen3.8-27b",
                        groq_api_key=key,
                        temperature=self.temperature,
                        max_tokens=max_tokens,
                        max_retries=0,
                        request_timeout=5.0,
                    )
                    res = client.invoke(messages)
                    groq_pool.mark_success(key)
                    return res
                except Exception as e:
                    err_str = str(e)
                    is_rate_limit = (
                        "429" in err_str
                        or "rate_limit_exceeded" in err_str
                        or "tokens" in err_str
                        or "OTPM" in err_str
                    )
                    if is_rate_limit:
                        groq_pool.mark_rate_limited(key, error_message=err_str)
                    else:
                        print(f"[GROQ ERROR] Key ...{key[-4:] if len(key) >= 4 else ''}: {e}")

        # -------------------------------------------------------------
        # TIER 2: Groq Alternative Model (openai/gpt-oss-120b)
        # Separate token quota on Groq platform
        # -------------------------------------------------------------
        if groq_pool.has_keys():
            for key in groq_pool.keys:
                try:
                    from langchain_groq import ChatGroq
                    client = ChatGroq(
                        model="openai/gpt-oss-120b",
                        groq_api_key=key,
                        temperature=self.temperature,
                        max_tokens=max_tokens,
                        max_retries=0,
                        request_timeout=6.0,
                    )
                    res = client.invoke(messages)
                    return res
                except Exception:
                    continue

        # -------------------------------------------------------------
        # TIER 3: Cross-Provider Failover to Google Gemini Key Pool
        # -------------------------------------------------------------
        if gemini_pool.has_keys() and _google_api_reachable():
            attempted_keys = set()
            while len(attempted_keys) < len(gemini_pool.keys):
                key = gemini_pool.get_next_key()
                if not key or key in attempted_keys:
                    break
                attempted_keys.add(key)

                for gemini_model in ("gemini-3.1-flash-lite", "gemini-3.8-flash"):
                    try:
                        from langchain_google_genai import ChatGoogleGenerativeAI
                        client = ChatGoogleGenerativeAI(
                            model=gemini_model,
                            google_api_key=key,
                            temperature=self.temperature,
                            max_output_tokens=max_tokens * 2,
                            max_retries=0,
                            request_timeout=7.0,
                        )
                        res = client.invoke(messages)
                        gemini_pool.mark_success(key)
                        return res
                    except Exception as ge:
                        err_str = str(ge)
                        if "429" in err_str or "ResourceExhausted" in err_str:
                            gemini_pool.mark_rate_limited(key, error_message=err_str)
                            break
                        continue

        # -------------------------------------------------------------
        # TIER 4: Local Ollama (if configured and running)
        # -------------------------------------------------------------
        ollama = get_ollama_llm()
        if ollama:
            try:
                res = ollama.invoke(messages)
                return res
            except Exception:
                pass

        # -------------------------------------------------------------
        # TIER 5: Exhausted — Raise to trigger deterministic synthesis
        # -------------------------------------------------------------
        raise RuntimeError(
            "All LLM providers and API keys are currently rate-limited, cooling down, or offline. "
            "Falling back to deterministic parametric synthesis."
        )


def get_supervisor_llm() -> ResilientChatModel:
    """Supervisor, DFM, Engineering, Cost, Safety, and Classifier agents."""
    return ResilientChatModel(agent_type="supervisor", temperature=0.1, default_max_tokens=300)


def get_design_llm() -> ResilientChatModel:
    """Design Agent and Incremental CAD synthesis agents."""
    return ResilientChatModel(agent_type="design", temperature=0.15, default_max_tokens=750)
