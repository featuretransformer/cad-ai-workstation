import json
from pathlib import Path

log_path = Path(r"C:\Users\shiva\.gemini\antigravity-ide\brain\cd26cf5f-62a7-4cfc-b4d0-b5fa3087dabd\.system_generated\logs\transcript_full.jsonl")

if not log_path.exists():
    print("Log path does not exist!")
    exit(1)

with open(log_path, "r", encoding="utf-8") as f:
    for line in reversed(f.readlines()):
        data = json.loads(line)
        content = data.get("content", "")
        if "100 Mechanical CAD Generation Test Prompts" in content:
            print("Found '100 Mechanical CAD Generation Test Prompts' in step! Content length:", len(content))
            # Extract between diff markers or take content
            start_marker = "[diff_block_start]"
            end_marker = "The USER performed the following action:"
            
            if start_marker in content:
                part = content.split(start_marker)[1]
                if end_marker in part:
                    part = part.split(end_marker)[0]
                lines = part.splitlines()
                clean_lines = []
                for dl in lines:
                    if dl.startswith("@@"):
                        continue
                    elif dl.startswith("+"):
                        clean_lines.append(dl[1:])
                    elif dl.startswith(" "):
                        clean_lines.append(dl[1:])
                    else:
                        clean_lines.append(dl)
                file_text = "\n".join(clean_lines).strip()
            else:
                file_text = content
            
            target = Path(r"c:\Users\shiva\OneDrive\Desktop\cad-ai-workstation-main\test")
            with open(target, "w", encoding="utf-8") as out:
                out.write(file_text)
            print(f"Successfully wrote {len(file_text)} chars to {target}")
            break
