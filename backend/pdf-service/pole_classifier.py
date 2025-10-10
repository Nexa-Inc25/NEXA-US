"""
PG&E Pole Type Classification System
Classifies poles based on levels, equipment, and accessibility
Enhanced with YOLOv8 computer vision detection
"""
import re
import json
from typing import Dict, List, Tuple, Optional
from PIL import Image
import pytesseract
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pole_vision_detector import PoleVisionDetector
import logging

logger = logging.getLogger(__name__)

class PoleClassifier:
    """Classify poles according to PG&E types 1-5"""
    
    def __init__(self, model_name='all-MiniLM-L6-v2', use_vision=True):
        self.model = SentenceTransformer(model_name)
        self.pole_types = self.load_pole_types()
        self.examples = self.load_examples()
        self.pricing_multipliers = self.load_pricing_multipliers()
        self.use_vision = use_vision
        
        # Initialize vision detector if enabled
        if use_vision:
            try:
                self.vision_detector = PoleVisionDetector()
                logger.info("Vision detector initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize vision detector: {e}")
                self.use_vision = False
                self.vision_detector = None
        else:
            self.vision_detector = None
        
    def load_pole_types(self) -> Dict:
        """Load pole type definitions from PG&E spec"""
        return {
            'Type 1': {
                'name': 'Easy',
                'description': '1 Primary level no equipment; Service poles',
                'levels': 1,
                'equipment': [],
                'difficulty': 'Easy',
                'code': 1
            },
            'Type 2': {
                'name': 'Moderate',
                'description': '2 levels; Type 2 equipment (cutouts, switches, fixed caps, 1-phase transformer)',
                'levels': 2,
                'equipment': ['cutouts', 'switches', 'fixed caps', '1-phase transformer'],
                'difficulty': 'Moderate',
                'code': 2
            },
            'Type 3': {
                'name': 'Medium',
                'description': '3 levels; Type 3 equipment (reclosers, regulators, boosters, sectionalizers, switched caps, 3-phase transformer banks)',
                'levels': 3,
                'equipment': ['reclosers', 'regulators', 'boosters', 'sectionalizers', 'switched caps', '3-phase transformer', 'transformer banks'],
                'difficulty': 'Medium',
                'code': 3
            },
            'Type 4': {
                'name': 'Difficult',
                'description': '4 levels; 3 levels + Type 2/3 equipment',
                'levels': 4,
                'equipment': ['Type 2 equipment', 'Type 3 equipment'],
                'difficulty': 'Difficult',
                'code': 4
            },
            'Type 5': {
                'name': 'Bid/NTE',
                'description': 'More than 4 levels; Out of ordinary/difficult',
                'levels': 5,
                'equipment': ['special', 'complex'],
                'difficulty': 'Bid/NTE',
                'code': 5
            }
        }
    
    def load_examples(self) -> Dict:
        """Load pole type examples from PG&E spec pages 2-4"""
        return {
            'Type 2': [
                'Primary (1) + buck (2)',
                'Primary (1) + secondary (2)',
                'Primary arm (1) + 1-phase transformer (2)',
                'Service pole with primary and secondary',
                'Two-level configuration with cutouts'
            ],
            'Type 3': [
                'Line/buck + transformer bank',
                'Line/buck + secondary',
                'Primary riser',
                'Poles with reclosers',
                'Three-level with regulators',
                'Main line, buck arm, transformer',
                'Poles with switched capacitors'
            ],
            'Type 4': [
                'Primary (1)/buck (2)/transformer (3)/secondary (4)',
                'Two circuits line/buck each',
                'Four-level configuration',
                'Complex multi-circuit setup',
                'Three levels plus Type 3 equipment'
            ],
            'Type 5': [
                'More than 4 levels',
                'Special accessibility issues',
                'Out of ordinary configuration',
                'Difficult terrain or access',
                'Complex equipment combinations',
                'Requires bid or NTE T&E'
            ]
        }
    
    def load_pricing_multipliers(self) -> Dict:
        """Load pricing multipliers for each pole type"""
        return {
            1: 1.0,   # Type 1: Base cost
            2: 1.2,   # Type 2: 20% more
            3: 1.5,   # Type 3: 50% more
            4: 2.0,   # Type 4: Double
            5: 'NTE'  # Type 5: Not-to-exceed/Bid required
        }
    
    def extract_pole_features(self, text: str, photos: Optional[List[str]] = None) -> Dict:
        """Extract pole features from text and photos"""
        features = {
            'levels': 0,
            'equipment': [],
            'description': text,
            'photo_text': '',
            'keywords': []
        }
        
        # Extract levels from text
        level_patterns = [
            r'(\d+)\s*level',
            r'(\d+)\s*primary',
            r'level\s*(\d+)',
            r'primary.*secondary.*tertiary.*quaternary'  # Count words
        ]
        
        for pattern in level_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    features['levels'] = max(int(m) if m.isdigit() else 4 for m in matches)
                except:
                    pass
        
        # Count level indicators
        if features['levels'] == 0:
            level_words = ['primary', 'secondary', 'buck', 'tertiary', 'quaternary']
            level_count = sum(1 for word in level_words if word in text.lower())
            features['levels'] = max(1, level_count)
        
        # Extract equipment mentions
        equipment_keywords = [
            'transformer', 'xfmr', 'cutout', 'switch', 'capacitor', 'cap',
            'recloser', 'regulator', 'booster', 'sectionalizer',
            'riser', 'bank', '3-phase', '1-phase', 'single-phase', 'three-phase'
        ]
        
        for keyword in equipment_keywords:
            if keyword in text.lower():
                features['equipment'].append(keyword)
        
        # Extract keywords for classification
        features['keywords'] = re.findall(r'\b[A-Za-z]+\b', text.lower())
        
        # Process photos if provided
        if photos:
            features['photo_text'] = self.extract_text_from_photos(photos)
            # Add photo text to description for classification
            features['description'] += ' ' + features['photo_text']
        
        return features
    
    def extract_text_from_photos(self, photo_paths: List[str]) -> str:
        """Extract text from photos using OCR"""
        extracted_text = []
        
        for path in photo_paths:
            try:
                # Open image
                image = Image.open(path)
                
                # Run OCR
                text = pytesseract.image_to_string(image)
                
                # Clean text
                text = ' '.join(text.split())
                
                if text:
                    extracted_text.append(text)
                    logger.info(f"Extracted text from {path}: {text[:100]}...")
                    
            except Exception as e:
                logger.error(f"Error processing photo {path}: {e}")
                
        return ' '.join(extracted_text)
    
    def classify_pole(self, text: str, photos: Optional[List[str]] = None) -> Tuple[int, float, str]:
        """
        Classify pole type based on text description and photos
        Uses computer vision if available and photos provided
        
        Returns:
            Tuple of (pole_type: int, confidence: float, reason: str)
        """
        try:
            # Try vision-based classification first if available
            if self.use_vision and self.vision_detector and photos:
                logger.info("Using vision detector for pole classification")
                
                vision_result = self.vision_detector.analyze_pole_images(photos)
                
                if vision_result and vision_result['confidence'] > 0.6:
                    pole_type = vision_result['pole_type']
                    confidence = vision_result['confidence']
                    
                    # Enhanced reason with component details
                    components_str = ", ".join([
                        f"{k}: {v}" for k, v in vision_result.get('components', {}).items()
                        if v > 0
                    ][:3])  # Top 3 components
                    
                    reason = f"Vision detection: {vision_result['reason']}. Components: {components_str}"
                    
                    logger.info(f"Vision classification: Type {pole_type} ({confidence:.2%})")
                    
                    # Verify with text if confidence is medium
                    if confidence < 0.8 and text:
                        text_features = self.extract_pole_features(text, None)
                        text_type = self.rule_based_classification(text_features)
                        
                        if text_type and abs(text_type - pole_type) <= 1:
                            # Text confirms vision (within 1 type)
                            confidence = min(0.95, confidence * 1.2)
                            reason += f" (confirmed by text analysis)"
                        elif text_type and abs(text_type - pole_type) > 1:
                            # Significant disagreement, average them
                            pole_type = (pole_type + text_type) // 2
                            confidence *= 0.8
                            reason += f" (adjusted from Type {vision_result['pole_type']} based on text)"
                    
                    return pole_type, confidence, reason
                else:
                    logger.info("Vision detection confidence too low, falling back to text analysis")
            
            # Extract features from text
            features = self.extract_pole_features(text, photos)
            
            # Rule-based classification
            pole_type = self.rule_based_classification(features)
            
            if pole_type:
                return pole_type, 0.85, f"Rule-based: {features['levels']} levels with {', '.join(features['equipment'][:3]) if features['equipment'] else 'no special equipment'}"
            
            # Fall back to semantic similarity
            pole_type, confidence, reason = self.similarity_classification(features['description'])
            
            return pole_type, confidence, reason
            
        except Exception as e:
            logger.error(f"Error classifying pole: {e}")
            return 3, 0.5, "Default to Type 3 (Medium) due to classification error"
    
    def rule_based_classification(self, features: Dict) -> Optional[int]:
        """Rule-based pole classification"""
        levels = features['levels']
        equipment = features['equipment']
        
        # Type 5: More than 4 levels or special keywords
        if levels > 4 or any(word in features['keywords'] for word in ['bid', 'nte', 'special', 'difficult']):
            return 5
        
        # Type 4: 4 levels or 3 levels with Type 3 equipment
        if levels == 4:
            return 4
        
        if levels == 3 and any(eq in equipment for eq in ['recloser', 'regulator', 'booster', 'sectionalizer', 'switched', '3-phase', 'bank']):
            return 4
        
        # Type 3: 3 levels or Type 3 equipment
        if levels == 3 or any(eq in equipment for eq in ['recloser', 'regulator', 'booster', 'sectionalizer', '3-phase', 'bank']):
            return 3
        
        # Type 2: 2 levels or Type 2 equipment
        if levels == 2 or any(eq in equipment for eq in ['cutout', 'switch', 'capacitor', '1-phase', 'transformer']):
            return 2
        
        # Type 1: 1 level, no equipment
        if levels == 1 and not equipment:
            return 1
        
        # No clear match
        return None
    
    def similarity_classification(self, description: str) -> Tuple[int, float, str]:
        """Classify using semantic similarity to examples"""
        # Prepare all examples
        all_examples = []
        type_labels = []
        
        for pole_type, examples in self.examples.items():
            for example in examples:
                all_examples.append(example)
                type_labels.append(int(pole_type.replace('Type ', '')))
        
        # Encode description and examples
        desc_embedding = self.model.encode(description, convert_to_tensor=True)
        example_embeddings = self.model.encode(all_examples, convert_to_tensor=True)
        
        # Calculate similarities
        similarities = util.cos_sim(desc_embedding, example_embeddings)[0]
        
        # Get top match
        best_idx = similarities.argmax().item()
        best_similarity = similarities[best_idx].item()
        best_type = type_labels[best_idx]
        best_example = all_examples[best_idx]
        
        # Convert similarity to confidence
        confidence = min(0.9, best_similarity)
        
        reason = f"Similar to: {best_example[:50]}... (confidence: {confidence:.2%})"
        
        return best_type, confidence, reason
    
    def get_pricing_multiplier(self, pole_type: int) -> float:
        """Get pricing multiplier for pole type"""
        return self.pricing_multipliers.get(pole_type, 1.0)
    
    def calculate_adjusted_price(self, base_price: float, pole_type: int) -> Tuple[float, str]:
        """
        Calculate adjusted price based on pole type
        
        Returns:
            Tuple of (adjusted_price: float, calculation: str)
        """
        multiplier = self.get_pricing_multiplier(pole_type)
        
        if multiplier == 'NTE':
            return 0.0, f"Type {pole_type}: Bid/NTE required - no automatic pricing"
        
        adjusted = base_price * multiplier
        calculation = f"${base_price:.2f} × {multiplier} (Type {pole_type}) = ${adjusted:.2f}"
        
        return adjusted, calculation
    
    def generate_pole_report(self, pole_type: int, confidence: float, 
                           features: Dict, pricing: Optional[Dict] = None) -> Dict:
        """Generate detailed pole classification report"""
        type_info = self.pole_types[f'Type {pole_type}']
        
        report = {
            'pole_type': pole_type,
            'type_name': type_info['name'],
            'description': type_info['description'],
            'confidence': round(confidence * 100, 1),
            'detected_levels': features.get('levels', 0),
            'detected_equipment': features.get('equipment', []),
            'difficulty': type_info['difficulty'],
            'pricing_multiplier': self.pricing_multipliers[pole_type]
        }
        
        if pricing:
            base_price = pricing.get('base_price', 0)
            adjusted, calc = self.calculate_adjusted_price(base_price, pole_type)
            report['pricing'] = {
                'base': base_price,
                'adjusted': adjusted,
                'calculation': calc
            }
        
        return report
    
    def save_classification(self, job_id: str, classification: Dict, data_path: str = '/data'):
        """Save pole classification to persistent storage"""
        try:
            # Load existing classifications
            classification_file = f'{data_path}/pole_classifications.json'
            try:
                with open(classification_file, 'r') as f:
                    classifications = json.load(f)
            except FileNotFoundError:
                classifications = {}
            
            # Add new classification
            classifications[job_id] = {
                **classification,
                'timestamp': str(np.datetime64('now'))
            }
            
            # Save back
            with open(classification_file, 'w') as f:
                json.dump(classifications, f, indent=2)
            
            logger.info(f"Saved pole classification for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error saving classification: {e}")
