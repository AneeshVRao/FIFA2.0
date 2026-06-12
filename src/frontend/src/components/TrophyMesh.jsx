import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';

export default function TrophyMesh() {
  const groupRef = useRef();

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    if (groupRef.current) {
      // Rotate the trophy
      groupRef.current.rotation.y = time * 0.8;
      // Gentle floating animation
      groupRef.current.position.y = -1.2 + Math.sin(time * 1.5) * 0.15;
    }
  });

  return (
    <group ref={groupRef} position={[0, -1.2, 0]}>
      {/* 1. Lower Base Plinth (Malachite Green) */}
      <mesh position={[0, 0.15, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[1.2, 1.3, 0.3, 32]} />
        <meshStandardMaterial color="#0c3823" roughness={0.2} metalness={0.1} />
      </mesh>

      {/* 2. Gold Band 1 */}
      <mesh position={[0, 0.32, 0]} castShadow>
        <cylinderGeometry args={[1.15, 1.2, 0.05, 32]} />
        <meshStandardMaterial color="#d4af37" roughness={0.15} metalness={0.9} />
      </mesh>

      {/* 3. Middle Base Plinth (Malachite Green) */}
      <mesh position={[0, 0.5, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[1.05, 1.15, 0.3, 32]} />
        <meshStandardMaterial color="#0c3823" roughness={0.2} metalness={0.1} />
      </mesh>

      {/* 4. Gold Band 2 */}
      <mesh position={[0, 0.68, 0]} castShadow>
        <cylinderGeometry args={[1.0, 1.05, 0.05, 32]} />
        <meshStandardMaterial color="#d4af37" roughness={0.15} metalness={0.9} />
      </mesh>

      {/* 5. Tapered Gold Stem (Body of the trophy) */}
      <mesh position={[0, 1.3, 0]} castShadow>
        <cylinderGeometry args={[0.5, 0.9, 1.2, 32]} />
        <meshStandardMaterial color="#d4af37" roughness={0.2} metalness={0.9} />
      </mesh>

      {/* 6. Spiral Arm Left (Procedural approximation of the two figures holding the globe) */}
      <mesh position={[-0.35, 2.0, 0]} rotation={[0, 0, -0.35]} castShadow>
        <cylinderGeometry args={[0.22, 0.35, 0.8, 16]} />
        <meshStandardMaterial color="#d4af37" roughness={0.2} metalness={0.9} />
      </mesh>

      {/* 7. Spiral Arm Right */}
      <mesh position={[0.35, 2.0, 0]} rotation={[0, 0, 0.35]} castShadow>
        <cylinderGeometry args={[0.22, 0.35, 0.8, 16]} />
        <meshStandardMaterial color="#d4af37" roughness={0.2} metalness={0.9} />
      </mesh>

      {/* 8. The Globe (Held at the top of the trophy) */}
      <mesh position={[0, 2.5, 0]} castShadow>
        <sphereGeometry args={[0.55, 32, 32]} />
        <meshStandardMaterial color="#d4af37" roughness={0.1} metalness={0.9} />
      </mesh>

      {/* 9. Continental Lines embossed on the globe (Ring details) */}
      <mesh position={[0, 2.5, 0]} rotation={[0.4, 0.5, 0.2]}>
        <torusGeometry args={[0.56, 0.02, 8, 32]} />
        <meshStandardMaterial color="#1e2230" roughness={0.5} metalness={0.1} />
      </mesh>
      
      <mesh position={[0, 2.5, 0]} rotation={[-0.3, -0.6, 0.5]}>
        <torusGeometry args={[0.56, 0.015, 8, 32]} />
        <meshStandardMaterial color="#1e2230" roughness={0.5} metalness={0.1} />
      </mesh>

      {/* Lights inside the local group */}
      <pointLight position={[2, 3, 2]} intensity={2.0} color="#ffffff" />
      <pointLight position={[-2, 1, -2]} intensity={1.0} color="#ffaa44" />
    </group>
  );
}
