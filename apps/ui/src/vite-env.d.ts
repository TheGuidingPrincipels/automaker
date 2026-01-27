/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SERVER_URL?: string;
  readonly VITE_APP_MODE?: '1' | '2' | '3' | '4';
  /** URL for the AI-Library backend API (default: http://localhost:8002) */
  readonly VITE_KNOWLEDGE_LIBRARY_API?: string;
}

// Extend ImportMeta to include env property
interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Global constants defined in vite.config.mts
declare const __APP_VERSION__: string;
