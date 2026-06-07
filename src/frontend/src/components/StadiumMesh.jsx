import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';

export default function StadiumMesh({ capacity = 60000, altitude = 10, hostNation = "USA" }) {
  const haloRef = useRef();
  const lightsGroupRef = useRef();

  // 1. Procedural scaling based on stadium capacity
  // Base scale corresponds to 60k capacity. Larger capacity yields wider, taller seating tiers.
  const capScale = Math.max(0.6, Math.min(1.5, capacity / 60000));
  const innerRadius = 4.5 * capScale;
  const outerRadius = 7.0 * capScale;

  // 2. Host country lights colors
  // USA = Blue & Red, Mexico = Green & White, Canada = Red & White
  let lightColor1 = "#0000ff"; // USA default blue
  let lightColor2 = "#ff0000"; // USA default red
  if (hostNation.toLowerCase() === "mexico") {
    lightColor1 = "#00ff00"; // green
    lightColor2 = "#ffffff"; // white
  } else if (hostNation.toLowerCase() === "canada") {
    lightColor1 = "#ff0000"; // red
    lightColor2 = "#ffffff"; // white
  }

  // 3. High Altitude indicator ring animation (Azteca / Akron pulse)
  const isHighAltitude = altitude > 1500;

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    
    // Rotate lights group slowly
    if (lightsGroupRef.current) {
      lightsGroupRef.current.rotation.y = time * 0.2;
    }
    
    // Pulsate the golden high-altitude halo ring
    if (haloRef.current && isHighAltitude) {
      const pulse = 1.0 + Math.sin(time * 3.0) * 0.08;
      haloRef.current.scale.set(pulse, pulse, 1.0);
      haloRef.current.material.opacity = 0.4 + Math.sin(time * 3.0) * 0.15;
    }
  });

  return (
    <group>
      {/* Pitch (Standard green grass plane) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.4, 0]} receiveShadow>
        <planeGeometry args={[11.5, 7.5]} />
        <meshStandardMaterial color="#142618" roughness={0.9} />
      </mesh>
      
      {/* Pitch Line Markings */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.39, 0]}>
        <planeGeometry args={[11.3, 7.3]} />
        <meshBasicMaterial color="#ffffff" wireframe />
      </mesh>

      {/* Seating Ring Tier 1 (Lower Bowl) */}
      <mesh position={[0, 0.1, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[innerRadius + 0.5, innerRadius, 1.0, 32, 1, true]} />
        <meshStandardMaterial color="#1e2230" roughness={0.6} side={2} />
      </mesh>

      {/* Seating Ring Tier 2 (Middle Tier) */}
      <mesh position={[0, 0.8, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[innerRadius + 1.5, innerRadius + 1.0, 1.2, 32, 1, true]} />
        <meshStandardMaterial color="#171924" roughness={0.6} side={2} />
      </mesh>

      {/* Seating Ring Tier 3 (Upper Bowl) */}
      <mesh position={[0, 1.6, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[outerRadius, innerRadius + 2.0, 1.5, 32, 1, true]} />
        <meshStandardMaterial color="#0f111a" roughness={0.6} side={2} />
      </mesh>

      {/* Roof Ring Structure */}
      <mesh position={[0, 2.4, 0]} castShadow>
        <cylinderGeometry args={[outerRadius + 0.5, outerRadius, 0.2, 32, 1, true]} />
        <meshStandardMaterial color="#ffffff" metalness={0.8} roughness={0.2} side={2} />
      </mesh>

      {/* High-Altitude Golden Halo Indicator */}
      {isHighAltitude && (
        <mesh ref={haloRef} position={[0, 2.8, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[outerRadius - 0.2, outerRadius + 0.3, 64]} />
          <meshBasicMaterial color="#d4af37" transparent opacity={0.6} depthWrite={false} side={2} />
        </mesh>
      )}

      {/* Procedural Floodlights Beams */}
      <group ref={lightsGroupRef}>
        {/* Corner 1 Spot */}
        <spotLight
          position={[-6, 5, -4]}
          angle={0.6}
          penumbra={0.5}
          intensity={8.0}
          color={lightColor1}
          castShadow
        />
        {/* Corner 2 Spot */}
        <spotLight
          position={[6, 5, 4]}
          angle={0.6}
          penumbra={0.5}
          intensity={8.0}
          color={lightColor2}
          castShadow
        />
        {/* Corner 3 Spot */}
        <spotLight
          position={[-6, 5, 4]}
          angle={0.6}
          penumbra={0.5}
          intensity={8.0}
          color={lightColor2}
          castShadow
        />
        {/* Corner 4 Spot */}
        <spotLight
          position={[6, 5, -4]}
          angle={0.6}
          penumbra={0.5}
          intensity={8.0}
          color={lightColor1}
          castShadow
        />
      </group>
      
      {/* Ambient Pit Light */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[0, 10, 0]} intensity={0.8} castShadow />
    </group>
  );
}
