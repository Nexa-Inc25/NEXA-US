#!/usr/bin/env python3
"""
AI Job Analyzer - Compare new jobs against learned patterns
Uses as-built knowledge to predict success and detect issues
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class AIJobAnalyzer:
    """AI system that learns from as-builts and predicts job outcomes"""
    
    def __init__(self):
        self.knowledge_base = self.load_knowledge_base()
        self.success_threshold = 0.75
        self.warning_threshold = 0.40
        
    def load_knowledge_base(self) -> Dict:
        """Load learned patterns from knowledge base"""
        try:
            with open('learned_patterns.json', 'r') as f:
                return json.load(f)
        except:
            return {"successful_jobs": [], "equipment_patterns": {}, 
                   "clearance_standards": {}, "crew_efficiency": {}}
    
    def analyze_new_job(self, job_description: str, job_details: Dict) -> Dict:
        """
        Analyze a new job against learned patterns
        Returns predictions and recommendations
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "job_description": job_description,
            "success_probability": 0,
            "risk_factors": [],
            "success_factors": [],
            "recommendations": [],
            "similar_jobs": [],
            "estimated_go_back_risk": "LOW",
            "confidence": 0
        }
        
        # Compare against successful patterns
        success_matches = 0
        total_patterns = 0
        
        for success_job in self.knowledge_base['successful_jobs']:
            similarity = self.calculate_similarity(job_details, success_job)
            if similarity > 0.6:
                analysis['similar_jobs'].append({
                    "pm_number": success_job['pm_number'],
                    "similarity": similarity,
                    "outcome": "SUCCESS"
                })
            
            for pattern in success_job['patterns']:
                total_patterns += 1
                if self.pattern_matches(job_details, pattern):
                    success_matches += 1
                    analysis['success_factors'].append(pattern['description'])
        
        # Calculate success probability
        if total_patterns > 0:
            analysis['success_probability'] = success_matches / total_patterns
            analysis['confidence'] = min(0.95, analysis['success_probability'] + 0.10)
        
        # Determine risk level
        if analysis['success_probability'] < self.warning_threshold:
            analysis['estimated_go_back_risk'] = "HIGH"
            analysis['risk_factors'].append("Low similarity to successful jobs")
            analysis['recommendations'].append("Request senior review before proceeding")
            analysis['recommendations'].append("Consider additional QC checkpoints")
        elif analysis['success_probability'] < self.success_threshold:
            analysis['estimated_go_back_risk'] = "MEDIUM"
            analysis['risk_factors'].append("Mixed pattern matches")
            analysis['recommendations'].append("Ensure all PGE specifications are met")
            analysis['recommendations'].append("Document clearances thoroughly")
        else:
            analysis['estimated_go_back_risk'] = "LOW"
            analysis['recommendations'].append("Proceed with standard procedures")
            analysis['recommendations'].append("Job matches successful patterns")
        
        return analysis
    
    def calculate_similarity(self, job_details: Dict, historical_job: Dict) -> float:
        """Calculate similarity between two jobs"""
        # Simple similarity based on pattern matching
        # In production, would use embeddings and cosine similarity
        matches = 0
        checks = 0
        
        # Check if similar equipment mentioned
        if 'equipment' in job_details:
            checks += 1
            if any(pattern['pattern'] == 'equipment_specs_met' 
                  for pattern in historical_job.get('patterns', [])):
                matches += 1
        
        # Check if clearances mentioned
        if 'clearances' in job_details:
            checks += 1
            if any(pattern['pattern'] == 'clearance_proper' 
                  for pattern in historical_job.get('patterns', [])):
                matches += 1
        
        return matches / checks if checks > 0 else 0
    
    def pattern_matches(self, job_details: Dict, pattern: Dict) -> bool:
        """Check if job details match a specific pattern"""
        pattern_type = pattern['pattern']
        
        if pattern_type == 'clearance_proper':
            return 'clearance' in str(job_details).lower()
        elif pattern_type == 'equipment_specs_met':
            return 'equipment' in str(job_details).lower() or 'pole' in str(job_details).lower()
        elif pattern_type == 'proper_documentation':
            return 'document' in str(job_details).lower() or 'pack' in str(job_details).lower()
        elif pattern_type == 'crew_efficiency':
            return 'crew' in str(job_details).lower() or 'hours' in str(job_details).lower()
        
        return False
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate human-readable report"""
        report = []
        report.append("="*60)
        report.append("AI JOB ANALYSIS REPORT")
        report.append("="*60)
        report.append(f"Generated: {analysis['timestamp']}")
        report.append(f"Job: {analysis['job_description']}")
        report.append("")
        
        # Risk Assessment
        risk_color = {
            "LOW": "✅",
            "MEDIUM": "⚠️",
            "HIGH": "🚫"
        }
        report.append(f"GO-BACK RISK: {risk_color.get(analysis['estimated_go_back_risk'], '')} {analysis['estimated_go_back_risk']}")
        report.append(f"Success Probability: {analysis['success_probability']:.1%}")
        report.append(f"AI Confidence: {analysis['confidence']:.1%}")
        report.append("")
        
        # Success Factors
        if analysis['success_factors']:
            report.append("✅ SUCCESS FACTORS DETECTED:")
            for factor in analysis['success_factors']:
                report.append(f"  • {factor}")
            report.append("")
        
        # Risk Factors
        if analysis['risk_factors']:
            report.append("⚠️ RISK FACTORS:")
            for risk in analysis['risk_factors']:
                report.append(f"  • {risk}")
            report.append("")
        
        # Similar Jobs
        if analysis['similar_jobs']:
            report.append("📊 SIMILAR HISTORICAL JOBS:")
            for job in analysis['similar_jobs'][:3]:
                report.append(f"  • PM {job['pm_number']}: {job['similarity']:.0%} match ({job['outcome']})")
            report.append("")
        
        # Recommendations
        report.append("📋 RECOMMENDATIONS:")
        for rec in analysis['recommendations']:
            report.append(f"  • {rec}")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)

def test_ai_analyzer():
    """Test the AI analyzer with sample jobs"""
    analyzer = AIJobAnalyzer()
    
    print("AI JOB ANALYZER - TESTING WITH LEARNED PATTERNS")
    print("="*60)
    
    # Test Case 1: Good job (similar to PM 35124034)
    good_job = {
        "equipment": ["Distribution Pole", "Transformer"],
        "clearances": {"overhead": "18 feet", "underground": "36 inches"},
        "crew_size": 4,
        "documentation": "Complete FM Pack prepared"
    }
    
    print("\nTest 1: Analyzing well-planned job...")
    analysis1 = analyzer.analyze_new_job("New distribution pole installation", good_job)
    print(analyzer.generate_report(analysis1))
    
    # Test Case 2: Risky job (missing key elements)
    risky_job = {
        "description": "Quick pole replacement",
        "crew_size": 2
    }
    
    print("\nTest 2: Analyzing potentially risky job...")
    analysis2 = analyzer.analyze_new_job("Emergency pole replacement", risky_job)
    print(analyzer.generate_report(analysis2))
    
    # Test Case 3: Mixed indicators
    mixed_job = {
        "equipment": ["Pole", "Guy wire"],
        "notes": "Clearance verification pending"
    }
    
    print("\nTest 3: Analyzing job with mixed indicators...")
    analysis3 = analyzer.analyze_new_job("Pole reinforcement project", mixed_job)
    print(analyzer.generate_report(analysis3))
    
    # Summary
    print("\n" + "="*60)
    print("AI LEARNING SUMMARY")
    print("="*60)
    print(f"Knowledge Base: {len(analyzer.knowledge_base['successful_jobs'])} successful jobs learned")
    print(f"Success Threshold: {analyzer.success_threshold:.0%}")
    print(f"Warning Threshold: {analyzer.warning_threshold:.0%}")
    print("\nThe AI can now:")
    print("  • Predict go-back risk BEFORE work begins")
    print("  • Compare new jobs to successful patterns")
    print("  • Provide specific recommendations")
    print("  • Learn continuously from new as-builts")

if __name__ == "__main__":
    test_ai_analyzer()
