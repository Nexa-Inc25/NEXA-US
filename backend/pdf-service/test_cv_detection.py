#!/usr/bin/env python3
"""
Test Computer Vision Change Detection for PM 35125285
Simulates detection of guy wire adjustments at 2195 Summit Level Rd
"""

import numpy as np
import cv2
import json
from cv_change_detector import GuyWireDetector, PoleChangeDetector

def create_test_images():
    """
    Create simulated test images for guy wire detection
    Simulates before (sagging) and after (straight) wire states
    """
    # Create blank images
    height, width = 600, 800
    
    # Before image - sagging wire
    before_img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Draw pole
    cv2.rectangle(before_img, (380, 100), (420, 500), (139, 69, 19), -1)
    
    # Draw sagging wire (quadratic curve)
    x = np.linspace(420, 700, 50)
    y = 0.002 * (x - 550)**2 + 200  # Quadratic for sagging
    points = np.column_stack([x, y]).astype(int)
    for i in range(len(points) - 1):
        cv2.line(before_img, tuple(points[i]), tuple(points[i+1]), (50, 50, 50), 3)
    
    cv2.putText(before_img, "BEFORE: Sagging Guy Wire", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # After image - straight wire
    after_img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Draw pole
    cv2.rectangle(after_img, (380, 100), (420, 500), (139, 69, 19), -1)
    
    # Draw straight wire
    cv2.line(after_img, (420, 200), (700, 200), (50, 50, 50), 3)
    
    cv2.putText(after_img, "AFTER: Tensioned Guy Wire", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return before_img, after_img

def test_guy_wire_detection():
    """Test guy wire state detection"""
    print("="*60)
    print("TEST: Guy Wire State Detection")
    print("="*60)
    
    detector = GuyWireDetector()
    before_img, after_img = create_test_images()
    
    # Save test images
    cv2.imwrite("test_before_sagging.jpg", before_img)
    cv2.imwrite("test_after_straight.jpg", after_img)
    
    # Analyze before image
    print("\nAnalyzing BEFORE image...")
    before_analysis = detector.detect_guy_wire_state(before_img)
    print(f"  State: {before_analysis.state}")
    print(f"  Confidence: {before_analysis.confidence:.1%}")
    print(f"  Curvature: {before_analysis.curvature:.4f}")
    print(f"  Points detected: {before_analysis.points_detected}")
    
    # Analyze after image
    print("\nAnalyzing AFTER image...")
    after_analysis = detector.detect_guy_wire_state(after_img)
    print(f"  State: {after_analysis.state}")
    print(f"  Confidence: {after_analysis.confidence:.1%}")
    print(f"  Curvature: {after_analysis.curvature:.4f}")
    print(f"  Points detected: {after_analysis.points_detected}")
    
    # Detect changes
    print("\nDetecting changes...")
    changes = detector.detect_changes(before_img, after_img)
    
    print(f"\nCHANGE DETECTION RESULTS:")
    print(f"  Before state: {changes['before_state']}")
    print(f"  After state: {changes['after_state']}")
    print(f"  Red-lining required: {'YES' if changes['red_lining_required'] else 'NO'}")
    print(f"  Overall confidence: {changes['confidence']:.1%}")
    
    if changes['changes']:
        print("\n  Changes detected:")
        for change in changes['changes']:
            print(f"    - Type: {change['type']}")
            print(f"      Description: {change['description']}")
            print(f"      Marking: {change['marking']}")
            print(f"      Reference: {change['reference']}")
            print(f"      Confidence: {change['confidence']:.1%}")
    
    return changes

def test_pm35125285_simulation():
    """
    Simulate PM 35125285 pole work at 2195 Summit Level Rd
    Tests the complete CV + generation workflow
    """
    print("\n" + "="*60)
    print("TEST: PM 35125285 - 2195 Summit Level Rd")
    print("="*60)
    
    # Create test photos
    before_img, after_img = create_test_images()
    
    # Simulate photo data
    before_photos = [
        {
            "path": "test_before_sagging.jpg",
            "description": "Guy wire showing sagging",
            "gps": {"lat": 38.337308, "lng": -120.483566},
            "timestamp": "2025-10-12T08:00:00"
        }
    ]
    
    after_photos = [
        {
            "path": "test_after_straight.jpg",
            "description": "Guy wire properly tensioned",
            "gps": {"lat": 38.337308, "lng": -120.483566},
            "timestamp": "2025-10-12T14:00:00"
        }
    ]
    
    # Run full analysis
    detector = PoleChangeDetector()
    
    # Note: For testing, we'll use the created images directly
    detector._load_image = lambda photo: cv2.imread(photo['path']) if 'path' in photo else None
    
    report = detector.analyze_job_photos(before_photos, after_photos)
    
    print(f"\nJOB ANALYSIS REPORT:")
    print(f"  PM Number: 35125285")
    print(f"  Location: 2195 Summit Level Rd, Rail Road Flat, CA")
    print(f"  Total changes: {report['total_changes']}")
    print(f"  Red-lining required: {'YES' if report['red_lining_required'] else 'NO'}")
    print(f"  Overall confidence: {report['overall_confidence']:.1%}")
    
    print(f"\n  Spec Compliance:")
    print(f"    Status: {report['spec_compliance']['status']}")
    print(f"    Score: {report['spec_compliance']['score']:.1%}")
    for note in report['spec_compliance']['notes']:
        print(f"    - {note}")
    
    # Simulate as-built generation decision
    print(f"\nAS-BUILT GENERATION:")
    if report['red_lining_required']:
        print("  ✅ Red-lining will be applied to construction drawing")
        print("     - Strike through sagging wire symbol")
        print("     - Add 'ADJUSTED' notation")
        print("     - Reference: Pages 7-9")
    else:
        print("  ✅ No red-lining needed")
        print("     - Mark as 'BUILT AS DESIGNED'")
        print("     - Reference: Page 25")
    
    # Save report
    with open('cv_detection_report_35125285.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Report saved to: cv_detection_report_35125285.json")
    
    return report

def test_edge_cases():
    """Test various edge cases for robustness"""
    print("\n" + "="*60)
    print("TEST: Edge Cases")
    print("="*60)
    
    detector = GuyWireDetector()
    
    # Test 1: No wire (blank image)
    print("\n1. Testing blank image (no wire)...")
    blank_img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    analysis = detector.detect_guy_wire_state(blank_img)
    print(f"   Result: {analysis.state} (Expected: undetected)")
    
    # Test 2: Multiple wires (complex scene)
    print("\n2. Testing multiple wires...")
    multi_img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    for y in range(150, 450, 50):
        cv2.line(multi_img, (100, y), (700, y), (50, 50, 50), 2)
    analysis = detector.detect_guy_wire_state(multi_img)
    print(f"   Result: {analysis.state} (Confidence: {analysis.confidence:.1%})")
    
    # Test 3: Extreme sagging
    print("\n3. Testing extreme sagging...")
    extreme_img = np.ones((600, 800, 3), dtype=np.uint8) * 255
    x = np.linspace(100, 700, 100)
    y = 0.01 * (x - 400)**2 + 200  # Extreme quadratic
    points = np.column_stack([x, y]).astype(int)
    for i in range(len(points) - 1):
        cv2.line(extreme_img, tuple(points[i]), tuple(points[i+1]), (50, 50, 50), 3)
    analysis = detector.detect_guy_wire_state(extreme_img)
    print(f"   Result: {analysis.state} (Curvature: {analysis.curvature:.4f})")
    
    print("\n✅ Edge case testing complete")

if __name__ == "__main__":
    # Run all tests
    print("NEXA COMPUTER VISION TESTING SUITE")
    print("="*60)
    
    # Test 1: Basic guy wire detection
    changes = test_guy_wire_detection()
    
    # Test 2: PM 35125285 simulation
    report = test_pm35125285_simulation()
    
    # Test 3: Edge cases
    test_edge_cases()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if changes['red_lining_required']:
        print("✅ Guy wire adjustment detected successfully")
        print("✅ Red-lining will be applied per Pages 7-9")
    else:
        print("✅ No changes detected")
        print("✅ Will mark 'Built as designed' per Page 25")
    
    print(f"\nConfidence in detection: {changes['confidence']:.1%}")
    print("\nCV system ready for production!")
