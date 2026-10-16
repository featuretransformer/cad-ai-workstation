import urllib.request
import json
import time
import sys

base_url = "http://localhost:8000"

def run_test():
    # 1. Create a session
    req = urllib.request.Request(
        f"{base_url}/api/sessions/",
        data=json.dumps({"name": "Live Verification Session"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        sess = json.loads(resp.read())
    session_id = sess["id"]
    print(f"Session created: {session_id}")

    test_prompts = [
        ("Shaft Design", "Design a steel transmission shaft 30mm diameter, 180mm length with chamfered ends"),
        ("Washer Component", "Design a washer OD 45mm, ID 22mm, thickness 4mm"),
        ("L-Bracket Component", "Design a heavy duty L-bracket 80x60mm base, 50mm vertical wall, 8mm thick with mounting holes"),
        ("Gear Component", "Design a spur gear 80mm pitch diameter, 20mm bore, 25mm face width"),
    ]

    results = []

    for label, prompt in test_prompts:
        print(f"\n{'='*50}\nTesting: {label}\nPrompt: {prompt}\n{'='*50}")
        gen_data = json.dumps({"session_id": session_id, "prompt": prompt}).encode()
        req = urllib.request.Request(
            f"{base_url}/api/design/generate",
            data=gen_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            gen_res = json.loads(resp.read())
        design_id = gen_res["design_id"]
        task_id = gen_res["task_id"]
        print(f"Queued task: {task_id} for design: {design_id}")

        # Poll status
        final_status = None
        for i in range(40):
            time.sleep(2)
            try:
                with urllib.request.urlopen(f"{base_url}/api/design/task/{task_id}/status") as resp:
                    st = json.loads(resp.read())
                status = st.get("status")
                print(f"  [{i*2}s] Status: {status}")
                if status in ["COMPLETE", "SUCCESS", "FAILED", "FAILURE"]:
                    final_status = status
                    break
            except Exception as e:
                print(f"  Status poll error: {e}")

        # Fetch design details
        time.sleep(1)
        with urllib.request.urlopen(f"{base_url}/api/design/{design_id}") as resp:
            design = json.loads(resp.read())

        status = design.get("status")
        valid = design.get("geometry_valid")
        print(f"Design record status: {status}, geometry_valid: {valid}")

        # Check exports
        with urllib.request.urlopen(f"{base_url}/api/export/{design_id}") as resp:
            exports = json.loads(resp.read())
        export_formats = [e["format"] for e in exports]
        print(f"Exports registered in DB: {export_formats}")

        # Verify GLB download
        glb_size = 0
        try:
            with urllib.request.urlopen(f"{base_url}/api/export/{design_id}/download/glb") as resp:
                glb_data = resp.read()
                glb_size = len(glb_data)
                print(f"GLB download SUCCESS! Size: {glb_size} bytes")
        except Exception as ge:
            print(f"GLB download warning: {ge}")

        results.append({
            "label": label,
            "design_id": design_id,
            "status": status,
            "valid": valid,
            "exports": export_formats,
            "glb_size": glb_size
        })

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE! SUMMARY:")
    for r in results:
        v_str = "VALID" if r["valid"] else "INVALID"
        print(f"  - {r['label']}: status={r['status']} ({v_str}), exports={r['exports']}, glb={r['glb_size']}B")

if __name__ == "__main__":
    run_test()
