import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / 'exports' / 'detailed_100_inspection.json'
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

prompts_file = Path(__file__).resolve().parent / 'parsed_user_prompts.json'
with open(prompts_file, 'r', encoding='utf-8') as f:
    prompts = json.load(f)

prompt_map = {item['id']: item for item in prompts}

print("=" * 80)
print("COMPREHENSIVE AUDIT OF 100 CAD GENERATIONS")
print("=" * 80)

assemblies = []
single_parts = []
gripper_fallbacks = []
box_fallbacks = []

for d in data:
    pid = d['id']
    p_info = prompt_map[pid]
    prompt_text = p_info['prompt']
    
    dims = d.get('dims', [0, 0, 0])
    vol = d.get('volume', 0.0)
    is_asm = d.get('is_assembly', False)
    comps = d.get('asm_components', [])
    
    # Check if assembly fell back to three-finger gripper
    if is_asm:
        assemblies.append(d)
        if any('finger' in str(c).lower() or 'gripper' in str(c).lower() for c in comps):
            if 'gripper' not in pid.lower() and 'finger' not in p_info['name'].lower():
                gripper_fallbacks.append((pid, p_info['name'], comps))
    else:
        single_parts.append(d)
        # Check if single part fell back to generic 5-hole box
        if dims == [60.0, 40.0, 12.0] or (abs(dims[0]-100) < 1 and abs(dims[1]-40) < 1 and abs(dims[2]-30) < 1 and vol > 100000 and 'channel' in prompt_text.lower()):
            box_fallbacks.append((pid, p_info['name']))

print(f"Total Single Parts: {len(single_parts)}")
print(f"Total Assemblies: {len(assemblies)}")
print(f"\nAssemblies that erroneously fell back to 3-Finger Gripper ({len(gripper_fallbacks)}):")
for pid, name, comps in gripper_fallbacks:
    print(f"  - [{pid}] {name}: components={comps}")

print(f"\nSingle parts that fell back to generic solid box ({len(box_fallbacks)}):")
for pid, name in box_fallbacks:
    print(f"  - [{pid}] {name}")
