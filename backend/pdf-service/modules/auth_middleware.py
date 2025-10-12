"""
Authentication and Authorization Middleware for NEXA
NERC CIP-003-11 compliant access controls
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from functools import wraps
import logging

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from passlib.context import CryptContext
import jwt
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
import redis

logger = logging.getLogger(__name__)

# Security configuration
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
security = HTTPBearer()

Base = declarative_base()

class SecurityConfig:
    """Security configuration for authentication"""
    
    JWT_SECRET = os.getenv('JWT_SECRET', 'change-this-in-production')
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Password policy (NERC CIP compliant)
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_HISTORY_COUNT = 5  # Remember last 5 passwords
    PASSWORD_MAX_AGE_DAYS = 90
    
    # Account lockout policy
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    # Session configuration
    SESSION_TIMEOUT_MINUTES = 15  # Idle timeout
    MAX_CONCURRENT_SESSIONS = 3
    
    # MFA configuration
    MFA_ENABLED = os.getenv('MFA_ENABLED', 'true').lower() == 'true'
    MFA_ISSUER = 'NEXA-Security'

class User(Base):
    """User model with NERC CIP compliant fields"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    
    # Security fields
    role = Column(String, nullable=False, default='viewer')  # admin, contractor, viewer
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    
    # Password management
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    password_history = Column(JSON, default=list)  # List of previous password hashes
    must_change_password = Column(Boolean, default=False)
    
    # Account security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    """Active user sessions for tracking"""
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    user = relationship("User", back_populates="sessions")

class AuditLog(Base):
    """Audit log for NERC CIP compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    user_id = Column(String, ForeignKey('users.id'), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    ip_address = Column(String, nullable=False)
    success = Column(Boolean, nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="audit_logs")

class PasswordValidator:
    """Validate passwords against NERC CIP requirements"""
    
    @staticmethod
    def validate_password(password: str, username: str = None) -> tuple[bool, List[str]]:
        """Validate password meets security requirements"""
        errors = []
        
        # Length check
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters")
        
        # Complexity checks
        if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letters")
        
        if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain lowercase letters")
        
        if SecurityConfig.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("Password must contain digits")
        
        if SecurityConfig.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain special characters")
        
        # Username similarity check
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain username")
        
        # Common password check
        common_passwords = ['password', '12345678', 'qwerty', 'abc123', 'password123']
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def check_password_history(password: str, password_history: List[str]) -> bool:
        """Check if password was recently used"""
        for old_hash in password_history[-SecurityConfig.PASSWORD_HISTORY_COUNT:]:
            if pwd_context.verify(password, old_hash):
                return False
        return True

class AuthenticationManager:
    """Handle authentication operations"""
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client or redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = 'viewer',
        created_by: str = None
    ) -> User:
        """Create new user with secure defaults"""
        
        # Validate password
        valid, errors = PasswordValidator.validate_password(password, username)
        if not valid:
            raise ValueError(f"Password validation failed: {', '.join(errors)}")
        
        # Hash password
        password_hash = pwd_context.hash(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            created_by=created_by,
            password_history=[password_hash]
        )
        
        self.db.add(user)
        self.db.commit()
        
        # Log user creation
        self._log_audit(
            user_id=user.id,
            action='user_created',
            resource=username,
            ip_address='system',
            success=True
        )
        
        return user
    
    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str
    ) -> Optional[User]:
        """Authenticate user with security checks"""
        
        # Get user
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            self._log_audit(
                user_id=None,
                action='login_failed',
                resource=username,
                ip_address=ip_address,
                success=False,
                details={'reason': 'user_not_found'}
            )
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            self._log_audit(
                user_id=user.id,
                action='login_failed',
                resource=username,
                ip_address=ip_address,
                success=False,
                details={'reason': 'account_locked'}
            )
            return None
        
        # Verify password
        if not pwd_context.verify(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many attempts
            if user.failed_login_attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES
                )
            
            self.db.commit()
            
            self._log_audit(
                user_id=user.id,
                action='login_failed',
                resource=username,
                ip_address=ip_address,
                success=False,
                details={'reason': 'invalid_password', 'attempts': user.failed_login_attempts}
            )
            return None
        
        # Check if password expired
        password_age = datetime.utcnow() - user.password_changed_at
        if password_age.days > SecurityConfig.PASSWORD_MAX_AGE_DAYS:
            user.must_change_password = True
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        
        self.db.commit()
        
        self._log_audit(
            user_id=user.id,
            action='login_success',
            resource=username,
            ip_address=ip_address,
            success=True
        )
        
        return user
    
    def create_access_token(
        self,
        user: User,
        ip_address: str,
        user_agent: str = None
    ) -> tuple[str, str]:
        """Create JWT access and refresh tokens"""
        
        # Create session ID
        session_id = secrets.token_urlsafe(16)
        
        # Access token payload
        access_payload = {
            'sub': user.id,
            'username': user.username,
            'role': user.role,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow(),
            'iss': 'nexa-security'
        }
        
        # Refresh token payload
        refresh_payload = {
            'sub': user.id,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': datetime.utcnow(),
            'iss': 'nexa-security'
        }
        
        access_token = jwt.encode(access_payload, SecurityConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, SecurityConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
        
        # Store session
        session = UserSession(
            user_id=user.id,
            token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        self.db.add(session)
        self.db.commit()
        
        # Store in Redis for fast validation
        self.redis.setex(
            f"session:{session_id}",
            SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user.id
        )
        
        return access_token, refresh_token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and check session"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET,
                algorithms=[SecurityConfig.JWT_ALGORITHM]
            )
            
            # Check session in Redis
            session_id = payload.get('session_id')
            if not self.redis.get(f"session:{session_id}"):
                return None
            
            # Update session activity
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            session = self.db.query(UserSession).filter_by(token_hash=token_hash).first()
            if session:
                session.last_activity = datetime.utcnow()
                self.db.commit()
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def _log_audit(
        self,
        action: str,
        resource: str,
        ip_address: str,
        success: bool,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log audit entry for compliance"""
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            success=success,
            details=details or {}
        )
        self.db.add(audit)
        self.db.commit()

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and authorization"""
    
    def __init__(self, app, db_session_factory, exempt_paths: List[str] = None):
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.exempt_paths = exempt_paths or ['/docs', '/openapi.json', '/auth/login', '/auth/register']
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Extract token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={'detail': 'Missing authentication token'}
            )
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        with self.db_session_factory() as db:
            auth_manager = AuthenticationManager(db)
            payload = auth_manager.verify_token(token)
            
            if not payload:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'detail': 'Invalid or expired token'}
                )
            
            # Add user info to request state
            request.state.user_id = payload['sub']
            request.state.username = payload['username']
            request.state.user_role = payload['role']
            
            # Log access
            auth_manager._log_audit(
                user_id=payload['sub'],
                action='api_access',
                resource=request.url.path,
                ip_address=request.client.host,
                success=True
            )
        
        response = await call_next(request)
        return response

def require_role(required_roles: List[str]):
    """Decorator to check user role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_role = getattr(request.state, 'user_role', None)
            if not user_role or user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test password validation
    valid, errors = PasswordValidator.validate_password("Test@Password123!")
    print(f"Password valid: {valid}, Errors: {errors}")
    
    # Test password hashing
    password = "SecureP@ssw0rd!"
    hashed = pwd_context.hash(password)
    verified = pwd_context.verify(password, hashed)
    print(f"Password hashing test: {verified}")
    
    print("Authentication middleware ready for NERC CIP compliance!")
