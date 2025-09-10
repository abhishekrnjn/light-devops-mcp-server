"""
Logging middleware for MCP HTTP Server.

This middleware provides comprehensive request/response logging,
performance monitoring, and audit trail functionality.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.

    This middleware logs all incoming requests and outgoing responses,
    including timing information, user context, and performance metrics.
    """

    def __init__(
        self, app, enable_detailed_logging: bool = True, log_request_body: bool = False
    ):
        """
        Initialize the logging middleware.

        Args:
            app: FastAPI application instance
            enable_detailed_logging: Whether to enable detailed logging
            log_request_body: Whether to log request body (be careful with sensitive data)
        """
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
        self.log_request_body = log_request_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through logging middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain

        Returns:
            HTTP response
        """
        # Start timing
        start_time = time.time()

        # Extract request information
        request_info = await self._extract_request_info(request)

        # Log incoming request
        logger.info(
            f"📥 {request.method} {request.url.path} - {request_info['client_ip']}"
        )

        if self.enable_detailed_logging:
            logger.debug(f"📋 Request details: {json.dumps(request_info, indent=2)}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Extract response information
            response_info = self._extract_response_info(response, process_time)

            # Log outgoing response
            logger.info(
                f"📤 {request.method} {request.url.path} - {response.status_code} - "
                f"{process_time:.3f}s"
            )

            if self.enable_detailed_logging:
                logger.debug(
                    f"📋 Response details: {json.dumps(response_info, indent=2)}"
                )

            # Add performance headers
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Timestamp"] = datetime.now().isoformat()

            return response

        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time

            # Log error
            logger.error(
                f"💥 {request.method} {request.url.path} - ERROR - {process_time:.3f}s - {str(e)}"
            )

            # Re-raise the exception for error handling middleware
            raise

    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """
        Extract information from the incoming request.

        Args:
            request: HTTP request

        Returns:
            Dictionary containing request information
        """
        info = {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "timestamp": datetime.now().isoformat(),
        }

        # Add headers (excluding sensitive ones)
        sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token"}
        info["headers"] = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in sensitive_headers
        }

        # Add request body if enabled and not too large
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                content_length = int(request.headers.get("content-length", 0))
                if content_length < 1024:  # Only log small bodies
                    body = await request.body()
                    if body:
                        info["body"] = body.decode("utf-8")
            except Exception as e:
                logger.warning(f"⚠️ Could not log request body: {e}")

        return info

    def _extract_response_info(
        self, response: Response, process_time: float
    ) -> Dict[str, Any]:
        """
        Extract information from the outgoing response.

        Args:
            response: HTTP response
            process_time: Request processing time in seconds

        Returns:
            Dictionary containing response information
        """
        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": response.headers.get("content-length"),
            "process_time": process_time,
            "timestamp": datetime.now().isoformat(),
        }

    def _should_log_request(self, request: Request) -> bool:
        """
        Determine if the request should be logged.

        Args:
            request: HTTP request

        Returns:
            True if request should be logged, False otherwise
        """
        # Skip logging for health checks and static content
        skip_paths = ["/health", "/metrics", "/favicon.ico"]
        if request.url.path in skip_paths:
            return False

        return True

    def _get_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract user context from the request.

        Args:
            request: HTTP request

        Returns:
            Dictionary containing user context or None
        """
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "user_id"):
                return {
                    "user_id": user.user_id,
                    "roles": getattr(user, "roles", []),
                    "permissions": getattr(user, "permissions", []),
                }

        return None
