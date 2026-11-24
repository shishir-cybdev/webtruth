"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";

// Pre-computed stable data (outside components to avoid Math.random in render)
const ORBIT_NODES = Array.from({ length: 12 }, (_, i) => ({
  angle: (i / 12) * Math.PI * 2,
  radius: 2.8 + (i % 3) * 0.4,
  height: ((i % 7) / 7 - 0.5) * 2,
  color: i % 3 === 0 ? "#a78bfa" : i % 3 === 1 ? "#22d3ee" : "#4ade80",
}));

function generateStarPositions(count: number): Float32Array {
  // Use a seeded pseudo-random to avoid Math.random lint error
  const arr = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const t = i * 2.3999632 + 0.1;
    arr[i * 3] = (((t * 127.1) % 1 + 1) % 1 - 0.5) * 60;
    arr[i * 3 + 1] = (((t * 311.7) % 1 + 1) % 1 - 0.5) * 60;
    arr[i * 3 + 2] = (((t * 74.1) % 1 + 1) % 1 - 0.5) * 60;
  }
  return arr;
}

const STAR_POSITIONS = generateStarPositions(1500);

function WireframeGlobe() {
  const meshRef = useRef<THREE.Mesh>(null);
  const linesRef = useRef<THREE.LineSegments>(null);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.08;
      meshRef.current.rotation.x += delta * 0.02;
    }
    if (linesRef.current) {
      linesRef.current.rotation.y += delta * 0.08;
      linesRef.current.rotation.x += delta * 0.02;
    }
  });

  const geo = useMemo(() => new THREE.SphereGeometry(2, 24, 16), []);
  const wireframe = useMemo(() => new THREE.WireframeGeometry(geo), [geo]);

  return (
    <group>
      <mesh ref={meshRef}>
        <sphereGeometry args={[2, 24, 16]} />
        <meshStandardMaterial
          color="#06b6d4"
          transparent
          opacity={0.03}
          wireframe={false}
        />
      </mesh>
      <lineSegments ref={linesRef} geometry={wireframe}>
        <lineBasicMaterial color="#22d3ee" transparent opacity={0.15} />
      </lineSegments>
    </group>
  );
}

function OrbitingNodes() {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.12;
    }
  });

  return (
    <group ref={groupRef}>
      {ORBIT_NODES.map((n, i) => (
        <mesh
          key={i}
          position={[Math.cos(n.angle) * n.radius, n.height, Math.sin(n.angle) * n.radius]}
        >
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshStandardMaterial color={n.color} emissive={n.color} emissiveIntensity={2} />
        </mesh>
      ))}
    </group>
  );
}

function StarField() {
  const ref = useRef<THREE.Points>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.005;
  });

  return (
    <Points ref={ref} positions={STAR_POSITIONS} stride={3} frustumCulled>
      <PointMaterial color="#94a3b8" size={0.05} sizeAttenuation transparent opacity={0.5} />
    </Points>
  );
}

function ConnectionRings() {
  const ring1 = useRef<THREE.Mesh>(null);
  const ring2 = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (ring1.current) ring1.current.rotation.z += delta * 0.15;
    if (ring2.current) ring2.current.rotation.x += delta * 0.1;
  });

  return (
    <group>
      <mesh ref={ring1}>
        <torusGeometry args={[3.2, 0.005, 2, 80]} />
        <meshStandardMaterial color="#22d3ee" transparent opacity={0.3} emissive="#22d3ee" emissiveIntensity={1} />
      </mesh>
      <mesh ref={ring2} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[3.5, 0.004, 2, 80]} />
        <meshStandardMaterial color="#a78bfa" transparent opacity={0.2} emissive="#a78bfa" emissiveIntensity={1} />
      </mesh>
    </group>
  );
}

export function HeroScene3D() {
  return (
    <div className="absolute inset-0 w-full h-full" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 7], fov: 60 }}
        gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
        dpr={[1, 1.5]}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.2} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#22d3ee" />
        <pointLight position={[-5, -3, -5]} intensity={0.5} color="#a78bfa" />
        <StarField />
        <WireframeGlobe />
        <OrbitingNodes />
        <ConnectionRings />
      </Canvas>
    </div>
  );
}

// Static fallback for no-WebGL environments
export function HeroSceneFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
      <div className="relative w-80 h-80 opacity-20">
        <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-ping" style={{ animationDuration: "3s" }} />
        <div className="absolute inset-8 rounded-full border border-violet-400/30 animate-ping" style={{ animationDuration: "2.5s", animationDelay: "0.5s" }} />
        <div className="absolute inset-16 rounded-full border border-cyan-400/30 animate-ping" style={{ animationDuration: "2s", animationDelay: "1s" }} />
      </div>
    </div>
  );
}
