import requests, time, json

url = "http://localhost:8000/api/design/generate"
payload = {
    "prompt": "Design an aluminum hex bolt M16 with 60mm length and chamfered tip"
}

print("Submitting design generation request...")
resp = requests.post(url, json=payload)
print("Status code:", resp.status_code)
data = resp.json()
print("Response:", data)

design_id = data.get("design_id")
print(f"Tracking design {design_id}...")

for _ in range(30):
    time.sleep(2)
    st_resp = requests.get(f"http://localhost:8000/api/design/{design_id}")
    st_data = st_resp.json()
    status = st_data.get("status")
    print(f"Current status: {status}")
    if status in ("complete", "failed"):
        print("Final result:")
        print("Status:", status)
        print("Material:", st_data.get("material"))
        print("Geometry Valid:", st_data.get("geometry_valid"))
        print("Capped DFM score:", st_data.get("dfm_score"))
        break
