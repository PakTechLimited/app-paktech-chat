"use client";

import { useMemo, useRef, useSyncExternalStore } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useTheme } from "next-themes";
import * as THREE from "three";

// Brand colours per theme (kept in sync with --brand-* in globals.css).
const PALETTE = {
  light: { line: "#6b46b5", node: "#a62f97", arc: "#6b46b5" },
  dark: { line: "#9b7fd4", node: "#c46bb5", arc: "#7c5cbf" },
} as const;

// Fixed lat/lon "offices": deterministic, so the picture is the same on every visit.
const NODES: Array<[number, number]> = [
  [24.9, 67.0], // Karachi
  [43.7, -79.4], // Toronto
  [51.5, -0.1], // London
  [25.2, 55.3], // Dubai
  [1.3, 103.8], // Singapore
  [37.8, -122.4], // San Francisco
];
const ARCS: Array<[number, number]> = [[0, 1], [0, 2], [0, 3], [3, 4], [1, 5], [2, 1]];

function toVec(lat: number, lon: number, r = 1): THREE.Vector3 {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lon + 180);
  return new THREE.Vector3(
    -r * Math.sin(phi) * Math.cos(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.sin(theta)
  );
}

function Globe({ mode, animate }: { mode: "light" | "dark"; animate: boolean }) {
  const group = useRef<THREE.Group>(null);
  const colors = PALETTE[mode];

  const wire = useMemo(
    () => new THREE.WireframeGeometry(new THREE.SphereGeometry(1, 20, 12)),
    []
  );
  const nodes = useMemo(() => NODES.map(([a, b]) => toVec(a, b, 1.01)), []);
  const arcs = useMemo(
    () =>
      ARCS.map(([a, b]) => {
        const mid = nodes[a].clone().add(nodes[b]).multiplyScalar(0.5);
        mid.setLength(1 + nodes[a].distanceTo(nodes[b]) * 0.45);
        const curve = new THREE.QuadraticBezierCurve3(nodes[a], mid, nodes[b]);
        return new THREE.BufferGeometry().setFromPoints(curve.getPoints(40));
      }),
    [nodes]
  );

  useFrame((_, delta) => {
    if (animate && group.current) group.current.rotation.y += delta * 0.18;
  });

  return (
    <group ref={group} rotation={[0.35, -1.2, 0]}>
      <lineSegments geometry={wire}>
        <lineBasicMaterial color={colors.line} transparent opacity={0.4} />
      </lineSegments>
      {nodes.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.028, 12, 12]} />
          <meshBasicMaterial color={colors.node} />
        </mesh>
      ))}
      {arcs.map((g, i) => (
        <lineSegments key={i} geometry={g}>
          <lineBasicMaterial color={colors.arc} transparent opacity={0.75} />
        </lineSegments>
      ))}
    </group>
  );
}

const subscribe = () => () => {};

function hasWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

const wideQuery = "(min-width: 1024px)";
const subscribeWide = (cb: () => void) => {
  const m = window.matchMedia(wideQuery);
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
};

const reducedMotionQuery = "(prefers-reduced-motion: reduce)";
const subscribeMotion = (cb: () => void) => {
  const m = window.matchMedia(reducedMotionQuery);
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
};

/**
 * Decorative 3D globe for the login screen. Loaded lazily (see auth-screen), renders nothing
 * where WebGL is missing, and holds still when the OS asks for reduced motion.
 */
export default function LoginGlobe({ className }: { className?: string }) {
  const { resolvedTheme } = useTheme();
  const webgl = useSyncExternalStore(subscribe, hasWebGL, () => false);
  const reduced = useSyncExternalStore(
    subscribeMotion,
    () => window.matchMedia(reducedMotionQuery).matches,
    () => false
  );
  const wide = useSyncExternalStore(
    subscribeWide,
    () => window.matchMedia(wideQuery).matches,
    () => false
  );
  // Skip the work entirely on small screens, where the side panel is hidden anyway.
  if (!webgl || !wide) return null;

  return (
    <div className={className} aria-hidden="true">
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0, 3.1], fov: 40 }}
        frameloop={reduced ? "demand" : "always"}
        gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
      >
        <Globe mode={resolvedTheme === "dark" ? "dark" : "light"} animate={!reduced} />
      </Canvas>
    </div>
  );
}
