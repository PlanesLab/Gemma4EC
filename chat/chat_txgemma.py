import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "google/txgemma-9b-chat"
cache_dir = os.environ.get("HF_HOME", None)

print("Loading tokenizer...")
tok = AutoTokenizer.from_pretrained(model_id, cache_dir=cache_dir)
print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    model_id, cache_dir=cache_dir,
    torch_dtype=torch.bfloat16, device_map="auto"
)
model.eval()

history = []
print("\nTxGemma-9B-Chat ready. Type 'quit' to exit.\n")
while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye.")
        break
    if not user_input:
        continue
    if user_input.lower() in ("quit", "exit", "q"):
        break
    history.append({"role": "user", "content": user_input})
    prompt = tok.apply_chat_template(history, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=512, do_sample=True, temperature=0.7)
    response = tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    history.append({"role": "model", "content": response})
    print(f"\nTxGemma: {response}\n")
