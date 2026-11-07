
# gemma4ec/src/training/formatting.py

def formatting_func(example):
    # Keeps your original pattern: "<prompt> <label><eos>"
    return f"{example['input_text']} {example['output_text']}<eos>"