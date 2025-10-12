"""
Simple Authentication System for NEXA
Provides basic JWT authentication without database dependency
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import jwt
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'nexa-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Simple file-based user storage
DATA_PATH = os.getenv('DATA_PATH', '/data')
if not os.path.exists(DATA_PATH) and DATA_PATH == '/data':
    DATA_PATH = './data'
USERS_FILE = os.path.join(DATA_PATH, 'users.json')

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "viewer"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class SimpleAuthManager:
    """Simple authentication manager using file storage"""
    
    def __init__(self):
        self.users_file = USERS_FILE
        self._ensure_data_dir()
        self._init_default_users()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
    
    def _init_default_users(self):
        """Initialize with default admin user if no users exist"""
        if not os.path.exists(self.users_file):
            default_users = {
                "admin@nexa.com": {
                    "email": "admin@nexa.com",
                    "password_hash": pwd_context.hash("admin123"),
                    "role": "admin",
                    "created_at": datetime.utcnow().isoformat()
                },
                "gf@nexa.com": {
                    "email": "gf@nexa.com",
                    "password_hash": pwd_context.hash("gf123"),
                    "role": "general_foreman",
                    "created_at": datetime.utcnow().isoformat()
                },
                "qa@nexa.com": {
                    "email": "qa@nexa.com",
                    "password_hash": pwd_context.hash("qa123"),
                    "role": "qa_inspector",
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            self._save_users(default_users)
            logger.info("✅ Initialized default users: admin@nexa.com, gf@nexa.com, qa@nexa.com")
    
    def _load_users(self) -> Dict:
        """Load users from file"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    
    def _save_users(self, users: Dict):
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user by email and password"""
        users = self._load_users()
        
        if email not in users:
            return None
        
        user = users[email]
        if not pwd_context.verify(password, user['password_hash']):
            return None
        
        # Return user info without password hash
        return {
            "email": user['email'],
            "role": user['role'],
            "created_at": user.get('created_at')
        }
    
    def register_user(self, email: str, password: str, role: str = "viewer") -> Dict:
        """Register new user"""
        users = self._load_users()
        
        if email in users:
            raise ValueError("User already exists")
        
        users[email] = {
            "email": email,
            "password_hash": pwd_context.hash(password),
            "role": role,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._save_users(users)
        
        return {
            "email": email,
            "role": role
        }
    
    def create_access_token(self, user: Dict) -> str:
        """Create JWT access token"""
        payload = {
            "sub": user['email'],
            "email": user['email'],
            "role": user['role'],
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT error: {e}")
            return None

# Global auth manager instance
auth_manager = SimpleAuthManager()

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict:
    """Get current authenticated user from token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict]:
    """Get current authenticated user from token (optional - returns None if no auth)"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = auth_manager.verify_token(token)
        return payload
    except:
        return None

def create_auth_router() -> APIRouter:
    """Create authentication router with endpoints"""
    router = APIRouter(prefix="/auth", tags=["Authentication"])
    
    @router.post("/login", response_model=Token)
    async def login(request: LoginRequest):
        """Login endpoint"""
        user = auth_manager.authenticate_user(request.email, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = auth_manager.create_access_token(user)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    
    @router.post("/register", response_model=Token)
    async def register(request: RegisterRequest):
        """Register new user"""
        try:
            user = auth_manager.register_user(
                email=request.email,
                password=request.password,
                role=request.role
            )
            
            access_token = auth_manager.create_access_token(user)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @router.get("/me")
    async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
        """Get current user information"""
        return current_user
    
    @router.post("/logout")
    async def logout(current_user: Dict = Depends(get_current_user)):
        """Logout endpoint (client should discard token)"""
        return {"message": "Logged out successfully"}
    
    @router.get("/health")
    async def auth_health():
        """Check auth system health"""
        return {
            "status": "healthy",
            "users_file": os.path.exists(USERS_FILE),
            "data_path": DATA_PATH
        }
    
    return router

def integrate_auth(app):
    """Integrate authentication into FastAPI app"""
    router = create_auth_router()
    app.include_router(router, prefix="/auth", tags=["Authentication"])
    logger.info("Authentication endpoints registered at /auth/*")
    logger.info("   Default users: admin@nexa.com (admin123), gf@nexa.com (gf123), qa@nexa.com (qa123)")
    return router
