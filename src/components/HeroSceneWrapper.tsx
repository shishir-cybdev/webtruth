"use client";

import dynamic from "next/dynamic";
import { HeroSceneFallback } from "./HeroScene3D";

const HeroScene3DLazy = dynamic(
  () => import("./HeroScene3D").then((m) => ({ default: m.HeroScene3D })),
  { ssr: false, loading: () => <HeroSceneFallback /> }
);

// Check WebGL support synchronously on client using a module-level cache
let webglCache: boolean | null = null;
function isWebGLSupported(): boolean {
  if (webglCache !== null) return webglCache;
  if (typeof window === "undefined") return true;
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    webglCache = !!gl;
    return webglCache;
  } catch {
    webglCache = false;
    return false;
  }
}

export function HeroSceneWrapper() {
  const supported = isWebGLSupported();
  if (!supported) return <HeroSceneFallback />;
  return <HeroScene3DLazy />;
}
