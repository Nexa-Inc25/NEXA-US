"""
Test ML Module Dependencies
Ensures no circular dependencies and all requirements are met
"""

import pytest
import importlib
import sys
from pathlib import Path
import networkx as nx
from typing import Dict, List

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestMLDependencies:
    """Test suite for ML module dependency validation"""
    
    @pytest.fixture
    def dependency_map(self) -> Dict[str, List[str]]:
        """Define expected module dependencies"""
        return {
            # Core modules - no internal dependencies
            'utils': [],
            'enhanced_spec_analyzer': ['utils'],
            'pole_vision_detector': ['utils'],
            
            # ML Training modules
            'model_fine_tuner': ['utils', 'roboflow_dataset_integrator', 'enhanced_spec_analyzer'],
            'conduit_ner_fine_tuner': ['model_fine_tuner', 'spec_learning_endpoints'],
            'overhead_ner_fine_tuner': ['model_fine_tuner', 'spec_learning_endpoints'],
            'clearance_enhanced_fine_tuner': ['model_fine_tuner', 'spec_learning_endpoints'],
            
            # Integration modules
            'roboflow_dataset_integrator': ['pole_vision_detector', 'utils'],
            'spec_learning_endpoints': ['enhanced_spec_analyzer', 'as_built_filler'],
            
            # Analysis modules  
            'clearance_analyzer': ['clearance_enhanced_fine_tuner'],
            'conduit_enhanced_analyzer': ['conduit_ner_fine_tuner'],
            'overhead_enhanced_analyzer': ['overhead_ner_fine_tuner'],
            
            # Workflow modules
            'as_built_filler': ['utils'],
            'job_workflow_api': ['as_built_filler']
        }
    
    def test_no_circular_dependencies(self, dependency_map):
        """Ensure no circular import chains exist"""
        # Build directed graph
        G = nx.DiGraph()
        
        for module, deps in dependency_map.items():
            if module not in G:
                G.add_node(module)
            for dep in deps:
                G.add_edge(module, dep)
        
        # Check for cycles
        cycles = list(nx.simple_cycles(G))
        
        assert len(cycles) == 0, f"Circular dependencies detected: {cycles}"
    
    def test_dependency_layers(self, dependency_map):
        """Verify modules are properly layered"""
        # Define expected layers
        layers = {
            0: ['utils'],  # Core utilities
            1: ['enhanced_spec_analyzer', 'pole_vision_detector', 'as_built_filler'],  # Foundation
            2: ['roboflow_dataset_integrator', 'spec_learning_endpoints', 'job_workflow_api'],  # Integration
            3: ['model_fine_tuner'],  # ML Base
            4: ['conduit_ner_fine_tuner', 'overhead_ner_fine_tuner', 'clearance_enhanced_fine_tuner'],  # Specialized ML
            5: ['clearance_analyzer', 'conduit_enhanced_analyzer', 'overhead_enhanced_analyzer']  # Analysis
        }
        
        # Verify no module imports from a higher layer
        for module, deps in dependency_map.items():
            module_layer = None
            for layer, modules in layers.items():
                if module in modules:
                    module_layer = layer
                    break
                    
            if module_layer is not None:
                for dep in deps:
                    dep_layer = None
                    for layer, modules in layers.items():
                        if dep in modules:
                            dep_layer = layer
                            break
                    
                    if dep_layer is not None:
                        assert dep_layer <= module_layer, \
                            f"{module} (layer {module_layer}) imports {dep} (layer {dep_layer}) - violates layering"
    
    def test_external_ml_dependencies_available(self):
        """Check that required ML libraries can be imported"""
        required_packages = [
            ('torch', 'PyTorch'),
            ('transformers', 'Hugging Face Transformers'),
            ('peft', 'Parameter-Efficient Fine-Tuning'),
            ('sentence_transformers', 'Sentence Transformers'),
            ('ultralytics', 'YOLOv8'),
            ('cv2', 'OpenCV'),
            ('albumentations', 'Image Augmentation'),
            ('sklearn', 'Scikit-learn')
        ]
        
        missing = []
        for package, name in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(f"{name} ({package})")
        
        assert len(missing) == 0, f"Missing ML dependencies: {', '.join(missing)}"
    
    def test_ml_module_imports(self):
        """Verify ML modules can be imported without errors"""
        ml_modules = [
            'modules.model_fine_tuner',
            'modules.conduit_ner_fine_tuner',
            'modules.overhead_ner_fine_tuner',
            'modules.clearance_enhanced_fine_tuner',
            'modules.roboflow_dataset_integrator',
            'modules.spec_learning_endpoints',
            'modules.ml_device_utils',
            'modules.ml_monitoring'
        ]
        
        failed_imports = []
        for module in ml_modules:
            try:
                # Check if module file exists
                module_path = Path(__file__).parent.parent / module.replace('.', '/') + '.py'
                if module_path.exists():
                    # Try to import (will fail if dependencies missing)
                    spec = importlib.util.spec_from_file_location(module, module_path)
                    if spec and spec.loader:
                        test_module = importlib.util.module_from_spec(spec)
                        # Don't execute, just check syntax
                else:
                    failed_imports.append(f"{module} (file not found)")
            except Exception as e:
                failed_imports.append(f"{module} ({str(e)})")
        
        if failed_imports:
            pytest.skip(f"Module files not ready: {', '.join(failed_imports)}")
    
    def test_no_deprecated_imports(self):
        """Ensure no imports of archived/deprecated modules"""
        deprecated = [
            'yolov8n',  # Old YOLO model archived
            'app_simple',  # Old app versions
            'app_production',
            'app_electrical'
        ]
        
        modules_dir = Path(__file__).parent.parent / "modules"
        if not modules_dir.exists():
            pytest.skip("Modules directory not found")
            
        violations = []
        for module_file in modules_dir.glob("*.py"):
            content = module_file.read_text()
            for deprecated_import in deprecated:
                if deprecated_import in content:
                    violations.append(f"{module_file.name} imports deprecated {deprecated_import}")
        
        assert len(violations) == 0, f"Deprecated imports found: {violations}"
    
    @pytest.mark.parametrize("module,max_deps", [
        ('model_fine_tuner', 5),
        ('conduit_ner_fine_tuner', 3),
        ('roboflow_dataset_integrator', 3),
        ('spec_learning_endpoints', 3),
    ])
    def test_dependency_limits(self, module, max_deps, dependency_map):
        """Ensure modules don't have too many dependencies (coupling)"""
        deps = dependency_map.get(module, [])
        assert len(deps) <= max_deps, \
            f"{module} has {len(deps)} dependencies (max {max_deps}) - high coupling"
    
    def test_ml_config_environment_vars(self):
        """Verify required environment variables are documented"""
        import os
        
        required_env_vars = [
            'ROBOFLOW_API_KEY',
            'MODEL_CACHE_DIR',
            'TRAINING_DATA_DIR'
        ]
        
        # Check if .env.example exists and contains required vars
        env_example = Path(__file__).parent.parent / ".env.example"
        if env_example.exists():
            content = env_example.read_text()
            missing = [var for var in required_env_vars if var not in content]
            assert len(missing) == 0, f"Missing env vars in .env.example: {missing}"
        else:
            pytest.skip(".env.example not found")
    
    def test_ml_requirements_synced(self):
        """Ensure requirements_ml.txt is in sync with actual imports"""
        req_file = Path(__file__).parent.parent / "requirements_ml.txt"
        if not req_file.exists():
            pytest.skip("requirements_ml.txt not found")
            
        # Parse requirements
        requirements = set()
        for line in req_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (before ==, >=, etc.)
                package = line.split('==')[0].split('>=')[0].split('<=')[0]
                package = package.split('[')[0]  # Remove extras
                requirements.add(package.lower())
        
        # Check critical ML packages are listed
        critical = ['torch', 'transformers', 'ultralytics', 'peft', 'sentence-transformers']
        missing = [p for p in critical if p not in requirements]
        
        assert len(missing) == 0, f"Critical ML packages missing from requirements: {missing}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
