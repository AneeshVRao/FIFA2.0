import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
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
        color="#d4af37" 
        size={0.065} 
        sizeAttenuation={true} 
        transparent 
        opacity={0.35} 
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
      <meshBasicMaterial color="hsl(140, 100%, 50%)" />
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
  const pinRefs = useRef({});

  return (
    <group>
      {/* 3D Sphere Globe representing North America Earth */}
      <mesh receiveShadow>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <meshStandardMaterial color="#05060b" roughness={0.9} metalness={0.2} />
      </mesh>

      {/* Procedural Dotted World Map */}
      <DottedGlobe />
      
      {/* Wireframe Outline for high-tech look */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS + 0.02, 24, 24]} />
        <meshBasicMaterial color="#d4af37" wireframe transparent opacity={0.07} />
      </mesh>

      {/* Render 16 Venue Pins */}
      {Object.entries(VENUE_COORDINATES).map(([vid, coords]) => {
        const pos = latLonToVector3(coords.lat, coords.lon);
        const isSelected = selectedVenueId === vid;
        
        return (
          <group key={vid} position={[pos.x, pos.y, pos.z]}>
            {/* Pulsing glow ring under pin */}
            <mesh>
              <ringGeometry args={[0.08, 0.12, 16]} />
              <meshBasicMaterial 
                color={isSelected ? "#39ff14" : "#d4af37"} 
                transparent 
                opacity={isSelected ? 0.8 : 0.4} 
                side={2}
              />
            </mesh>
            {/* Cartesian pointer */}
            <mesh 
              position={[0, 0, 0.1]} 
              onClick={(e) => {
                e.stopPropagation();
                onSelectVenue(vid);
              }}
            >
              <sphereGeometry args={[0.07, 16, 16]} />
              <meshBasicMaterial color={isSelected ? "#39ff14" : "#d4af37"} />
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
  const points = curve.getPoints(50);

  return (
    <Line
      points={points}
      color="hsl(45, 100%, 50%)"
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
      <div className="w-full h-full min-h-[400px] bg-[#070911] border border-white/5 rounded-[2rem] flex flex-col justify-between p-8 relative liquid-glass overflow-hidden">
        <div className="absolute top-6 left-6 z-10">
          <div className="text-xs uppercase font-display text-fifagold font-bold tracking-widest">
            2D fallback SVG broadcast layout
          </div>
          <h2 className="text-xl font-display text-white font-semibold mt-1">Host Venues</h2>
        </div>
        
        {/* Render 2D Map of North America venues */}
        <div className="flex-1 flex items-center justify-center p-4">
          <svg viewBox="0 0 800 450" className="w-full max-w-2xl h-auto opacity-70">
            {/* Outline of USA/Canada/Mexico */}
            <path d="M150,50 L650,50 L700,400 L200,400 Z" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={1} />
            
            {/* Draw Travel flight path in 2D if active */}
            {flightPath && (() => {
              const startCoords = VENUE_COORDINATES[flightPath.start.id];
              const endCoords = VENUE_COORDINATES[flightPath.end.id];
              if (startCoords && endCoords) {
                // Map coordinates roughly to SVG canvas size
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
                    stroke="hsl(45, 100%, 50%)"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                  />
                );
              }
            })()}

            {/* Plot 16 relative dots */}
            {Object.entries(VENUE_COORDINATES).map(([vid, data]) => {
              // rough projection mapping to canvas
              const mapX = (lon) => 400 + (lon + 95) * 8;
              const mapY = (lat) => 225 - (lat - 35) * 8;
              const x = mapX(data.lon);
              const y = mapY(data.lat);
              const isSelected = selectedVenueId === vid;
              
              return (
                <g key={vid} className="cursor-pointer" onClick={() => onSelectVenue(vid)}>
                  <circle cx={x} cy={y} r={isSelected ? 8 : 4} fill={isSelected ? "#39ff14" : "#d4af37"} />
                  {isSelected && <circle cx={x} cy={y} r={14} fill="none" stroke="#39ff14" strokeWidth={1.5} className="animate-ping" />}
                  <text x={x + 10} y={y + 4} fill={isSelected ? "#ffffff" : "rgba(255,255,255,0.4)"} fontSize="10" fontFamily="sans-serif">
                    {data.city}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* HUD Info */}
        <div className="flex justify-between items-center text-xs text-slate-500 border-t border-white/5 pt-4">
          <span>WebGL disabled: using lightweight 2D vectors</span>
          <span>16 Official Venues mapped</span>
        </div>
      </div>
    );
  }

  // 3D Canvas Globe Layout
  // Resolves flight path GPS from selected ID
  const resolvedFlightPath = flightPath ? {
    start: VENUE_COORDINATES[flightPath.start.id],
    end: VENUE_COORDINATES[flightPath.end.id]
  } : null;

  return (
    <div className="w-full h-full min-h-[450px] bg-[#070911] border border-white/5 rounded-[2rem] relative liquid-glass overflow-hidden">
      <div className="absolute top-6 left-6 z-10 pointer-events-none">
        <div className="text-xs uppercase font-display text-fifagold font-bold tracking-widest">
          3D interactive venue globe
        </div>
        <h2 className="text-xl font-display text-white font-semibold mt-1">North America Venues</h2>
      </div>

      {/* R3F Canvas Container */}
      <Canvas
        camera={{ position: [0, 0, 10], fov: 60 }}
        dpr={isMobile ? 1 : 2} // Clamp mobile DPR to 1 for high frame rates
        shadows
      >
        <GlobePins 
          selectedVenueId={selectedVenueId} 
          onSelectVenue={onSelectVenue}
          flightPath={resolvedFlightPath}
        />
        <OrbitControls 
          enableZoom={false} // Disable zoom to prevent scroll hijacking on mobile touch
          enablePan={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI - Math.PI / 4}
        />
      </Canvas>

      {/* Interactive Overlay Travel Telemetry */}
      {flightPath && (
        <div className="absolute bottom-6 left-6 right-6 flex justify-between items-center bg-black/40 backdrop-blur-md rounded-2xl p-4 border border-white/5 pointer-events-none">
          <div className="flex items-center gap-3">
            <TravelIcon className="w-5 h-5 text-fifagold" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-widest">Travel Distance</div>
              <div className="text-sm font-mono font-bold text-white">
                {flightPath.distance_km.toLocaleString()} km
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <AltitudeIcon className="w-5 h-5 text-fifagold" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-widest">Altitude Delta</div>
              <div className="text-sm font-mono font-bold text-white">
                {flightPath.altitude_diff_m.toLocaleString()} m
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
