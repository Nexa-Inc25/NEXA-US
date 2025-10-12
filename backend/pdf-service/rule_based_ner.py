#!/usr/bin/env python3
"""
Rule-based NER for PG&E utility documents
More reliable than ML with limited training data
"""

import re
from typing import List, Dict

class RuleBasedNER:
    """Extract entities using domain-specific rules"""
    
    def __init__(self):
        # Define patterns for each entity type
        self.patterns = {
            "MEASURE": [
                r'\b\d+\.?\d*\s*(kV|V|volts?|feet|ft|inches?|in|meters?|m|mm|cm)\b',
                r'\b\d+\.?\d*\s*(amps?|A|ohms?|Ω|watts?|W|kW|MW)\b',
                r'\b\d+[-/]\d+\b',  # Ratios like 4/0
            ],
            "EQUIPMENT": [
                r'\b(pole|insulator|conductor|crossarm|damper|guard|wire|cable|conduit|transformer|switch|fuse|breaker|meter)\b',
                r'\b(ACSR|AAC|MCM|PVC|steel|copper|aluminum|wood|concrete)\b',
                r'\b(FuseSaver|deadend|guy|bracket|clamp|connector)\b',
            ],
            "STANDARD": [
                r'\b(G\.?O\.?\s*95|GO\s*95|General\s+Order\s+95)\b',
                r'\b(CPUC|PUC|ANSI|IEEE|NEC|NESC|RUS)\b',
                r'\b(Document|Doc\.?|Bulletin|Standard|Spec\.?)\s*[A-Z0-9-]+\b',
                r'\b(Rule|Section|Article|Part)\s*[\d\.]+\b',
            ],
            "LOCATION": [
                r'\b(underground|overhead|aerial|pole\s+top|street|highway|road|crossing)\b',
                r'\b(Zone\s+\d+|Area\s+\w+|high-fire\s+area)\b',
                r'\b(trench|vault|manhole|pad|foundation)\b',
            ],
            "ACTION": [
                r'\b(install|replace|mount|apply|perform|remove|inspect|test|verify)\b',
                r'\b(required|shall|must|should|need)\b',
            ],
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for entity_type, patterns in self.patterns.items():
            combined = '|'.join(f'({p})' for p in patterns)
            self.compiled_patterns[entity_type] = re.compile(combined, re.IGNORECASE)
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract entities from text"""
        entities = []
        
        # Track what's already been tagged to avoid overlaps
        tagged_positions = set()
        
        # Extract entities by type (order matters for priority)
        for entity_type in ["STANDARD", "MEASURE", "EQUIPMENT", "LOCATION", "ACTION"]:
            pattern = self.compiled_patterns[entity_type]
            
            for match in pattern.finditer(text):
                start, end = match.span()
                
                # Check if this position is already tagged
                if any(pos in tagged_positions for pos in range(start, end)):
                    continue
                
                # Add entity
                entities.append({
                    "entity_group": entity_type,
                    "word": match.group(),
                    "start": start,
                    "end": end,
                    "score": 0.95  # High confidence for rule-based
                })
                
                # Mark positions as tagged
                for pos in range(start, end):
                    tagged_positions.add(pos)
        
        # Sort by position
        entities.sort(key=lambda x: x["start"])
        
        return entities
    
    def analyze_infraction(self, text: str) -> Dict:
        """Analyze an infraction for repealability"""
        entities = self.extract_entities(text)
        
        # Look for key indicators
        has_standard = any(e["entity_group"] == "STANDARD" for e in entities)
        has_measure = any(e["entity_group"] == "MEASURE" for e in entities)
        has_equipment = any(e["entity_group"] == "EQUIPMENT" for e in entities)
        
        # Calculate confidence
        confidence = 0
        if has_standard:
            confidence += 40  # Standards are strong indicators
        if has_measure:
            confidence += 30  # Specific measurements help
        if has_equipment:
            confidence += 20  # Equipment context helps
        
        # Determine repealability
        if has_standard and has_measure:
            repealable = True
            reason = "Specific standard and measurement cited"
        elif has_standard:
            repealable = True
            reason = "Standard requirement cited"
        else:
            repealable = False
            reason = "No clear standard violation"
        
        return {
            "repealable": repealable,
            "confidence": min(confidence, 95),
            "reason": reason,
            "entities": entities,
            "key_evidence": {
                "standards": [e["word"] for e in entities if e["entity_group"] == "STANDARD"],
                "measures": [e["word"] for e in entities if e["entity_group"] == "MEASURE"],
                "equipment": [e["word"] for e in entities if e["entity_group"] == "EQUIPMENT"],
            }
        }


def test_rule_based_ner():
    """Test the rule-based NER"""
    ner = RuleBasedNER()
    
    test_cases = [
        "Install 12kV deadend insulator at pole top with minimum clearance of 8 feet",
        "Replace existing 4/0 ACSR conductor with 336.4 MCM AAC per GO 95 Rule 31.2",
        "Trench depth shall be 48 inches for underground conduit per Document 093412",
        "Crossarm mounted at 20 inches from pole top violating G.O. 95",
    ]
    
    print("="*60)
    print("RULE-BASED NER TESTING")
    print("="*60)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {text}")
        
        # Extract entities
        entities = ner.extract_entities(text)
        
        if entities:
            print("Entities found:")
            for entity in entities:
                print(f"  • {entity['entity_group']}: '{entity['word']}' ({entity['score']*100:.0f}% conf)")
        
        # Analyze for repealability
        analysis = ner.analyze_infraction(text)
        print(f"\nRepealability Analysis:")
        print(f"  Repealable: {analysis['repealable']}")
        print(f"  Confidence: {analysis['confidence']}%")
        print(f"  Reason: {analysis['reason']}")
        
        if analysis['key_evidence']['standards']:
            print(f"  Standards cited: {', '.join(analysis['key_evidence']['standards'])}")


if __name__ == "__main__":
    test_rule_based_ner()
