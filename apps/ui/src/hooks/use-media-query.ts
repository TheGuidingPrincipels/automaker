import { useState, useEffect, useRef } from 'react';

/**
 * Hook to detect if a media query matches
 * @param query - The media query string (e.g., '(max-width: 768px)')
 * @returns boolean indicating if the media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  // Track if this is the initial mount to avoid redundant setMatches call
  const isInitialMount = useRef(true);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    const handleChange = (e: MediaQueryListEvent) => {
      setMatches(e.matches);
    };

    // Only sync state when query changes after initial mount
    // (initial mount already has correct value from useState initializer)
    if (isInitialMount.current) {
      isInitialMount.current = false;
    } else {
      setMatches(mediaQuery.matches);
    }

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [query]);

  return matches;
}

/**
 * Hook to detect if the device is mobile (screen width <= 768px)
 * @returns boolean indicating if the device is mobile
 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 900px)');
}

/**
 * Hook to detect if the device is tablet or smaller (screen width <= 1024px)
 * @returns boolean indicating if the device is tablet or smaller
 */
export function useIsTablet(): boolean {
  return useMediaQuery('(max-width: 1024px)');
}

/**
 * Hook to detect if the toolbar is narrow enough that worktree panel should collapse
 * Used for first-stage responsive collapse of Plan button to overflow menu
 * @returns boolean indicating if Plan should collapse
 */
export function useIsNarrowToolbarForWorktree(): boolean {
  return useMediaQuery('(max-width: 900px)');
}

/**
 * Hook to detect if the toolbar is narrow enough that Plan button should collapse
 * Used for first-stage responsive collapse of Plan button to overflow menu
 * @returns boolean indicating if Plan should collapse
 */
export function useIsNarrowToolbarForPlan(): boolean {
  return useMediaQuery('(max-width: 1378px)');
}

/**
 * Hook to detect if the toolbar is narrow enough that Auto Mode should collapse
 * Used for second-stage responsive collapse of Auto Mode to overflow menu
 * @returns boolean indicating if Auto Mode should collapse
 */
export function useIsNarrowToolbarForAutoMode(): boolean {
  return useMediaQuery('(max-width: 1300px)');
}

/**
 * Hook to detect if the toolbar is narrow enough that Agents control should collapse
 * Used for third-stage responsive collapse of Agents control to overflow menu
 * @returns boolean indicating if Agents should collapse
 */
export function useIsNarrowToolbarForAgents(): boolean {
  return useMediaQuery('(max-width: 1110px)');
}
