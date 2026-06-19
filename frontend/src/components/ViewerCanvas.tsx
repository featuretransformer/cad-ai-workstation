"use client";
import { Suspense, useRef, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Grid, Environment, useGLTF, Center } from "@react-three/drei";
import { useCADStore } from "@/store/cadStore";
import * as THREE from "three";

function CADModel({ url, wireframe }: { url: string; wireframe: boolean }) {
  const { scene } = useGLTF(url);
  const ref = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!scene) return;
    scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((m: THREE.Material) => {
            (m as THREE.MeshStandardMaterial).wireframe = wireframe;
          });
        } else {
          (mesh.material as THREE.MeshStandardMaterial).wireframe = wireframe;
        }
      }
    });
  }, [scene, wireframe]);

  return (
    <Center>
      <primitive ref={ref} object={scene} />
    </Center>
  );
}

function PlaceholderModel() {
  const meshRef = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.3;
  });
  return (
    <mesh ref={meshRef}>
      <boxGeometry args={[2, 0.5, 1.5]} />
      <meshStandardMaterial color="#0ea5e9" wireframe />
    </mesh>
  );
}

function ViewerControls() {
  const { wireframe, toggleWireframe, glbUrl } = useCADStore();
  return (
    <div style={{
      position: "absolute", top: 12, right: 12, display: "flex", gap: 6, zIndex: 10,
    }}>
      <button className="btn btn-ghost" style={{ fontSize: 11, padding: "5px 10px" }} onClick={toggleWireframe}>
        {wireframe ? "Solid" : "Wireframe"}
      </button>
      {glbUrl && (
        <div className="badge badge-success" style={{ fontSize: 10, padding: "4px 10px" }}>● Model Loaded</div>
      )}
    </div>
  );
}

function AxisOverlay() {
  return (
    <div style={{ position: "absolute", bottom: 16, left: 16, display: "flex", gap: 8, fontSize: 10, color: "var(--text-muted)" }}>
      <span style={{ color: "#ef4444" }}>X</span>
      <span style={{ color: "#22c55e" }}>Y</span>
      <span style={{ color: "#3b82f6" }}>Z</span>
      <span style={{ marginLeft: 4 }}>mm</span>
    </div>
  );
}

export default function ViewerCanvas() {
  const { glbUrl, wireframe, isGenerating } = useCADStore();

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", background: "radial-gradient(ellipse at center, #0f172a 0%, #020617 100%)" }}>
      <ViewerControls />
      <AxisOverlay />

      {isGenerating && (
        <div style={{
          position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
          zIndex: 10, textAlign: "center",
        }}>
          <div style={{ width: 48, height: 48, border: "2px solid var(--border)", borderTop: "2px solid var(--cyan)", borderRadius: "50%", margin: "0 auto 12px" }} className="animate-spin" />
          <div style={{ color: "var(--cyan)", fontSize: 13 }}>Generating geometry...</div>
        </div>
      )}

      <Canvas
        camera={{ position: [5, 4, 5], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
        shadows
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1.2} castShadow />
        <directionalLight position={[-5, 5, -5]} intensity={0.4} color="#22d3ee" />

        <Grid
          infiniteGrid
          cellSize={10}
          cellThickness={0.5}
          sectionSize={50}
          sectionThickness={1}
          cellColor="#1e293b"
          sectionColor="#334155"
          fadeDistance={200}
          fadeStrength={1}
        />

        <Suspense fallback={<PlaceholderModel />}>
          {glbUrl ? (
            <CADModel url={glbUrl} wireframe={wireframe} />
          ) : (
            <PlaceholderModel />
          )}
        </Suspense>

        <OrbitControls makeDefault enableDamping dampingFactor={0.05} />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
