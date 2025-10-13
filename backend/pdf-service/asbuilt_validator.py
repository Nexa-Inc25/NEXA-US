#!/usr/bin/env python3
"""
PGE As-Built Validator - Pre-submission Compliance Checker
Prevents go-backs by ensuring perfect documentation
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class AsBuiltValidator:
    """Validate as-builts against PGE 2025 procedures"""
    
    def __init__(self):
        with open('pge_procedures_2025.json', 'r') as f:
            self.pge_standards = json.load(f)
        
        self.critical_threshold = 1  # Any critical issue = rejection
        self.pass_threshold = 80     # 80% score to pass
    
    def validate_complete_package(self, package_info: Dict) -> Dict:
        """
        Complete validation of an as-built package
        Returns detailed compliance report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "pm_number": package_info.get('pm_number', 'UNKNOWN'),
            "overall_status": "PASS",
            "compliance_score": 100,
            "critical_issues": [],
            "high_priority_issues": [],
            "medium_priority_issues": [],
            "recommendations": [],
            "document_checklist": {},
            "ready_for_submission": False,
            "estimated_go_back_risk": "LOW"
        }
        
        print("="*60)
        print("PGE AS-BUILT VALIDATION REPORT")
        print("="*60)
        print(f"PM Number: {report['pm_number']}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("")
        
        # 1. Check document order and completeness
        print("📋 CHECKING DOCUMENT ORDER...")
        doc_score = self.check_document_order(package_info, report)
        
        # 2. Validate critical requirements
        print("\n✅ VALIDATING CRITICAL REQUIREMENTS...")
        critical_score = self.validate_critical_requirements(package_info, report)
        
        # 3. Check 2025 specific requirements
        print("\n📅 CHECKING 2025 REQUIREMENTS...")
        proc_score = self.check_2025_requirements(package_info, report)
        
        # 4. Photo validation
        print("\n📸 VALIDATING PHOTOS...")
        photo_score = self.validate_photos(package_info, report)
        
        # 5. Common mistakes check
        print("\n⚠️ CHECKING FOR COMMON MISTAKES...")
        mistake_score = self.check_common_mistakes(package_info, report)
        
        # Calculate overall score
        report['compliance_score'] = int((doc_score + critical_score + proc_score + photo_score + mistake_score) / 5)
        
        # Determine status
        if report['critical_issues']:
            report['overall_status'] = "FAIL"
            report['estimated_go_back_risk'] = "HIGH"
            report['ready_for_submission'] = False
        elif report['compliance_score'] >= self.pass_threshold:
            report['overall_status'] = "PASS"
            report['estimated_go_back_risk'] = "LOW"
            report['ready_for_submission'] = True
        else:
            report['overall_status'] = "REVIEW"
            report['estimated_go_back_risk'] = "MEDIUM"
            report['ready_for_submission'] = False
        
        # Generate final report
        self.print_final_report(report)
        
        return report
    
    def check_document_order(self, package: Dict, report: Dict) -> int:
        """Check if documents are in correct order"""
        score = 100
        documents = package.get('documents', [])
        
        for required_doc in self.pge_standards['document_order']:
            doc_name = required_doc['document']
            report['document_checklist'][doc_name] = "❌ Missing"
            
            # Check if document exists
            for doc in documents:
                if doc_name.lower() in doc.lower():
                    report['document_checklist'][doc_name] = "✅ Present"
                    break
            
            if report['document_checklist'][doc_name] == "❌ Missing" and required_doc['required']:
                score -= 10
                report['high_priority_issues'].append(f"Missing required document: {doc_name}")
        
        return max(0, score)
    
    def validate_critical_requirements(self, package: Dict, report: Dict) -> int:
        """Validate critical requirements that cause automatic rejection"""
        score = 100
        
        # EC Tag signature (CRITICAL)
        if not package.get('ec_tag', {}).get('signature'):
            report['critical_issues'].append("EC Tag missing signature - AUTOMATIC REJECTION")
            score = 0
        
        # PM Number format
        pm_number = str(package.get('pm_number', ''))
        if len(pm_number) != 8 or not pm_number.isdigit():
            report['high_priority_issues'].append(f"Invalid PM number format: {pm_number} (must be 8 digits)")
            score -= 20
        
        # Face sheet completeness
        if not package.get('face_sheet', {}).get('complete'):
            report['high_priority_issues'].append("Face sheet incomplete")
            score -= 15
        
        return max(0, score)
    
    def check_2025_requirements(self, package: Dict, report: Dict) -> int:
        """Check 2025 specific requirements"""
        score = 100
        proc = self.pge_standards['2025_procedures']
        
        # Digital submission format
        if package.get('format') != 'PDF/A':
            report['medium_priority_issues'].append(f"Wrong format: {package.get('format')} (requires PDF/A)")
            score -= 10
        
        # QR code
        if proc['qr_code_required'] and not package.get('qr_code'):
            report['medium_priority_issues'].append("QR code missing (required for 2025)")
            score -= 10
        
        # GPS coordinates
        if proc['gps_coordinates'] and not package.get('gps'):
            report['high_priority_issues'].append("GPS coordinates missing")
            score -= 15
        
        # File size
        file_size_mb = package.get('file_size_mb', 0)
        if file_size_mb > proc['max_file_size_mb']:
            report['medium_priority_issues'].append(f"File too large: {file_size_mb}MB (max {proc['max_file_size_mb']}MB)")
            score -= 5
        
        # Required metadata
        for metadata in proc['required_metadata']:
            if metadata.lower().replace(' ', '_') not in str(package).lower():
                report['recommendations'].append(f"Add metadata: {metadata}")
                score -= 2
        
        return max(0, score)
    
    def validate_photos(self, package: Dict, report: Dict) -> int:
        """Validate photo requirements"""
        score = 100
        photos = package.get('photos', {})
        
        # Before photos
        if not photos.get('before'):
            report['high_priority_issues'].append("Missing before photos")
            score -= 25
        elif not photos.get('before_timestamp'):
            report['medium_priority_issues'].append("Before photos missing timestamps")
            score -= 10
        
        # After photos
        if not photos.get('after'):
            report['high_priority_issues'].append("Missing after photos")
            score -= 25
        elif not photos.get('after_timestamp'):
            report['medium_priority_issues'].append("After photos missing timestamps")
            score -= 10
        
        # Photo metadata
        if self.pge_standards['2025_procedures']['photo_metadata']:
            if not photos.get('metadata'):
                report['recommendations'].append("Add GPS metadata to photos")
                score -= 5
        
        return max(0, score)
    
    def check_common_mistakes(self, package: Dict, report: Dict) -> int:
        """Check for common mistakes that cause go-backs"""
        score = 100
        
        for mistake in self.pge_standards['common_mistakes']:
            if "EC tag signature" in mistake and not package.get('ec_tag', {}).get('signature'):
                # Already caught in critical
                continue
            elif "Photos without timestamps" in mistake:
                # Already caught in photo validation
                continue
            elif "Labor hours" in mistake:
                if not package.get('labor_hours_verified'):
                    report['recommendations'].append("Verify labor hours match time sheets")
                    score -= 5
            elif "material list" in mistake.lower():
                if not package.get('material_list_complete'):
                    report['high_priority_issues'].append("Material list may be incomplete")
                    score -= 10
            elif "test results" in mistake.lower():
                if not package.get('test_results'):
                    report['high_priority_issues'].append("Test results not attached")
                    score -= 15
        
        return max(0, score)
    
    def print_final_report(self, report: Dict):
        """Print the final validation report"""
        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        
        # Overall status
        status_symbol = {
            "PASS": "✅",
            "FAIL": "❌",
            "REVIEW": "⚠️"
        }
        
        print(f"\nOVERALL STATUS: {status_symbol[report['overall_status']]} {report['overall_status']}")
        print(f"Compliance Score: {report['compliance_score']}%")
        print(f"Go-Back Risk: {report['estimated_go_back_risk']}")
        print(f"Ready for Submission: {'YES' if report['ready_for_submission'] else 'NO'}")
        
        # Critical issues
        if report['critical_issues']:
            print("\n🚨 CRITICAL ISSUES (Must Fix):")
            for issue in report['critical_issues']:
                print(f"  • {issue}")
        
        # High priority issues
        if report['high_priority_issues']:
            print("\n⚠️ HIGH PRIORITY ISSUES:")
            for issue in report['high_priority_issues']:
                print(f"  • {issue}")
        
        # Document checklist
        print("\n📋 DOCUMENT CHECKLIST:")
        for doc, status in report['document_checklist'].items():
            print(f"  {status} {doc}")
        
        # Recommendations
        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
        
        # Final message
        print("\n" + "="*60)
        if report['ready_for_submission']:
            print("✅ AS-BUILT PACKAGE IS READY FOR SUBMISSION!")
            print("Low risk of go-back. Proceed with confidence.")
        else:
            print("❌ AS-BUILT PACKAGE NEEDS CORRECTIONS")
            print(f"Fix {len(report['critical_issues']) + len(report['high_priority_issues'])} issues before submission")
            print("Estimated savings by fixing now: $1,500 - $3,000")
        print("="*60)

def test_validator():
    """Test the validator with sample packages"""
    validator = AsBuiltValidator()
    
    # Test 1: Perfect as-built (like PM 35124034)
    perfect_package = {
        "pm_number": "35124034",
        "documents": [
            "Cover Sheet", "EC Tag", "Face Sheet", 
            "Material List", "Labor Summary", "Site Photos - Before",
            "Site Photos - After", "Test Results", "Inspection Sign-off"
        ],
        "ec_tag": {"signature": True, "type": "digital"},
        "face_sheet": {"complete": True},
        "format": "PDF/A",
        "qr_code": True,
        "gps": {"lat": 37.7749, "lng": -122.4194},
        "file_size_mb": 9.01,
        "photos": {
            "before": True,
            "before_timestamp": True,
            "after": True,
            "after_timestamp": True,
            "metadata": True
        },
        "labor_hours_verified": True,
        "material_list_complete": True,
        "test_results": True
    }
    
    print("\n🔍 VALIDATING PM 35124034 (Perfect As-Built)...")
    print("-"*60)
    report1 = validator.validate_complete_package(perfect_package)
    
    # Test 2: Problem as-built (like the go-back)
    problem_package = {
        "pm_number": "4556864",  # Wrong format (7 digits)
        "documents": [
            "Cover Sheet", "Face Sheet", "Material List",
            "Site Photos - Before"  # Missing several required docs
        ],
        "ec_tag": {"signature": False},  # CRITICAL: No signature
        "face_sheet": {"complete": False},
        "format": "PDF",  # Wrong format
        "file_size_mb": 0.37,
        "photos": {
            "before": True,
            "before_timestamp": False,  # Missing timestamps
            "after": False  # Missing after photos
        },
        "test_results": False
    }
    
    print("\n\n🔍 VALIDATING Problem As-Built...")
    print("-"*60)
    report2 = validator.validate_complete_package(problem_package)

if __name__ == "__main__":
    test_validator()
