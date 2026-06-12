import React from 'react';

// Iconsax-style ultra-light SVG icons (stroke-width 1)
export const TrophyIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    {/* FIFA World Cup Trophy Silhouette */}
    <circle cx="12" cy="6" r="3" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.5 8.5C8 12 8 16 9 19h6c1-3 1-7-.5-10.5" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 19v1a1 1 0 001 1h2a1 1 0 001-1v-1" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 14h4" />
  </svg>
);

export const SoccerBallIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <circle cx="12" cy="12" r="9" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8l-2.5 2 1 3h3l1-3L12 8z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8V3m-2.5 7L5 8.5M10.5 13l-2.5 3.5m3 0v4.5m1-4.5l2.5 3.5m-1-7l4.5-1.5" />
  </svg>
);

export const StadiumIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <ellipse cx="12" cy="12" rx="9" ry="5" />
    <ellipse cx="12" cy="12" rx="6" ry="3.2" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12v3m12-3v3M12 7.2v9.6M9 8.8v6.4M15 8.8v6.4" />
  </svg>
);

export const TravelIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" strokeDasharray="3 3" d="M3 12c4-6 10-6 14 0" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M16 11l3 1-3 1v-2z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12h-2m-8 6h5m-7-12h3" />
  </svg>
);

export const AltitudeIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 20l6-8 4 5 8-11" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeDasharray="2 2" d="M3 6h18M3 11h18M3 16h18" />
  </svg>
);

export const WarningIcon = ({ className = "w-6 h-6", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

export const CloseIcon = ({ className = "w-5 h-5", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export const PlayIcon = ({ className = "w-5 h-5", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
  </svg>
);

export const InfoIcon = ({ className = "w-5 h-5", strokeWidth = 1 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export const ChartIcon = ({ className = "w-5 h-5", strokeWidth = 1.5 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" />
  </svg>
);

export const SearchIcon = ({ className = "w-5 h-5", strokeWidth = 1.5 }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className={className} strokeWidth={strokeWidth}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
