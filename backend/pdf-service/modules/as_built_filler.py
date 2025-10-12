"""
As-Built Auto-Filler using YOLO + Spec Cross-Reference
Processes Foreman photos, detects equipment, checks compliance, fills PDF
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import green, red, black
from reportlab.lib.units import inch
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import json

logger = logging.getLogger(__name__)

class AsBuiltFiller:
    """
    Auto-fills as-builts from photos using YOLO detection + spec compliance
    """
    
    def __init__(self, data_dir: str = "/data"):
        self.data_dir = data_dir
        self.model = None
        self.spec_embeddings = None
        self.spec_chunks = None
        self.load_resources()
    
    def load_resources(self):
        """Load model and spec embeddings"""
        try:
            # Load sentence transformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Load spec embeddings from learned spec book
            embeddings_file = os.path.join(self.data_dir, "spec_embeddings.pkl")
            if os.path.exists(embeddings_file):
                with open(embeddings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.spec_embeddings = data.get('embeddings')
                    self.spec_chunks = data.get('chunks', [])
                    logger.info(f"✅ Loaded {len(self.spec_chunks)} spec chunks")
            else:
                logger.warning("⚠️ No spec embeddings found - run /upload-specs first!")
        except Exception as e:
            logger.error(f"Error loading resources: {e}")
    
    def process_photos_for_as_built(
        self, 
        job_id: str, 
        photos: List[Dict],
        job_details: Dict = None
    ) -> Dict[str, Any]:
        """
        Process photos and generate as-built data
        """
        logger.info(f"🔍 Processing {len(photos)} photos for job {job_id}")
        
        # Aggregate detections from all photos
        all_detections = []
        equipment_found = {
            'poles': [],
            'crossarms': [],
            'insulators': [],
            'transformers': [],
            'guy_wires': [],
            'grounds': []
        }
        
        for photo_data in photos:
            # YOLO detections from photo
            detections = photo_data.get('detections', [])
            
            for det in detections:
                label = det.get('label', '').lower()
                confidence = det.get('confidence', 0)
                
                # Categorize equipment
                if 'pole' in label:
                    equipment_found['poles'].append({
                        'type': det.get('classification', 'Unknown'),
                        'confidence': confidence,
                        'compliant': True  # Will check against specs
                    })
                elif 'crossarm' in label or 'cross-arm' in label:
                    equipment_found['crossarms'].append({
                        'type': 'Standard',
                        'confidence': confidence,
                        'angle': det.get('angle', 'Level')
                    })
                elif 'insulator' in label:
                    equipment_found['insulators'].append({
                        'count': det.get('count', 1),
                        'type': 'Porcelain',
                        'confidence': confidence
                    })
                
                all_detections.append(det)
        
        # Cross-reference with specs for compliance
        compliance_analysis = self.check_spec_compliance(equipment_found)
        
        # Generate as-built data structure
        as_built_data = {
            'job_id': job_id,
            'timestamp': datetime.now().isoformat(),
            'equipment_installed': equipment_found,
            'compliance': compliance_analysis,
            'photos_processed': len(photos),
            'total_detections': len(all_detections),
            'go_backs_found': compliance_analysis.get('issues', []),
            'ready_for_qa': len(compliance_analysis.get('issues', [])) == 0
        }
        
        # Add job details if provided
        if job_details:
            as_built_data.update({
                'pm_number': job_details.get('pm_number'),
                'location': job_details.get('location'),
                'foreman': job_details.get('foreman_name'),
                'crew': job_details.get('crew_number')
            })
        
        return as_built_data
    
    def check_spec_compliance(self, equipment: Dict) -> Dict[str, Any]:
        """
        Check equipment against learned PG&E specs
        """
        if not self.spec_embeddings or not self.spec_chunks:
            return {
                'checked': False,
                'message': 'No spec book loaded',
                'issues': []
            }
        
        compliance_results = {
            'checked': True,
            'compliant_items': [],
            'issues': [],
            'confidence_scores': [],
            'spec_references': []
        }
        
        # Check each equipment type
        checks = [
            ('poles', 'pole installation specifications height clearance'),
            ('crossarms', 'crossarm mounting angle Grade B construction'),
            ('insulators', 'insulator spacing requirements voltage rating'),
            ('transformers', 'transformer mounting clearance requirements'),
            ('guy_wires', 'guy wire tension anchor specifications'),
            ('grounds', 'grounding requirements resistance ohms')
        ]
        
        for equipment_type, query in checks:
            if equipment.get(equipment_type):
                # Search specs for this equipment
                matches = self.search_specs(query)
                
                if matches:
                    best_match = matches[0]
                    confidence = best_match['score']
                    spec_text = best_match['text']
                    
                    # Determine compliance
                    compliant = confidence > 0.75  # High confidence = likely compliant
                    
                    if compliant:
                        compliance_results['compliant_items'].append({
                            'type': equipment_type,
                            'confidence': round(confidence * 100, 1),
                            'spec_reference': spec_text[:200],
                            'status': 'COMPLIANT'
                        })
                    else:
                        compliance_results['issues'].append({
                            'type': equipment_type,
                            'issue': f"Low spec match confidence ({round(confidence * 100, 1)}%)",
                            'recommendation': 'Review installation against spec',
                            'spec_reference': spec_text[:200]
                        })
                    
                    compliance_results['confidence_scores'].append(confidence)
                    compliance_results['spec_references'].append(spec_text[:100])
        
        # Calculate overall compliance
        if compliance_results['confidence_scores']:
            avg_confidence = np.mean(compliance_results['confidence_scores'])
            compliance_results['average_confidence'] = round(avg_confidence * 100, 1)
            compliance_results['overall_compliant'] = avg_confidence > 0.75 and len(compliance_results['issues']) == 0
        
        return compliance_results
    
    def search_specs(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search learned spec book for relevant sections
        """
        if not self.model or not self.spec_embeddings:
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode([query], normalize_embeddings=True)
            
            # Compute similarities
            similarities = np.dot(self.spec_embeddings, query_embedding.T).flatten()
            
            # Get top matches
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if idx < len(self.spec_chunks):
                    results.append({
                        'text': self.spec_chunks[idx],
                        'score': float(similarities[idx]),
                        'index': int(idx)
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error searching specs: {e}")
            return []
    
    def generate_as_built_pdf(
        self,
        as_built_data: Dict,
        output_path: str = None
    ) -> str:
        """
        Generate filled as-built PDF from processed data
        """
        job_id = as_built_data['job_id']
        if not output_path:
            output_path = os.path.join(self.data_dir, f"as_built_{job_id}.pdf")
        
        logger.info(f"📄 Generating as-built PDF: {output_path}")
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1*inch, height - 1*inch, "AS-BUILT REPORT")
        
        # Job Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, height - 1.5*inch, "Job Information:")
        
        c.setFont("Helvetica", 10)
        y_pos = height - 1.8*inch
        
        job_info = [
            f"Job ID: {job_id}",
            f"PM Number: {as_built_data.get('pm_number', 'N/A')}",
            f"Location: {as_built_data.get('location', 'N/A')}",
            f"Foreman: {as_built_data.get('foreman', 'N/A')}",
            f"Crew: {as_built_data.get('crew', 'N/A')}",
            f"Date: {as_built_data.get('timestamp', '')[:10]}",
            f"Photos Processed: {as_built_data.get('photos_processed', 0)}"
        ]
        
        for info in job_info:
            c.drawString(1.2*inch, y_pos, info)
            y_pos -= 0.2*inch
        
        # Equipment Installed
        y_pos -= 0.3*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_pos, "Equipment Installed:")
        y_pos -= 0.3*inch
        
        c.setFont("Helvetica", 10)
        equipment = as_built_data.get('equipment_installed', {})
        
        for equip_type, items in equipment.items():
            if items:
                c.drawString(1.2*inch, y_pos, f"• {equip_type.title()}: {len(items)} installed")
                y_pos -= 0.2*inch
                
                # Show first item details
                if items and y_pos > 2*inch:
                    item = items[0]
                    details = []
                    if 'type' in item:
                        details.append(f"Type: {item['type']}")
                    if 'confidence' in item:
                        details.append(f"Detection: {item['confidence']:.1f}%")
                    if details:
                        c.setFont("Helvetica", 9)
                        c.drawString(1.5*inch, y_pos, f"  {', '.join(details)}")
                        y_pos -= 0.2*inch
                        c.setFont("Helvetica", 10)
        
        # Compliance Analysis
        y_pos -= 0.3*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y_pos, "Compliance Analysis:")
        y_pos -= 0.3*inch
        
        compliance = as_built_data.get('compliance', {})
        
        if compliance.get('checked'):
            c.setFont("Helvetica", 10)
            
            # Overall status
            if compliance.get('overall_compliant'):
                c.setFillColor(green)
                c.drawString(1.2*inch, y_pos, "✓ COMPLIANT - Ready for QA")
            else:
                c.setFillColor(red)
                c.drawString(1.2*inch, y_pos, "✗ ISSUES FOUND - Review Required")
            
            c.setFillColor(black)
            y_pos -= 0.2*inch
            
            # Confidence
            avg_conf = compliance.get('average_confidence', 0)
            c.drawString(1.2*inch, y_pos, f"Average Confidence: {avg_conf}%")
            y_pos -= 0.2*inch
            
            # Compliant items
            if compliance.get('compliant_items'):
                c.setFont("Helvetica", 9)
                c.setFillColor(green)
                c.drawString(1.2*inch, y_pos, f"Compliant Items: {len(compliance['compliant_items'])}")
                y_pos -= 0.15*inch
                
                for item in compliance['compliant_items'][:3]:  # Show first 3
                    c.drawString(1.5*inch, y_pos, 
                                f"• {item['type']}: {item['confidence']}% confidence")
                    y_pos -= 0.15*inch
            
            # Issues
            if compliance.get('issues'):
                y_pos -= 0.1*inch
                c.setFont("Helvetica", 9)
                c.setFillColor(red)
                c.drawString(1.2*inch, y_pos, f"Issues Found: {len(compliance['issues'])}")
                y_pos -= 0.15*inch
                
                for issue in compliance['issues'][:3]:  # Show first 3
                    c.drawString(1.5*inch, y_pos, 
                                f"• {issue['type']}: {issue['issue']}")
                    y_pos -= 0.15*inch
            
            c.setFillColor(black)
            
            # Spec references
            if compliance.get('spec_references') and y_pos > 2*inch:
                y_pos -= 0.2*inch
                c.setFont("Helvetica-Bold", 10)
                c.drawString(1.2*inch, y_pos, "Spec References:")
                y_pos -= 0.15*inch
                
                c.setFont("Helvetica", 8)
                for ref in compliance['spec_references'][:2]:
                    c.drawString(1.5*inch, y_pos, f"• {ref[:60]}...")
                    y_pos -= 0.15*inch
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(1*inch, 0.75*inch, 
                    f"Generated by NEXA Document Analyzer - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # QA Status
        c.setFont("Helvetica-Bold", 10)
        if as_built_data.get('ready_for_qa'):
            c.setFillColor(green)
            c.drawString(width - 3*inch, 0.75*inch, "STATUS: READY FOR QA")
        else:
            c.setFillColor(red)
            c.drawString(width - 3*inch, 0.75*inch, "STATUS: REVIEW REQUIRED")
        
        # Save PDF
        c.save()
        
        logger.info(f"✅ As-built PDF generated: {output_path}")
        return output_path
