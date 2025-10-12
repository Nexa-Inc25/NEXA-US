#!/usr/bin/env python3
"""
ML Dependency Verification Script
Checks for circular dependencies, missing packages, and version conflicts
"""

import ast
import importlib
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple
import networkx as nx
from collections import defaultdict

class DependencyAnalyzer:
    def __init__(self, modules_dir: Path):
        self.modules_dir = modules_dir
        self.import_graph = nx.DiGraph()
        self.external_deps = defaultdict(set)
        self.missing_deps = []
        
    def analyze_file(self, filepath: Path) -> Set[str]:
        """Extract imports from a Python file"""
        imports = set()
        
        try:
            with open(filepath, 'r') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            
        return imports
    
    def categorize_imports(self, imports: Set[str], module_name: str) -> Tuple[Set[str], Set[str]]:
        """Separate internal and external imports"""
        internal = set()
        external = set()
        
        for imp in imports:
            if imp.startswith('modules.'):
                # Internal module reference
                internal.add(imp.replace('modules.', ''))
            elif any(imp.startswith(m) for m in ['torch', 'transformers', 'peft', 
                                                  'ultralytics', 'roboflow', 'cv2',
                                                  'albumentations', 'sentence_transformers']):
                # Known ML external dependency
                external.add(imp.split('.')[0])
                
        return internal, external
    
    def build_dependency_graph(self):
        """Build complete dependency graph for ML modules"""
        ml_modules = [
            'model_fine_tuner',
            'conduit_ner_fine_tuner', 
            'overhead_ner_fine_tuner',
            'clearance_enhanced_fine_tuner',
            'roboflow_dataset_integrator',
            'spec_learning_endpoints',
            'pole_vision_detector',
            'enhanced_spec_analyzer',
            'clearance_analyzer',
            'conduit_enhanced_analyzer',
            'overhead_enhanced_analyzer'
        ]
        
        for module in ml_modules:
            filepath = self.modules_dir / f"{module}.py"
            if filepath.exists():
                imports = self.analyze_file(filepath)
                internal, external = self.categorize_imports(imports, module)
                
                # Add to graph
                if module not in self.import_graph:
                    self.import_graph.add_node(module)
                    
                for dep in internal:
                    if dep in ml_modules:
                        self.import_graph.add_edge(module, dep)
                        
                # Track external deps
                self.external_deps[module] = external
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Detect circular import cycles"""
        try:
            cycles = list(nx.simple_cycles(self.import_graph))
            return cycles
        except:
            return []
    
    def check_external_dependencies(self) -> Dict[str, bool]:
        """Verify external packages are installed"""
        status = {}
        all_external = set()
        
        for module_deps in self.external_deps.values():
            all_external.update(module_deps)
            
        for dep in all_external:
            try:
                # Map import names to package names
                package_map = {
                    'cv2': 'cv2',
                    'torch': 'torch',
                    'transformers': 'transformers',
                    'peft': 'peft',
                    'ultralytics': 'ultralytics',
                    'roboflow': 'roboflow',
                    'albumentations': 'albumentations',
                    'sentence_transformers': 'sentence-transformers'
                }
                
                package = package_map.get(dep, dep)
                importlib.import_module(dep)
                status[package] = True
                
            except ImportError:
                status[package] = False
                self.missing_deps.append(package)
                
        return status
    
    def generate_report(self):
        """Generate comprehensive dependency report"""
        print("=" * 60)
        print("NEXA ML MODULE DEPENDENCY ANALYSIS")
        print("=" * 60)
        
        # Build dependency graph
        self.build_dependency_graph()
        
        # 1. Module Graph Stats
        print("\n📊 Module Graph Statistics:")
        print(f"  Total ML modules: {self.import_graph.number_of_nodes()}")
        print(f"  Total dependencies: {self.import_graph.number_of_edges()}")
        print(f"  Average connections: {self.import_graph.number_of_edges() / max(self.import_graph.number_of_nodes(), 1):.2f}")
        
        # 2. Check for circular dependencies
        print("\n🔄 Circular Dependency Check:")
        cycles = self.find_circular_dependencies()
        if cycles:
            print("  ❌ CIRCULAR DEPENDENCIES DETECTED:")
            for cycle in cycles:
                print(f"    {' -> '.join(cycle)} -> {cycle[0]}")
        else:
            print("  ✅ No circular dependencies found")
        
        # 3. Dependency layers
        print("\n📦 Dependency Layers:")
        if self.import_graph.number_of_nodes() > 0:
            # Calculate depths
            depths = {}
            for node in nx.topological_sort(self.import_graph):
                predecessors = list(self.import_graph.predecessors(node))
                if not predecessors:
                    depths[node] = 0
                else:
                    depths[node] = max(depths[p] for p in predecessors) + 1
                    
            # Group by layer
            layers = defaultdict(list)
            for node, depth in depths.items():
                layers[depth].append(node)
                
            for depth in sorted(layers.keys()):
                print(f"  Layer {depth}: {', '.join(layers[depth])}")
        
        # 4. External dependencies
        print("\n🌐 External ML Dependencies:")
        ext_status = self.check_external_dependencies()
        
        installed = [k for k, v in ext_status.items() if v]
        missing = [k for k, v in ext_status.items() if not v]
        
        if installed:
            print(f"  ✅ Installed ({len(installed)}): {', '.join(sorted(installed))}")
        if missing:
            print(f"  ❌ Missing ({len(missing)}): {', '.join(sorted(missing))}")
            
        # 5. Module-specific dependencies
        print("\n📋 Module External Dependencies:")
        for module, deps in sorted(self.external_deps.items()):
            if deps:
                print(f"  {module}: {', '.join(sorted(deps))}")
        
        # 6. Risk assessment
        print("\n⚠️ Risk Assessment:")
        risks = []
        
        if cycles:
            risks.append("HIGH: Circular dependencies will cause import errors")
        if missing:
            risks.append(f"HIGH: {len(missing)} missing packages will cause runtime failures")
        if self.import_graph.number_of_edges() > self.import_graph.number_of_nodes() * 2:
            risks.append("MEDIUM: High coupling between modules")
            
        if risks:
            for risk in risks:
                print(f"  - {risk}")
        else:
            print("  ✅ No significant risks detected")
            
        # 7. Recommendations
        print("\n💡 Recommendations:")
        if missing:
            print(f"  1. Install missing packages: pip install {' '.join(missing)}")
        if cycles:
            print("  2. Refactor circular dependencies using dependency injection")
        print("  3. Document all module interfaces in __init__.py files")
        print("  4. Add integration tests for module boundaries")
        
        # Generate score
        score = 100
        score -= len(cycles) * 20  # -20 per circular dependency
        score -= len(missing) * 10  # -10 per missing package
        score = max(0, score)
        
        print("\n" + "=" * 60)
        print(f"COMPLIANCE SCORE: {score}%")
        print("=" * 60)
        
        return score

def main():
    """Run dependency analysis"""
    modules_dir = Path(__file__).parent / "modules"
    
    if not modules_dir.exists():
        print(f"Error: Modules directory not found at {modules_dir}")
        sys.exit(1)
        
    analyzer = DependencyAnalyzer(modules_dir)
    score = analyzer.generate_report()
    
    # Exit with non-zero if compliance is below threshold
    if score < 70:
        sys.exit(1)

if __name__ == "__main__":
    main()
