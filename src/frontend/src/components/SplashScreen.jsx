import React, { useEffect, useState, useRef, Suspense } from 'react';
import anime from 'animejs';
import { Canvas } from '@react-three/fiber';
import TrophyMesh from './TrophyMesh';
import logoUrl from '../assets/logo.svg';

export default function SplashScreen({ onComplete }) {
  const [percent, setPercent] = useState(0);
  const containerRef = useRef(null);
  const emblemRef = useRef(null);
  const barRef = useRef(null);
  const textRef = useRef(null);

  useEffect(() => {
    // 1. Animate percentage counter
    const obj = { value: 0 };
    const counterAnim = anime({
      targets: obj,
      value: 100,
      round: 1,
      easing: 'cubicBezier(0.4, 0, 0.2, 1)',
      duration: 2500,
      update: () => {
        setPercent(obj.value);
      }
    });

    // 2. Animate loading progress bar
    const barAnim = anime({
      targets: barRef.current,
      width: '100%',
      easing: 'cubicBezier(0.4, 0, 0.2, 1)',
      duration: 2500,
    });

    // 3. Animate emblem rotation and pulse
    const emblemAnim = anime({
      targets: emblemRef.current,
      scale: [0.85, 1.05, 1],
      opacity: [0, 1],
      duration: 2000,
      easing: 'easeOutQuint'
    });

    // 4. Outro transition
    Promise.all([counterAnim.finished, barAnim.finished, emblemAnim.finished]).then(() => {
      // Scale down text and emblem, then fade out container
      anime.timeline({
        complete: () => {
          if (onComplete) onComplete();
        }
      })
      .add({
        targets: [emblemRef.current, textRef.current, barRef.current?.parentNode],
        scale: 0.9,
        opacity: 0,
        duration: 400,
        easing: 'easeInQuad'
      })
      .add({
        targets: containerRef.current,
        opacity: 0,
        duration: 600,
        easing: 'easeOutQuad'
      });
    });
  }, [onComplete]);

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 z-50 bg-[#050505] flex flex-col items-center justify-center overflow-hidden"
    >
      {/* Background Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
      
      {/* Radial Gold Flare */}
      <div className="absolute w-[600px] h-[600px] bg-radial from-fifagold/10 to-transparent blur-[120px] pointer-events-none"></div>

      <div className="flex flex-col items-center gap-10 max-w-sm w-full px-6 relative z-10 select-none">
        
        {/* Animated 3D Golden Trophy Canvas & FIFA 26 Logo */}
        <div ref={emblemRef} className="relative w-64 h-64 flex items-center justify-center select-none">
          {/* Inner Glowing Ring */}
          <div className="absolute w-44 h-44 rounded-full border border-fifagold/10 animate-ping opacity-30"></div>
          {/* Double Gold Bezel */}
          <div className="absolute w-52 h-52 rounded-full border-2 border-dashed border-fifagold/20 animate-[spin_60s_linear_infinite] scale-95"></div>
          
          {/* 3D Rotating Trophy in Background */}
          <div className="absolute inset-0 z-0 opacity-40 pointer-events-none">
            <Canvas camera={{ position: [0, 1.2, 5.5], fov: 40 }} style={{ width: '100%', height: '100%' }}>
              <ambientLight intensity={0.4} />
              <directionalLight position={[5, 5, 5]} intensity={1.5} color="#fff" />
              <Suspense fallback={null}>
                <TrophyMesh />
              </Suspense>
            </Canvas>
          </div>

          {/* Official FIFA 26 WC Logo in Foreground */}
          <img 
            src={logoUrl} 
            className="w-24 h-36 object-contain z-10 filter drop-shadow-[0_0_15px_rgba(225,181,11,0.45)]"
            alt="Official FIFA 26 WC Logo"
          />
        </div>

        {/* Loading Information */}
        <div ref={textRef} className="text-center space-y-3">
          <div className="font-display font-black text-xl tracking-[0.25em] text-white uppercase">
            Goal<span className="text-fifagold">IQ</span> Engine
          </div>
          <div className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">
            World Cup 2026 Prediction System
          </div>
          <div className="font-mono text-2xl font-bold text-fifagold tabular-nums mt-4">
            {percent}%
          </div>
        </div>

        {/* Progress Bar Container */}
        <div className="w-full h-[2px] bg-white/5 rounded-full overflow-hidden border border-white/5">
          <div 
            ref={barRef}
            className="h-full bg-gradient-to-r from-fifagold to-fifagreen"
            style={{ width: '0%' }}
          ></div>
        </div>
      </div>
    </div>
  );
}
