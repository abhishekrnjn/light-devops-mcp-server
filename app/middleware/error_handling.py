"""
Error handling middleware for MCP HTTP Server.

This middleware provides centralized error handling, logging, and response formatting
for all requests, ensuring consistent error responses across the API.
"""

import logging
import traceback
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.mcp import ErrorResponse

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling.
    
    This middleware catches all exceptions, logs them appropriately,
    and returns consistent error responses.
    """

    def __init__(self, app, enable_error_logging: bool = True):
        """
        Initialize the error handling middleware.
        
        Args:
            app: FastAPI application instance
            enable_error_logging: Whether to enable detailed error logging
        """
        super().__init__(app)
        self.enable_error_logging = enable_error_logging

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through error handling middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        try:
            response = await call_next(request)
            return response
            
        except StarletteHTTPException as e:
            # Handle FastAPI/Starlette HTTP exceptions
            return await self._handle_http_exception(request, e)
            
        except HTTPException as e:
            # Handle custom HTTP exceptions
            return await self._handle_http_exception(request, e)
            
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(request, e)

    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle HTTP exceptions with proper logging and response formatting.
        
        Args:
            request: HTTP request
            exc: HTTP exception
            
        Returns:
            JSON error response
        """
        # Log the error
        logger.warning(
            f"🚨 HTTP {exc.status_code} error for {request.method} {request.url.path}: {exc.detail}"
        )
        
        # Create error response
        error_response = ErrorResponse(
            success=False,
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            details={
                "path": str(request.url.path),
                "method": request.method,
                "status_code": exc.status_code,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict(),
            headers={"Content-Type": "application/json"}
        )

    async def _handle_unexpected_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Handle unexpected exceptions with proper logging and response formatting.
        
        Args:
            request: HTTP request
            exc: Exception
            
        Returns:
            JSON error response
        """
        # Log the error with full traceback
        logger.error(
            f"💥 Unexpected error for {request.method} {request.url.path}: {str(exc)}"
        )
        
        if self.enable_error_logging:
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        
        # Create error response
        error_response = ErrorResponse(
            success=False,
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={
                "path": str(request.url.path),
                "method": request.method,
                "error_type": type(exc).__name__,
            }
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict(),
            headers={"Content-Type": "application/json"}
        )

    def _get_error_context(self, request: Request) -> Dict[str, Any]:
        """
        Get context information for error logging.
        
        Args:
            request: HTTP request
            
        Returns:
            Dictionary containing error context
        """
        return {
            "path": str(request.url.path),
            "method": request.method,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
