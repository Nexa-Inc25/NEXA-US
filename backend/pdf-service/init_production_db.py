#!/usr/bin/env python3
"""
Production Database Initialization for NEXA AI Document Analyzer
Creates tables ONLY - no test/mock data
All data must come from real document uploads
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Render PostgreSQL URLs
INTERNAL_URL = "postgresql://nexa_db_94sr_user:H9AZevmgdNd5pWEFVkTm880HX5A6ATzd@dpg-d3mifuili9vc73a8a9kg-a/nexa_db_94sr"
EXTERNAL_URL = "postgresql://nexa_db_94sr_user:H9AZevmgdNd5pWEFVkTm880HX5A6ATzd@dpg-d3mifuili9vc73a8a9kg-a.oregon-postgres.render.com/nexa_db_94sr"

# Determine which URL to use
if os.getenv("RENDER"):
    DATABASE_URL = INTERNAL_URL
    logger.info("Using Render internal database URL")
else:
    # Local development - use external URL
    DATABASE_URL = EXTERNAL_URL
    logger.info("Using external database URL for local testing")

# Set environment variable for field_crew_workflow to use
os.environ["DATABASE_URL"] = DATABASE_URL

print("="*70)
print("NEXA AI DOCUMENT ANALYZER - PRODUCTION DATABASE INITIALIZATION")
print("="*70)
print("Creating tables for REAL document processing only")
print("NO mock data will be created - system uses only uploaded documents")
print("-"*70)

try:
    # Import SQLAlchemy components
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
    
    # Create engine
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        echo=False
    )
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), version()"))
        db_name, version = result.fetchone()
        print(f"\n✅ Connected to database: {db_name}")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
    
    # Create base
    Base = declarative_base()
    
    # Define tables (matching field_crew_workflow.py models)
    
    class SpecEmbedding(Base):
        """Store spec book embeddings for rule matching"""
        __tablename__ = 'spec_embeddings'
        
        id = Column(Integer, primary_key=True)
        spec_book_id = Column(String(100), nullable=False)
        rule_text = Column(Text, nullable=False)
        embedding = Column(JSON, nullable=False)  # Store as JSON array
        page_number = Column(Integer)
        section = Column(String(200))
        created_at = Column(DateTime, default=datetime.utcnow)
    
    class AuditInfraction(Base):
        """Store audit infractions and repeal analysis"""
        __tablename__ = 'audit_infractions'
        
        id = Column(Integer, primary_key=True)
        job_id = Column(String(100), nullable=False)
        pm_number = Column(String(50))
        infraction_text = Column(Text, nullable=False)
        repealable = Column(Boolean, default=False)
        confidence = Column(Float)
        spec_reference = Column(Text)
        page_number = Column(Integer)
        reason = Column(Text)
        status = Column(String(50), default='pending')  # pending, appealed, accepted, rejected
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class DocumentUpload(Base):
        """Track all document uploads - spec books and audits"""
        __tablename__ = 'document_uploads'
        
        id = Column(Integer, primary_key=True)
        document_id = Column(String(100), unique=True, nullable=False)
        document_type = Column(String(50))  # spec_book, audit, pm_package
        filename = Column(String(255))
        pm_number = Column(String(50))
        upload_date = Column(DateTime, default=datetime.utcnow)
        processed = Column(Boolean, default=False)
        page_count = Column(Integer)
        file_size_mb = Column(Float)
        processing_time_seconds = Column(Float)
        error_message = Column(Text)
    
    class ProcessingMetrics(Base):
        """Track system performance metrics"""
        __tablename__ = 'processing_metrics'
        
        id = Column(Integer, primary_key=True)
        date = Column(DateTime, default=datetime.utcnow)
        documents_processed = Column(Integer, default=0)
        infractions_found = Column(Integer, default=0)
        appeals_successful = Column(Integer, default=0)
        appeals_failed = Column(Integer, default=0)
        avg_confidence = Column(Float)
        processing_time_avg = Column(Float)
        accuracy_rate = Column(Float)
    
    # Create all tables
    print("\n📊 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n✅ Successfully created {len(tables)} tables:")
    for table in sorted(tables):
        columns = inspector.get_columns(table)
        print(f"   • {table:25} ({len(columns)} columns)")
    
    # Display production configuration
    print("\n" + "="*70)
    print("✅ PRODUCTION DATABASE READY")
    print("="*70)
    
    print("\n📋 System Configuration:")
    print("• Environment: PRODUCTION")
    print("• Mock Data: DISABLED")
    print("• Test Data: NONE")
    print("• Data Source: Real document uploads only")
    
    print("\n🎯 Production Targets:")
    print("• 70 PM packages daily")
    print("• 10 concurrent users")
    print("• 95%+ accuracy on repeal decisions")
    print("• 30-90 day data retention")
    
    print("\n📄 Document Processing Pipeline:")
    print("1. Upload spec book PDF → Extract rules → Generate embeddings")
    print("2. Upload audit PDF → Find infractions → Match to spec rules")
    print("3. Determine repealability → Store results in database")
    print("4. PM dashboard → View results → Appeal infractions")
    
    print("\n⚠️  IMPORTANT:")
    print("• No test data has been created")
    print("• System will only process real uploaded documents")
    print("• All spec books must be uploaded through API")
    print("• All audits must be real PG&E documents")
    
    print("\n🚀 Next Steps:")
    print("1. Start the API server: python field_crew_workflow.py")
    print("2. Upload a real PG&E spec book PDF")
    print("3. Upload real audit documents for analysis")
    print("4. Access PM dashboard to view results")
    
    print("\n" + "="*70)
    logger.info("Database initialization complete - ready for production")
    
except Exception as e:
    logger.error(f"❌ Database initialization failed: {e}")
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check DATABASE_URL is correct")
    print("2. Ensure PostgreSQL is running on Render")
    print("3. Verify network connectivity to Render")
    print("4. Check database credentials")
    sys.exit(1)
