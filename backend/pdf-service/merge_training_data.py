#!/usr/bin/env python3
"""
Script to merge all NER training datasets and evaluate performance
"""
import os
from pathlib import Path

def merge_conll_files(output_file="ner_training_merged.conll"):
    """Merge all CoNLL training files into one"""
    
    data_dir = Path(__file__).parent / "data"
    output_path = data_dir / output_file
    
    # Files to merge in order
    training_files = [
        "ner_training_comprehensive.conll",
        "ner_training_augmented.conll"
    ]
    
    merged_content = []
    total_sentences = 0
    total_tokens = 0
    entity_counts = {}
    
    for filename in training_files:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"Reading {filename}...")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.strip().split('\n')
                
                sentence_tokens = 0
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip comments
                        parts = line.split()
                        if len(parts) >= 3:
                            token = parts[0]
                            tag = parts[2]
                            sentence_tokens += 1
                            total_tokens += 1
                            
                            if tag != 'O':
                                entity_type = tag.split('-')[1] if '-' in tag else tag
                                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                        elif len(parts) == 2:
                            # Handle lines with only token and tag (no POS)
                            token = parts[0]
                            tag = parts[1]
                            sentence_tokens += 1
                            total_tokens += 1
                            
                            if tag != 'O':
                                entity_type = tag.split('-')[1] if '-' in tag else tag
                                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                    else:
                        if sentence_tokens > 0:
                            total_sentences += 1
                            sentence_tokens = 0
                
                # Add a blank line between files for separation
                if merged_content and merged_content[-1].strip():
                    merged_content.append("")
                
                merged_content.append(content)
                
                # Count last sentence if file doesn't end with blank line
                if sentence_tokens > 0:
                    total_sentences += 1
        else:
            print(f"Warning: {filename} not found")
    
    # Write merged file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(merged_content))
    
    print(f"\n✅ Merged training data saved to: {output_path}")
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total sentences: {total_sentences}")
    print(f"   Total tokens: {total_tokens}")
    print(f"\n   Entity distribution:")
    for entity_type, count in sorted(entity_counts.items()):
        percentage = (count / total_tokens) * 100
        print(f"   - {entity_type:15s}: {count:4d} ({percentage:.1f}%)")
    
    return output_path

def evaluate_tagger_performance():
    """Evaluate the NER tagger with the merged dataset"""
    try:
        from custom_taggers import train_ner_tagger, load_ner_data
        import random
        from sklearn.metrics import precision_recall_fscore_support, classification_report
        
        # Load and train with merged data
        merged_file = merge_conll_files()
        print(f"\n🔧 Training NER tagger with merged dataset...")
        
        # Load all data
        all_data = load_ner_data(str(merged_file))
        
        # Split 80/20 for train/test
        random.shuffle(all_data)
        split_point = int(len(all_data) * 0.8)
        train_data = all_data[:split_point]
        test_data = all_data[split_point:]
        
        print(f"   Training sentences: {len(train_data)}")
        print(f"   Test sentences: {len(test_data)}")
        
        # Train the tagger
        from custom_taggers import ConstructionNERTagger
        tagger = ConstructionNERTagger(train_data)
        
        # Evaluate on test set
        y_true = []
        y_pred = []
        
        for sentence in test_data:
            tokens = [token for token, _, _ in sentence]
            true_tags = [tag for _, _, tag in sentence]
            
            # Get predictions
            predicted = tagger.tag(tokens)
            pred_tags = [tag for _, tag in predicted]
            
            y_true.extend(true_tags)
            y_pred.extend(pred_tags)
        
        # Calculate metrics excluding 'O' labels
        labels = list(set(y_true) - {'O'})
        
        # Overall metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, average='weighted', zero_division=0
        )
        
        print(f"\n📈 Performance Metrics (Weighted Average):")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall:    {recall:.3f}")
        print(f"   F1-Score:  {f1:.3f}")
        
        # Detailed report
        print(f"\n📋 Detailed Classification Report:")
        print(classification_report(y_true, y_pred, labels=labels, zero_division=0))
        
        # Check if we reached target
        if f1 >= 0.85:
            print(f"\n🎉 SUCCESS! Achieved target F1-score of 85%+")
        else:
            improvement_needed = 0.85 - f1
            print(f"\n📊 Current F1: {f1:.3f} - Need {improvement_needed:.3f} improvement to reach 85% target")
            
    except ImportError as e:
        print(f"Error: Required module not found - {e}")
        print("Make sure sklearn is installed: pip install scikit-learn")
    except Exception as e:
        print(f"Error during evaluation: {e}")

if __name__ == "__main__":
    evaluate_tagger_performance()
