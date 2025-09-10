"""
Request validation middleware for MCP HTTP Server.

This middleware provides centralized request validation, sanitization,
and security checks for all incoming requests.
"""

import logging
import json
from typing import Callable, Dict, Any, Optional, List
from urllib.parse import unquote

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.schemas.mcp import ErrorResponse

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized request validation and sanitization.
    
    This middleware validates incoming requests, sanitizes input data,
    and performs security checks before passing requests to handlers.
    """

    def __init__(self, app, enable_validation: bool = True, max_request_size: int = 10 * 1024 * 1024):
        """
        Initialize the request validation middleware.
        
        Args:
            app: FastAPI application instance
            enable_validation: Whether to enable request validation
            max_request_size: Maximum request size in bytes (10MB default)
        """
        super().__init__(app)
        self.enable_validation = enable_validation
        self.max_request_size = max_request_size
        
        # Security patterns to check for
        self.suspicious_patterns = [
            r"<script",
            r"javascript:",
            r"onload=",
            r"onerror=",
            r"eval\(",
            r"exec\(",
            r"system\(",
            r"shell_exec",
            r"passthru",
            r"proc_open",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through validation middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        if not self.enable_validation:
            return await call_next(request)

        try:
            # Validate request size
            await self._validate_request_size(request)
            
            # Validate request headers
            self._validate_headers(request)
            
            # Validate query parameters
            self._validate_query_params(request)
            
            # Validate request body for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            
            # Validate URL path
            self._validate_url_path(request)
            
            # Process request
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Handle validation errors
            logger.warning(f"⚠️ Request validation failed: {e}")
            return await self._create_validation_error_response(str(e))

    async def _validate_request_size(self, request: Request) -> None:
        """
        Validate request size.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If request is too large
        """
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > self.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large. Maximum size: {self.max_request_size} bytes"
                )

    def _validate_headers(self, request: Request) -> None:
        """
        Validate request headers.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If headers are invalid
        """
        # Check for required headers
        required_headers = ["user-agent"]
        for header in required_headers:
            if header not in request.headers:
                logger.warning(f"⚠️ Missing required header: {header}")
        
        # Check for suspicious header values
        for name, value in request.headers.items():
            if self._contains_suspicious_content(value):
                logger.warning(f"⚠️ Suspicious content in header {name}: {value}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid header content detected"
                )

    def _validate_query_params(self, request: Request) -> None:
        """
        Validate query parameters.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If query parameters are invalid
        """
        for name, value in request.query_params.items():
            # Check for suspicious content
            if self._contains_suspicious_content(value):
                logger.warning(f"⚠️ Suspicious content in query param {name}: {value}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid query parameter content detected"
                )
            
            # Check for URL encoding issues
            try:
                unquote(value)
            except Exception as e:
                logger.warning(f"⚠️ Invalid URL encoding in query param {name}: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid URL encoding detected"
                )

    async def _validate_request_body(self, request: Request) -> None:
        """
        Validate request body.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If request body is invalid
        """
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            try:
                # Read and parse JSON body
                body = await request.body()
                if body:
                    json_data = json.loads(body.decode("utf-8"))
                    
                    # Validate JSON structure
                    self._validate_json_structure(json_data)
                    
                    # Check for suspicious content in JSON
                    self._validate_json_content(json_data)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Invalid JSON in request body: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON format"
                )
            except Exception as e:
                logger.warning(f"⚠️ Error validating request body: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid request body"
                )

    def _validate_url_path(self, request: Request) -> None:
        """
        Validate URL path.
        
        Args:
            request: HTTP request
            
        Raises:
            HTTPException: If URL path is invalid
        """
        path = str(request.url.path)
        
        # Check for suspicious content in path
        if self._contains_suspicious_content(path):
            logger.warning(f"⚠️ Suspicious content in URL path: {path}")
            raise HTTPException(
                status_code=400,
                detail="Invalid URL path detected"
            )
        
        # Check for path traversal attempts
        if ".." in path or "//" in path:
            logger.warning(f"⚠️ Path traversal attempt detected: {path}")
            raise HTTPException(
                status_code=400,
                detail="Invalid URL path detected"
            )

    def _validate_json_structure(self, data: Any, max_depth: int = 10, current_depth: int = 0) -> None:
        """
        Validate JSON structure for security.
        
        Args:
            data: JSON data to validate
            max_depth: Maximum nesting depth allowed
            current_depth: Current nesting depth
            
        Raises:
            HTTPException: If JSON structure is invalid
        """
        if current_depth > max_depth:
            raise HTTPException(
                status_code=400,
                detail="JSON structure too deep"
            )
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Validate key
                if not isinstance(key, str):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid JSON key type"
                    )
                
                # Check key length
                if len(key) > 1000:
                    raise HTTPException(
                        status_code=400,
                        detail="JSON key too long"
                    )
                
                # Recursively validate value
                self._validate_json_structure(value, max_depth, current_depth + 1)
                
        elif isinstance(data, list):
            # Check list size
            if len(data) > 10000:
                raise HTTPException(
                    status_code=400,
                    detail="JSON array too large"
                )
            
            # Recursively validate each item
            for item in data:
                self._validate_json_structure(item, max_depth, current_depth + 1)

    def _validate_json_content(self, data: Any) -> None:
        """
        Validate JSON content for security.
        
        Args:
            data: JSON data to validate
            
        Raises:
            HTTPException: If JSON content is suspicious
        """
        if isinstance(data, dict):
            for key, value in data.items():
                # Check key and value for suspicious content
                if self._contains_suspicious_content(key) or self._contains_suspicious_content(str(value)):
                    raise HTTPException(
                        status_code=400,
                        detail="Suspicious content detected in JSON"
                    )
                
                # Recursively validate nested data
                self._validate_json_content(value)
                
        elif isinstance(data, list):
            for item in data:
                self._validate_json_content(item)

    def _contains_suspicious_content(self, text: str) -> bool:
        """
        Check if text contains suspicious patterns.
        
        Args:
            text: Text to check
            
        Returns:
            True if suspicious content is found, False otherwise
        """
        import re
        
        text_lower = text.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    async def _create_validation_error_response(self, error_message: str) -> JSONResponse:
        """
        Create a validation error response.
        
        Args:
            error_message: Error message
            
        Returns:
            JSON error response
        """
        error_response = ErrorResponse(
            success=False,
            error="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"message": error_message}
        )
        
        return JSONResponse(
            status_code=400,
            content=error_response.dict(),
            headers={"Content-Type": "application/json"}
        )
