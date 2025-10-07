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

# Simple NER tagger class
class SimpleNERTagger:
    """Simplified NER tagger for construction domain"""
    
    def __init__(self, training_data=None):
        self.patterns = {
            'SECTION': ['4.1', '4.2', '4.3', '4.4', '4.5', '4.6', 'Section'],
            'MATERIAL': ['copper', 'aluminum', 'steel', 'fiberglass', 'bolts', 'hardware', 'anchors', 'crossarms'],
            'MEASURE': ['feet', 'ft', 'inch', 'meter', 'm'],
            'SPEC': ['8.8', '5.6', '600V', '400V', 'grade'],
            'ZONE': ['Zone'],
        }
    
    def tag(self, tokens):
        """Tag tokens with NER labels"""
        tagged = []
        for i, token in enumerate(tokens):
            tag = 'O'
            token_lower = token.lower()
            
            # Check patterns
            for label, patterns in self.patterns.items():
                if any(pattern.lower() in token_lower for pattern in patterns):
                    tag = f'B-{label}'
                    break
            
            # Check for section numbers
            if token.startswith('4.') and any(c.isdigit() for c in token):
                tag = 'B-SECTION'
            
            # Check for measurements (number followed by unit)
            if token.isdigit() and i < len(tokens) - 1:
                next_token = tokens[i + 1].lower()
                if any(unit in next_token for unit in ['feet', 'ft', 'inch', 'meter', 'm']):
                    tag = 'B-MEASURE'
            
            # Check for zones
            if i > 0 and tokens[i-1].lower() == 'zone':
                tag = 'I-ZONE'
            
            tagged.append((token, tag))
        
        return tagged

# Train NER tagger
def train_ner_tagger(data_file=None):
    """Train custom NER tagger"""
    logger.info("Training custom NER tagger...")
    
    # Use default path if not provided
    if data_file is None:
        data_file = os.path.join(os.path.dirname(__file__), 'data', 'ner_training_data.conll')
    
    training_data = load_ner_data(data_file)
    
    # For simplicity, use rule-based tagger
    # In production, you'd train a proper classifier
    tagger = SimpleNERTagger(training_data)
    
    return tagger
