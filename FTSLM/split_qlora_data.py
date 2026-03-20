import json
import random

INPUT_FILE = "nirbaan_qlora_ready.jsonl"
TRAIN_FILE = "train.jsonl"
DEV_FILE = "dev.jsonl"
TEST_FILE = "test.jsonl"

print(f"🔪 Slicing {INPUT_FILE} into Train, Dev, and Test sets...")

try:
    # 1. Load the pristine QLoRA formatted data
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        dataset = [json.loads(line) for line in f if line.strip()]
    
    total_examples = len(dataset)
    print(f"Loaded {total_examples} perfect examples.")

    # 2. Shuffle with a fixed seed for scientific reproducibility
    random.seed(42)
    random.shuffle(dataset)

    # 3. Calculate the 80 / 10 / 10 splits
    train_cutoff = int(total_examples * 0.8)
    dev_cutoff = int(total_examples * 0.9)

    train_data = dataset[:train_cutoff]
    dev_data = dataset[train_cutoff:dev_cutoff]
    test_data = dataset[dev_cutoff:]

    # 4. Helper function to save the new files
    def save_to_jsonl(data_list, filename):
        with open(filename, 'w', encoding='utf-8') as out_f:
            for item in data_list:
                out_f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"✅ Saved {len(data_list)} examples to {filename}")

    # 5. Execute the saves
    save_to_jsonl(train_data, TRAIN_FILE)
    save_to_jsonl(dev_data, DEV_FILE)
    save_to_jsonl(test_data, TEST_FILE)

    print("\n🎉 Split complete! The dataset is officially ready for Google Colab.")

except FileNotFoundError:
    print(f"❌ Error: Could not find '{INPUT_FILE}'.")