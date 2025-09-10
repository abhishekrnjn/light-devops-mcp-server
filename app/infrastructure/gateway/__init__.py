"""
Gateway routing infrastructure for MCP HTTP Server.

This package provides a strategy pattern implementation for routing requests
through different gateways (Cequence, Direct, etc.) based on configuration.
"""

from .cequence_router import CequenceRouter
from .direct_router import DirectRouter
from .gateway_router import GatewayRouter
from .router_factory import RouterFactory

__all__ = ["GatewayRouter", "CequenceRouter", "DirectRouter", "RouterFactory"]
