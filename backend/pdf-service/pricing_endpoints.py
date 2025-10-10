"""
PG&E Pricing Endpoints for NEXA Document Analyzer
Adds /learn-pricing and /pricing-status endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
from typing import Optional
import os
import shutil

from pricing_integration import PricingAnalyzer

logger = logging.getLogger(__name__)

# Create router
pricing_router = APIRouter()

# Global pricing analyzer (will be initialized in main app)
pricing_analyzer: Optional[PricingAnalyzer] = None


def init_pricing_analyzer(model, data_path='/data'):
    """Initialize pricing analyzer (called from main app)"""
    global pricing_analyzer
    pricing_analyzer = PricingAnalyzer(model, data_path)
    logger.info("💰 Pricing analyzer initialized")


@pricing_router.post("/learn-pricing")
async def learn_pricing(
    pricing_file: UploadFile = File(..., description="PG&E pricing CSV file"),
    region: str = Form("Stockton", description="Region name")
):
    """
    Upload and learn PG&E pricing data from CSV
    
    Expected CSV columns:
    - program_code: TAG or 07D
    - ref_code: TAG-1, TAG-2, 07-1, etc.
    - unit_type: Pole, Electric Crew Rate, Adder, etc.
    - unit_description: Full description
    - unit_of_measure: Per Tag, Hourly, Each, etc.
    - price_type: per_unit, per_hour, percent_cost_plus, etc.
    - rate: Numeric rate (optional)
    - percent: Percentage for adders (optional)
    - notes: Additional notes (optional)
    """
    if pricing_analyzer is None:
        raise HTTPException(503, "Pricing analyzer not initialized")
    
    if not pricing_file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files are supported")
    
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{pricing_file.filename}"
        with open(temp_path, 'wb') as f:
            content = await pricing_file.read()
            f.write(content)
        
        # Learn pricing data
        result = pricing_analyzer.learn_pricing(temp_path, region)
        
        # Clean up temp file
        os.remove(temp_path)
        
        logger.info(f"✅ Learned pricing data: {result['entries_indexed']} entries from {region}")
        
        return {
            "status": "success",
            "message": f"Pricing data learned successfully",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Error learning pricing data: {e}")
        raise HTTPException(500, f"Failed to learn pricing data: {str(e)}")


@pricing_router.get("/pricing-status")
async def get_pricing_status():
    """Get status of loaded pricing data"""
    if pricing_analyzer is None:
        return {
            "status": "not_initialized",
            "message": "Pricing analyzer not initialized"
        }
    
    summary = pricing_analyzer.get_pricing_summary()
    return summary


@pricing_router.post("/pricing-lookup")
async def pricing_lookup(
    text: str = Form(..., description="Text to search for pricing"),
    top_k: int = Form(3, description="Number of matches to return")
):
    """
    Look up pricing for a given text
    
    Useful for testing pricing matches without running full audit analysis
    """
    if pricing_analyzer is None:
        raise HTTPException(503, "Pricing analyzer not initialized")
    
    try:
        matches = pricing_analyzer.find_pricing(text, top_k)
        
        if not matches:
            return {
                "status": "no_matches",
                "message": "No pricing matches found",
                "text": text
            }
        
        return {
            "status": "success",
            "text": text,
            "matches": matches
        }
        
    except Exception as e:
        logger.error(f"Error in pricing lookup: {e}")
        raise HTTPException(500, f"Pricing lookup failed: {str(e)}")


@pricing_router.post("/calculate-cost")
async def calculate_cost(
    infraction_text: str = Form(..., description="Infraction description"),
    hours_estimate: float = Form(8.0, description="Estimated hours for hourly rates")
):
    """
    Calculate cost impact for an infraction
    
    Useful for testing cost calculations
    """
    if pricing_analyzer is None:
        raise HTTPException(503, "Pricing analyzer not initialized")
    
    try:
        # Find pricing matches
        matches = pricing_analyzer.find_pricing(infraction_text, top_k=3)
        
        if not matches:
            return {
                "status": "no_pricing",
                "message": "No pricing data found for this infraction",
                "infraction_text": infraction_text
            }
        
        # Calculate cost impact
        cost_impact = pricing_analyzer.calculate_cost_impact(
            infraction_text,
            matches,
            hours_estimate
        )
        
        return {
            "status": "success",
            "infraction_text": infraction_text,
            "cost_impact": cost_impact,
            "pricing_matches": [
                {
                    'ref_code': m['ref_code'],
                    'description': m['unit_description'],
                    'relevance_score': m['relevance_score']
                }
                for m in matches[:3]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error calculating cost: {e}")
        raise HTTPException(500, f"Cost calculation failed: {str(e)}")


@pricing_router.get("/pricing-by-code/{ref_code}")
async def get_pricing_by_code(ref_code: str):
    """
    Get pricing directly by reference code (e.g., TAG-2, 07-1)
    """
    if pricing_analyzer is None:
        raise HTTPException(503, "Pricing analyzer not initialized")
    
    pricing = pricing_analyzer.get_pricing_by_ref_code(ref_code)
    
    if pricing is None:
        raise HTTPException(404, f"No pricing found for ref code: {ref_code}")
    
    return {
        "status": "success",
        "ref_code": ref_code,
        "pricing": pricing
    }


@pricing_router.delete("/clear-pricing")
async def clear_pricing():
    """Clear all pricing data"""
    if pricing_analyzer is None:
        raise HTTPException(503, "Pricing analyzer not initialized")
    
    try:
        # Remove pricing files
        if os.path.exists(pricing_analyzer.pricing_index_path):
            os.remove(pricing_analyzer.pricing_index_path)
        if os.path.exists(pricing_analyzer.pricing_metadata_path):
            os.remove(pricing_analyzer.pricing_metadata_path)
        
        # Reset analyzer
        pricing_analyzer.pricing_index = None
        pricing_analyzer.pricing_metadata = []
        pricing_analyzer.pricing_df = None
        
        logger.info("🗑️ Pricing data cleared")
        
        return {
            "status": "success",
            "message": "Pricing data cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing pricing data: {e}")
        raise HTTPException(500, f"Failed to clear pricing data: {str(e)}")
