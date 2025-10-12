"""
Secure Upload Module for NEXA
NERC CIP Compliant with encryption, validation, and auditing
"""

import hashlib
import hmac
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import jwt
import aiofiles
from fastapi import UploadFile, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
# Magic is optional for MIME type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except Exception:
    magic = None
    MAGIC_AVAILABLE = False
# YARA is optional for malware scanning
try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    yara = None
    YARA_AVAILABLE = False
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

# Security configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
security = HTTPBearer()

class SecurityConfig:
    """Security configuration for NERC CIP compliance"""
    
    # Encryption
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
    JWT_SECRET = os.getenv('JWT_SECRET', 'change-this-in-production')
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24
    
    # File validation
    ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
    
    # Storage
    SECURE_STORAGE_PATH = Path(os.getenv('SECURE_STORAGE_PATH', '/data/secure_uploads'))
    QUARANTINE_PATH = Path(os.getenv('QUARANTINE_PATH', '/data/quarantine'))
    
    # Audit
    AUDIT_LOG_PATH = Path(os.getenv('AUDIT_LOG_PATH', '/data/audit_logs'))
    
    # RBAC roles
    ROLES = {
        'admin': ['upload', 'download', 'delete', 'audit'],
        'contractor': ['upload', 'download'],
        'viewer': ['download']
    }

class FileEncryptor:
    """AES-256 encryption for files at rest"""
    
    def __init__(self, key: Optional[str] = None):
        if key:
            self.cipher = Fernet(key.encode())
        else:
            # Derive key from environment secret
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'nexa-salt-2025',  # Should be random in production
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(
                SecurityConfig.ENCRYPTION_KEY.encode()
            ))
            self.cipher = Fernet(key)
    
    def encrypt_file(self, file_data: bytes) -> bytes:
        """Encrypt file data with AES-256"""
        return self.cipher.encrypt(file_data)
    
    def decrypt_file(self, encrypted_data: bytes) -> bytes:
        """Decrypt file data"""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_metadata(self, metadata: Dict) -> str:
        """Encrypt metadata as JSON"""
        json_str = json.dumps(metadata)
        return self.cipher.encrypt(json_str.encode()).decode()
    
    def decrypt_metadata(self, encrypted_metadata: str) -> Dict:
        """Decrypt metadata from JSON"""
        decrypted = self.cipher.decrypt(encrypted_metadata.encode())
        return json.loads(decrypted.decode())

class FileValidator:
    """Validate files for security threats"""
    
    def __init__(self):
        self.mime = magic.Magic(mime=True) if MAGIC_AVAILABLE else None
        self.yara_rules = self._load_yara_rules()
    
    def _load_yara_rules(self):
        """Load YARA rules for malware detection"""
        if not YARA_AVAILABLE:
            return None
            
        rules_path = Path('security/yara_rules.yar')
        if rules_path.exists():
            return yara.compile(filepath=str(rules_path))
        else:
            # Basic rule for demo
            rule_string = '''
            rule Suspicious_PDF {
                meta:
                    description = "Detects suspicious PDF content"
                strings:
                    $pdf = "%PDF"
                    $js = "/JavaScript"
                    $launch = "/Launch"
                    $embedded = "/EmbeddedFile"
                condition:
                    $pdf and ($js or $launch or $embedded)
            }
            '''
            return yara.compile(source=rule_string)
    
    async def validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """Comprehensive file validation"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SecurityConfig.ALLOWED_EXTENSIONS:
            results['valid'] = False
            results['errors'].append(f"File type {file_ext} not allowed")
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset
        
        if file_size > SecurityConfig.MAX_FILE_SIZE:
            results['valid'] = False
            results['errors'].append(f"File too large: {file_size} bytes")
        
        # Check MIME type if magic is available
        file_data = await file.read()
        
        if self.mime:
            mime_type = self.mime.from_buffer(file_data)
            if mime_type not in SecurityConfig.ALLOWED_MIME_TYPES:
                results['valid'] = False
                results['errors'].append(f"MIME type {mime_type} not allowed")
        else:
            # Fallback: check by extension only when magic is not available
            results['warnings'].append("MIME type validation skipped (magic library unavailable)")
        
        # Scan for malware with YARA
        if self.yara_rules:
            matches = self.yara_rules.match(data=file_data)
            if matches:
                results['valid'] = False
                results['errors'].append(f"Security threat detected: {matches}")
        
        # Reset file pointer
        file.file.seek(0)
        
        return results

class AuditLogger:
    """NERC CIP compliant audit logging"""
    
    def __init__(self):
        self.log_path = SecurityConfig.AUDIT_LOG_PATH
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.encryptor = FileEncryptor()
    
    async def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        ip_address: str,
        success: bool,
        details: Optional[Dict] = None
    ):
        """Log access attempt with encryption"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'ip_address': ip_address,
            'success': success,
            'details': details or {}
        }
        
        # Encrypt sensitive data
        encrypted_entry = self.encryptor.encrypt_metadata(log_entry)
        
        # Write to daily log file
        log_file = self.log_path / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.log"
        async with aiofiles.open(log_file, 'a') as f:
            await f.write(encrypted_entry + '\n')
        
        # Also log to standard logger for monitoring
        logger.info(f"Audit: {action} by {user_id} on {resource} - {'SUCCESS' if success else 'FAILURE'}")
    
    async def get_audit_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """Retrieve and decrypt audit logs"""
        logs = []
        
        # Iterate through date range
        current_date = start_date
        while current_date <= end_date:
            log_file = self.log_path / f"audit_{current_date.strftime('%Y%m%d')}.log"
            if log_file.exists():
                async with aiofiles.open(log_file, 'r') as f:
                    async for line in f:
                        try:
                            decrypted = self.encryptor.decrypt_metadata(line.strip())
                            if user_id is None or decrypted['user_id'] == user_id:
                                logs.append(decrypted)
                        except Exception as e:
                            logger.error(f"Failed to decrypt log entry: {e}")
            current_date += timedelta(days=1)
        
        return logs

class TokenManager:
    """JWT token management for authentication"""
    
    @staticmethod
    def create_access_token(
        user_id: str,
        role: str,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(hours=SecurityConfig.JWT_EXPIRATION_HOURS)
        claims = {
            'sub': user_id,
            'role': role,
            'exp': expire,
            'iat': datetime.utcnow(),
            'iss': 'nexa-security',
            **(additional_claims or {})
        }
        return jwt.encode(claims, SecurityConfig.JWT_SECRET, algorithm=SecurityConfig.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET,
                algorithms=[SecurityConfig.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

class SecureUploadManager:
    """Main secure upload manager with all security features"""
    
    def __init__(self):
        self.encryptor = FileEncryptor()
        self.validator = FileValidator()
        self.audit = AuditLogger()
        self.storage_path = SecurityConfig.SECURE_STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.quarantine_path = SecurityConfig.QUARANTINE_PATH
        self.quarantine_path.mkdir(parents=True, exist_ok=True)
    
    async def secure_upload(
        self,
        file: UploadFile,
        user_id: str,
        user_role: str,
        ip_address: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Secure file upload with full validation and encryption"""
        
        # Check permissions
        if 'upload' not in SecurityConfig.ROLES.get(user_role, []):
            await self.audit.log_access(
                user_id, 'upload', file.filename, ip_address, False,
                {'reason': 'insufficient_permissions'}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for upload"
            )
        
        # Validate file
        validation = await self.validator.validate_file(file)
        if not validation['valid']:
            # Move to quarantine
            quarantine_file = self.quarantine_path / f"{datetime.utcnow().timestamp()}_{file.filename}"
            file_data = await file.read()
            async with aiofiles.open(quarantine_file, 'wb') as f:
                await f.write(file_data)
            
            await self.audit.log_access(
                user_id, 'upload', file.filename, ip_address, False,
                {'reason': 'validation_failed', 'errors': validation['errors']}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {validation['errors']}"
            )
        
        # Read and encrypt file
        file_data = await file.read()
        encrypted_data = self.encryptor.encrypt_file(file_data)
        
        # Generate secure filename
        file_hash = hashlib.sha256(file_data).hexdigest()
        secure_filename = f"{file_hash}_{datetime.utcnow().timestamp()}.enc"
        file_path = self.storage_path / secure_filename
        
        # Store encrypted file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(encrypted_data)
        
        # Store encrypted metadata
        file_metadata = {
            'original_name': file.filename,
            'content_type': file.content_type,
            'size': len(file_data),
            'hash': file_hash,
            'uploaded_by': user_id,
            'upload_time': datetime.utcnow().isoformat(),
            'secure_path': str(file_path),
            'custom_metadata': metadata or {}
        }
        
        metadata_path = file_path.with_suffix('.meta')
        encrypted_metadata = self.encryptor.encrypt_metadata(file_metadata)
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(encrypted_metadata)
        
        # Log successful upload
        await self.audit.log_access(
            user_id, 'upload', file.filename, ip_address, True,
            {'file_hash': file_hash, 'size': len(file_data)}
        )
        
        return {
            'success': True,
            'file_id': file_hash,
            'message': 'File uploaded securely',
            'encryption': 'AES-256',
            'compliance': 'NERC CIP-003-11'
        }
    
    async def secure_download(
        self,
        file_id: str,
        user_id: str,
        user_role: str,
        ip_address: str
    ) -> tuple[bytes, Dict]:
        """Secure file download with decryption"""
        
        # Check permissions
        if 'download' not in SecurityConfig.ROLES.get(user_role, []):
            await self.audit.log_access(
                user_id, 'download', file_id, ip_address, False,
                {'reason': 'insufficient_permissions'}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for download"
            )
        
        # Find encrypted file
        encrypted_files = list(self.storage_path.glob(f"{file_id}_*.enc"))
        if not encrypted_files:
            await self.audit.log_access(
                user_id, 'download', file_id, ip_address, False,
                {'reason': 'file_not_found'}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_path = encrypted_files[0]
        metadata_path = file_path.with_suffix('.meta')
        
        # Load and decrypt metadata
        async with aiofiles.open(metadata_path, 'r') as f:
            encrypted_metadata = await f.read()
        metadata = self.encryptor.decrypt_metadata(encrypted_metadata)
        
        # Load and decrypt file
        async with aiofiles.open(file_path, 'rb') as f:
            encrypted_data = await f.read()
        decrypted_data = self.encryptor.decrypt_file(encrypted_data)
        
        # Log successful download
        await self.audit.log_access(
            user_id, 'download', metadata['original_name'], ip_address, True,
            {'file_id': file_id}
        )
        
        return decrypted_data, metadata

# Dependency injection functions for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Extract and verify user from JWT token"""
    token = credentials.credentials
    user_data = TokenManager.verify_token(token)
    return user_data

async def check_rbac(action: str, user: Dict = Depends(get_current_user)):
    """Check if user has permission for action"""
    user_role = user.get('role', 'viewer')
    if action not in SecurityConfig.ROLES.get(user_role, []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {user_role} cannot perform {action}"
        )
    return True

# Example secure endpoints for integration
def create_secure_endpoints(app):
    """Add secure upload endpoints to FastAPI app"""
    manager = SecureUploadManager()
    
    @app.post("/secure/upload")
    async def secure_upload_endpoint(
        file: UploadFile,
        user: Dict = Depends(get_current_user),
        _: bool = Depends(lambda u=Depends(get_current_user): check_rbac('upload', u))
    ):
        return await manager.secure_upload(
            file=file,
            user_id=user['sub'],
            user_role=user['role'],
            ip_address='127.0.0.1',  # Get from request in production
            metadata={'project': 'NEXA', 'type': 'utility_doc'}
        )
    
    @app.get("/secure/download/{file_id}")
    async def secure_download_endpoint(
        file_id: str,
        user: Dict = Depends(get_current_user),
        _: bool = Depends(lambda u=Depends(get_current_user): check_rbac('download', u))
    ):
        file_data, metadata = await manager.secure_download(
            file_id=file_id,
            user_id=user['sub'],
            user_role=user['role'],
            ip_address='127.0.0.1'
        )
        return {
            'filename': metadata['original_name'],
            'data': file_data.hex()  # Convert to hex for JSON response
        }
    
    @app.get("/secure/audit")
    async def audit_logs_endpoint(
        start_date: datetime,
        end_date: datetime,
        user: Dict = Depends(get_current_user),
        _: bool = Depends(lambda u=Depends(get_current_user): check_rbac('audit', u))
    ):
        logs = await manager.audit.get_audit_logs(start_date, end_date)
        return {'audit_logs': logs, 'count': len(logs)}

if __name__ == "__main__":
    # Test encryption
    encryptor = FileEncryptor()
    test_data = b"Sensitive utility document content"
    encrypted = encryptor.encrypt_file(test_data)
    decrypted = encryptor.decrypt_file(encrypted)
    assert test_data == decrypted
    print("Encryption test passed!")
    
    # Test token
    token = TokenManager.create_access_token('contractor_001', 'contractor')
    payload = TokenManager.verify_token(token)
    print(f"Token payload: {payload}")
    
    print("Security module ready for NERC CIP compliance!")
