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
OUTPUT_FILE = "nirbaan_final_cleaned.jsonl"
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

print(f"🚀 Starting HIGH-SPEED LLM Cleanup Pass...")
print(f"📁 Total raw scripts: {len(lines)}")
print(f"⏩ Skipping {processed_count} already cleaned scripts...")

lines_to_process = lines[processed_count:]
total_remaining = len(lines_to_process)

def clean_script(line, index):
    """Function that handles a single script so we can run it in parallel."""
    if not line.strip():
        return None
        
    try:
        data = json.loads(line)
        raw_text = data.get("text", "")
        
        system_prompt = """
        You are a highly precise text-editing AI. Your only job is to clean a raw text dataset entry and categorize it.
        
        CRITICAL INSTRUCTIONS:
        1. ENGLISH ONLY: Scan the text for any non-English characters, words, or sentences. Translate them seamlessly into English if they fit the story, or completely remove them if they are random hallucinations. The final output MUST be 100% English alphabet characters.
        2. READABILITY: Find any corrupted ASCII or control characters (like \u0013, \u0003, \u0004) and replace them with standard human-readable English punctuation (like apostrophes). 
        3. NO REWRITING: Do NOT change the core story or the narrative tone. Do NOT alter the "INPUT:" and "OUTPUT:" formatting. You are a proofreader, not an author.
        4. CATEGORIZE: Read the obsession and assign the exact clinical OCD subtype (e.g., "Harm OCD", "Contamination OCD", "Pedophilia OCD", "Relationship OCD", "Scrupulosity OCD", "Checking/Hit-and-Run OCD", "Existential/Schizophrenia OCD", "Sexual Orientation OCD", "Postpartum OCD").
        5. STRICT JSON: Return ONLY a valid JSON object.
        """
        
        user_prompt = f"Here is the raw text entry:\n\n{raw_text}\n\nReturn a JSON object with exactly two keys:\n\"type\": (The determined OCD subtype string)\n\"text\": (The fully cleaned, perfectly readable text string)"
        
        # Exponential Backoff Retry Loop (tries 4 times if the server is busy)
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
                
                cleaned_json = json.loads(response.choices[0].message.content)
                
                # Use the lock to safely write to the file
                with file_write_lock:
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
                        out_f.write(json.dumps(cleaned_json, ensure_ascii=False) + "\n")
                
                return cleaned_json.get('type', 'Unknown')
                
            except Exception as api_error:
                if "429" in str(api_error) or "rate limit" in str(api_error).lower():
                    time.sleep(2 ** attempt) # Waits 1s, then 2s, then 4s, then 8s
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
    future_to_index = {executor.submit(clean_script, line, i): i for i, line in enumerate(lines_to_process)}
    
    # Process results as they finish (they will finish out of order, which is fine)
    for future in as_completed(future_to_index):
        completed_count += 1
        result = future.result()
        if result and not result.startswith("Error"):
            print(f"✅ Cleaned [{completed_count}/{total_remaining}]: Categorized as {result}")
        else:
            print(f"❌ Failed on a script: {result}")

print(f"\n🎉 HIGH-SPEED CLEANUP COMPLETE! Your perfect dataset is saved as {OUTPUT_FILE}")