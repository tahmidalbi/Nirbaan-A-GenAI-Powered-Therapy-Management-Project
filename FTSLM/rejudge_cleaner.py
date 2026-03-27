import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# 1. Initialize the OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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", 
)

INPUT_FILE = "nirbaan_synthetic_dataset.jsonl"
OUTPUT_FILE = "nirbaan_qlora_ready.jsonl"
MAX_CONCURRENT_REQUESTS = 5  # Processes 5 scripts at the exact same time

# Create a lock so multiple threads don't write to the file at the exact same millisecond
file_write_lock = threading.Lock()

# 2. Count how many scripts are already clean so we can resume if it crashes
processed_count = 0
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        processed_count = sum(1 for line in f if line.strip())

# 3. Read the raw lines
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"🚀 Starting HIGH-SPEED Cleanup & QLoRA Formatting...")
print(f"📁 Total raw scripts: {len(lines)}")
print(f"⏩ Skipping {processed_count} already processed scripts...")

lines_to_process = lines[processed_count:]
total_remaining = len(lines_to_process)

# The static instruction for your fine-tuning dataset
SYSTEM_INSTRUCTION = "Act as an ERP therapist. Generate an imaginal exposure script based on the following OCD obsession, compulsion, and feared consequence."

def clean_and_format(line, index):
    """Function that handles a single script so we can run it in parallel."""
    if not line.strip():
        return None
        
    try:
        data = json.loads(line)
        raw_text = data.get("text", "")
        
        # PYTHON PRE-CLEAN: Strip the worst glitches BEFORE the AI even sees it
        raw_text = raw_text.replace("\u0013", "'").replace("\u0003", "'").replace("\u0004", "'").replace("\u2019", "'")
        
        system_prompt = """
        You are an expert clinical psychologist and meticulous data formatter. Your job is to clean, categorize, and reformat a synthetic ERP exposure script for a QLoRA fine-tuning dataset.
        
        CRITICAL INSTRUCTIONS:
        1. READABILITY: Find any corrupted ASCII or control characters (like \u0013, \u0003, \u0004) and replace them with standard human-readable English punctuation (like apostrophes). 
        2. ENGLISH ONLY: Ensure the text is 100% English. Translate or remove any random non-English hallucinations.
        3. CATEGORIZE THE THEME: Assign the exact clinical OCD subtype (e.g., "Harm OCD", "Contamination OCD", "Pedophilia OCD (POCD)", "Relationship OCD (ROCD)", "Scrupulosity OCD", "Checking/Hit-and-Run OCD", "Existential/Schizophrenia OCD", "Sexual Orientation OCD (HOCD)", "Postpartum OCD").
        4. SPLIT FOR QLORA: The raw text contains an "INPUT:" section and an "OUTPUT:" section. You must separate these into two distinct fields. Do NOT change the "Script intensity" score. Keep the original story intact, just fix the punctuation.

        Return ONLY a JSON object with exactly three keys:
        "type": (The exact OCD subtype)
        "input": (The cleaned text from the INPUT section, excluding the word "INPUT:")
        "output": (The cleaned text from the OUTPUT section, excluding the word "OUTPUT:")
        """
        
        user_prompt = f"Here is the raw text entry:\n\n{raw_text}"
        
        # Exponential Backoff Retry Loop
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="nousresearch/hermes-3-llama-3.1-70b",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1 
                )
                
                # Parse the AI's response
                cleaned_data = json.loads(response.choices[0].message.content)
                
                # Construct the final QLoRA-ready JSON object
                final_qlora_json = {
                    "instruction": SYSTEM_INSTRUCTION,
                    "input": cleaned_data.get("input", "").strip(),
                    "output": cleaned_data.get("output", "").strip(),
                    "type": cleaned_data.get("type", "Unknown")
                }
                
                # Use the lock to safely write to the file
                with file_write_lock:
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
                        out_f.write(json.dumps(final_qlora_json, ensure_ascii=False) + "\n")
                
                return f"{final_qlora_json['type']} (Formatted successfully)"
                
            except Exception as api_error:
                if "429" in str(api_error) or "rate limit" in str(api_error).lower():
                    time.sleep(2 ** attempt) 
                elif attempt == max_retries - 1:
                    return f"Error: {str(api_error)}"
                else:
                    time.sleep(2)
                    
    except Exception as e:
        return f"Error: {str(e)}"

# 4. The Multithreaded Execution
completed_count = 0
with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
    # Submit all tasks to the thread pool
    future_to_index = {executor.submit(clean_and_format, line, i): i for i, line in enumerate(lines_to_process)}
    
    # Process results as they finish
    for future in as_completed(future_to_index):
        completed_count += 1
        result = future.result()
        if result and not result.startswith("Error"):
            print(f"✅ Processed [{completed_count}/{total_remaining}]: {result}")
        else:
            print(f"❌ Failed on a script: {result}")

print(f"\n🎉 DATASET PERFECTED! Saved as {OUTPUT_FILE}")