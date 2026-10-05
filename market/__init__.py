"""Local, operator-owned market prototype. No token issuance or remote access."""

from .core import Market
from .contracts import MarketError

__all__ = ["Market", "MarketError"]
