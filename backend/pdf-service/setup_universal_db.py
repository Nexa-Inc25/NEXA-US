#!/usr/bin/env python3
"""
Setup Universal Standards Database for NEXA
Run this to create all necessary tables and initial data
"""
import os
import asyncio
import asyncpg
import json
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/nexa")

# Database schema SQL
SCHEMA_SQL = """
-- Drop existing tables if needed (careful in production!)
DROP TABLE IF EXISTS form_submissions CASCADE;
DROP TABLE IF EXISTS utility_form_mappings CASCADE;
DROP TABLE IF EXISTS form_templates CASCADE;
DROP TABLE IF EXISTS standards_data_lake CASCADE;
DROP TABLE IF EXISTS jobs_universal CASCADE;
DROP TABLE IF EXISTS cross_utility_patterns CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS utilities_master CASCADE;

-- Master Utilities Registry
CREATE TABLE utilities_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    region JSONB,
    form_patterns JSONB DEFAULT '{}'::jsonb,
    spec_patterns JSONB DEFAULT '{}'::jsonb,
    nomenclature JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Organizations (Contractors)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE,
    subscription_tier VARCHAR(50) DEFAULT 'trial',
    subscription_status VARCHAR(50) DEFAULT 'active',
    max_users INTEGER DEFAULT 10,
    primary_contact_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Universal Standards Data Lake
CREATE TABLE standards_data_lake (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utility_id UUID REFERENCES utilities_master(id),
    standard_category VARCHAR(100),
    standard_subcategory VARCHAR(100),
    standard_code VARCHAR(50),
    utility_reference VARCHAR(255),
    utility_spec_number VARCHAR(100),
    requirement_text TEXT,
    requirement_value JSONB,
    applies_to JSONB,
    exceptions JSONB,
    embedding REAL[], -- Simplified for now, use pgvector in production
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jobs with auto-detected utility
CREATE TABLE jobs_universal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    job_number VARCHAR(100),
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),
    address TEXT,
    detected_utility_id UUID REFERENCES utilities_master(id),
    confirmed_utility_id UUID REFERENCES utilities_master(id),
    job_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Form Templates
CREATE TABLE form_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_type VARCHAR(100),
    universal_fields JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Utility-Specific Form Mappings
CREATE TABLE utility_form_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utility_id UUID REFERENCES utilities_master(id),
    form_template_id UUID REFERENCES form_templates(id),
    field_mappings JSONB,
    validation_rules JSONB,
    utility_form_number VARCHAR(100),
    utility_form_name VARCHAR(255),
    UNIQUE(utility_id, form_template_id)
);

-- Form Submissions
CREATE TABLE form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs_universal(id),
    form_template_id UUID REFERENCES form_templates(id),
    submitted_by VARCHAR(255),
    universal_data JSONB,
    utility_specific_data JSONB,
    validation_status VARCHAR(50),
    validation_results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cross-Utility Patterns
CREATE TABLE cross_utility_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(100),
    pattern_description TEXT,
    utility_occurrences JSONB,
    universal_solution TEXT,
    confidence_score DECIMAL(3,2),
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_standards_category ON standards_data_lake(standard_category, standard_subcategory);
CREATE INDEX idx_standards_utility ON standards_data_lake(utility_id);
CREATE INDEX idx_jobs_org ON jobs_universal(organization_id);
CREATE INDEX idx_jobs_utility ON jobs_universal(detected_utility_id);
"""

# Initial utility data
INITIAL_UTILITIES = [
    {
        "code": "PGE",
        "name": "Pacific Gas & Electric",
        "region": {
            "state": "CA",
            "counties": ["San Francisco", "Alameda", "Sacramento", "Fresno"],
            "service_area": "Northern California"
        },
        "form_patterns": {
            "go_back": "GO-BACK NOTICE",
            "inspection": "INSPECTION REPORT",
            "as_built": "AS-BUILT DRAWING"
        },
        "spec_patterns": {
            "section": r"Section \d+\.\d+",
            "spec_number": r"\d{6}"
        },
        "nomenclature": {
            "crossarm": ["cross-arm", "x-arm", "cross arm"],
            "guy_wire": ["guy", "guy wire", "guy-wire"],
            "transformer": ["xfmr", "trans", "transformer"]
        }
    },
    {
        "code": "SCE",
        "name": "Southern California Edison",
        "region": {
            "state": "CA",
            "counties": ["Los Angeles", "Orange", "San Bernardino", "Riverside"],
            "service_area": "Southern California"
        },
        "form_patterns": {
            "go_back": "CORRECTION NOTICE",
            "inspection": "FIELD INSPECTION",
            "as_built": "FIELD SKETCH"
        },
        "spec_patterns": {
            "section": r"Chapter \d+ Article \d+",
            "spec_number": r"[A-Z]{2}-\d{4}"
        },
        "nomenclature": {
            "crossarm": ["cross-arm", "crossarm"],
            "guy_wire": ["guy", "anchor"],
            "transformer": ["transformer", "XFMR"]
        }
    },
    {
        "code": "FPL",
        "name": "Florida Power & Light",
        "region": {
            "state": "FL",
            "counties": ["Miami-Dade", "Broward", "Palm Beach"],
            "service_area": "South Florida"
        },
        "form_patterns": {
            "go_back": "DEFICIENCY REPORT",
            "inspection": "QA INSPECTION",
            "as_built": "COMPLETION DRAWING"
        },
        "spec_patterns": {
            "section": r"Standard \d{3}",
            "spec_number": r"FPL-\d{4}"
        },
        "nomenclature": {
            "crossarm": ["crossarm", "arm"],
            "guy_wire": ["guy", "stay"],
            "transformer": ["transformer", "TX"]
        }
    },
    {
        "code": "CONED",
        "name": "Consolidated Edison",
        "region": {
            "state": "NY",
            "counties": ["New York", "Bronx", "Queens", "Westchester"],
            "service_area": "New York City"
        },
        "form_patterns": {
            "go_back": "WORK DEFICIENCY",
            "inspection": "INSPECTION FORM",
            "as_built": "WORK COMPLETION"
        },
        "spec_patterns": {
            "section": r"Spec [A-Z]-\d+",
            "spec_number": r"EO-\d{4}"
        },
        "nomenclature": {
            "crossarm": ["crossarm", "arm assembly"],
            "guy_wire": ["guy", "tension wire"],
            "transformer": ["transformer", "distribution transformer"]
        }
    }
]

# Sample form templates
FORM_TEMPLATES = [
    {
        "form_type": "inspection",
        "universal_fields": {
            "job_number": "string",
            "inspection_date": "date",
            "inspector_name": "string",
            "pole_number": "string",
            "pole_height": "number",
            "equipment_type": "string",
            "clearance_horizontal": "number",
            "clearance_vertical": "number",
            "grounding_present": "boolean",
            "photos": "array",
            "notes": "text"
        }
    },
    {
        "form_type": "go_back",
        "universal_fields": {
            "job_number": "string",
            "infraction_date": "date",
            "infraction_type": "string",
            "description": "text",
            "spec_violation": "string",
            "corrective_action": "text",
            "cost_impact": "number",
            "photos": "array"
        }
    },
    {
        "form_type": "as_built",
        "universal_fields": {
            "job_number": "string",
            "completion_date": "date",
            "foreman_name": "string",
            "work_performed": "text",
            "materials_used": "array",
            "crew_size": "number",
            "hours_worked": "number",
            "photos": "array"
        }
    }
]

async def setup_database():
    """Setup the database with schema and initial data"""
    print("🔧 Setting up NEXA Universal Standards Database...")
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create schema
        print("📊 Creating database schema...")
        await conn.execute(SCHEMA_SQL)
        
        # Insert utilities
        print("🏢 Adding utility companies...")
        for utility in INITIAL_UTILITIES:
            await conn.execute("""
                INSERT INTO utilities_master (code, name, region, form_patterns, spec_patterns, nomenclature)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
            utility["code"], 
            utility["name"],
            json.dumps(utility["region"]),
            json.dumps(utility["form_patterns"]),
            json.dumps(utility["spec_patterns"]),
            json.dumps(utility["nomenclature"]))
        
        # Insert form templates
        print("📝 Adding form templates...")
        for template in FORM_TEMPLATES:
            template_id = await conn.fetchval("""
                INSERT INTO form_templates (form_type, universal_fields)
                VALUES ($1, $2)
                RETURNING id
            """, template["form_type"], json.dumps(template["universal_fields"]))
            
            # Create mappings for each utility
            utilities = await conn.fetch("SELECT id, code FROM utilities_master")
            for utility in utilities:
                # Create utility-specific field mappings
                if utility['code'] == 'PGE':
                    field_mappings = {
                        "job_number": "Job_Number",
                        "clearance_horizontal": "Horizontal_Clearance_Feet",
                        "clearance_vertical": "Vertical_Clearance_Feet"
                    }
                elif utility['code'] == 'SCE':
                    field_mappings = {
                        "job_number": "JobID",
                        "clearance_horizontal": "H_Clear_Ft",
                        "clearance_vertical": "V_Clear_Ft"
                    }
                else:
                    field_mappings = {}  # Use universal names
                
                await conn.execute("""
                    INSERT INTO utility_form_mappings 
                    (utility_id, form_template_id, field_mappings, validation_rules)
                    VALUES ($1, $2, $3, $4)
                """, 
                utility['id'], 
                template_id,
                json.dumps(field_mappings),
                json.dumps({}))
        
        # Create sample organization
        print("🏗️ Creating sample organization...")
        await conn.execute("""
            INSERT INTO organizations (name, subdomain, primary_contact_email)
            VALUES ($1, $2, $3)
        """, "Demo Contractor", "demo", "demo@nexa.com")
        
        print("✅ Database setup complete!")
        
        # Show summary
        utility_count = await conn.fetchval("SELECT COUNT(*) FROM utilities_master")
        template_count = await conn.fetchval("SELECT COUNT(*) FROM form_templates")
        
        print(f"\n📊 Summary:")
        print(f"  - Utilities configured: {utility_count}")
        print(f"  - Form templates: {template_count}")
        print(f"  - Organizations: 1 (demo)")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_database())
