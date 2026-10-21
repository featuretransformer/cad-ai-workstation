"""
Unit tests for APIKeyPool and Resilient Multi-Key Failover.
"""
import pytest
import time
from utils.key_pool import APIKeyPool
from utils.llm import ResilientChatModel


def test_key_pool_round_robin():
    pool = APIKeyPool("test", ["k1", "k2", "k3"])
    assert pool.has_keys() is True
    assert pool.status()["total_keys"] == 3
    assert pool.status()["available_keys"] == 3

    # Consecutive calls should cycle round-robin
    keys = [pool.get_next_key() for _ in range(6)]
    assert keys == ["k1", "k2", "k3", "k1", "k2", "k3"]


def test_key_pool_cooldown_and_recovery():
    pool = APIKeyPool("test", ["k1", "k2"])

    # Mark k1 as rate-limited with 1s cooldown
    pool.mark_rate_limited("k1", retry_after=1.0)
    assert pool.status()["cooling_keys"] == 1
    assert pool.status()["available_keys"] == 1

    # While k1 is cooling down, only k2 should be returned
    assert pool.get_next_key() == "k2"
    assert pool.get_next_key() == "k2"

    # Wait for cooldown to expire
    time.sleep(1.2)
    pool.mark_success("k1")
    assert pool.status()["cooling_keys"] == 0
    assert pool.status()["available_keys"] == 2


def test_key_pool_parse_error_duration():
    pool = APIKeyPool("test", ["k1"])
    err = "Limit 1000, Used 722, Requested 750. Please try again in 12.5s."
    pool.mark_rate_limited("k1", error_message=err)

    rem = pool.get_earliest_cooldown_remaining()
    assert 10.0 <= rem <= 15.0


def test_resilient_chat_model_instantiation():
    model = ResilientChatModel(agent_type="supervisor", default_max_tokens=300)
    assert model.agent_type == "supervisor"
    assert model.default_max_tokens == 300
