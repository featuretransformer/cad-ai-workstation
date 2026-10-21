import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

out_dir = Path(r'C:\Users\shiva\.gemini\antigravity-ide\brain\bcb54c3b-1432-45ae-b89f-b1c6cb340848\renders')
out_dir.mkdir(parents=True, exist_ok=True)

exports_dir = Path(__file__).resolve().parent.parent / 'exports'
prompts_file = Path(__file__).resolve().parent / 'parsed_user_prompts.json'

with open(prompts_file, 'r', encoding='utf-8') as f:
    prompts = json.load(f)

rendered_count = 0
for p in prompts:
    pid = p['id']
    stl_path = exports_dir / f"eval_{pid.lower()}" / "output.stl"
    if not stl_path.exists():
        continue
    
    img_path = out_dir / f"{pid.lower()}_render.png"
    if img_path.exists():
        rendered_count += 1
        continue
        
    try:
        mesh = trimesh.load(str(stl_path))
        fig = plt.figure(figsize=(6, 6), dpi=100, facecolor='#ffffff')
        ax = fig.add_subplot(111, projection='3d', facecolor='#ffffff')
        
        # Subsample faces if too detailed
        faces = mesh.faces
        if len(faces) > 15000:
            indices = np.random.choice(len(faces), 15000, replace=False)
            faces = faces[indices]
            
        triangles = mesh.vertices[faces]
        col = Poly3DCollection(triangles, alpha=0.92, facecolor='#5c82a6', edgecolor='#2c4460', linewidths=0.15)
        ax.add_collection3d(col)
        
        min_b, max_b = mesh.bounds
        center = (min_b + max_b) / 2
        max_range = max(np.max(max_b - min_b) / 2, 1.0)
        ax.set_xlim(center[0] - max_range, center[0] + max_range)
        ax.set_ylim(center[1] - max_range, center[1] + max_range)
        ax.set_zlim(center[2] - max_range, center[2] + max_range)
        ax.view_init(elev=28, azim=45)
        
        dx = round(max_b[0] - min_b[0], 1)
        dy = round(max_b[1] - min_b[1], 1)
        dz = round(max_b[2] - min_b[2], 1)
        name = p['name']
        vol = round(mesh.volume, 1)
        ax.set_title(f"{pid}: {name}\n{dx} x {dy} x {dz} mm | Vol: {vol} mm3", fontsize=10, pad=10)
        
        plt.tight_layout()
        plt.savefig(str(img_path))
        plt.close(fig)
        rendered_count += 1
        if rendered_count % 10 == 0:
            print(f"Rendered {rendered_count}/{len(prompts)} models...")
    except Exception as e:
        print(f"Error rendering {pid}: {e}")

print(f"Batch rendering complete! Total rendered: {rendered_count}/{len(prompts)}")
