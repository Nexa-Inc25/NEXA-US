"""
Test Enhanced NER Model (F1>0.9) with Real Job Package Examples
"""

import os
import json
from pathlib import Path
from transformers import pipeline
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_ner():
    """Test the enhanced NER model with real utility job package text"""
    
    # Use Windows-compatible path
    model_path = "./fine_tuned_ner_deep"
    
    # Check if model exists
    if not Path(model_path).exists():
        # Try alternate locations
        alt_paths = [
            "./data/fine_tuned_ner_deep",
            "../fine_tuned_ner_deep",
            r"C:\Users\mikev\CascadeProjects\nexa-inc-mvp\backend\pdf-service\fine_tuned_ner_deep"
        ]
        
        for alt_path in alt_paths:
            if Path(alt_path).exists():
                model_path = alt_path
                logger.info(f"Found model at: {model_path}")
                break
        else:
            logger.error(f"❌ Model not found at {model_path} or alternate locations")
            logger.error("Please run train_ner_enhanced.bat first")
            return
    
    logger.info("=" * 60)
    logger.info("TESTING ENHANCED NER MODEL (F1>0.9 Target)")
    logger.info("=" * 60)
    
    # Load the NER pipeline
    logger.info(f"\n📁 Loading model from: {model_path}")
    ner_pipeline = pipeline(
        "ner",
        model=model_path,
        tokenizer=model_path,
        aggregation_strategy="simple"
    )
    
    # Real job package test cases
    test_cases = [
        {
            "text": "Install 12kV deadend insulator at pole top with minimum clearance of 8 feet",
            "expected": ["INSTALLATION", "MATERIAL", "LOCATION", "MEASURE"]
        },
        {
            "text": "Replace existing 4/0 ACSR conductor with 336.4 MCM AAC per GO 95 Rule 31.2",
            "expected": ["INSTALLATION", "MATERIAL", "MEASURE", "STANDARD"]
        },
        {
            "text": "Trench depth shall be 48 inches for underground conduit per Document 093412",
            "expected": ["LOCATION", "MEASURE", "EQUIPMENT", "SPECIFICATION"]
        },
        {
            "text": "Mount FuseSaver device on 8-foot crossarm with single-phase tap requirement",
            "expected": ["INSTALLATION", "EQUIPMENT", "MEASURE", "SPECIFICATION"]
        },
        {
            "text": "Apply fireproof coating to all exposed steel members in Zone 4 high-fire area",
            "expected": ["INSTALLATION", "MATERIAL", "ZONE", "LOCATION"]
        },
        {
            "text": "Install bird guard protection on all energized equipment above 15kV per ANSI C37.60",
            "expected": ["INSTALLATION", "EQUIPMENT", "MEASURE", "STANDARD"]
        },
        {
            "text": "Grade B construction required for crossings over highways per CPUC General Order 95",
            "expected": ["GRADE", "LOCATION", "STANDARD"]
        },
        {
            "text": "Perform Megger test at 5000V for cable insulation before energization",
            "expected": ["TEST", "MEASURE", "EQUIPMENT"]
        }
    ]
    
    # Test each case
    logger.info("\n" + "=" * 60)
    logger.info("INFERENCE RESULTS")
    logger.info("=" * 60)
    
    correct_predictions = 0
    total_expected = 0
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n📝 Test Case {i}:")
        logger.info(f"Text: \"{test_case['text']}\"")
        logger.info(f"\nExpected entity types: {', '.join(test_case['expected'])}")
        
        # Run NER
        entities = ner_pipeline(test_case['text'])
        
        # Extract unique entity types found
        found_types = list(set([e['entity_group'] for e in entities]))
        
        logger.info(f"Found entity types: {', '.join(found_types) if found_types else 'None'}")
        
        # Show detailed entities
        if entities:
            logger.info("\nDetailed entities:")
            for entity in entities:
                conf = entity['score'] * 100
                logger.info(f"  • {entity['entity_group']}: '{entity['word']}' ({conf:.1f}% conf)")
        
        # Check accuracy
        for expected in test_case['expected']:
            total_expected += 1
            if expected in found_types:
                correct_predictions += 1
                logger.info(f"  ✅ {expected} found")
            else:
                logger.info(f"  ❌ {expected} missing")
    
    # Calculate overall accuracy
    accuracy = (correct_predictions / total_expected) * 100 if total_expected > 0 else 0
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Entity Detection Accuracy: {accuracy:.1f}%")
    logger.info(f"Correct: {correct_predictions}/{total_expected}")
    
    if accuracy >= 90:
        logger.info("\n✅ EXCELLENT! Model ready for production (>90% accuracy)")
    elif accuracy >= 80:
        logger.info("\n⚠️ Good performance but could be better (80-90% accuracy)")
    else:
        logger.info("\n❌ Needs improvement (<80% accuracy)")
    
    # Test on go-back analysis examples
    logger.info("\n" + "=" * 60)
    logger.info("GO-BACK ANALYSIS TEST")
    logger.info("=" * 60)
    
    go_back_examples = [
        "Crossarm mounted at 20 inches from pole top violating G.O. 95",
        "Underground conduit depth of 18 inches per Document 093412", 
        "FuseSaver installation without single-phase tap requirement",
        "Clearance over street only 16 feet - requires 18 feet minimum"
    ]
    
    for example in go_back_examples:
        logger.info(f"\n🔍 Go-back text: \"{example}\"")
        entities = ner_pipeline(example)
        
        if entities:
            for entity in entities:
                conf = entity['score'] * 100
                if conf > 85:  # High confidence entities
                    logger.info(f"  🎯 {entity['entity_group']}: '{entity['word']}' ({conf:.0f}% - REPEALABLE)")
                else:
                    logger.info(f"  ⚠️ {entity['entity_group']}: '{entity['word']}' ({conf:.0f}% - REVIEW)")
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    test_enhanced_ner()
