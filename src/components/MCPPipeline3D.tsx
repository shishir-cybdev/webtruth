"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Line, Points, PointMaterial } from "@react-three/drei";
import * as THREE from "three";
import type { BackendStepStatus } from "@/types/api";

export interface MCPNodeState {
  browser: BackendStepStatus;
  evidence: BackendStepStatus;
  comparison: BackendStepStatus;
  trust: BackendStepStatus;
}

const NODE_CONFIGS: Array<{
  key: keyof MCPNodeState;
  label: string;
  subtitle: string;
  position: [number, number, number];
  baseColor: string;
}> = [
  { key: "browser", label: "Browser MCP", subtitle: "Playwright", position: [-3.3, 0.45, 0], baseColor: "#22d3ee" },
  { key: "evidence", label: "Evidence MCP", subtitle: "SQLite Vault", position: [-1.1, 0.1, 0.2], baseColor: "#4ade80" },
  { key: "comparison", label: "Comparison MCP", subtitle: "Normalizer", position: [1.1, 0.45, -0.2], baseColor: "#a78bfa" },
  { key: "trust", label: "Trust MCP", subtitle: "Integrity", position: [3.3, 0.1, 0], baseColor: "#38bdf8" },
];

function generateAmbientParticles(count: number): Float32Array {
  const arr = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const t = i * 1.6180339 + 0.37;
    arr[i * 3] = (((t * 97.3) % 1 + 1) % 1 - 0.5) * 14;
    arr[i * 3 + 1] = (((t * 193.7) % 1 + 1) % 1 - 0.5) * 6;
    arr[i * 3 + 2] = (((t * 53.1) % 1 + 1) % 1 - 0.5) * 6;
  }
  return arr;
}

const AMBIENT_PARTICLES = generateAmbientParticles(220);

function getStatusVisuals(status: BackendStepStatus, baseColor: string) {
  switch (status) {
    case "running":
      return { color: "#a78bfa", emissiveIntensity: 2.2, scale: 1.18, opacity: 0.95 };
    case "completed":
      return { color: baseColor, emissiveIntensity: 1.5, scale: 1.05, opacity: 0.9 };
    case "failed":
      return { color: "#f87171", emissiveIntensity: 1.8, scale: 1.0, opacity: 0.9 };
    case "skipped":
      return { color: "#64748b", emissiveIntensity: 0.2, scale: 0.85, opacity: 0.4 };
    case "pending":
    default:
      return { color: "#334155", emissiveIntensity: 0.25, scale: 0.92, opacity: 0.55 };
  }
}

function MCPNodeMesh({
  position,
  status,
  baseColor,
  reducedMotion,
}: {
  position: [number, number, number];
  status: BackendStepStatus;
  baseColor: string;
  reducedMotion: boolean;
}) {
  const coreRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const visuals = getStatusVisuals(status, baseColor);

  useFrame((state, delta) => {
    if (reducedMotion) return;
    const speed = status === "running" ? 1.8 : status === "completed" ? 0.5 : 0.15;
    if (coreRef.current) {
      coreRef.current.rotation.y += delta * speed;
      coreRef.current.rotation.x += delta * speed * 0.4;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z -= delta * speed * 0.8;
      if (status === "running") {
        const pulse = 1 + Math.sin(state.clock.elapsedTime * 4.5) * 0.12;
        ringRef.current.scale.set(pulse, pulse, pulse);
      } else {
        ringRef.current.scale.set(1, 1, 1);
      }
    }
  });

  return (
    <group position={position} scale={visuals.scale}>
      {/* Core Octahedron */}
      <mesh ref={coreRef}>
        <octahedronGeometry args={[0.42, 0]} />
        <meshStandardMaterial
          color={visuals.color}
          emissive={visuals.color}
          emissiveIntensity={visuals.emissiveIntensity}
          wireframe={status === "pending"}
          transparent
          opacity={visuals.opacity}
          roughness={0.2}
          metalness={0.7}
        />
      </mesh>

      {/* Outer Orbit Ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 3, 0, 0]}>
        <torusGeometry args={[0.64, 0.018, 8, 36]} />
        <meshStandardMaterial
          color={visuals.color}
          emissive={visuals.color}
          emissiveIntensity={status === "running" ? 2.0 : 0.8}
          transparent
          opacity={status === "pending" ? 0.25 : 0.8}
        />
      </mesh>
    </group>
  );
}

function EnergyPath({
  start,
  end,
  active,
  completed,
  reducedMotion,
}: {
  start: [number, number, number];
  end: [number, number, number];
  active: boolean;
  completed: boolean;
  reducedMotion: boolean;
}) {
  const pulseRef = useRef<THREE.Mesh>(null);
  const points = useMemo(() => [start, end], [start, end]);

  useFrame((state) => {
    if (reducedMotion || !pulseRef.current) return;
    if (!active && !completed) {
      pulseRef.current.visible = false;
      return;
    }
    pulseRef.current.visible = true;
    const speed = active ? 1.4 : 0.55;
    const t = (state.clock.elapsedTime * speed) % 1;
    pulseRef.current.position.set(
      start[0] + (end[0] - start[0]) * t,
      start[1] + (end[1] - start[1]) * t,
      start[2] + (end[2] - start[2]) * t
    );
  });

  const lineColor = active ? "#a78bfa" : completed ? "#22d3ee" : "#1e293b";

  return (
    <group>
      <Line
        points={points}
        color={lineColor}
        lineWidth={active ? 2.5 : completed ? 1.8 : 1}
        transparent
        opacity={active ? 0.9 : completed ? 0.65 : 0.4}
      />
      <mesh ref={pulseRef} visible={false}>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshStandardMaterial
          color={active ? "#22d3ee" : "#4ade80"}
          emissive={active ? "#22d3ee" : "#4ade80"}
          emissiveIntensity={2.5}
        />
      </mesh>
    </group>
  );
}

function AmbientParticlesField({ reducedMotion }: { reducedMotion: boolean }) {
  const ref = useRef<THREE.Points>(null);
  useFrame((_, delta) => {
    if (reducedMotion || !ref.current) return;
    ref.current.rotation.y += delta * 0.03;
  });

  return (
    <Points ref={ref} positions={AMBIENT_PARTICLES} stride={3} frustumCulled>
      <PointMaterial color="#38bdf8" size={0.04} sizeAttenuation transparent opacity={0.45} />
    </Points>
  );
}

export function MCPPipeline3D({
  nodeStates,
  reducedMotion,
}: {
  nodeStates: MCPNodeState;
  reducedMotion: boolean;
}) {
  return (
    <Canvas
      camera={{ position: [0, 0.3, 6.2], fov: 45 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.45} />
      <pointLight position={[5, 5, 5]} intensity={1.2} color="#22d3ee" />
      <pointLight position={[-5, -3, 4]} intensity={0.8} color="#a78bfa" />

      <AmbientParticlesField reducedMotion={reducedMotion} />

      {/* Connecting Energy Paths */}
      <EnergyPath
        start={NODE_CONFIGS[0].position}
        end={NODE_CONFIGS[1].position}
        active={nodeStates.browser === "running" || nodeStates.evidence === "running"}
        completed={nodeStates.browser === "completed"}
        reducedMotion={reducedMotion}
      />
      <EnergyPath
        start={NODE_CONFIGS[1].position}
        end={NODE_CONFIGS[2].position}
        active={nodeStates.evidence === "running" || nodeStates.comparison === "running"}
        completed={nodeStates.evidence === "completed"}
        reducedMotion={reducedMotion}
      />
      <EnergyPath
        start={NODE_CONFIGS[2].position}
        end={NODE_CONFIGS[3].position}
        active={nodeStates.comparison === "running" || nodeStates.trust === "running"}
        completed={nodeStates.comparison === "completed"}
        reducedMotion={reducedMotion}
      />

      {/* Four MCP Nodes */}
      {NODE_CONFIGS.map((cfg) => (
        <MCPNodeMesh
          key={cfg.key}
          position={cfg.position}
          status={nodeStates[cfg.key]}
          baseColor={cfg.baseColor}
          reducedMotion={reducedMotion}
        />
      ))}
    </Canvas>
  );
}
