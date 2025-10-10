"""
PG&E Pricing Integration for NEXA Document Analyzer
Adds cost impact analysis to repeal recommendations

Integrates with app_oct2025_enhanced.py to provide:
- Cost savings for repealable infractions
- Pricing lookups for TAG and 07D programs
- Adder calculations (restoration, access, premium time)
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
import logging
from typing import Dict, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)


class PricingAnalyzer:
    """Analyzes cost impact of infractions using PG&E pricing master"""
    
    def __init__(self, 
                 model: SentenceTransformer,
                 data_path: str = '/data',
                 pricing_threshold: float = 0.40):
        """
        Initialize pricing analyzer
        
        Args:
            model: Sentence transformer model for embeddings
            data_path: Path to persistent storage
            pricing_threshold: Minimum similarity for pricing matches (default: 0.40)
        """
        self.model = model
        self.data_path = data_path
        self.pricing_threshold = pricing_threshold
        
        # Pricing data storage
        self.pricing_index_path = os.path.join(data_path, 'pricing_index.faiss')
        self.pricing_metadata_path = os.path.join(data_path, 'pricing_metadata.pkl')
        
        # Load existing pricing data if available
        self.pricing_df = None
        self.pricing_index = None
        self.pricing_metadata = []
        
        # Labor and equipment data
        self.labor_df = None
        self.equip_df = None
        
        self._load_pricing_data()
        self._load_labor_equipment_data()
    
    def _load_pricing_data(self):
        """Load pricing index and metadata from disk"""
        try:
            if os.path.exists(self.pricing_index_path) and os.path.exists(self.pricing_metadata_path):
                # Load FAISS index
                self.pricing_index = faiss.read_index(self.pricing_index_path)
                
                # Load metadata
                with open(self.pricing_metadata_path, 'rb') as f:
                    self.pricing_metadata = pickle.load(f)
                
                logger.info(f"✅ Loaded pricing index: {len(self.pricing_metadata)} entries")
            else:
                logger.info("ℹ️ No pricing data found - use /learn-pricing to upload")
        except Exception as e:
            logger.error(f"Error loading pricing data: {e}")
    
    def _load_labor_equipment_data(self):
        """Load labor and equipment rate data from CSVs"""
        try:
            # Try to load labor rates
            labor_path = os.path.join(self.data_path, 'ibew1245_labor_rates_2025.csv')
            if not os.path.exists(labor_path):
                # Try local path for development
                labor_path = 'ibew1245_labor_rates_2025.csv'
            
            if os.path.exists(labor_path):
                self.labor_df = pd.read_csv(labor_path)
                logger.info(f"✅ Loaded labor rates: {len(self.labor_df)} classifications")
            else:
                logger.warning("⚠️ Labor rates CSV not found")
            
            # Try to load equipment rates
            equip_path = os.path.join(self.data_path, 'pge_equipment_rates_2025.csv')
            if not os.path.exists(equip_path):
                # Try local path for development
                equip_path = 'pge_equipment_rates_2025.csv'
            
            if os.path.exists(equip_path):
                self.equip_df = pd.read_csv(equip_path)
                logger.info(f"✅ Loaded equipment rates: {len(self.equip_df)} items")
            else:
                logger.warning("⚠️ Equipment rates CSV not found")
                
        except Exception as e:
            logger.error(f"Error loading labor/equipment data: {e}")
    
    def learn_pricing(self, csv_path: str, region: str = "Stockton") -> Dict:
        """
        Learn pricing data from CSV file
        
        Args:
            csv_path: Path to PG&E pricing CSV
            region: Region name (default: Stockton)
        
        Returns:
            Dict with status and statistics
        """
        try:
            # Load CSV
            df = pd.read_csv(csv_path)
            logger.info(f"📊 Loaded pricing CSV: {len(df)} rows")
            
            # Validate required columns
            required_cols = ['program_code', 'ref_code', 'unit_type', 'unit_description']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Store dataframe
            self.pricing_df = df
            
            # Create embeddings for semantic search
            embeddings_list = []
            metadata_list = []
            
            for idx, row in df.iterrows():
                # Create searchable text from key fields
                search_text = f"{row['ref_code']} {row['unit_type']} {row['unit_description']}"
                if pd.notna(row.get('notes')):
                    search_text += f" {row['notes']}"
                
                # Generate embedding
                embedding = self.model.encode([search_text], normalize_embeddings=True)[0]
                embeddings_list.append(embedding)
                
                # Store metadata
                metadata = {
                    'program_code': row['program_code'],
                    'ref_code': row['ref_code'],
                    'unit_type': row['unit_type'],
                    'unit_description': row['unit_description'],
                    'unit_of_measure': row.get('unit_of_measure', ''),
                    'price_type': row.get('price_type', ''),
                    'rate': float(row['rate']) if pd.notna(row.get('rate')) else None,
                    'percent': float(row['percent']) if pd.notna(row.get('percent')) else None,
                    'notes': row.get('notes', ''),
                    'region': region,
                    'search_text': search_text
                }
                metadata_list.append(metadata)
            
            # Create FAISS index
            embeddings_array = np.array(embeddings_list).astype('float32')
            dimension = embeddings_array.shape[1]
            
            index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
            index.add(embeddings_array)
            
            # Save to disk
            faiss.write_index(index, self.pricing_index_path)
            with open(self.pricing_metadata_path, 'wb') as f:
                pickle.dump(metadata_list, f)
            
            self.pricing_index = index
            self.pricing_metadata = metadata_list
            
            logger.info(f"✅ Pricing data indexed: {len(metadata_list)} entries")
            
            return {
                'status': 'success',
                'entries_indexed': len(metadata_list),
                'region': region,
                'programs': df['program_code'].unique().tolist(),
                'storage_path': self.data_path
            }
            
        except Exception as e:
            logger.error(f"Error learning pricing data: {e}")
            raise
    
    def find_pricing(self, infraction_text: str, top_k: int = 3) -> List[Dict]:
        """
        Find pricing matches for an infraction
        
        Args:
            infraction_text: Text describing the infraction
            top_k: Number of top matches to return
        
        Returns:
            List of pricing matches with similarity scores
        """
        if self.pricing_index is None or not self.pricing_metadata:
            return []
        
        try:
            # Generate embedding for infraction
            inf_embedding = self.model.encode([infraction_text], normalize_embeddings=True)
            
            # Search index
            similarities, indices = self.pricing_index.search(inf_embedding, top_k)
            
            matches = []
            for sim, idx in zip(similarities[0], indices[0]):
                if sim >= self.pricing_threshold:
                    metadata = self.pricing_metadata[idx].copy()
                    metadata['similarity'] = float(sim)
                    metadata['relevance_score'] = round(float(sim) * 100, 1)
                    matches.append(metadata)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error finding pricing: {e}")
            return []
    
    def detect_crew_from_text(self, text: str) -> Tuple[int, float, bool]:
        """
        Detect crew size, hours, and premium time from infraction text
        
        Args:
            text: Infraction text to analyze
        
        Returns:
            Tuple of (crew_size, hours, is_premium)
        """
        # Regex for crew size
        crew_match = re.search(r'(\d+)-man\s+crew', text, re.IGNORECASE)
        crew_size = int(crew_match.group(1)) if crew_match else 0
        
        # Regex for hours
        hours_match = re.search(r'(\d+)\s+(hours?|hrs?)', text, re.IGNORECASE)
        hours = float(hours_match.group(1)) if hours_match else 8.0  # Default 8 hours
        
        # Check for premium/double time
        is_premium = bool(re.search(r'(premium\s+time|double\s+time|overtime)', text, re.IGNORECASE))
        
        return crew_size, hours, is_premium
    
    def calculate_labor_cost(self, crew_size: int, hours: float, is_premium: bool = False) -> Tuple[float, List[Dict]]:
        """
        Calculate labor cost for a crew
        
        Args:
            crew_size: Number of workers in crew
            hours: Hours worked
            is_premium: Whether premium/double time applies
        
        Returns:
            Tuple of (total_labor_cost, labor_breakdown)
        """
        if crew_size == 0 or self.labor_df is None:
            return 0.0, []
        
        rate_column = 'doubletime_rate_usd_per_hr' if is_premium else 'straight_rate_usd_per_hr'
        
        # Get rates
        try:
            foreman_rate = self.labor_df.loc[
                self.labor_df['classification'] == 'Foreman', 
                rate_column
            ].values[0]
            
            journeyman_rate = self.labor_df.loc[
                self.labor_df['classification'] == 'Journeyman Lineman', 
                rate_column
            ].values[0]
        except (IndexError, KeyError) as e:
            logger.warning(f"Could not find labor rates: {e}")
            return 0.0, []
        
        labor_breakdown = []
        
        # 1 Foreman + (crew_size - 1) Journeymen
        foreman_cost = foreman_rate * hours
        labor_breakdown.append({
            'classification': 'Foreman',
            'rate': round(foreman_rate, 2),
            'hours': hours,
            'total': round(foreman_cost, 2)
        })
        
        for i in range(crew_size - 1):
            journeyman_cost = journeyman_rate * hours
            labor_breakdown.append({
                'classification': 'Journeyman Lineman',
                'rate': round(journeyman_rate, 2),
                'hours': hours,
                'total': round(journeyman_cost, 2)
            })
        
        total_labor = sum(item['total'] for item in labor_breakdown)
        
        return round(total_labor, 2), labor_breakdown
    
    def select_and_calculate_equipment(self, job_type: str, crew_size: int, hours: float) -> Tuple[float, List[Dict]]:
        """
        Auto-select and calculate equipment costs based on job type
        
        Args:
            job_type: Type of job (extracted from infraction text)
            crew_size: Size of crew (affects equipment quantity)
            hours: Hours worked
        
        Returns:
            Tuple of (total_equipment_cost, equipment_breakdown)
        """
        if self.equip_df is None:
            return 0.0, []
        
        # Auto-select equipment based on job type keywords
        equip_codes = []
        
        if re.search(r'pole', job_type, re.IGNORECASE):
            # Pole jobs need: Digger Derrick, Bucket Truck, Pickup, Trailer
            equip_codes = ['31', '15', '57', '85']
        elif re.search(r'(overhead|oh|cable)', job_type, re.IGNORECASE):
            # Overhead work: Bucket Truck, Pickup
            equip_codes = ['15', '57']
        elif re.search(r'underground', job_type, re.IGNORECASE):
            # Underground: Digger, Pickup, Trailer
            equip_codes = ['31', '57', '85']
        else:
            # Default: Basic truck
            equip_codes = ['57']
        
        equipment_breakdown = []
        total_equipment = 0.0
        
        for code in equip_codes:
            try:
                row = self.equip_df[self.equip_df['equip_no'].astype(str) == str(code)]
                if row.empty:
                    continue
                
                rate = float(row['rate_usd_per_hr'].values[0])
                
                # Determine quantity based on crew size
                qty_col = f'qty_for_crew_{min(crew_size, 4)}' if crew_size > 0 else 'qty_for_crew_1'
                qty = float(row[qty_col].values[0]) if qty_col in row.columns and pd.notna(row[qty_col].values[0]) else 1.0
                
                item_total = rate * hours * qty
                
                equipment_breakdown.append({
                    'description': row['description'].values[0],
                    'equip_no': code,
                    'rate': round(rate, 2),
                    'quantity': qty,
                    'hours': hours,
                    'total': round(item_total, 2)
                })
                
                total_equipment += item_total
                
            except Exception as e:
                logger.warning(f"Could not calculate equipment {code}: {e}")
                continue
        
        return round(total_equipment, 2), equipment_breakdown
    
    def calculate_cost_impact(self, 
                             infraction_text: str,
                             pricing_matches: List[Dict],
                             hours_estimate: float = 8.0) -> Optional[Dict]:
        """
        Calculate cost impact for a repealable infraction
        
        Args:
            infraction_text: Text describing the infraction
            pricing_matches: List of pricing matches from find_pricing()
            hours_estimate: Estimated hours for hourly rates (default: 8)
        
        Returns:
            Dict with cost breakdown or None if no pricing found
        """
        if not pricing_matches:
            return None
        
        # Use best match
        best_match = pricing_matches[0]
        
        cost_impact = {
            'ref_code': best_match['ref_code'],
            'unit_description': best_match['unit_description'],
            'base_rate': best_match['rate'],
            'unit': best_match['unit_of_measure'],
            'price_type': best_match['price_type'],
            'adders': [],
            'total_savings': 0.0,
            'notes': []
        }
        
        # Calculate base cost
        if best_match['rate'] is not None:
            if best_match['price_type'] == 'per_hour':
                base_cost = best_match['rate'] * hours_estimate
                cost_impact['base_cost'] = round(base_cost, 2)
                cost_impact['notes'].append(f"Based on {hours_estimate} hours")
            elif best_match['price_type'] == 'per_unit':
                cost_impact['base_cost'] = best_match['rate']
            elif best_match['price_type'] == 'per_day':
                cost_impact['base_cost'] = best_match['rate']
            elif best_match['price_type'] == 'per_order':
                cost_impact['base_cost'] = best_match['rate']
            else:
                cost_impact['base_cost'] = best_match['rate']
        else:
            cost_impact['base_cost'] = 0.0
            # Enhanced note for 07D poles with estimates
            if '07-' in best_match['ref_code'] and 'Pole' in best_match['unit_type']:
                cost_impact['notes'].append("Rate TBD - est. $3,000-$5,000 for 07D poles based on class; manual fill recommended")
            else:
                cost_impact['notes'].append("Rate TBD - reference other units")
        
        # Check for adders in other matches
        for match in pricing_matches[1:]:
            if 'Adder' in match['unit_type']:
                adder = {
                    'type': match['unit_type'],
                    'description': match['unit_description']
                }
                
                if match['price_type'] == 'percent_cost_plus':
                    if match['percent'] is not None:
                        adder['percent'] = match['percent']
                        adder['estimated'] = round(cost_impact['base_cost'] * (match['percent'] / 100), 2)
                    else:
                        adder['percent'] = 5  # Default
                        adder['estimated'] = round(cost_impact['base_cost'] * 0.05, 2)
                        adder['note'] = "Default 5% - verify with sheet"
                elif match['rate'] is not None:
                    adder['rate'] = match['rate']
                    adder['estimated'] = match['rate']
                
                cost_impact['adders'].append(adder)
        
        # Detect crew, hours, and premium time from infraction text
        crew_size, hours, is_premium = self.detect_crew_from_text(infraction_text)
        
        # Calculate labor costs if crew detected
        labor_total, labor_breakdown = self.calculate_labor_cost(crew_size, hours, is_premium)
        if labor_total > 0:
            cost_impact['labor'] = {
                'total': labor_total,
                'breakdown': labor_breakdown,
                'crew_size': crew_size,
                'hours': hours,
                'premium_time': is_premium
            }
            cost_impact['notes'].append(f"{crew_size}-man crew, {hours} hours" + (" (premium time)" if is_premium else ""))
        
        # Calculate equipment costs if crew detected
        equipment_total, equipment_breakdown = self.select_and_calculate_equipment(
            infraction_text, 
            crew_size, 
            hours
        )
        if equipment_total > 0:
            cost_impact['equipment'] = {
                'total': equipment_total,
                'breakdown': equipment_breakdown
            }
        
        # Calculate total savings
        total = cost_impact['base_cost']
        for adder in cost_impact['adders']:
            if 'estimated' in adder:
                total += adder['estimated']
        
        if labor_total > 0:
            total += labor_total
        if equipment_total > 0:
            total += equipment_total
        
        cost_impact['total_savings'] = round(total, 2)
        
        # Add contextual notes
        if 'Inaccessible' in best_match['unit_description']:
            cost_impact['notes'].append("Inaccessible location - higher rate")
        if 'Premium' in best_match['unit_description']:
            cost_impact['notes'].append("Premium time differential applied")
        
        return cost_impact
    
    def extract_ref_codes(self, text: str) -> List[str]:
        """
        Extract PG&E reference codes from text (e.g., TAG-2, 07-1)
        
        Args:
            text: Text to search for ref codes
        
        Returns:
            List of found ref codes
        """
        # Pattern for TAG-X or 07-X format
        pattern = r'\b(TAG-\d+(?:\.\d+)?|07D?-\d+(?:\.\d+)?)\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [m.upper() for m in matches]
    
    def get_pricing_by_ref_code(self, ref_code: str) -> Optional[Dict]:
        """
        Get pricing directly by reference code
        
        Args:
            ref_code: PG&E reference code (e.g., TAG-2)
        
        Returns:
            Pricing metadata or None
        """
        ref_code_upper = ref_code.upper()
        for metadata in self.pricing_metadata:
            if metadata['ref_code'].upper() == ref_code_upper:
                return metadata
        return None
    
    def get_pricing_summary(self) -> Dict:
        """Get summary of loaded pricing data"""
        # Check labor/equipment CSVs
        labor_count = len(self.labor_df) if self.labor_df is not None else 0
        equip_count = len(self.equip_df) if self.equip_df is not None else 0
        
        # Check pricing index
        if not self.pricing_metadata:
            # If we have CSVs but no index
            if labor_count > 0 or equip_count > 0:
                return {
                    'status': 'partial',
                    'message': 'Labor/equipment CSVs loaded but pricing index not built',
                    'labor_rates': labor_count,
                    'equipment_rates': equip_count,
                    'pricing_index': False,
                    'action_needed': 'Upload pricing master CSV to /learn-pricing endpoint'
                }
            return {
                'status': 'empty',
                'message': 'No pricing data loaded'
            }
        
        programs = {}
        for item in self.pricing_metadata:
            prog = item['program_code']
            if prog not in programs:
                programs[prog] = {'count': 0, 'ref_codes': []}
            programs[prog]['count'] += 1
            programs[prog]['ref_codes'].append(item['ref_code'])
        
        return {
            'status': 'loaded',
            'total_entries': len(self.pricing_metadata),
            'programs': programs,
            'labor_rates': labor_count,
            'equipment_rates': equip_count,
            'storage_path': self.data_path,
            'threshold': self.pricing_threshold
        }


# ============================================
# INTEGRATION WITH ANALYZE-AUDIT ENDPOINT
# ============================================

def enhance_infraction_with_pricing(infraction_result: Dict,
                                    pricing_analyzer: PricingAnalyzer) -> Dict:
    """
    Enhance an infraction analysis result with cost impact
    
    Args:
        infraction_result: Result from analyze-audit endpoint
        pricing_analyzer: PricingAnalyzer instance
    
    Returns:
        Enhanced result with cost_impact field
    """
    infraction_text = infraction_result.get('infraction_text', '')
    
    # Only add pricing for repealable infractions
    if infraction_result.get('status') != 'POTENTIALLY REPEALABLE':
        return infraction_result
    
    # Try to extract ref codes first (more accurate)
    ref_codes = pricing_analyzer.extract_ref_codes(infraction_text)
    
    if ref_codes:
        # Direct lookup by ref code
        pricing_match = pricing_analyzer.get_pricing_by_ref_code(ref_codes[0])
        if pricing_match:
            pricing_matches = [pricing_match]
        else:
            # Fallback to semantic search
            pricing_matches = pricing_analyzer.find_pricing(infraction_text, top_k=3)
    else:
        # Semantic search
        pricing_matches = pricing_analyzer.find_pricing(infraction_text, top_k=3)
    
    # Calculate cost impact
    if pricing_matches:
        cost_impact = pricing_analyzer.calculate_cost_impact(
            infraction_text,
            pricing_matches
        )
        
        if cost_impact:
            infraction_result['cost_impact'] = cost_impact
            infraction_result['pricing_matches'] = [
                {
                    'ref_code': m['ref_code'],
                    'description': m['unit_description'],
                    'relevance_score': m['relevance_score']
                }
                for m in pricing_matches[:3]
            ]
    
    return infraction_result


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Example: Initialize and test
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    analyzer = PricingAnalyzer(model, data_path='./test_data')
    
    # Simulate infraction
    infraction = {
        'infraction_text': 'TAG-2: 2AA Capital OH Replacement – Inaccessible marked as go-back',
        'status': 'POTENTIALLY REPEALABLE',
        'confidence': 'HIGH'
    }
    
    # Enhance with pricing (would need pricing data loaded)
    # enhanced = enhance_infraction_with_pricing(infraction, analyzer)
    # print(enhanced)
    
    print("✅ Pricing integration module ready")
    print("   Use /learn-pricing to upload PG&E pricing CSV")
    print("   Pricing will auto-enhance repealable infractions")
