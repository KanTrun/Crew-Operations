"""External API clients (Apify, SerpApi, ...)."""

from ca_agents.clients.serpapi_client import (
    SerpApiAuthError,
    SerpApiDisabledError,
    SerpApiError,
    SerpApiQuotaExceededError,
    get_quota_status,
    is_serpapi_enabled,
    search_serpapi,
)

__all__ = [
    "SerpApiAuthError",
    "SerpApiDisabledError",
    "SerpApiError",
    "SerpApiQuotaExceededError",
    "get_quota_status",
    "is_serpapi_enabled",
    "search_serpapi",
]
