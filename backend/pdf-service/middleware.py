"""
Middleware for request validation and error handling
"""
import time
import uuid
from typing import Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and correlation ID generation"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id
        
        # Log request
        start_time = time.time()
        logger.info(f"[{correlation_id}] {request.method} {request.url.path} from {request.client.host}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(f"[{correlation_id}] Response: {response.status_code} in {process_time:.2f}s")
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(f"[{correlation_id}] Error after {process_time:.2f}s: {str(exc)}")
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"X-Correlation-ID": correlation_id}
            )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Enhanced error handling with user-friendly messages"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as exc:
            # Handle expected HTTP exceptions with better messages
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            
            # Custom error messages for common issues
            error_messages = {
                400: {
                    "Spec book not learned": {
                        "error": "Setup Required",
                        "message": "Please upload a spec book first before analyzing audits",
                        "action": "Upload spec book using /upload-spec-book endpoint"
                    },
                    "Only PDF files": {
                        "error": "Invalid File Type",
                        "message": "Only PDF files are supported",
                        "action": "Please upload a PDF file"
                    },
                    "No text could be extracted": {
                        "error": "Empty Document",
                        "message": "The PDF appears to be empty or contains only images",
                        "action": "Please ensure the PDF contains readable text"
                    }
                },
                413: {
                    "error": "File Too Large",
                    "message": "File exceeds maximum size of 1100MB",
                    "action": "Please reduce file size or split into smaller documents"
                }
            }
            
            # Find matching error message
            error_response = {"correlation_id": correlation_id}
            
            if exc.status_code in error_messages:
                if isinstance(error_messages[exc.status_code], dict):
                    # Check for specific error patterns
                    for pattern, response_data in error_messages[exc.status_code].items():
                        if pattern in exc.detail:
                            error_response.update(response_data)
                            break
                    else:
                        # Default message for status code
                        error_response["error"] = f"Request Error ({exc.status_code})"
                        error_response["message"] = exc.detail
                else:
                    error_response.update(error_messages[exc.status_code])
            else:
                error_response["error"] = f"Request Error ({exc.status_code})"
                error_response["message"] = exc.detail
                
            error_response["timestamp"] = datetime.utcnow().isoformat()
            
            logger.warning(f"[{correlation_id}] HTTP {exc.status_code}: {exc.detail}")
            
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response,
                headers={"X-Correlation-ID": correlation_id}
            )
            
        except Exception as exc:
            # Handle unexpected errors
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            logger.error(f"[{correlation_id}] Unexpected error: {str(exc)}", exc_info=True)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"X-Correlation-ID": correlation_id}
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}  # IP -> list of timestamps
        
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
            
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip] 
                if now - ts < self.period
            ]
        else:
            self.requests[client_ip] = []
            
        # Check rate limit
        if len(self.requests[client_ip]) >= self.calls:
            correlation_id = getattr(request.state, 'correlation_id', 'unknown')
            logger.warning(f"[{correlation_id}] Rate limit exceeded for {client_ip}")
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": f"Maximum {self.calls} requests per {self.period} seconds",
                    "retry_after": self.period,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + self.period)),
                    "Retry-After": str(self.period)
                }
            )
            
        # Record request
        self.requests[client_ip].append(now)
        
        # Add rate limit headers
        response = await call_next(request)
        remaining = self.calls - len(self.requests[client_ip])
        
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response
