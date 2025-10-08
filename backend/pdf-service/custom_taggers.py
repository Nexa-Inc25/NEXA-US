"""
Custom NLTK POS and NER taggers for construction/utility domain
"""
import nltk
from nltk.tag import UnigramTagger, DefaultTagger, ClassifierBasedTagger
from nltk.corpus import treebank
import logging
import os

logger = logging.getLogger(__name__)

# Load POS training data
def load_pos_data(file_path):
    """Load POS training data from custom format"""
    sentences = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    tokens = []
                    for token in line.strip().split():
                        parts = token.rsplit('/', 1)
                        if len(parts) == 2:
                            tokens.append(tuple(parts))
                    if tokens:
                        sentences.append(tokens)
    return sentences

# Load CoNLL NER data
def load_ner_data(file_path):
    """Load NER training data from CoNLL format"""
    sentences = []
    current_sentence = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        token = parts[0]
                        ner_tag = parts[1] if len(parts) > 1 else 'O'
                        current_sentence.append((token, ner_tag))
                else:
                    if current_sentence:
                        sentences.append(current_sentence)
                        current_sentence = []
            if current_sentence:
                sentences.append(current_sentence)
    return sentences

# Feature extraction for NER
def ner_features(tokens, index, history):
    """Extract features for NER classification"""
    token = tokens[index]
    features = {
        'word': token,
        'word_lower': token.lower(),
        'is_digit': token.isdigit(),
        'is_upper': token.isupper(),
        'is_title': token.istitle(),
        'length': len(token),
        'prefix-1': token[0] if token else '',
        'suffix-1': token[-1] if token else '',
        'has_dot': '.' in token,
        'has_hyphen': '-' in token,
    }
    
    # Check for specific patterns
    features['is_section'] = token.startswith('4.') or token.lower() == 'section'
    features['is_zone'] = token.lower() == 'zone'
    features['is_measure'] = any(unit in token.lower() for unit in ['feet', 'ft', 'inch', 'meter', 'm'])
    features['is_voltage'] = 'V' in token or 'volt' in token.lower()
    
    # Context features
    if index > 0:
        features['prev_word'] = tokens[index - 1]
        features['prev_word_lower'] = tokens[index - 1].lower()
        features['prev_is_digit'] = tokens[index - 1].isdigit()
    else:
        features['prev_word'] = '<START>'
        features['prev_word_lower'] = '<start>'
        features['prev_is_digit'] = False
    
    if index < len(tokens) - 1:
        features['next_word'] = tokens[index + 1]
        features['next_word_lower'] = tokens[index + 1].lower()
    else:
        features['next_word'] = '<END>'
        features['next_word_lower'] = '<end>'
    
    return features

# Train POS tagger
def train_pos_tagger(data_file=None):
    """Train custom POS tagger with construction domain data"""
    logger.info("Training custom POS tagger...")
    
    # Use default path if not provided
    if data_file is None:
        data_file = os.path.join(os.path.dirname(__file__), 'data', 'pos_training_data.txt')
    
    training_data = load_pos_data(data_file)
    
    # Create backoff chain
    default_tagger = DefaultTagger('NN')
    
    # If we have training data, use it
    if training_data:
        tagger = UnigramTagger(training_data, backoff=default_tagger)
    else:
        # Fallback to default NLTK tagger
        logger.warning("No POS training data found, using default tagger")
        tagger = default_tagger
    
    return tagger

# Import for classifier-based NER
try:
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using rule-based NER")

# Enhanced NER features for construction domain
def construction_ner_features(tokens, index, history):
    """Extract features for construction-specific NER"""
    token = tokens[index]
    features = {
        'word': token,
        'word_lower': token.lower(),
        'is_digit': token.isdigit(),
        'is_upper': token.isupper(),
        'is_title': token.istitle(),
        'is_alphanumeric': token.isalnum(),
        'length': len(token),
        'prefix-1': token[0] if token else '',
        'prefix-2': token[:2] if len(token) >= 2 else token,
        'suffix-1': token[-1] if token else '',
        'suffix-2': token[-2:] if len(token) >= 2 else token,
        'has_dot': '.' in token,
        'has_hyphen': '-' in token,
        'has_slash': '/' in token,
    }
    
    # Construction-specific patterns - expanded for new entity types
    features['is_section'] = bool(token.startswith(('4.', '5.', '6.', '7.', '8.', '9.', '10.', 'Section')) or 
                                  (token.count('.') >= 1 and token[0].isdigit()))
    features['is_measurement'] = bool(token.isdigit() or 
                                      any(unit in token.lower() for unit in ['feet', 'ft', 'inch', 'meter', 'm', 'kv', 'v', 'a', 'psi', 'mm', 'ka']))
    features['is_material'] = token.lower() in [
        'copper', 'aluminum', 'steel', 'fiberglass', 'stainless', 'galvanized',
        'pvc', 'concrete', 'iron', 'brass', 'plastic', 'composite', 'wood',
        'porcelain', 'glass', 'xlpe', 'epr', 'polycarbonate', 'metal', 'fiber'
    ]
    features['is_equipment'] = token.lower() in [
        'pole', 'poles', 'transformer', 'transformers', 'cable', 'cables', 'wire', 'wires',
        'bolt', 'bolts', 'anchor', 'anchors', 'crossarm', 'crossarms', 'hardware',
        'insulation', 'conduit', 'switchgear', 'fuse', 'fuses', 'breaker', 'breakers',
        'busbar', 'busbars', 'insulator', 'insulators', 'guard', 'guards', 'barrier', 'barriers',
        'switch', 'switches', 'arrestor', 'arrestors', 'meter', 'junction', 'raceway', 'raceways',
        'duct', 'vault', 'riser', 'capacitor', 'relay', 'relays', 'electrode', 'electrodes'
    ]
    features['is_specification'] = token.lower() in [
        'compression', 'lockable', 'weatherproof', 'outdoor', 'preformed', 'color-coded',
        'submersible', 'ventilated', 'fused', 'torqued', 'galvanized', 'rigid'
    ]
    features['is_installation'] = token.lower() in [
        'mounted', 'installed', 'underground', 'overhead', 'pad-mounted', 'pole-mounted',
        'buried', 'exposed', 'connected', 'grounded', 'encased', 'enclosed',
        'surface-mounted', 'flush-mounted', 'direct-buried', 'rackmounted', 
        'wall-mounted', 'ceiling-mounted', 'floor-mounted'
    ] or '-mounted' in token.lower() or '-buried' in token.lower()
    features['is_location'] = token.lower() in [
        'ground', 'substation', 'substations', 'zone', 'area', 'control', 'room', 'rooms',
        'manhole', 'vault', 'entrance', 'outdoor', 'top', 'tops'
    ]
    features['is_test'] = token.lower() in [
        'tested', 'test', 'tests', 'testing', 'strength', 'capacity', 'loading', 
        'drop', 'measured', 'torqued', 'verified', 'resistance', 'dielectric', 
        'pull', 'passed', 'failed', 'exceeds'
    ] or token.lower().endswith(('test', 'tested'))
    features['is_standard'] = token in ['NESC', 'NEMA', 'NEC', 'IEEE', 'OSHA', 'ANSI']
    features['is_grade'] = bool(('#' in token and any(c.isdigit() for c in token)) or
                                ('.' in token and any(c.isdigit() for c in token.split('.')[0])) or
                                (token.startswith('H-') and any(c.isdigit() for c in token)))
    features['is_zone'] = token.lower() == 'zone' or (len(token) == 1 and token.isupper())
    features['is_voltage'] = 'V' in token or 'kV' in token or 'kA' in token
    features['is_awg'] = 'AWG' in token or '/0' in token or '#' in token
    
    # Context features
    if index > 0:
        prev_token = tokens[index - 1]
        features['prev_word'] = prev_token
        features['prev_word_lower'] = prev_token.lower()
        features['prev_is_digit'] = prev_token.isdigit()
        features['prev_is_section'] = prev_token.lower() == 'section'
        features['prev_is_zone'] = prev_token.lower() == 'zone'
        features['prev_is_grade'] = prev_token.lower() == 'grade'
    else:
        features['BOS'] = True  # Beginning of sentence
    
    if index < len(tokens) - 1:
        next_token = tokens[index + 1]
        features['next_word'] = next_token
        features['next_word_lower'] = next_token.lower()
        features['next_is_digit'] = next_token.isdigit()
        features['next_is_unit'] = next_token.lower() in ['feet', 'ft', 'inch', 'meter', 'm', 'v', 'kv', 'a']
    else:
        features['EOS'] = True  # End of sentence
    
    # Bigram features
    if index > 0:
        features['bigram'] = f"{tokens[index-1]}_{token}"
    if index < len(tokens) - 1:
        features['bigram_next'] = f"{token}_{tokens[index+1]}"
    
    return features

# Enhanced classifier-based NER tagger
class ConstructionNERTagger:
    """Advanced NER tagger for construction domain using classifier"""
    
    def __init__(self, training_data=None):
        self.classifier = None
        self.vectorizer = None
        self.training_data = training_data
        
        # Fallback patterns for rule-based tagging - expanded
        self.patterns = {
            'SECTION': ['4.', '5.', '6.', '7.', '8.', '9.', '10.', 'Section'],
            'MATERIAL': ['copper', 'aluminum', 'steel', 'fiberglass', 'stainless', 'galvanized',
                        'pvc', 'concrete', 'iron', 'brass', 'plastic', 'composite', 'wood',
                        'porcelain', 'glass', 'xlpe', 'epr', 'polycarbonate', 'metal', 'fiber'],
            'EQUIPMENT': ['pole', 'transformer', 'cable', 'wire', 'bolt', 'anchor', 'crossarm',
                         'hardware', 'insulation', 'conduit', 'switchgear', 'fuse', 'breaker',
                         'busbar', 'insulator', 'guard', 'barrier', 'switch', 'arrestor',
                         'meter', 'junction', 'raceway', 'duct', 'vault', 'riser', 'capacitor',
                         'relay', 'electrode', 'enclosure', 'box', 'tray', 'sign'],
            'MEASURE': ['feet', 'ft', 'inch', 'meter', 'm', 'kv', 'v', 'a', 'awg', 'psi', 'mm', 'ka'],
            'GRADE': ['8.8', '5.6', '#2', '#4', '#6', '#8', '2/0', '40', '80', 'H-10', 'H-20'],
            'ZONE': ['Zone', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'],
            'STANDARD': ['NESC', 'NEMA', 'NEC', 'IEEE', 'OSHA', 'ANSI'],
            'SPECIFICATION': ['compression', 'lockable', 'weatherproof', 'outdoor', 'preformed',
                            'color-coded', 'submersible', 'ventilated', 'fused', 'torqued',
                            'galvanized', 'rigid', 'flexible', 'bolted'],
            'INSTALLATION': ['mounted', 'installed', 'underground', 'overhead', 'pad-mounted',
                           'pole-mounted', 'buried', 'exposed', 'connected', 'grounded',
                           'encased', 'enclosed'],
            'LOCATION': ['ground', 'substation', 'control', 'room', 'manhole', 'vault',
                        'entrance', 'outdoor', 'top', 'area'],
            'TEST': ['test', 'tested', 'strength', 'capacity', 'loading', 'drop', 'measured'],
        }
        
        if SKLEARN_AVAILABLE and training_data:
            self.train(training_data)
    
    def train(self, training_data):
        """Train the classifier on labeled data"""
        if not SKLEARN_AVAILABLE:
            return
        
        X = []
        y = []
        
        for sentence in training_data:
            tokens = [token for token, _ in sentence]
            tags = [tag for _, tag in sentence]
            
            for i in range(len(tokens)):
                features = construction_ner_features(tokens, i, tags[:i])
                X.append(features)
                y.append(tags[i])
        
        # Create pipeline with vectorizer and classifier
        self.vectorizer = DictVectorizer(sparse=True)
        self.classifier = DecisionTreeClassifier(max_depth=20, min_samples_split=5)
        
        # Train
        X_vec = self.vectorizer.fit_transform(X)
        self.classifier.fit(X_vec, y)
        logger.info(f"Trained NER classifier on {len(training_data)} sentences")
    
    def tag(self, tokens):
        """Tag tokens with NER labels"""
        if self.classifier and self.vectorizer:
            # Use trained classifier
            X = []
            for i in range(len(tokens)):
                features = construction_ner_features(tokens, i, [])
                X.append(features)
            
            X_vec = self.vectorizer.transform(X)
            predictions = self.classifier.predict(X_vec)
            
            return list(zip(tokens, predictions))
        else:
            # Fallback to rule-based tagging
            return self._rule_based_tag(tokens)
    
    def _rule_based_tag(self, tokens):
        """Rule-based tagging fallback - expanded for all entity types"""
        tagged = []
        for i, token in enumerate(tokens):
            tag = 'O'
            token_lower = token.lower()
            
            # Check for section numbers
            if any(token.startswith(sec) for sec in self.patterns['SECTION']) and any(c.isdigit() for c in token):
                tag = 'B-SECTION'
            # Check for standards
            elif token in self.patterns['STANDARD']:
                tag = 'B-STANDARD'
            # Check for zones
            elif i > 0 and tokens[i-1].lower() == 'zone':
                tag = 'I-ZONE'
            elif token_lower == 'zone':
                tag = 'B-ZONE'
            # Check for measurements
            elif token.isdigit():
                if i < len(tokens) - 1:
                    next_token = tokens[i + 1].lower()
                    if any(unit in next_token for unit in self.patterns['MEASURE']):
                        tag = 'B-MEASURE'
            # Check for voltage/current measurements
            elif any(unit in token for unit in ['kV', 'kA', 'V', 'A']) and any(c.isdigit() for c in token):
                tag = 'B-MEASURE'
            # Check for grades
            elif ('#' in token and any(c.isdigit() for c in token)) or token.startswith('H-'):
                tag = 'B-GRADE'
            elif '.' in token and any(c.isdigit() for c in token):
                if any(grade in token for grade in self.patterns['GRADE']):
                    tag = 'B-GRADE'
            # Check equipment (priority over materials)
            elif token_lower in [e.lower() for e in self.patterns['EQUIPMENT']]:
                tag = 'B-EQUIPMENT'
            # Check materials
            elif token_lower in [m.lower() for m in self.patterns['MATERIAL']]:
                tag = 'B-MATERIAL'
            # Check specifications
            elif token_lower in [s.lower() for s in self.patterns['SPECIFICATION']]:
                tag = 'B-SPECIFICATION'
            # Check installations
            elif token_lower in [inst.lower() for inst in self.patterns['INSTALLATION']]:
                tag = 'B-INSTALLATION'
            # Check locations
            elif token_lower in [loc.lower() for loc in self.patterns['LOCATION']]:
                tag = 'B-LOCATION'
            # Check test-related terms
            elif token_lower in [t.lower() for t in self.patterns['TEST']]:
                tag = 'B-TEST'
            # Multi-word entities (check previous token for continuation)
            elif i > 0 and tagged[i-1][1].startswith('B-'):
                prev_tag = tagged[i-1][1].split('-')[1]
                # Check for multi-word patterns
                if prev_tag == 'MATERIAL' and token_lower in ['steel', 'fir', 'optic']:
                    tag = f'I-{prev_tag}'
                elif prev_tag == 'EQUIPMENT' and token_lower in ['breaker', 'breakers', 'box', 'boxes', 'tray', 'trays']:
                    tag = f'I-{prev_tag}'
                elif prev_tag == 'LOCATION' and token_lower in ['room', 'rooms']:
                    tag = f'I-{prev_tag}'
                elif prev_tag == 'MEASURE' and token_lower in self.patterns['MEASURE']:
                    tag = f'I-{prev_tag}'
            
            tagged.append((token, tag))
        
        return tagged

# Train NER tagger
def train_ner_tagger(data_file=None):
    """Train custom NER tagger"""
    logger.info("Training custom NER tagger for construction domain...")
    
    # Try comprehensive dataset first, then expanded, then basic
    if data_file is None:
        comprehensive_file = os.path.join(os.path.dirname(__file__), 'data', 'ner_training_comprehensive.conll')
        expanded_file = os.path.join(os.path.dirname(__file__), 'data', 'ner_training_expanded.conll')
        basic_file = os.path.join(os.path.dirname(__file__), 'data', 'ner_training_data.conll')
        
        if os.path.exists(comprehensive_file):
            data_file = comprehensive_file
            logger.info("Using comprehensive NER training dataset")
        elif os.path.exists(expanded_file):
            data_file = expanded_file
            logger.info("Using expanded NER training dataset")
        else:
            data_file = basic_file
            logger.info("Using basic NER training dataset")
    
    training_data = load_ner_data(data_file)
    
    # Use advanced classifier-based tagger
    tagger = ConstructionNERTagger(training_data)
    
    return tagger
