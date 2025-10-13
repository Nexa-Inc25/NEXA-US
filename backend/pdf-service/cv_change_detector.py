#!/usr/bin/env python3
"""
NEXA Computer Vision Change Detector
Analyzes before/after photos to detect changes requiring red-lining
Specializes in guy wire sagging detection using curve fitting
"""

import cv2
import numpy as np
from scipy.optimize import curve_fit
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import json
import base64
from io import BytesIO
from PIL import Image

@dataclass
class WireAnalysis:
    """Analysis results for wire detection"""
    state: str  # "sagging", "straight", "undetected"
    confidence: float
    curvature: float
    points_detected: int
    rmse: float
    visual_evidence: Optional[str] = None  # Base64 encoded annotated image

class GuyWireDetector:
    """
    Computer Vision system for detecting guy wire changes
    Uses edge detection, Hough transforms, and curve fitting
    """
    
    def __init__(self):
        # Thresholds based on empirical testing
        self.SAGGING_THRESHOLD = 0.05  # Curvature coefficient threshold
        self.RMSE_THRESHOLD = 5.0  # Residual error threshold
        self.MIN_POINTS = 10  # Minimum points for reliable detection
        
        # PG&E spec references
        self.spec_rules = {
            "red_lining_required": "Pages 7-9: Red-line all changes",
            "no_changes": "Page 25: Mark 'Built as designed' if no changes",
            "guy_wire_adjustment": "Page 9: Strike through old, write 'adjusted'"
        }
    
    def detect_guy_wire_state(self, img: np.ndarray) -> WireAnalysis:
        """
        Detect if guy wire is sagging or straight
        Returns analysis with confidence score
        """
        try:
            # Pre-process image
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Line detection using Probabilistic Hough
            lines = cv2.HoughLinesP(
                edges, 
                rho=1, 
                theta=np.pi/180, 
                threshold=50,
                minLineLength=100, 
                maxLineGap=10
            )
            
            if lines is None or len(lines) < 2:
                return WireAnalysis(
                    state="undetected",
                    confidence=0.0,
                    curvature=0.0,
                    points_detected=0,
                    rmse=0.0
                )
            
            # Extract points from detected lines
            points = self._extract_wire_points(lines)
            
            if len(points) < self.MIN_POINTS:
                return WireAnalysis(
                    state="undetected",
                    confidence=0.3,
                    curvature=0.0,
                    points_detected=len(points),
                    rmse=0.0
                )
            
            # Fit curve and analyze sagging
            curvature, rmse, fitted_curve = self._fit_quadratic_curve(points)
            
            # Determine state based on curvature
            if abs(curvature) > self.SAGGING_THRESHOLD or rmse > self.RMSE_THRESHOLD:
                state = "sagging"
                # Higher curvature = more confident it's sagging
                confidence = min(0.95, 0.7 + abs(curvature) * 5)
            else:
                state = "straight"
                # Lower curvature = more confident it's straight
                confidence = max(0.85, 0.98 - rmse / 10)
            
            # Generate annotated image for evidence
            annotated_img = self._annotate_detection(img, points, fitted_curve, state)
            visual_evidence = self._image_to_base64(annotated_img)
            
            return WireAnalysis(
                state=state,
                confidence=confidence,
                curvature=abs(curvature),
                points_detected=len(points),
                rmse=rmse,
                visual_evidence=visual_evidence
            )
            
        except Exception as e:
            print(f"Error in wire detection: {e}")
            return WireAnalysis(
                state="undetected",
                confidence=0.0,
                curvature=0.0,
                points_detected=0,
                rmse=0.0
            )
    
    def _extract_wire_points(self, lines: np.ndarray) -> np.ndarray:
        """Extract unique points from detected line segments"""
        points = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            points.extend([(x1, y1), (x2, y2)])
        
        # Remove duplicates and sort by x-coordinate
        points = np.unique(np.array(points), axis=0)
        points = points[points[:, 0].argsort()]
        
        # Filter outliers using IQR method
        if len(points) > 10:
            q1 = np.percentile(points[:, 1], 25)
            q3 = np.percentile(points[:, 1], 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            points = points[(points[:, 1] >= lower_bound) & (points[:, 1] <= upper_bound)]
        
        return points
    
    def _fit_quadratic_curve(self, points: np.ndarray) -> Tuple[float, float, np.poly1d]:
        """
        Fit quadratic curve to points: y = ax^2 + bx + c
        Returns curvature coefficient, RMSE, and fitted curve
        """
        x, y = points[:, 0], points[:, 1]
        
        try:
            # Quadratic function for curve fitting
            def quad_func(x, a, b, c):
                return a * x**2 + b * x + c
            
            # Fit curve
            popt, pcov = curve_fit(quad_func, x, y)
            a, b, c = popt
            
            # Calculate residuals
            y_fitted = quad_func(x, *popt)
            residuals = y - y_fitted
            rmse = np.sqrt(np.mean(residuals**2))
            
            # Create polynomial for visualization
            fitted_curve = np.poly1d([a, b, c])
            
            return a, rmse, fitted_curve
            
        except Exception as e:
            print(f"Curve fitting failed: {e}")
            # Fallback to linear fit
            coeffs = np.polyfit(x, y, 1)
            fitted_curve = np.poly1d(coeffs)
            return 0.0, 0.0, fitted_curve
    
    def _annotate_detection(self, img: np.ndarray, points: np.ndarray, 
                           curve: np.poly1d, state: str) -> np.ndarray:
        """Annotate image with detection results"""
        annotated = img.copy()
        
        # Draw detected points
        for point in points:
            cv2.circle(annotated, tuple(point.astype(int)), 3, (0, 255, 0), -1)
        
        # Draw fitted curve
        if len(points) > 0:
            x_range = np.linspace(points[:, 0].min(), points[:, 0].max(), 100)
            y_curve = curve(x_range)
            curve_points = np.column_stack([x_range, y_curve]).astype(int)
            
            # Color based on state
            color = (0, 0, 255) if state == "sagging" else (0, 255, 0)
            for i in range(len(curve_points) - 1):
                cv2.line(annotated, tuple(curve_points[i]), tuple(curve_points[i+1]), color, 2)
        
        # Add text annotation
        cv2.putText(annotated, f"State: {state.upper()}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return annotated
    
    def _image_to_base64(self, img: np.ndarray) -> str:
        """Convert image to base64 string"""
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
    
    def detect_changes(self, before_img: np.ndarray, after_img: np.ndarray) -> Dict:
        """
        Compare before/after images to detect changes
        Returns change analysis for red-lining decision
        """
        before_analysis = self.detect_guy_wire_state(before_img)
        after_analysis = self.detect_guy_wire_state(after_img)
        
        changes = []
        red_lining_required = False
        confidence = min(before_analysis.confidence, after_analysis.confidence)
        
        # Detect guy wire adjustment
        if before_analysis.state == "sagging" and after_analysis.state == "straight":
            changes.append({
                "type": "guy_wire_adjustment",
                "description": "Guy wire adjusted from loose to clamped",
                "marking": "Strike through sagging symbol, write 'ADJUSTED'",
                "reference": self.spec_rules["guy_wire_adjustment"],
                "confidence": confidence
            })
            red_lining_required = True
        
        # Detect new sagging (potential issue)
        elif before_analysis.state == "straight" and after_analysis.state == "sagging":
            changes.append({
                "type": "guy_wire_loosened",
                "description": "WARNING: Guy wire appears looser after work",
                "marking": "Circle area, mark 'VERIFY TENSION'",
                "reference": "Potential safety issue - verify installation",
                "confidence": confidence
            })
            red_lining_required = True
        
        # No changes detected
        elif before_analysis.state == after_analysis.state:
            if before_analysis.state != "undetected":
                changes.append({
                    "type": "no_change",
                    "description": f"Guy wire remains {before_analysis.state}",
                    "marking": "No red-lining required",
                    "reference": self.spec_rules["no_changes"],
                    "confidence": confidence
                })
        
        return {
            "before_state": before_analysis.state,
            "after_state": after_analysis.state,
            "changes": changes,
            "red_lining_required": red_lining_required,
            "confidence": confidence,
            "visual_evidence": {
                "before": before_analysis.visual_evidence,
                "after": after_analysis.visual_evidence
            },
            "metrics": {
                "before_curvature": before_analysis.curvature,
                "after_curvature": after_analysis.curvature,
                "before_points": before_analysis.points_detected,
                "after_points": after_analysis.points_detected
            }
        }

class PoleChangeDetector:
    """
    Extended CV system for detecting various pole-related changes
    """
    
    def __init__(self):
        self.guy_wire_detector = GuyWireDetector()
        self.change_types = {
            "guy_wire": self.guy_wire_detector,
            # Future: Add more detectors
            # "crossarm": CrossarmDetector(),
            # "insulator": InsulatorDetector(),
            # "clearance": ClearanceDetector()
        }
    
    def analyze_job_photos(self, before_photos: List[Dict], after_photos: List[Dict]) -> Dict:
        """
        Comprehensive analysis of all job photos
        Returns complete change report for as-built generation
        """
        all_changes = []
        requires_red_lining = False
        overall_confidence = 1.0
        
        # Match before/after photo pairs
        for i, (before, after) in enumerate(zip(before_photos, after_photos)):
            # Load images (assuming file paths or URLs)
            before_img = self._load_image(before)
            after_img = self._load_image(after)
            
            if before_img is not None and after_img is not None:
                # Run change detection
                result = self.guy_wire_detector.detect_changes(before_img, after_img)
                
                if result['changes']:
                    for change in result['changes']:
                        change['photo_pair'] = i + 1
                        all_changes.append(change)
                    
                    if result['red_lining_required']:
                        requires_red_lining = True
                    
                    overall_confidence = min(overall_confidence, result['confidence'])
        
        # Compile final report
        report = {
            "total_changes": len([c for c in all_changes if c['type'] != 'no_change']),
            "red_lining_required": requires_red_lining,
            "overall_confidence": overall_confidence,
            "changes": all_changes,
            "spec_compliance": self._determine_spec_compliance(all_changes, requires_red_lining)
        }
        
        return report
    
    def _load_image(self, photo_data: Dict) -> Optional[np.ndarray]:
        """Load image from file path, URL, or base64"""
        try:
            if 'path' in photo_data:
                return cv2.imread(photo_data['path'])
            elif 'base64' in photo_data:
                img_data = base64.b64decode(photo_data['base64'])
                nparr = np.frombuffer(img_data, np.uint8)
                return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif 'url' in photo_data:
                # Would need to implement URL fetching
                pass
        except Exception as e:
            print(f"Error loading image: {e}")
        return None
    
    def _determine_spec_compliance(self, changes: List[Dict], red_lining: bool) -> Dict:
        """Determine PG&E spec compliance based on detected changes"""
        compliance = {
            "status": "COMPLIANT",
            "score": 1.0,
            "notes": []
        }
        
        if red_lining:
            compliance['notes'].append("Red-lining required per Pages 7-9 due to detected changes")
        else:
            compliance['notes'].append("No red-lining required - built as designed per Page 25")
        
        # Check for potential issues
        for change in changes:
            if change['type'] == 'guy_wire_loosened':
                compliance['status'] = "REVIEW REQUIRED"
                compliance['score'] = 0.7
                compliance['notes'].append("Guy wire appears looser - verify tension meets spec")
        
        return compliance

# Example usage function
def test_cv_detection():
    """Test the CV detection system with sample images"""
    detector = PoleChangeDetector()
    
    # Simulate before/after photos for PM 35125285
    before_photos = [
        {"path": "test_images/before_sagging_wire.jpg", "description": "Sagging guy wire"},
        {"path": "test_images/before_pole_view.jpg", "description": "Overall pole view"}
    ]
    
    after_photos = [
        {"path": "test_images/after_tight_wire.jpg", "description": "Adjusted guy wire"},
        {"path": "test_images/after_pole_view.jpg", "description": "Completed installation"}
    ]
    
    # Run analysis
    report = detector.analyze_job_photos(before_photos, after_photos)
    
    print("="*60)
    print("COMPUTER VISION CHANGE DETECTION REPORT")
    print("="*60)
    print(f"Total Changes Detected: {report['total_changes']}")
    print(f"Red-lining Required: {'YES' if report['red_lining_required'] else 'NO'}")
    print(f"Overall Confidence: {report['overall_confidence']:.1%}")
    print("\nChanges Detected:")
    for change in report['changes']:
        print(f"  - {change['description']} (Photo pair {change.get('photo_pair', 'N/A')})")
        print(f"    Action: {change['marking']}")
        print(f"    Reference: {change['reference']}")
    print("\nSpec Compliance:")
    print(f"  Status: {report['spec_compliance']['status']}")
    print(f"  Score: {report['spec_compliance']['score']:.1%}")
    for note in report['spec_compliance']['notes']:
        print(f"  - {note}")
    
    return report

if __name__ == "__main__":
    # Run test if executed directly
    test_cv_detection()
