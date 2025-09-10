"""
Router factory for creating appropriate gateway routers.

This module provides a factory pattern for creating the appropriate
gateway router based on configuration settings.
"""

import logging
from typing import Optional

from app.config import settings
from app.infrastructure.gateway.cequence_router import CequenceRouter
from app.infrastructure.gateway.direct_router import DirectRouter
from app.infrastructure.gateway.gateway_router import GatewayRouter

logger = logging.getLogger(__name__)


class RouterFactory:
    """
    Factory class for creating gateway routers.
    
    This factory creates the appropriate router based on configuration
    settings, providing a single point of control for router selection.
    """

    _instance: Optional[GatewayRouter] = None

    @classmethod
    def get_router(cls) -> GatewayRouter:
        """
        Get the appropriate gateway router based on configuration.
        
        Returns:
            GatewayRouter: The configured router instance
            
        Raises:
            ValueError: If no valid router configuration is found
        """
        if cls._instance is None:
            cls._instance = cls._create_router()
        
        return cls._instance

    @classmethod
    def _create_router(cls) -> GatewayRouter:
        """
        Create a new router instance based on configuration.
        
        Returns:
            GatewayRouter: The configured router instance
        """
        if settings.CEQUENCE_ENABLED and settings.CEQUENCE_GATEWAY_URL:
            logger.info("🌐 Creating Cequence Gateway router")
            return CequenceRouter()
        else:
            logger.info("📡 Creating Direct mode router")
            return DirectRouter()

    @classmethod
    def reset(cls) -> None:
        """
        Reset the router instance.
        
        This is useful for testing or when configuration changes
        and a new router needs to be created.
        """
        cls._instance = None
        logger.info("🔄 Router instance reset")

    @classmethod
    def get_router_type(cls) -> str:
        """
        Get the type of router that will be created.
        
        Returns:
            str: The router type ('cequence' or 'direct')
        """
        if settings.CEQUENCE_ENABLED and settings.CEQUENCE_GATEWAY_URL:
            return "cequence"
        else:
            return "direct"
