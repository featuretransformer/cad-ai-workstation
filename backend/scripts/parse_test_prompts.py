import re
import json
from pathlib import Path

test_file = Path(r"c:\Users\shiva\OneDrive\Desktop\cad-ai-workstation-main\test")
content = test_file.read_text(encoding="utf-8")

# Pattern: ### (E|M|C|H)\d+ — Title
# followed by prompt text until next header or end
pattern = re.compile(r"###\s+([EMCH]\d+)\s+[—-]\s+([^\n]+)\n(.*?)(?=\n###|\n#|\Z)", re.DOTALL)

matches = pattern.findall(content)
print(f"Extracted {len(matches)} prompts from {test_file}")

prompts = []
for pid, title, ptext in matches:
    clean_ptext = ptext.strip()
    tier = "Easy" if pid.startswith("E") else "Medium" if pid.startswith("M") else "Complex"
    level = "Level 1 (Easy)" if pid.startswith("E") else "Level 2 (Medium)" if pid.startswith("M") else "Level 3 (Complex)" if pid.startswith("C") else "Level 4 (Highly Complex)"
    prompts.append({
        "id": pid,
        "tier": tier,
        "level": level,
        "name": title.strip(),
        "prompt": clean_ptext,
    })

print(f"Total: {len(prompts)}")
easy_count = sum(1 for p in prompts if p["tier"] == "Easy")
med_count = sum(1 for p in prompts if p["tier"] == "Medium")
cmplx_count = sum(1 for p in prompts if p["tier"] == "Complex")
print(f"Easy: {easy_count} | Medium: {med_count} | Complex: {cmplx_count}")

out_path = Path(__file__).resolve().parent / "parsed_user_prompts.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(prompts, f, indent=2)

print(f"Saved to {out_path}")
