"""
Security Testing Suite for NEXA
Validates NERC CIP compliance and security controls
"""

import pytest
import asyncio
import hashlib
import jwt
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile
from io import BytesIO

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.secure_upload import (
    SecurityConfig, FileEncryptor, FileValidator,
    AuditLogger, TokenManager, SecureUploadManager
)
from modules.auth_middleware import (
    PasswordValidator, AuthenticationManager,
    AuthenticationMiddleware, User, UserSession
)

class TestPasswordSecurity:
    """Test password validation and policies"""
    
    def test_password_complexity(self):
        """Test NERC CIP password requirements"""
        # Valid password
        valid, errors = PasswordValidator.validate_password("Test@Password123!")
        assert valid == True
        assert len(errors) == 0
        
        # Too short
        valid, errors = PasswordValidator.validate_password("Test@123")
        assert valid == False
        assert any("at least" in e for e in errors)
        
        # No uppercase
        valid, errors = PasswordValidator.validate_password("test@password123!")
        assert valid == False
        assert any("uppercase" in e for e in errors)
        
        # No special characters
        valid, errors = PasswordValidator.validate_password("TestPassword123")
        assert valid == False
        assert any("special" in e for e in errors)
        
        # Common password
        valid, errors = PasswordValidator.validate_password("Password123!")
        assert valid == False
        assert any("common" in e for e in errors)
    
    def test_password_history(self):
        """Test password history checking"""
        password_history = [
            "$argon2id$v=19$m=65536,t=3,p=4$oldpassword1",
            "$argon2id$v=19$m=65536,t=3,p=4$oldpassword2",
        ]
        
        # New password should pass
        assert PasswordValidator.check_password_history(
            "NewPassword@123",
            password_history
        ) == True

class TestEncryption:
    """Test file encryption capabilities"""
    
    def test_file_encryption(self):
        """Test AES-256 file encryption"""
        encryptor = FileEncryptor()
        
        # Test data
        original_data = b"Sensitive utility infrastructure document content"
        
        # Encrypt
        encrypted = encryptor.encrypt_file(original_data)
        assert encrypted != original_data
        assert len(encrypted) > len(original_data)
        
        # Decrypt
        decrypted = encryptor.decrypt_file(encrypted)
        assert decrypted == original_data
    
    def test_metadata_encryption(self):
        """Test metadata encryption"""
        encryptor = FileEncryptor()
        
        metadata = {
            'filename': 'utility_spec.pdf',
            'user': 'contractor_001',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Encrypt metadata
        encrypted_meta = encryptor.encrypt_metadata(metadata)
        assert isinstance(encrypted_meta, str)
        
        # Decrypt metadata
        decrypted_meta = encryptor.decrypt_metadata(encrypted_meta)
        assert decrypted_meta == metadata

class TestFileValidation:
    """Test file validation and security scanning"""
    
    @pytest.mark.asyncio
    async def test_file_type_validation(self):
        """Test allowed file types"""
        validator = FileValidator()
        
        # Valid PDF file
        pdf_file = Mock(spec=UploadFile)
        pdf_file.filename = "test.pdf"
        pdf_file.file.tell.return_value = 1024
        pdf_file.file.seek = Mock()
        pdf_file.read = AsyncMock(return_value=b"%PDF-1.4")
        
        result = await validator.validate_file(pdf_file)
        assert result['valid'] == True
        
        # Invalid executable file
        exe_file = Mock(spec=UploadFile)
        exe_file.filename = "malware.exe"
        exe_file.file.tell.return_value = 1024
        exe_file.file.seek = Mock()
        exe_file.read = AsyncMock(return_value=b"MZ\x90\x00")
        
        result = await validator.validate_file(exe_file)
        assert result['valid'] == False
        assert any("not allowed" in e for e in result['errors'])
    
    @pytest.mark.asyncio
    async def test_file_size_validation(self):
        """Test file size limits"""
        validator = FileValidator()
        
        # Oversized file
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large.pdf"
        large_file.file.tell.return_value = 200 * 1024 * 1024  # 200MB
        large_file.file.seek = Mock()
        large_file.read = AsyncMock(return_value=b"%PDF-1.4")
        
        result = await validator.validate_file(large_file)
        assert result['valid'] == False
        assert any("too large" in e for e in result['errors'])

class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_jwt_token_creation(self):
        """Test JWT token generation"""
        token = TokenManager.create_access_token(
            user_id='user123',
            role='contractor',
            additional_claims={'project': 'NEXA'}
        )
        
        # Decode token
        payload = jwt.decode(
            token,
            SecurityConfig.JWT_SECRET,
            algorithms=[SecurityConfig.JWT_ALGORITHM]
        )
        
        assert payload['sub'] == 'user123'
        assert payload['role'] == 'contractor'
        assert payload['project'] == 'NEXA'
        assert 'exp' in payload
    
    def test_token_verification(self):
        """Test token verification"""
        # Create valid token
        token = TokenManager.create_access_token('user123', 'admin')
        payload = TokenManager.verify_token(token)
        assert payload['sub'] == 'user123'
        
        # Test expired token
        expired_token = jwt.encode(
            {
                'sub': 'user123',
                'exp': datetime.utcnow() - timedelta(hours=1)
            },
            SecurityConfig.JWT_SECRET,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )
        
        with pytest.raises(Exception):
            TokenManager.verify_token(expired_token)
    
    @patch('modules.auth_middleware.Session')
    def test_account_lockout(self, mock_db):
        """Test account lockout after failed attempts"""
        auth_manager = AuthenticationManager(mock_db)
        
        # Mock user with failed attempts
        mock_user = Mock(spec=User)
        mock_user.id = 'user123'
        mock_user.failed_login_attempts = 4
        mock_user.locked_until = None
        mock_user.password_hash = "wrong_hash"
        
        mock_db.query().filter().first.return_value = mock_user
        
        # Attempt login with wrong password (5th attempt)
        result = auth_manager.authenticate_user(
            'testuser',
            'wrongpassword',
            '127.0.0.1'
        )
        
        assert result is None
        assert mock_user.failed_login_attempts == 5
        assert mock_user.locked_until is not None

class TestRBAC:
    """Test role-based access control"""
    
    def test_role_permissions(self):
        """Test role permission mapping"""
        # Admin should have all permissions
        admin_perms = SecurityConfig.ROLES['admin']
        assert 'upload' in admin_perms
        assert 'download' in admin_perms
        assert 'delete' in admin_perms
        assert 'audit' in admin_perms
        
        # Contractor has limited permissions
        contractor_perms = SecurityConfig.ROLES['contractor']
        assert 'upload' in contractor_perms
        assert 'download' in contractor_perms
        assert 'delete' not in contractor_perms
        assert 'audit' not in contractor_perms
        
        # Viewer has minimal permissions
        viewer_perms = SecurityConfig.ROLES['viewer']
        assert 'download' in viewer_perms
        assert 'upload' not in viewer_perms

class TestAuditLogging:
    """Test audit logging for compliance"""
    
    @pytest.mark.asyncio
    async def test_audit_log_encryption(self):
        """Test audit log encryption"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure audit logger with temp directory
            SecurityConfig.AUDIT_LOG_PATH = Path(tmpdir)
            audit = AuditLogger()
            
            # Log an access event
            await audit.log_access(
                user_id='contractor_001',
                action='upload',
                resource='spec.pdf',
                ip_address='192.168.1.100',
                success=True,
                details={'size': 1024}
            )
            
            # Verify log file was created
            log_files = list(Path(tmpdir).glob("*.log"))
            assert len(log_files) == 1
            
            # Read and verify encryption
            with open(log_files[0], 'r') as f:
                encrypted_log = f.read().strip()
            
            # Should not be plaintext
            assert 'contractor_001' not in encrypted_log
            assert 'upload' not in encrypted_log
    
    @pytest.mark.asyncio
    async def test_audit_log_retrieval(self):
        """Test retrieving and decrypting audit logs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            SecurityConfig.AUDIT_LOG_PATH = Path(tmpdir)
            audit = AuditLogger()
            
            # Log multiple events
            for i in range(5):
                await audit.log_access(
                    user_id=f'user_{i}',
                    action='download',
                    resource=f'file_{i}.pdf',
                    ip_address='127.0.0.1',
                    success=True
                )
            
            # Retrieve logs
            logs = await audit.get_audit_logs(
                start_date=datetime.utcnow() - timedelta(days=1),
                end_date=datetime.utcnow() + timedelta(days=1)
            )
            
            assert len(logs) == 5
            assert logs[0]['action'] == 'download'
            assert 'timestamp' in logs[0]

class TestSecureUpload:
    """Test complete secure upload flow"""
    
    @pytest.mark.asyncio
    async def test_secure_upload_flow(self):
        """Test end-to-end secure upload"""
        with tempfile.TemporaryDirectory() as tmpdir:
            SecurityConfig.SECURE_STORAGE_PATH = Path(tmpdir) / "secure"
            SecurityConfig.QUARANTINE_PATH = Path(tmpdir) / "quarantine"
            SecurityConfig.AUDIT_LOG_PATH = Path(tmpdir) / "audit"
            
            manager = SecureUploadManager()
            
            # Create mock file
            file_content = b"Test utility document content"
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = "test_spec.pdf"
            mock_file.content_type = "application/pdf"
            mock_file.file.tell.return_value = len(file_content)
            mock_file.file.seek = Mock()
            mock_file.read = AsyncMock(return_value=file_content)
            
            # Mock validation to pass
            with patch.object(manager.validator, 'validate_file', 
                            return_value={'valid': True, 'errors': []}):
                
                result = await manager.secure_upload(
                    file=mock_file,
                    user_id='contractor_001',
                    user_role='contractor',
                    ip_address='127.0.0.1',
                    metadata={'project': 'NEXA'}
                )
            
            assert result['success'] == True
            assert result['encryption'] == 'AES-256'
            assert result['compliance'] == 'NERC CIP-003-11'
            assert 'file_id' in result
            
            # Verify file was encrypted and stored
            encrypted_files = list(SecurityConfig.SECURE_STORAGE_PATH.glob("*.enc"))
            assert len(encrypted_files) == 1
    
    @pytest.mark.asyncio
    async def test_quarantine_suspicious_file(self):
        """Test quarantine of suspicious files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            SecurityConfig.SECURE_STORAGE_PATH = Path(tmpdir) / "secure"
            SecurityConfig.QUARANTINE_PATH = Path(tmpdir) / "quarantine"
            SecurityConfig.AUDIT_LOG_PATH = Path(tmpdir) / "audit"
            
            manager = SecureUploadManager()
            
            # Create suspicious file
            suspicious_content = b"MZ\x90\x00MALICIOUS_CODE"
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = "malware.exe"
            mock_file.content_type = "application/x-msdownload"
            mock_file.file.tell.return_value = len(suspicious_content)
            mock_file.file.seek = Mock()
            mock_file.read = AsyncMock(return_value=suspicious_content)
            
            # Mock validation to fail
            with patch.object(manager.validator, 'validate_file',
                            return_value={'valid': False, 
                                        'errors': ['Suspicious file detected']}):
                
                with pytest.raises(Exception) as exc_info:
                    await manager.secure_upload(
                        file=mock_file,
                        user_id='contractor_001',
                        user_role='contractor',
                        ip_address='127.0.0.1'
                    )
                
                assert "validation failed" in str(exc_info.value).lower()
            
            # Verify file was quarantined
            quarantined_files = list(SecurityConfig.QUARANTINE_PATH.glob("*"))
            assert len(quarantined_files) == 1

class TestIntegration:
    """Integration tests for security layer"""
    
    def test_fastapi_integration(self):
        """Test FastAPI app with security"""
        from modules.secure_upload import create_secure_endpoints
        
        app = FastAPI()
        create_secure_endpoints(app)
        
        client = TestClient(app)
        
        # Test without auth - should fail
        response = client.post("/secure/upload")
        assert response.status_code == 403  # Forbidden
        
        # Test with valid token
        token = TokenManager.create_access_token('user123', 'contractor')
        headers = {'Authorization': f'Bearer {token}'}
        
        # Should require file
        response = client.post("/secure/upload", headers=headers)
        assert response.status_code in [422, 400]  # Validation error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
