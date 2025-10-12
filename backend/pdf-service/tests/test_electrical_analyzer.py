#!/usr/bin/env python3
"""
Test script for Electrical Spec Analyzer
Tests without requiring PDFs
"""

print("Testing Electrical Spec Analyzer...")
print("="*60)

# Test imports
try:
    from transformers import pipeline
    print("✅ Transformers imported")
except ImportError as e:
    print(f"❌ Error importing transformers: {e}")
    
try:
    import fitz
    print("✅ PyMuPDF imported")
except ImportError as e:
    print(f"❌ Error importing PyMuPDF: {e}")

# Test loading the electrical NER model
print("\n" + "="*60)
print("Loading Electrical NER Model...")
print("="*60)

try:
    # First try the electrical model
    print("Attempting to load disham993/electrical-ner-ModernBERT-base...")
    ner = pipeline(
        "ner",
        model="disham993/electrical-ner-ModernBERT-base",
        aggregation_strategy="simple",
        device=-1  # CPU
    )
    print("✅ Electrical NER model loaded successfully!")
    model_loaded = "electrical"
except Exception as e:
    print(f"⚠️ Could not load electrical model: {e}")
    print("Falling back to general BERT NER model...")
    try:
        ner = pipeline(
            "ner",
            model="dslim/bert-base-NER",
            aggregation_strategy="simple",
            device=-1
        )
        print("✅ General BERT NER model loaded")
        model_loaded = "general"
    except Exception as e:
        print(f"❌ Failed to load any model: {e}")
        model_loaded = None

# Test entity extraction
if model_loaded:
    print("\n" + "="*60)
    print("Testing Entity Extraction")
    print("="*60)
    
    test_cases = [
        "Install 12kV deadend insulator at pole top with 8 feet clearance per GO 95",
        "Replace 4/0 ACSR conductor with 336.4 MCM AAC per CPUC requirements",
        "Underground conduit at 48 inches depth violating Rule 31.2",
        "Crossarm mounted at 20 inches from pole top",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {text}")
        print("-" * 40)
        
        try:
            entities = ner(text)
            
            if entities:
                print("Entities found:")
                # Group by type
                by_type = {}
                for ent in entities:
                    entity_type = ent.get('entity_group', 'UNKNOWN')
                    if entity_type not in by_type:
                        by_type[entity_type] = []
                    by_type[entity_type].append({
                        'word': ent['word'],
                        'score': ent.get('score', 0)
                    })
                
                for entity_type, items in by_type.items():
                    print(f"\n  {entity_type}:")
                    for item in items:
                        print(f"    • '{item['word']}' (confidence: {item['score']:.1%})")
            else:
                print("  No entities found")
                
        except Exception as e:
            print(f"  Error: {e}")

    # Test repealability logic
    print("\n" + "="*60)
    print("Testing Repealability Analysis")
    print("="*60)
    
    # Simulate finding standards in text
    import re
    
    infraction = "Crossarm at 20 inches violating GO 95 clearance requirements"
    print(f"\nInfraction: {infraction}")
    
    # Check for utility keywords
    utility_patterns = {
        'standards': ['GO 95', 'GO 128', 'CPUC', 'ANSI', 'IEEE', 'Rule \\d+'],
        'equipment': ['pole', 'insulator', 'conductor', 'crossarm', 'wire'],
        'measures': ['\\d+\\s*kV', '\\d+\\s*feet', '\\d+\\s*inches', 'clearance']
    }
    
    found_keywords = {}
    for category, patterns in utility_patterns.items():
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, infraction, re.IGNORECASE)
            matches.extend(found)
        if matches:
            found_keywords[category] = matches
    
    print(f"\nUtility keywords found: {found_keywords}")
    
    # Determine repealability
    if 'standards' in found_keywords:
        print(f"✅ REPEALABLE: References standard(s) {found_keywords['standards']}")
        print(f"   Confidence: 85-90% (standard cited)")
    elif 'equipment' in found_keywords and 'measures' in found_keywords:
        print(f"⚠️ POTENTIALLY REPEALABLE: Equipment and measures found")
        print(f"   Confidence: 75-80% (needs spec cross-reference)")
    else:
        print(f"❌ NOT REPEALABLE: No clear standard violations")
        print(f"   Confidence: 70% (default)")

print("\n" + "="*60)
print("Test Complete!")
print("="*60)
print("\nNext steps:")
print("1. Save the electrical_spec_analyzer.py code")
print("2. Create FastAPI endpoints for PDF upload")
print("3. Test with real PDF files")
print("4. Deploy to Render.com")
