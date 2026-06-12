import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { TravelIcon, AltitudeIcon } from './Icons';

// GPS Coordinate mapping to 3D Cartesian coordinates on sphere of radius R
const GLOBE_RADIUS = 5.0;

function latLonToVector3(lat, lon, radius = GLOBE_RADIUS) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  
  const x = -(radius * Math.sin(phi) * Math.sin(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.cos(theta);
  
  return new THREE.Vector3(x, y, z);
}

// Procedural World Map boundary detector
function isLand(lat, lon) {
  // North America
  if (lat > 12 && lat < 75 && lon > -170 && lon < -50) return true;
  // South America
  if (lat > -56 && lat <= 12 && lon > -90 && lon < -34) return true;
  // Africa
  if (lat > -35 && lat < 37 && lon > -20 && lon < 52) return true;
  // Europe
  if (lat > 35 && lat < 72 && lon > -25 && lon < 45) return true;
  // Asia
  if (lat > 5 && lat < 75 && lon >= 45 && lon < 180) return true;
  // Australia
  if (lat > -45 && lat < -10 && lon > 110 && lon < 155) return true;
  // Greenland
  if (lat >= 60 && lat < 85 && lon > -75 && lon < -15) return true;
  // Antarctica
  if (lat < -60) return true;
  return false;
}

// Procedural Dotted World Map particles
function DottedGlobe() {
  const pointsGeometry = useMemo(() => {
    const positions = [];
    // Distribute points uniformly on sphere and filter by landmass boundaries
    for (let i = 0; i < 22000; i++) {
      const lon = Math.random() * 360 - 180;
      const lat = Math.asin(Math.random() * 2 - 1) * (180 / Math.PI);
      if (isLand(lat, lon)) {
        const vec = latLonToVector3(lat, lon, GLOBE_RADIUS + 0.01);
        positions.push(vec.x, vec.y, vec.z);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    return geometry;
  }, []);

  return (
    <points geometry={pointsGeometry}>
      <pointsMaterial 
        color="#888888" 
        size={0.03} 
        sizeAttenuation={true} 
        transparent 
        opacity={0.3} 
      />
    </points>
  );
}

// Moving animated glowing pulse along travel flight path
function TravelPulse({ start, end }) {
  const startVec = latLonToVector3(start.lat, start.lon, GLOBE_RADIUS + 0.06);
  const endVec = latLonToVector3(end.lat, end.lon, GLOBE_RADIUS + 0.06);
  
  const midVec = new THREE.Vector3().addVectors(startVec, endVec).multiplyScalar(0.5);
  const dist = startVec.distanceTo(endVec);
  midVec.normalize().multiplyScalar(GLOBE_RADIUS + 0.2 + dist * 0.15); // curved height
  
  const curve = useMemo(() => new THREE.QuadraticBezierCurve3(startVec, midVec, endVec), [start, end]);
  const pulseRef = useRef();
  
  useFrame((state) => {
    const t = (state.clock.getElapsedTime() * 0.45) % 1.0; // loops every ~2.2 seconds
    if (pulseRef.current) {
      const pos = curve.getPointAt(t);
      pulseRef.current.position.copy(pos);
    }
  });
  
  return (
    <mesh ref={pulseRef}>
      <sphereGeometry args={[0.075, 8, 8]} />
      {/* Bloom threshold will pick up colors > 1 */}
      <meshBasicMaterial color={[0, 4, 2]} toneMapped={false} />
    </mesh>
  );
}

// 16 Official Venue GPS coordinates
const VENUE_COORDINATES = {
  v_atlanta: { lat: 33.7553, lon: -84.4006, name: "Mercedes-Benz Stadium", city: "Atlanta", alt: 315, nation: "USA" },
  v_boston: { lat: 42.0909, lon: -71.2643, name: "Gillette Stadium", city: "Boston", alt: 85, nation: "USA" },
  v_dallas: { lat: 32.7473, lon: -97.0945, name: "AT&T Stadium", city: "Dallas", alt: 180, nation: "USA" },
  v_guadalajara: { lat: 20.6811, lon: -103.4627, name: "Estadio Akron", city: "Guadalajara", alt: 1560, nation: "Mexico" },
  v_houston: { lat: 29.6847, lon: -95.4081, name: "NRG Stadium", city: "Houston", alt: 15, nation: "USA" },
  v_kansascity: { lat: 39.0489, lon: -94.4839, name: "Arrowhead Stadium", city: "Kansas City", alt: 275, nation: "USA" },
  v_losangeles: { lat: 33.9534, lon: -118.3392, name: "SoFi Stadium", city: "Los Angeles", alt: 40, nation: "USA" },
  v_mexicocity: { lat: 19.3030, lon: -99.1505, name: "Estadio Azteca", city: "Mexico City", alt: 2240, nation: "Mexico" },
  v_miami: { lat: 25.9578, lon: -80.2388, name: "Hard Rock Stadium", city: "Miami", alt: 3, nation: "USA" },
  v_monterrey: { lat: 25.6700, lon: -100.2440, name: "Estadio BBVA", city: "Monterrey", alt: 535, nation: "Mexico" },
  v_newyork: { lat: 40.8135, lon: -74.0744, name: "MetLife Stadium", city: "New York", alt: 10, nation: "USA" },
  v_philadelphia: { lat: 39.9008, lon: -75.1675, name: "Lincoln Financial Field", city: "Philadelphia", alt: 5, nation: "USA" },
  v_sanfrancisco: { lat: 37.4032, lon: -121.9698, name: "Levi's Stadium", city: "San Francisco", alt: 12, nation: "USA" },
  v_seattle: { lat: 47.5952, lon: -122.3316, name: "Lumen Field", city: "Seattle", alt: 4, nation: "USA" },
  v_toronto: { lat: 43.6328, lon: -79.4186, name: "BMO Field", city: "Toronto", alt: 76, nation: "Canada" },
  v_vancouver: { lat: 49.2767, lon: -123.1119, name: "BC Place", city: "Vancouver", alt: 5, nation: "Canada" }
};

// 3D Pins Component inside Canvas
function GlobePins({ selectedVenueId, onSelectVenue, flightPath }) {
  return (
    <group>
      {/* 3D Sphere Globe representing Earth Core (Vantablack) */}
      <mesh receiveShadow>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <meshStandardMaterial color="#020202" roughness={0.9} metalness={0.1} />
      </mesh>

      {/* Procedural Dotted World Map */}
      <DottedGlobe />
      
      {/* Subtle Atmospheric glow */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS + 0.015, 64, 64]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={0.02} side={THREE.BackSide} />
      </mesh>

      {/* Render 16 Venue Pins */}
      {Object.entries(VENUE_COORDINATES).map(([vid, coords]) => {
        const pos = latLonToVector3(coords.lat, coords.lon);
        const isSelected = selectedVenueId === vid;
        
        return (
          <group key={vid} position={[pos.x, pos.y, pos.z]}>
            {/* Glowing pin base */}
            <mesh>
              <ringGeometry args={[0.04, 0.08, 32]} />
              <meshBasicMaterial 
                color={isSelected ? [0, 4, 2] : [1, 1, 1]} 
                toneMapped={false}
                transparent 
                opacity={isSelected ? 1 : 0.2} 
                side={2}
              />
            </mesh>
            {/* Cartesian pointer */}
            <mesh 
              position={[0, 0, 0.05]} 
              onClick={(e) => {
                e.stopPropagation();
                onSelectVenue(vid);
              }}
            >
              <sphereGeometry args={[0.06, 16, 16]} />
              <meshBasicMaterial color={isSelected ? [0, 5, 2] : "#444444"} toneMapped={false} />
            </mesh>
          </group>
        );
      })}

      {/* Render Travel flight path Bezier line if active */}
      {flightPath && (
        <>
          <FlightPathLine start={flightPath.start} end={flightPath.end} />
          <TravelPulse start={flightPath.start} end={flightPath.end} />
        </>
      )}
    </group>
  );
}

// Draws a curved flight path trajectory
function FlightPathLine({ start, end }) {
  const startVec = latLonToVector3(start.lat, start.lon, GLOBE_RADIUS + 0.05);
  const endVec = latLonToVector3(end.lat, end.lon, GLOBE_RADIUS + 0.05);
  
  // Calculate mid-point and raise it to represent altitude arc
  const midVec = new THREE.Vector3().addVectors(startVec, endVec).multiplyScalar(0.5);
  const dist = startVec.distanceTo(endVec);
  midVec.normalize().multiplyScalar(GLOBE_RADIUS + 0.2 + dist * 0.15); // curved elevation

  const curve = new THREE.QuadraticBezierCurve3(startVec, midVec, endVec);
  const points = curve.getPoints(64);

  return (
    <Line
      points={points}
      color={[0, 2, 1]} // Glowing green
      toneMapped={false}
      lineWidth={1.5}
      transparent
      opacity={0.8}
    />
  );
}

// Main Map Container with WebGL detection
export default function BroadcastMap({ selectedVenueId, onSelectVenue, flightPath }) {
  const [webGLSupported, setWebGLSupported] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // 1. Detect WebGL capabilities
  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const support = !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
      setWebGLSupported(support);
    } catch (e) {
      setWebGLSupported(false);
    }
    
    // Check mobile user agents
    setIsMobile(/iPhone|iPad|Android/i.test(navigator.userAgent));
  }, []);

  // 2D SVG Fallback Map
  if (!webGLSupported) {
    return (
      <div className="w-full h-full min-h-[400px] bg-[#050505] ring-1 ring-white/10 rounded-[2rem] p-1.5 flex flex-col relative overflow-hidden">
        <div className="w-full h-full bg-[#0a0a0a] rounded-[calc(2rem-0.375rem)] p-8 flex flex-col justify-between shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] relative">
          <div className="absolute top-8 left-8 z-10">
            <div className="text-[10px] uppercase font-mono text-fifagold tracking-[0.2em]">
              2D Fallback SVG
            </div>
            <h2 className="text-3xl font-display text-white tracking-tight mt-2">Host Venues</h2>
          </div>
          
          <div className="flex-1 flex items-center justify-center p-4">
            <svg viewBox="0 0 800 450" className="w-full max-w-2xl h-auto opacity-40">
              <path d="M150,50 L650,50 L700,400 L200,400 Z" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
              
              {flightPath && (() => {
                const startCoords = VENUE_COORDINATES[flightPath.start.id];
                const endCoords = VENUE_COORDINATES[flightPath.end.id];
                if (startCoords && endCoords) {
                  const mapX = (lon) => 400 + (lon + 95) * 8;
                  const mapY = (lat) => 225 - (lat - 35) * 8;
                  const sx = mapX(startCoords.lon);
                  const sy = mapY(startCoords.lat);
                  const ex = mapX(endCoords.lon);
                  const ey = mapY(endCoords.lat);
                  return (
                    <path
                      d={`M${sx},${sy} Q${(sx+ex)/2},${Math.min(sy,ey)-50} ${ex},${ey}`}
                      fill="none"
                      stroke="hsl(140, 100%, 50%)"
                      strokeWidth={1}
                      strokeDasharray="4 4"
                    />
                  );
                }
              })()}

              {Object.entries(VENUE_COORDINATES).map(([vid, data]) => {
                const mapX = (lon) => 400 + (lon + 95) * 8;
                const mapY = (lat) => 225 - (lat - 35) * 8;
                const x = mapX(data.lon);
                const y = mapY(data.lat);
                const isSelected = selectedVenueId === vid;
                
                return (
                  <g key={vid} className="cursor-pointer" onClick={() => onSelectVenue(vid)}>
                    <circle cx={x} cy={y} r={isSelected ? 6 : 3} fill={isSelected ? "hsl(140, 100%, 50%)" : "#ffffff"} />
                    {isSelected && <circle cx={x} cy={y} r={12} fill="none" stroke="hsl(140, 100%, 50%)" strokeWidth={1} className="animate-ping" />}
                    <text x={x + 10} y={y + 3} fill={isSelected ? "#ffffff" : "rgba(255,255,255,0.4)"} fontSize="10" fontFamily="Space Grotesk">
                      {data.city}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
          
          <div className="flex justify-between items-center text-[10px] text-white/30 border-t border-white/5 pt-6 font-mono tracking-widest">
            <span>WEBGL DISABLED</span>
            <span>16 OFFICIAL VENUES</span>
          </div>
        </div>
      </div>
    );
  }

  // 3D Canvas Globe Layout with Double-Bezel Ethereal Glass
  const resolvedFlightPath = flightPath ? {
    start: VENUE_COORDINATES[flightPath.start.id],
    end: VENUE_COORDINATES[flightPath.end.id]
  } : null;

  return (
    <div className="w-full h-full min-h-[500px] bg-[#050505] ring-1 ring-white/10 rounded-[2rem] p-1.5 flex flex-col relative overflow-hidden group">
      {/* Inner Core */}
      <div className="w-full h-full bg-[#080808] rounded-[calc(2rem-0.375rem)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] relative overflow-hidden">
        
        <div className="absolute top-8 left-8 z-10 pointer-events-none">
          <div className="text-[10px] uppercase font-mono text-white/50 tracking-[0.2em]">
            Interactive Telemetry
          </div>
          <h2 className="text-3xl font-display text-white tracking-tight mt-2">Global Venues</h2>
        </div>

        {/* R3F Canvas Container */}
        <Canvas
          camera={{ position: [0, 0, 10], fov: 60 }}
          dpr={isMobile ? 1 : [1, 2]}
          gl={{ antialias: false }} // Post-processing handles antialiasing
        >
          <color attach="background" args={['#080808']} />
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          
          <GlobePins 
            selectedVenueId={selectedVenueId} 
            onSelectVenue={onSelectVenue}
            flightPath={resolvedFlightPath}
          />
          
          <OrbitControls 
            enableZoom={false} 
            enablePan={false}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI - Math.PI / 4}
            autoRotate
            autoRotateSpeed={0.5}
          />

          <EffectComposer disableNormalPass>
            <Bloom luminanceThreshold={1} mipmapBlur intensity={1.5} />
            <Vignette eskil={false} offset={0.1} darkness={1.1} />
          </EffectComposer>
        </Canvas>

        {/* Interactive Overlay Travel Telemetry */}
        {flightPath && (
          <div className="absolute bottom-8 left-8 right-8 flex justify-between items-center bg-black/60 backdrop-blur-2xl rounded-full p-4 px-8 border border-white/10 pointer-events-none transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                <TravelIcon className="w-5 h-5 text-white" strokeWidth={1} />
              </div>
              <div>
                <div className="text-[10px] text-white/50 font-mono tracking-widest">DISTANCE</div>
                <div className="text-lg font-display text-white">
                  {flightPath.distance_km.toLocaleString()} <span className="text-sm text-white/50">km</span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                <AltitudeIcon className="w-5 h-5 text-white" strokeWidth={1} />
              </div>
              <div>
                <div className="text-[10px] text-white/50 font-mono tracking-widest">ALTITUDE DELTA</div>
                <div className="text-lg font-display text-white">
                  {flightPath.altitude_diff_m.toLocaleString()} <span className="text-sm text-white/50">m</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
