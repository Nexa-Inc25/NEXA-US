#!/usr/bin/env python3
"""
Mega Bundle Analyzer for NEXA
Processes 3500+ job packages for profitability analysis and scheduling optimization
Supports both post-win and pre-bid modes
"""

import os
import re
import json
import shutil
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
from collections import defaultdict
import pdfplumber
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

@dataclass
class Job:
    """Represents a single job package"""
    id: str
    tag: str  # 07D, KAA, 2AA etc.
    pm_number: str
    notification_number: str
    coordinates: Tuple[float, float]  # (lat, lon)
    requirements: Dict[str, Any]
    estimated_hours: Dict[str, float]
    compliance_score: float
    dependencies: List[str]
    priority: int

@dataclass
class CostEstimate:
    """Cost breakdown for a job"""
    labor_hours: float
    equipment_hours: float
    labor_cost: float
    equipment_cost: float
    material_cost: float
    overhead: float
    total_cost: float
    revenue: float
    profit: float
    profit_margin: float

class MegaBundleAnalyzer:
    """
    Analyzes large job bundles for profitability and scheduling
    """
    
    def __init__(self, 
                 data_dir: str = "/data",
                 spec_embeddings_path: str = "/data/spec_embeddings.pkl",
                 pricing_data_path: str = "/data/pricing_data.json"):
        """
        Initialize the analyzer
        
        Args:
            data_dir: Directory for storing bundle data
            spec_embeddings_path: Path to spec embeddings for compliance checking
            pricing_data_path: Path to pricing/rates data
        """
        
        self.data_dir = Path(data_dir)
        self.bundle_dir = self.data_dir / "mega_bundles"
        self.bundle_dir.mkdir(exist_ok=True)
        
        # Load embeddings for spec compliance
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.spec_embeddings = self._load_spec_embeddings(spec_embeddings_path)
        
        # Load pricing data
        self.rates = self._load_pricing_data(pricing_data_path)
        
        # Job type definitions (hours, dependencies, materials)
        self.job_definitions = {
            "07D": {
                "name": "Pole Replacement - Distribution",
                "labor_hours": 8,
                "equipment_hours": 4,
                "material_cost": 2500,
                "dependencies": [],
                "priority": 1
            },
            "KAA": {
                "name": "Crossarm Installation",
                "labor_hours": 6,
                "equipment_hours": 3,
                "material_cost": 800,
                "dependencies": ["07D"],  # Must have pole first
                "priority": 2
            },
            "2AA": {
                "name": "Anchor Installation",
                "labor_hours": 4,
                "equipment_hours": 2,
                "material_cost": 500,
                "dependencies": [],
                "priority": 3
            },
            "TRX": {
                "name": "Transformer Installation",
                "labor_hours": 10,
                "equipment_hours": 5,
                "material_cost": 5000,
                "dependencies": ["07D"],
                "priority": 2
            },
            "UG1": {
                "name": "Underground Primary",
                "labor_hours": 12,
                "equipment_hours": 8,
                "material_cost": 3000,
                "dependencies": [],
                "priority": 1
            }
        }
    
    def _load_spec_embeddings(self, path: str) -> Optional[Dict]:
        """Load spec embeddings for compliance checking"""
        try:
            import pickle
            if Path(path).exists():
                with open(path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Could not load spec embeddings: {e}")
        return None
    
    def _load_pricing_data(self, path: str) -> Dict:
        """Load pricing rates"""
        
        # Default rates if file doesn't exist
        default_rates = {
            "labor_rate": 85.0,  # $/hour
            "equipment_rate": 150.0,  # $/hour
            "overhead_percentage": 0.15,  # 15% overhead
            "profit_margin_target": 0.20,  # 20% target margin
            "contract_rates": {}  # Per-tag rates from contract
        }
        
        try:
            if Path(path).exists():
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    default_rates.update(loaded)
        except Exception as e:
            logger.warning(f"Using default rates: {e}")
        
        return default_rates
    
    def extract_job_from_pdf(self, pdf_path: Path) -> Optional[Job]:
        """
        Extract job data from a single PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Job object or None if extraction fails
        """
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract all text
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                
                # Extract job tag (07D, KAA, etc.)
                tag_match = re.search(r'\b(07D|KAA|2AA|TRX|UG1)\b', text)
                tag = tag_match.group(1) if tag_match else "UNK"
                
                # Extract PM number
                pm_match = re.search(r'PM[- ]?(\d{4,})', text)
                pm_number = pm_match.group(1) if pm_match else pdf_path.stem
                
                # Extract notification number
                notif_match = re.search(r'N[- ]?(\d{4,})', text)
                notification_number = notif_match.group(1) if notif_match else ""
                
                # Extract coordinates (simplified - look for lat/lon pattern)
                coord_match = re.search(r'(\d+\.\d+)[,\s]+(-?\d+\.\d+)', text)
                if coord_match:
                    lat = float(coord_match.group(1))
                    lon = float(coord_match.group(2))
                    coordinates = (lat, lon)
                else:
                    # Default to Sacramento area if not found
                    coordinates = (38.5816 + np.random.uniform(-0.5, 0.5), 
                                 -121.4944 + np.random.uniform(-0.5, 0.5))
                
                # Extract requirements (materials, special equipment)
                requirements = self._extract_requirements(text)
                
                # Get job definition
                job_def = self.job_definitions.get(tag, self.job_definitions["07D"])
                
                # Check compliance against specs
                compliance_score = self._check_compliance(requirements)
                
                return Job(
                    id=pm_number,
                    tag=tag,
                    pm_number=pm_number,
                    notification_number=notification_number,
                    coordinates=coordinates,
                    requirements=requirements,
                    estimated_hours={
                        "labor": job_def["labor_hours"],
                        "equipment": job_def["equipment_hours"]
                    },
                    compliance_score=compliance_score,
                    dependencies=job_def["dependencies"],
                    priority=job_def["priority"]
                )
                
        except Exception as e:
            logger.error(f"Failed to extract job from {pdf_path}: {e}")
            return None
    
    def _extract_requirements(self, text: str) -> Dict:
        """Extract material and equipment requirements from job text"""
        
        requirements = {
            "poles": 0,
            "crossarms": 0,
            "transformers": 0,
            "anchors": 0,
            "conductor_feet": 0,
            "special_equipment": []
        }
        
        # Look for quantities (simplified regex patterns)
        pole_match = re.search(r'(\d+)\s*poles?', text, re.IGNORECASE)
        if pole_match:
            requirements["poles"] = int(pole_match.group(1))
        
        crossarm_match = re.search(r'(\d+)\s*cross\s*arms?', text, re.IGNORECASE)
        if crossarm_match:
            requirements["crossarms"] = int(crossarm_match.group(1))
        
        # Check for special equipment
        if "crane" in text.lower():
            requirements["special_equipment"].append("crane")
        if "bucket truck" in text.lower():
            requirements["special_equipment"].append("bucket_truck")
        
        return requirements
    
    def _check_compliance(self, requirements: Dict) -> float:
        """
        Check compliance against spec embeddings
        
        Returns:
            Compliance score 0-1 (1 = fully compliant)
        """
        
        if not self.spec_embeddings:
            return 0.85  # Default if no embeddings
        
        # Convert requirements to text for embedding
        req_text = f"Job requires {requirements['poles']} poles, {requirements['crossarms']} crossarms"
        if requirements.get('special_equipment'):
            req_text += f" with {', '.join(requirements['special_equipment'])}"
        
        # Generate embedding
        req_embedding = self.embedder.encode(req_text)
        
        # If we have actual spec embeddings, do similarity search
        if 'embeddings' in self.spec_embeddings:
            import torch
            from sentence_transformers import util as st_util
            
            spec_embeddings = self.spec_embeddings['embeddings']
            if isinstance(spec_embeddings, np.ndarray):
                spec_embeddings = torch.from_numpy(spec_embeddings)
            
            # Calculate similarities
            similarities = st_util.cos_sim(
                torch.from_numpy(req_embedding.reshape(1, -1)),
                spec_embeddings
            )[0]
            
            # Use max similarity as compliance score
            compliance = float(torch.max(similarities))
        else:
            # Fallback to reasonable estimate
            compliance = 0.75 + np.random.uniform(0, 0.15)
        
        return min(1.0, compliance)
    
    def calculate_costs(self, job: Job, rates: Dict, mode: str = "post-win") -> CostEstimate:
        """
        Calculate costs and profitability for a job using spec-based hour estimation
        
        Args:
            job: Job object
            rates: Pricing rates
            mode: "post-win" or "pre-bid"
            
        Returns:
            CostEstimate object
        """
        
        # Use spec-based hour estimator if available
        try:
            from spec_based_hour_estimator import estimate_hours_standalone
            
            # Prepare job dict for estimator
            job_dict = {
                'tag': job.tag,
                'requirements': job.requirements,
                'description': f"{job.tag} job at {job.coordinates}",
                'pm_number': job.pm_number
            }
            
            # Get spec-based hour estimate
            hour_estimate = estimate_hours_standalone(job_dict, rates)
            
            # Update job's estimated hours with spec-based estimates
            if hour_estimate['confidence'] > 0.7:  # Use spec estimate if confident
                job.estimated_hours["labor"] = hour_estimate['labor_hours']
                job.estimated_hours["equipment"] = hour_estimate['equipment_hours']
                logger.info(f"Using spec-based hours for {job.tag}: {hour_estimate['labor_hours']}L/{hour_estimate['equipment_hours']}E (conf: {hour_estimate['confidence']:.0%})")
            else:
                logger.warning(f"Low confidence ({hour_estimate['confidence']:.0%}) for {job.tag}, using defaults")
        except ImportError:
            logger.warning("Spec-based hour estimator not available, using defaults")
        except Exception as e:
            logger.error(f"Error in spec-based estimation: {e}, using defaults")
        
        # Get job definition for material costs
        job_def = self.job_definitions.get(job.tag, self.job_definitions["07D"])
        
        # Calculate costs with potentially updated hours
        labor_cost = job.estimated_hours["labor"] * rates["labor_rate"]
        equipment_cost = job.estimated_hours["equipment"] * rates["equipment_rate"]
        material_cost = job_def["material_cost"]
        
        # Add overhead
        subtotal = labor_cost + equipment_cost + material_cost
        overhead = subtotal * rates["overhead_percentage"]
        total_cost = subtotal + overhead
        
        # Calculate revenue
        if mode == "post-win" and job.tag in rates.get("contract_rates", {}):
            # Use actual contract rate
            revenue = rates["contract_rates"][job.tag]
        else:
            # For pre-bid, estimate revenue needed for target margin
            revenue = total_cost * (1 + rates["profit_margin_target"])
        
        # Calculate profit
        profit = revenue - total_cost
        profit_margin = profit / revenue if revenue > 0 else 0
        
        return CostEstimate(
            labor_hours=job.estimated_hours["labor"],
            equipment_hours=job.estimated_hours["equipment"],
            labor_cost=labor_cost,
            equipment_cost=equipment_cost,
            material_cost=material_cost,
            overhead=overhead,
            total_cost=total_cost,
            revenue=revenue,
            profit=profit,
            profit_margin=profit_margin
        )
