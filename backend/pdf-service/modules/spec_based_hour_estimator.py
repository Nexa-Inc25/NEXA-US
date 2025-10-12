#!/usr/bin/env python3
"""
Spec-Based Hour Estimator for NEXA
Dynamically estimates labor/equipment hours by cross-referencing spec embeddings
Uses industry defaults and spec-driven adjustments for accurate profitability calculations
"""

import re
import json
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util as st_util

logger = logging.getLogger(__name__)

class SpecBasedHourEstimator:
    """
    Estimates job hours by querying spec embeddings for time-implying phrases
    and applying industry-standard defaults with spec-driven adjustments
    """
    
    def __init__(self, 
                 embeddings_path: str = "/data/spec_embeddings.pkl",
                 defaults_path: str = "/data/hour_defaults.json"):
        """
        Initialize the hour estimator
        
        Args:
            embeddings_path: Path to spec embeddings file
            defaults_path: Path to industry defaults JSON
        """
        
        self.embeddings_path = Path(embeddings_path)
        self.defaults_path = Path(defaults_path)
        
        # Load sentence transformer
        logger.info("Loading sentence transformer for hour estimation...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load spec embeddings
        self.spec_data = self._load_spec_embeddings()
        
        # Load or create industry defaults
        self.defaults = self._load_industry_defaults()
        
        # Compile regex patterns for time extraction
        self.time_patterns = [
            # Direct hours: "4 hours", "8.5 hrs", "2-4 hours"
            (r'(\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?)\s*(?:hours?|hrs?)', 1.0),
            # Minutes: "30 minutes", "45 mins"
            (r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)', 1/60.0),
            # Days: "2 days", "1.5 days"
            (r'(\d+(?:\.\d+)?)\s*(?:days?)', 8.0),  # 8 hours per day
            # Man-hours: "200 man-hours", "50 person-hours"
            (r'(\d+(?:\.\d+)?)\s*(?:man|person)[-\s]?hours?', 1.0),
            # Crew-hours: "4 crew-hours" (assuming 3-person crew)
            (r'(\d+(?:\.\d+)?)\s*crew[-\s]?hours?', 3.0),
            # Steps/methods implying time: "3-step process", "5 methods"
            (r'(\d+)[-\s]?(?:steps?|methods?|phases?|stages?)', 0.5),  # 0.5 hr per step
        ]
        
        # Keywords that imply time adjustments
        self.adjustment_keywords = {
            # Difficulty modifiers (add time)
            'difficult': 1.5,
            'complex': 2.0,
            'challenging': 1.5,
            'rocky': 2.0,
            'congested': 1.5,
            'heavy traffic': 2.0,
            'confined space': 1.5,
            'hazardous': 2.5,
            'emergency': -1.0,  # Faster but costlier
            
            # Simplification modifiers (reduce time)
            'simplified': -1.0,
            'exemption': -1.0,
            'waived': -1.5,
            'standard': 0,
            'typical': 0,
            'routine': -0.5,
            'pre-approved': -1.0,
            
            # Equipment implications
            'crane required': 2.0,  # Equipment setup time
            'bucket truck': 1.0,
            'hand dig': 3.0,  # Manual work takes longer
            'mechanical': -1.0,  # Faster with machines
        }
    
    def _load_spec_embeddings(self) -> Optional[Dict]:
        """Load spec embeddings from pickle file"""
        
        if not self.embeddings_path.exists():
            logger.warning(f"Spec embeddings not found at {self.embeddings_path}")
            return None
        
        try:
            with open(self.embeddings_path, 'rb') as f:
                data = pickle.load(f)
                logger.info(f"Loaded {len(data.get('chunks', []))} spec chunks for hour estimation")
                return data
        except Exception as e:
            logger.error(f"Failed to load spec embeddings: {e}")
            return None
    
    def _load_industry_defaults(self) -> Dict:
        """
        Load or create industry-standard hour defaults
        Based on aggregated research from multiple sources
        """
        
        defaults = {
            # Pole work (07D variants)
            "07D": {
                "name": "Pole Replacement - Distribution",
                "labor_hours": {"min": 4, "avg": 5, "max": 8},
                "equipment_hours": {"min": 2, "avg": 3, "max": 4},
                "notes": "3-4 hrs favorable conditions, 8+ complex/traffic"
            },
            "07T": {
                "name": "Pole Replacement - Transmission",
                "labor_hours": {"min": 6, "avg": 8, "max": 12},
                "equipment_hours": {"min": 3, "avg": 4, "max": 6},
                "notes": "Larger poles, higher voltages"
            },
            
            # Crossarm and attachments (KAA, 2AA)
            "KAA": {
                "name": "Crossarm Installation",
                "labor_hours": {"min": 1, "avg": 1.5, "max": 3},
                "equipment_hours": {"min": 0.5, "avg": 1, "max": 2},
                "notes": "Simple attachment, 1-2 hrs typical"
            },
            "2AA": {
                "name": "Anchor Installation",
                "labor_hours": {"min": 1, "avg": 1.5, "max": 3},
                "equipment_hours": {"min": 0.5, "avg": 1, "max": 2},
                "notes": "Guy wire anchors"
            },
            
            # Underground work
            "UG1": {
                "name": "Underground Primary Conduit",
                "labor_hours_per_ft": 0.04,  # 0.025-0.066 range, using midpoint
                "equipment_hours_per_ft": 0.02,
                "base_hours": 2,  # Setup/termination
                "notes": "200 man-hours per 3000 ft industry standard"
            },
            "UG2": {
                "name": "Underground Secondary",
                "labor_hours_per_ft": 0.03,
                "equipment_hours_per_ft": 0.015,
                "base_hours": 1.5,
                "notes": "Simpler than primary"
            },
            
            # Transformers
            "TRX": {
                "name": "Transformer Installation",
                "labor_hours": {"min": 6, "avg": 7, "max": 10},
                "equipment_hours": {"min": 3, "avg": 4, "max": 5},
                "notes": "Pad mount or pole mount"
            },
            "TRP": {
                "name": "Transformer Replacement",
                "labor_hours": {"min": 4, "avg": 5, "max": 8},
                "equipment_hours": {"min": 2, "avg": 3, "max": 4},
                "notes": "Faster than new install"
            },
            
            # Default for unknown tags
            "DEFAULT": {
                "name": "General Electrical Work",
                "labor_hours": {"min": 3, "avg": 4, "max": 6},
                "equipment_hours": {"min": 1, "avg": 2, "max": 3},
                "notes": "Generic estimate"
            }
        }
        
        # Try to load custom defaults if they exist
        if self.defaults_path.exists():
            try:
                with open(self.defaults_path, 'r') as f:
                    custom = json.load(f)
                    defaults.update(custom)
                    logger.info(f"Loaded custom hour defaults from {self.defaults_path}")
            except Exception as e:
                logger.warning(f"Could not load custom defaults: {e}")
        
        return defaults
    
    def estimate_hours(self, 
                      job: Dict[str, Any], 
                      rates: Optional[Dict] = None,
                      confidence_threshold: float = 0.8) -> Dict:
        """
        Estimate labor and equipment hours for a job by cross-referencing specs
        
        Args:
            job: Job dictionary with 'tag', 'requirements', 'description', etc.
            rates: Optional rate dictionary (for cost calculations)
            confidence_threshold: Minimum similarity score for spec matches
            
        Returns:
            Dictionary with hour estimates, confidence, and reasoning
        """
        
        # Get base defaults for job tag
        tag = job.get('tag', 'DEFAULT')
        tag_defaults = self.defaults.get(tag, self.defaults['DEFAULT'])
        
        # Initialize base hours
        if 'labor_hours' in tag_defaults and isinstance(tag_defaults['labor_hours'], dict):
            base_labor = tag_defaults['labor_hours']['avg']
            base_equipment = tag_defaults['equipment_hours']['avg']
        elif 'labor_hours_per_ft' in tag_defaults:
            # Underground work - calculate based on footage
            footage = job.get('footage', 100)  # Default 100 ft if not specified
            base_labor = tag_defaults['base_hours'] + (footage * tag_defaults['labor_hours_per_ft'])
            base_equipment = (footage * tag_defaults['equipment_hours_per_ft'])
        else:
            base_labor = 4.0
            base_equipment = 2.0
        
        # If no spec embeddings available, return defaults
        if not self.spec_data:
            return {
                'labor_hours': base_labor,
                'equipment_hours': base_equipment,
                'confidence': 0.5,
                'method': 'industry_defaults',
                'adjustments': [],
                'reasoning': [f"Using industry defaults for {tag}"]
            }
        
        # Create query from job requirements
        query_text = self._build_query_text(job)
        
        # Query spec embeddings
        spec_matches, adjustments = self._query_spec_embeddings(
            query_text, 
            confidence_threshold
        )
        
        # Extract time implications from matched specs
        time_adjustments = self._extract_time_adjustments(spec_matches)
        
        # Apply adjustments
        final_labor = base_labor
        final_equipment = base_equipment
        reasoning = []
        
        # Apply spec-based time adjustments
        for adj in time_adjustments:
            if adj['type'] == 'labor':
                final_labor += adj['hours']
                reasoning.append(f"Labor: {adj['reason']}")
            elif adj['type'] == 'equipment':
                final_equipment += adj['hours']
                reasoning.append(f"Equipment: {adj['reason']}")
            elif adj['type'] == 'both':
                final_labor += adj['hours']
                final_equipment += adj['hours'] * 0.6  # Equipment typically 60% of labor
                reasoning.append(f"Both: {adj['reason']}")
        
        # Apply keyword-based adjustments
        for adj in adjustments:
            final_labor += adj['labor_adjustment']
            final_equipment += adj['equipment_adjustment']
            if adj['reason']:
                reasoning.append(adj['reason'])
        
        # Ensure minimum hours (can't be negative or zero)
        final_labor = max(0.5, final_labor)
        final_equipment = max(0.25, final_equipment)
        
        # Calculate confidence based on spec match quality
        confidence = self._calculate_confidence(spec_matches, adjustments)
        
        return {
            'labor_hours': round(final_labor, 2),
            'equipment_hours': round(final_equipment, 2),
            'confidence': round(confidence, 3),
            'base_hours': {
                'labor': base_labor,
                'equipment': base_equipment
            },
            'adjustments': {
                'labor': round(final_labor - base_labor, 2),
                'equipment': round(final_equipment - base_equipment, 2)
            },
            'reasoning': reasoning[:5],  # Top 5 reasons
            'spec_matches': len(spec_matches),
            'method': 'spec_enhanced' if spec_matches else 'defaults_only'
        }
    
    def _build_query_text(self, job: Dict) -> str:
        """Build search query from job details"""
        
        parts = []
        
        # Add tag description
        tag = job.get('tag', '')
        if tag in self.defaults:
            parts.append(self.defaults[tag]['name'])
        
        # Add requirements
        requirements = job.get('requirements', {})
        if isinstance(requirements, dict):
            if requirements.get('poles', 0) > 0:
                parts.append(f"{requirements['poles']} poles")
            if requirements.get('crossarms', 0) > 0:
                parts.append(f"{requirements['crossarms']} crossarms")
            if requirements.get('special_equipment'):
                parts.append(' '.join(requirements['special_equipment']))
        elif isinstance(requirements, str):
            parts.append(requirements)
        
        # Add description if available
        if 'description' in job:
            parts.append(job['description'][:200])  # First 200 chars
        
        # Add location context if available
        if 'location_type' in job:
            parts.append(f"location: {job['location_type']}")
        
        return ' '.join(parts)
    
    def _query_spec_embeddings(self, 
                               query_text: str,
                               threshold: float = 0.8) -> Tuple[List[Dict], List[Dict]]:
        """
        Query spec embeddings for relevant matches
        
        Returns:
            Tuple of (matched_chunks, adjustments)
        """
        
        if not self.spec_data or 'embeddings' not in self.spec_data:
            return [], []
        
        # Encode query
        with torch.no_grad():
            query_embedding = self.model.encode(query_text, convert_to_tensor=True)
        
        # Get spec embeddings
        spec_embeddings = self.spec_data['embeddings']
        if isinstance(spec_embeddings, np.ndarray):
            spec_embeddings = torch.from_numpy(spec_embeddings)
        
        # Calculate similarities
        similarities = st_util.cos_sim(query_embedding, spec_embeddings)[0]
        
        # Find matches above threshold
        matches = []
        adjustments = []
        
        for idx, score in enumerate(similarities):
            if score >= threshold and idx < len(self.spec_data['chunks']):
                chunk = self.spec_data['chunks'][idx]
                matches.append({
                    'chunk': chunk,
                    'score': float(score),
                    'index': idx
                })
                
                # Check for adjustment keywords
                chunk_lower = chunk.lower()
                for keyword, adjustment in self.adjustment_keywords.items():
                    if keyword in chunk_lower:
                        adjustments.append({
                            'keyword': keyword,
                            'labor_adjustment': adjustment if adjustment > 0 else adjustment * 0.5,
                            'equipment_adjustment': adjustment * 0.5 if adjustment > 0 else adjustment * 0.25,
                            'reason': f"'{keyword}' found in spec (similarity: {score:.2f})"
                        })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:5], adjustments  # Top 5 matches
    
    def _extract_time_adjustments(self, spec_matches: List[Dict]) -> List[Dict]:
        """Extract time implications from matched spec chunks"""
        
        adjustments = []
        
        for match in spec_matches:
            chunk = match['chunk']
            score = match['score']
            
            # Try each time pattern
            for pattern, multiplier in self.time_patterns:
                matches = re.findall(pattern, chunk, re.IGNORECASE)
                
                for time_match in matches:
                    # Extract numeric value
                    if isinstance(time_match, tuple):
                        time_str = time_match[0] if time_match else '0'
                    else:
                        time_str = time_match
                    
                    # Handle ranges (e.g., "4-6 hours")
                    if '-' in time_str or '–' in time_str:
                        parts = re.split(r'[-–]', time_str)
                        if len(parts) == 2:
                            try:
                                min_val = float(parts[0].strip())
                                max_val = float(parts[1].strip())
                                hours = (min_val + max_val) / 2  # Use average
                            except:
                                hours = 0
                        else:
                            hours = 0
                    else:
                        try:
                            hours = float(time_str)
                        except:
                            hours = 0
                    
                    if hours > 0:
                        # Apply multiplier (e.g., days to hours)
                        adjusted_hours = hours * multiplier
                        
                        # Weight by similarity score
                        weighted_hours = adjusted_hours * score
                        
                        # Determine if labor, equipment, or both
                        chunk_lower = chunk.lower()
                        if 'equipment' in chunk_lower or 'crane' in chunk_lower or 'truck' in chunk_lower:
                            adj_type = 'equipment'
                        elif 'labor' in chunk_lower or 'crew' in chunk_lower or 'worker' in chunk_lower:
                            adj_type = 'labor'
                        else:
                            adj_type = 'both'
                        
                        adjustments.append({
                            'type': adj_type,
                            'hours': weighted_hours,
                            'reason': f"+{weighted_hours:.1f}h from spec: '{chunk[:50]}...' (match: {score:.0%})"
                        })
        
        return adjustments
    
    def _calculate_confidence(self, 
                             spec_matches: List[Dict],
                             adjustments: List[Dict]) -> float:
        """Calculate confidence score for the estimate"""
        
        if not spec_matches:
            return 0.5  # Default confidence when using defaults only
        
        # Base confidence on best match score
        best_score = max(match['score'] for match in spec_matches) if spec_matches else 0.5
        
        # Boost confidence if multiple high-quality matches
        high_quality_matches = sum(1 for match in spec_matches if match['score'] > 0.85)
        confidence_boost = min(0.15, high_quality_matches * 0.05)
        
        # Reduce confidence if many adjustments (uncertainty)
        adjustment_penalty = min(0.2, len(adjustments) * 0.02)
        
        # Calculate final confidence
        confidence = best_score + confidence_boost - adjustment_penalty
        
        return max(0.3, min(1.0, confidence))  # Clamp between 0.3 and 1.0
    
    def save_custom_defaults(self, custom_defaults: Dict):
        """Save custom hour defaults for specific tags"""
        
        try:
            with open(self.defaults_path, 'w') as f:
                json.dump(custom_defaults, f, indent=2)
            logger.info(f"Saved custom defaults to {self.defaults_path}")
        except Exception as e:
            logger.error(f"Failed to save custom defaults: {e}")
    
    def get_industry_defaults(self) -> Dict:
        """Get all industry default hours"""
        return self.defaults

# Standalone function for backward compatibility
def estimate_hours_standalone(job: Dict, rates: Optional[Dict] = None) -> Dict:
    """
    Standalone function for estimating hours
    Creates a singleton estimator instance
    """
    
    global _estimator_instance
    
    if '_estimator_instance' not in globals():
        _estimator_instance = SpecBasedHourEstimator()
    
    return _estimator_instance.estimate_hours(job, rates)

# Integration function for FastAPI
def integrate_spec_hour_estimation(app):
    """Add hour estimation endpoints to FastAPI app"""
    
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
    from typing import Optional
    
    router = APIRouter(prefix="/hour-estimation", tags=["Hour Estimation"])
    estimator = SpecBasedHourEstimator()
    
    class JobRequest(BaseModel):
        tag: str
        requirements: Optional[Dict] = {}
        description: Optional[str] = ""
        footage: Optional[float] = None
        location_type: Optional[str] = None
    
    @router.post("/estimate")
    async def estimate_job_hours(job: JobRequest):
        """
        Estimate labor and equipment hours for a job
        Uses spec embeddings for accurate, context-aware estimates
        """
        
        result = estimator.estimate_hours(job.dict())
        
        if result['confidence'] < 0.7:
            logger.warning(f"Low confidence estimate for {job.tag}: {result['confidence']}")
        
        return result
    
    @router.get("/defaults")
    async def get_default_hours():
        """Get industry-standard default hours for all job types"""
        return estimator.get_industry_defaults()
    
    @router.post("/feedback")
    async def submit_actual_hours(
        job_tag: str,
        estimated_hours: float,
        actual_hours: float,
        notes: Optional[str] = None
    ):
        """
        Submit actual hours for improving estimates (feedback loop)
        Future: Use this data for ML model fine-tuning
        """
        
        # Log feedback for future analysis
        feedback = {
            "tag": job_tag,
            "estimated": estimated_hours,
            "actual": actual_hours,
            "variance": actual_hours - estimated_hours,
            "variance_pct": ((actual_hours - estimated_hours) / estimated_hours * 100) if estimated_hours > 0 else 0,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }
        
        # In production, save to database or file
        logger.info(f"Hour feedback received: {feedback}")
        
        return {
            "message": "Feedback recorded",
            "variance": f"{feedback['variance_pct']:.1f}%"
        }
    
    app.include_router(router)
    logger.info("✅ Spec-based hour estimation endpoints added")

if __name__ == "__main__":
    # Test the estimator
    estimator = SpecBasedHourEstimator()
    
    # Test job
    test_job = {
        "tag": "07D",
        "requirements": {
            "poles": 1,
            "crossarms": 2,
            "special_equipment": ["bucket_truck"]
        },
        "description": "Replace distribution pole with 18 ft clearance requirement in residential area"
    }
    
    result = estimator.estimate_hours(test_job)
    
    print("Hour Estimation Test")
    print("="*50)
    print(f"Job Tag: {test_job['tag']}")
    print(f"Labor Hours: {result['labor_hours']}")
    print(f"Equipment Hours: {result['equipment_hours']}")
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Method: {result['method']}")
    print("\nReasoning:")
    for reason in result['reasoning']:
        print(f"  - {reason}")
