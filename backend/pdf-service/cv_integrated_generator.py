#!/usr/bin/env python3
"""
NEXA CV-Integrated As-Built Generator
Combines computer vision change detection with AI-powered document generation
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import cv2
import numpy as np
import json
from datetime import datetime
import os

from cv_change_detector import PoleChangeDetector, GuyWireDetector
from asbuilt_generator_simple import PGEAsBuiltGenerator, AsBuiltComponents

app = FastAPI(title="NEXA CV-Enhanced Generator", version="2.0")

# Initialize detectors and generators
cv_detector = PoleChangeDetector()
asbuilt_generator = PGEAsBuiltGenerator()

class PhotoUpload(BaseModel):
    filename: str
    timestamp: str
    gps: Dict[str, float]
    description: str
    base64_data: Optional[str] = None

class JobSubmission(BaseModel):
    pm_number: str
    notification_number: str
    location_address: str
    gps: Dict[str, float]
    crew_lead: str
    lan_id: str
    before_photos: List[PhotoUpload]
    after_photos: List[PhotoUpload]
    materials_list: List[Dict]
    pole_class: Optional[str] = None
    pole_height: Optional[str] = None
    guy_wires: Optional[bool] = None

@app.post("/api/analyze-photo")
async def analyze_single_photo(photo: UploadFile = File(...)):
    """
    Analyze a single photo for guy wire state
    Returns detection results with confidence
    """
    try:
        # Read image
        contents = await photo.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Run detection
        detector = GuyWireDetector()
        analysis = detector.detect_guy_wire_state(img)
        
        return {
            "status": "success",
            "analysis": {
                "state": analysis.state,
                "confidence": f"{analysis.confidence:.1%}",
                "curvature": analysis.curvature,
                "points_detected": analysis.points_detected,
                "visual_evidence": analysis.visual_evidence
            },
            "spec_reference": {
                "sagging": "Guy wire requires adjustment per safety standards",
                "straight": "Guy wire properly tensioned",
                "undetected": "Unable to detect guy wire in image"
            }.get(analysis.state, "")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare-photos")
async def compare_before_after(
    before: UploadFile = File(...),
    after: UploadFile = File(...)
):
    """
    Compare before/after photos to detect changes
    Returns change analysis for red-lining decisions
    """
    try:
        # Read images
        before_contents = await before.read()
        after_contents = await after.read()
        
        before_img = cv2.imdecode(np.frombuffer(before_contents, np.uint8), cv2.IMREAD_COLOR)
        after_img = cv2.imdecode(np.frombuffer(after_contents, np.uint8), cv2.IMREAD_COLOR)
        
        # Run change detection
        detector = GuyWireDetector()
        changes = detector.detect_changes(before_img, after_img)
        
        return {
            "status": "success",
            "before_state": changes["before_state"],
            "after_state": changes["after_state"],
            "changes_detected": len(changes["changes"]),
            "red_lining_required": changes["red_lining_required"],
            "confidence": f"{changes['confidence']:.1%}",
            "changes": changes["changes"],
            "metrics": changes["metrics"],
            "visual_evidence": changes["visual_evidence"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-asbuilt-with-cv")
async def generate_asbuilt_with_cv(job: JobSubmission):
    """
    Generate as-built package with CV-based change detection
    Automatically determines red-lining based on detected changes
    """
    try:
        # Convert photos for CV analysis
        before_photos_cv = []
        after_photos_cv = []
        
        for photo in job.before_photos:
            if photo.base64_data:
                before_photos_cv.append({"base64": photo.base64_data})
        
        for photo in job.after_photos:
            if photo.base64_data:
                after_photos_cv.append({"base64": photo.base64_data})
        
        # Run CV change detection
        cv_report = cv_detector.analyze_job_photos(before_photos_cv, after_photos_cv)
        
        # Prepare field data for generator
        field_data = {
            "pm_number": job.pm_number,
            "notification_number": job.notification_number,
            "location_address": job.location_address,
            "gps": job.gps,
            "crew_lead": job.crew_lead,
            "lan_id": job.lan_id,
            "work_description": "Electric pole work",
            "total_hours": 6.5,  # Default
            "pole_class": job.pole_class,
            "pole_height": job.pole_height,
            "guy_wires": job.guy_wires,
            "materials_list": job.materials_list,
            "before_photos": [p.dict() for p in job.before_photos],
            "after_photos": [p.dict() for p in job.after_photos]
        }
        
        # Add CV-detected changes to field data
        if cv_report["red_lining_required"]:
            field_data["equipment_added"] = None
            field_data["equipment_removed"] = None
            field_data["equipment_relocated"] = None
            
            # Map CV changes to equipment changes
            for change in cv_report["changes"]:
                if change["type"] == "guy_wire_adjustment":
                    field_data["equipment_added"] = "Guy wire adjusted from loose to clamped"
                elif change["type"] == "guy_wire_loosened":
                    field_data["equipment_removed"] = "WARNING: Guy wire tension reduced"
        else:
            # No changes - built as designed
            field_data["equipment_added"] = None
            field_data["equipment_removed"] = None
            field_data["equipment_relocated"] = None
        
        # Generate as-built with CV-informed changes
        components, pdf_path = asbuilt_generator.generate_asbuilt(field_data)
        
        # Enhanced EC tag with CV findings
        if cv_report["red_lining_required"]:
            components.ec_tag["cv_analysis"] = {
                "changes_detected": cv_report["total_changes"],
                "confidence": cv_report["overall_confidence"],
                "red_lining_applied": True,
                "reference": "Pages 7-9: Red-lined per CV-detected changes"
            }
        else:
            components.ec_tag["cv_analysis"] = {
                "changes_detected": 0,
                "confidence": cv_report["overall_confidence"],
                "red_lining_applied": False,
                "reference": "Page 25: Built as designed - no changes detected by CV"
            }
        
        return {
            "status": "success",
            "pm_number": job.pm_number,
            "pdf_path": pdf_path,
            "compliance_score": components.compliance_score,
            "cv_analysis": {
                "total_changes": cv_report["total_changes"],
                "red_lining_required": cv_report["red_lining_required"],
                "confidence": cv_report["overall_confidence"],
                "changes": cv_report["changes"]
            },
            "components": {
                "ec_tag": components.ec_tag,
                "construction_drawing": components.construction_drawing,
                "materials_list": components.materials_list,
                "photos": components.photos_section
            },
            "spec_compliance": cv_report["spec_compliance"],
            "repeal_reasons": components.repeal_reasons
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit-with-cv")
async def audit_generated_package(pm_number: str):
    """
    Simulate QA audit of generated package with CV validation
    Provides repeal reasons based on spec references
    """
    try:
        # Load the generated package (would be from database in production)
        package_path = f"generated_asbuilts/{pm_number}_asbuilt.pdf"
        components_path = f"generated_asbuilts/{pm_number}_components.json"
        
        if not os.path.exists(components_path):
            raise HTTPException(status_code=404, detail="Package not found")
        
        with open(components_path, 'r') as f:
            components = json.load(f)
        
        audit_results = []
        
        # Check EC Tag
        if components.get("ec_tag", {}).get("signature"):
            audit_results.append({
                "item": "EC Tag Signature",
                "status": "PASS",
                "reason": "Digital LAN ID acceptable per Section 4/Page 15"
            })
        else:
            audit_results.append({
                "item": "EC Tag Signature",
                "status": "FAIL",
                "reason": "Missing signature - automatic rejection"
            })
        
        # Check red-lining
        cv_analysis = components.get("ec_tag", {}).get("cv_analysis", {})
        if cv_analysis.get("red_lining_applied"):
            audit_results.append({
                "item": "Red-lining",
                "status": "PASS",
                "reason": f"Changes properly red-lined per Pages 7-9 (CV confidence: {cv_analysis.get('confidence', 0):.1%})"
            })
        elif cv_analysis.get("changes_detected", 0) == 0:
            audit_results.append({
                "item": "Red-lining",
                "status": "PASS",
                "reason": "No red-lining required - built as designed per Page 25"
            })
        else:
            audit_results.append({
                "item": "Red-lining",
                "status": "REPEALABLE",
                "reason": "Missing red-lines but CV shows no actual changes - repealable per Page 25",
                "confidence": 98
            })
        
        # Check FDA requirement
        if "N/A" in components.get("ec_tag", {}).get("fda", ""):
            audit_results.append({
                "item": "FDA Requirement",
                "status": "PASS",
                "reason": "FDA not required - no damaged equipment per Page 25"
            })
        
        # Check photos
        photos = components.get("photos_section", {})
        if photos.get("compliance", {}).get("meets_minimum"):
            audit_results.append({
                "item": "Photo Documentation",
                "status": "PASS",
                "reason": "Minimum 3 before/after photos with GPS/timestamps met"
            })
        else:
            audit_results.append({
                "item": "Photo Documentation",
                "status": "FAIL",
                "reason": "Insufficient photos per Page 12 requirements"
            })
        
        # Check for pole work package completeness (Table 3, Page 20)
        required_docs = ["EC Tag", "Construction Drawing", "Materials List", "Photos"]
        all_present = all([
            components.get("ec_tag"),
            components.get("construction_drawing"),
            components.get("materials_list"),
            components.get("photos_section")
        ])
        
        if all_present:
            audit_results.append({
                "item": "Package Completeness",
                "status": "PASS",
                "reason": "All required documents present per Table 3, Page 20"
            })
        else:
            audit_results.append({
                "item": "Package Completeness",
                "status": "FAIL",
                "reason": "Missing required documents per Table 3, Page 20"
            })
        
        # Calculate overall audit score
        passed = len([r for r in audit_results if r["status"] == "PASS"])
        repealable = len([r for r in audit_results if r["status"] == "REPEALABLE"])
        failed = len([r for r in audit_results if r["status"] == "FAIL"])
        
        audit_score = (passed + repealable * 0.5) / len(audit_results)
        
        return {
            "status": "success",
            "pm_number": pm_number,
            "audit_score": f"{audit_score:.1%}",
            "audit_results": audit_results,
            "summary": {
                "passed": passed,
                "repealable": repealable,
                "failed": failed,
                "recommendation": "APPROVE" if audit_score >= 0.95 else "REVIEW REQUIRED"
            },
            "cv_validation": {
                "used": cv_analysis.get("changes_detected") is not None,
                "confidence": cv_analysis.get("confidence", 0)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0",
        "features": {
            "cv_detection": True,
            "asbuilt_generation": True,
            "spec_compliance": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
