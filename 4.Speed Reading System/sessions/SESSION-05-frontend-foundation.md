# Session 5: Frontend Foundation

> ⚠️ **Legacy (Standalone) Plan**: This session describes building a standalone frontend app. For Automaker integration, use `SESSION-05-REVISED-automaker-integration.md`.

## Overview

**Duration**: ~3-4 hours
**Goal**: Set up the React frontend with routing, styling, state management, and API client infrastructure.

**Deliverable**: A running React app with dark theme, basic layout, and configured API communication.

---

## Prerequisites

- Sessions 1-4 completed (backend running at `http://localhost:8000`)
- Node.js 20+ installed
- pnpm or npm installed

---

## Objectives & Acceptance Criteria

| #   | Objective             | Acceptance Criteria                        |
| --- | --------------------- | ------------------------------------------ |
| 1   | Vite + React 19 setup | Dev server runs at `http://localhost:5173` |
| 2   | TanStack Router       | File-based routing configured              |
| 3   | TanStack Query        | API caching and fetching configured        |
| 4   | Tailwind CSS 4        | Dark theme as default                      |
| 5   | shadcn/ui             | Component library installed                |
| 6   | Zustand               | Global state store configured              |
| 7   | API client            | Type-safe API functions                    |
| 8   | Layout components     | Shell, header, main content areas          |

---

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx                    # App entry point
│   ├── App.tsx                     # Root component with providers
│   ├── index.css                   # Global styles + Tailwind
│   ├── routes/
│   │   ├── __root.tsx              # Root layout
│   │   ├── index.tsx               # Home page (redirect to /deepread)
│   │   └── deepread/
│   │       ├── index.tsx           # Main DeepRead page
│   │       └── $documentId.tsx     # Document reader page
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── slider.tsx
│   │   │   ├── card.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── AppShell.tsx        # Main app shell
│   │   │   ├── Header.tsx          # Top header
│   │   │   └── Container.tsx       # Content container
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       └── ErrorDisplay.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts           # Base API client
│   │   │   ├── documents.ts        # Document API functions
│   │   │   ├── sessions.ts         # Session API functions
│   │   │   └── types.ts            # API response types
│   │   ├── utils.ts                # Utility functions
│   │   └── cn.ts                   # Class name utility
│   ├── stores/
│   │   ├── readerStore.ts          # Reader state (WPM, playback)
│   │   └── appStore.ts             # App-level state
│   └── hooks/
│       ├── useDocuments.ts         # Document query hooks
│       └── useSessions.ts          # Session query hooks
├── components.json                  # shadcn/ui config
├── tailwind.config.ts
├── tsconfig.json
├── vite.config.ts
├── package.json
└── index.html
```

---

## Implementation Details

### 1. Initialize Project

```bash
cd frontend

# Create Vite project
pnpm create vite@latest . --template react-ts

# Install dependencies
pnpm add react@19 react-dom@19
pnpm add @tanstack/react-router @tanstack/react-query
pnpm add zustand
pnpm add clsx tailwind-merge
pnpm add lucide-react  # Icons

# Dev dependencies
pnpm add -D tailwindcss postcss autoprefixer
pnpm add -D @types/node
pnpm add -D @tanstack/router-vite-plugin

# Initialize Tailwind
pnpm dlx tailwindcss init -p
```

### 2. Vite Configuration (`vite.config.ts`)

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { TanStackRouterVite } from '@tanstack/router-vite-plugin';
import path from 'path';

export default defineConfig({
  plugins: [react(), TanStackRouterVite()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### 3. TypeScript Configuration (`tsconfig.json`)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### 4. Tailwind Configuration (`tailwind.config.ts`)

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark theme colors
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
```

### 5. Global Styles (`src/index.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222 47% 6%;
    --foreground: 210 40% 98%;
    --card: 222 47% 8%;
    --card-foreground: 210 40% 98%;
    --popover: 222 47% 8%;
    --popover-foreground: 210 40% 98%;
    --primary: 217 91% 60%;
    --primary-foreground: 222 47% 6%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    --accent: 217 33% 17%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 63% 31%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 217 91% 60%;
    --radius: 0.5rem;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground;
    font-feature-settings:
      'rlig' 1,
      'calt' 1;
  }
}

/* Reader mode specific styles */
.reader-mode {
  --reader-bg: 0 0% 0%;
  --reader-text: 0 0% 100%;
}

/* Scrollbar styling for dark theme */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-background;
}

::-webkit-scrollbar-thumb {
  @apply bg-muted rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-muted-foreground/50;
}
```

### 6. Class Name Utility (`src/lib/cn.ts`)

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 7. API Types (`src/lib/api/types.ts`)

```typescript
// Document types
export type SourceType = 'paste' | 'md' | 'pdf';
export type Language = 'en' | 'de';

export interface DocumentMeta {
  id: string;
  title: string;
  source_type: SourceType;
  language: Language;
  total_words: number;
  tokenizer_version: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentPreview {
  id: string;
  title: string;
  preview_text: string;
  total_words: number;
  anchors: Anchor[];
}

export interface Anchor {
  word_index: number;
  type: 'paragraph' | 'heading';
  preview: string;
}

// Token types
export type BreakType = 'paragraph' | 'heading' | null;

export interface Token {
  word_index: number;
  display_text: string;
  orp_index_display: number;
  delay_multiplier_after: number;
  break_before: BreakType;
  is_sentence_start: boolean;
  is_paragraph_start: boolean;
}

export interface TokenChunk {
  document_id: string;
  total_words: number;
  range_start: number;
  range_end: number;
  tokens: Token[];
}

// Session types
export interface Session {
  id: string;
  document_id: string;
  target_wpm: number;
  ramp_enabled: boolean;
  ramp_seconds: number;
  ramp_start_wpm: number | null;
  current_word_index: number;
  last_known_percent: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface SessionListItem {
  id: string;
  document_id: string;
  document_title: string;
  last_known_percent: number;
  updated_at: string;
  expires_at: string;
}

export interface ResolveStartResult {
  resolved_word_index: number;
  reason: 'sentence_start' | 'paragraph_start' | 'heading_start' | 'exact';
}

// Request types
export interface CreateDocumentFromTextRequest {
  title?: string;
  language: Language;
  text: string;
}

export interface CreateSessionRequest {
  document_id: string;
  start_word_index?: number;
  target_wpm?: number;
  ramp_enabled?: boolean;
  ramp_seconds?: number;
}

export interface UpdateProgressRequest {
  current_word_index: number;
  last_known_percent: number;
  target_wpm?: number;
  ramp_enabled?: boolean;
}

export interface ResolveStartRequest {
  approx_word_index: number;
  prefer?: 'sentence' | 'paragraph' | 'heading';
  direction?: 'backward' | 'forward' | 'nearest';
  window?: number;
}

// API error
export interface ApiError {
  detail: string;
}
```

### 8. API Client (`src/lib/api/client.ts`)

```typescript
const API_BASE = '/api';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail || 'An error occurred');
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint: string): Promise<void> {
    return this.request(endpoint, { method: 'DELETE' });
  }

  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - browser will set it with boundary
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail || 'An error occurred');
    }

    return response.json();
  }
}

export const apiClient = new ApiClient();
```

### 9. Documents API (`src/lib/api/documents.ts`)

```typescript
import { apiClient } from './client';
import type {
  DocumentMeta,
  DocumentPreview,
  TokenChunk,
  CreateDocumentFromTextRequest,
  ResolveStartRequest,
  ResolveStartResult,
  Language,
} from './types';

export const documentsApi = {
  createFromText: (data: CreateDocumentFromTextRequest) =>
    apiClient.post<DocumentMeta>('/documents/from-text', data),

  createFromFile: (file: File, language: Language) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    return apiClient.upload<DocumentMeta>('/documents/from-file', formData);
  },

  getDocument: (documentId: string) => apiClient.get<DocumentMeta>(`/documents/${documentId}`),

  getPreview: (documentId: string) =>
    apiClient.get<DocumentPreview>(`/documents/${documentId}/preview`),

  getTokens: (documentId: string, start = 0, limit = 500) =>
    apiClient.get<TokenChunk>(`/documents/${documentId}/tokens?start=${start}&limit=${limit}`),

  resolveStart: (documentId: string, data: ResolveStartRequest) =>
    apiClient.post<ResolveStartResult>(`/documents/${documentId}/resolve-start`, data),

  deleteDocument: (documentId: string) => apiClient.delete(`/documents/${documentId}`),
};
```

### 10. Sessions API (`src/lib/api/sessions.ts`)

```typescript
import { apiClient } from './client';
import type {
  Session,
  SessionListItem,
  CreateSessionRequest,
  UpdateProgressRequest,
} from './types';

export const sessionsApi = {
  create: (data: CreateSessionRequest) => apiClient.post<Session>('/sessions', data),

  getRecent: (days = 7) => apiClient.get<SessionListItem[]>(`/sessions/recent?days=${days}`),

  getLatestForDocument: (documentId: string) =>
    apiClient.get<Session | null>(`/sessions/document/${documentId}/latest`),

  getSession: (sessionId: string) => apiClient.get<Session>(`/sessions/${sessionId}`),

  updateProgress: (sessionId: string, data: UpdateProgressRequest) =>
    apiClient.patch<Session>(`/sessions/${sessionId}/progress`, data),

  deleteSession: (sessionId: string) => apiClient.delete(`/sessions/${sessionId}`),
};
```

### 11. Zustand Stores

#### Reader Store (`src/stores/readerStore.ts`)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ReaderSettings {
  targetWpm: number;
  rampEnabled: boolean;
  rampSeconds: number;
}

interface ReaderState {
  // Settings (persisted)
  settings: ReaderSettings;

  // Playback state (not persisted)
  isPlaying: boolean;
  currentWordIndex: number;
  elapsedReadingTime: number; // ms, excludes paused time

  // Actions
  setTargetWpm: (wpm: number) => void;
  setRampEnabled: (enabled: boolean) => void;
  setRampSeconds: (seconds: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setCurrentWordIndex: (index: number) => void;
  incrementElapsedTime: (ms: number) => void;
  resetPlayback: () => void;
}

export const useReaderStore = create<ReaderState>()(
  persist(
    (set) => ({
      // Default settings
      settings: {
        targetWpm: 300,
        rampEnabled: true,
        rampSeconds: 30,
      },

      // Playback state
      isPlaying: false,
      currentWordIndex: 0,
      elapsedReadingTime: 0,

      // Settings actions
      setTargetWpm: (wpm) =>
        set((state) => ({
          settings: { ...state.settings, targetWpm: Math.max(100, Math.min(1500, wpm)) },
        })),

      setRampEnabled: (enabled) =>
        set((state) => ({
          settings: { ...state.settings, rampEnabled: enabled },
        })),

      setRampSeconds: (seconds) =>
        set((state) => ({
          settings: { ...state.settings, rampSeconds: Math.max(0, Math.min(60, seconds)) },
        })),

      // Playback actions
      setIsPlaying: (playing) => set({ isPlaying: playing }),

      setCurrentWordIndex: (index) => set({ currentWordIndex: index }),

      incrementElapsedTime: (ms) =>
        set((state) => ({ elapsedReadingTime: state.elapsedReadingTime + ms })),

      resetPlayback: () =>
        set({
          isPlaying: false,
          currentWordIndex: 0,
          elapsedReadingTime: 0,
        }),
    }),
    {
      name: 'deepread-reader-settings',
      partialize: (state) => ({ settings: state.settings }),
    }
  )
);
```

#### App Store (`src/stores/appStore.ts`)

```typescript
import { create } from 'zustand';

interface AppState {
  // Current document being viewed/read
  currentDocumentId: string | null;
  currentSessionId: string | null;

  // UI state
  isReaderMode: boolean;

  // Actions
  setCurrentDocument: (id: string | null) => void;
  setCurrentSession: (id: string | null) => void;
  enterReaderMode: () => void;
  exitReaderMode: () => void;
}

export const useAppStore = create<AppState>()((set) => ({
  currentDocumentId: null,
  currentSessionId: null,
  isReaderMode: false,

  setCurrentDocument: (id) => set({ currentDocumentId: id }),
  setCurrentSession: (id) => set({ currentSessionId: id }),
  enterReaderMode: () => set({ isReaderMode: true }),
  exitReaderMode: () => set({ isReaderMode: false }),
}));
```

### 12. Query Hooks (`src/hooks/useDocuments.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api/documents';
import type { CreateDocumentFromTextRequest, Language } from '@/lib/api/types';

export const documentKeys = {
  all: ['documents'] as const,
  detail: (id: string) => ['documents', id] as const,
  preview: (id: string) => ['documents', id, 'preview'] as const,
  tokens: (id: string, start: number) => ['documents', id, 'tokens', start] as const,
};

export function useDocument(documentId: string | null) {
  return useQuery({
    queryKey: documentKeys.detail(documentId!),
    queryFn: () => documentsApi.getDocument(documentId!),
    enabled: !!documentId,
  });
}

export function useDocumentPreview(documentId: string | null) {
  return useQuery({
    queryKey: documentKeys.preview(documentId!),
    queryFn: () => documentsApi.getPreview(documentId!),
    enabled: !!documentId,
  });
}

export function useTokenChunk(documentId: string | null, start: number) {
  return useQuery({
    queryKey: documentKeys.tokens(documentId!, start),
    queryFn: () => documentsApi.getTokens(documentId!, start),
    enabled: !!documentId,
    staleTime: Infinity, // Tokens don't change
  });
}

export function useCreateDocumentFromText() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDocumentFromTextRequest) => documentsApi.createFromText(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    },
  });
}

export function useCreateDocumentFromFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, language }: { file: File; language: Language }) =>
      documentsApi.createFromFile(file, language),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    },
  });
}

export function useResolveStart(documentId: string) {
  return useMutation({
    mutationFn: (data: Parameters<typeof documentsApi.resolveStart>[1]) =>
      documentsApi.resolveStart(documentId, data),
  });
}
```

### 13. Layout Components

#### App Shell (`src/components/layout/AppShell.tsx`)

```typescript
import { cn } from '@/lib/cn'
import { useAppStore } from '@/stores/appStore'

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const isReaderMode = useAppStore((s) => s.isReaderMode)

  return (
    <div
      className={cn(
        'min-h-screen transition-colors duration-300',
        isReaderMode ? 'bg-black' : 'bg-background'
      )}
    >
      {children}
    </div>
  )
}
```

#### Header (`src/components/layout/Header.tsx`)

```typescript
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/cn'

export function Header() {
  const isReaderMode = useAppStore((s) => s.isReaderMode)

  if (isReaderMode) {
    return null  // Hide header in reader mode
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold text-primary">DeepRead</span>
          <span className="text-sm text-muted-foreground">RSVP Reader</span>
        </div>
      </div>
    </header>
  )
}
```

#### Container (`src/components/layout/Container.tsx`)

```typescript
import { cn } from '@/lib/cn'

interface ContainerProps {
  children: React.ReactNode
  className?: string
}

export function Container({ children, className }: ContainerProps) {
  return (
    <div className={cn('container mx-auto px-4 py-6', className)}>
      {children}
    </div>
  )
}
```

### 14. Common Components

#### Loading Spinner (`src/components/common/LoadingSpinner.tsx`)

```typescript
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <Loader2
      className={cn('animate-spin text-primary', sizeClasses[size], className)}
    />
  )
}
```

#### Error Display (`src/components/common/ErrorDisplay.tsx`)

```typescript
import { AlertCircle } from 'lucide-react'

interface ErrorDisplayProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorDisplay({
  title = 'Error',
  message,
  onRetry,
}: ErrorDisplayProps) {
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
        <div className="flex-1">
          <h3 className="font-medium text-destructive">{title}</h3>
          <p className="text-sm text-muted-foreground mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 text-sm text-primary hover:underline"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

### 15. Root Route (`src/routes/__root.tsx`)

```typescript
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { AppShell } from '@/components/layout/AppShell'
import { Header } from '@/components/layout/Header'

export const Route = createRootRoute({
  component: () => (
    <AppShell>
      <Header />
      <main>
        <Outlet />
      </main>
    </AppShell>
  ),
})
```

### 16. Index Route (`src/routes/index.tsx`)

```typescript
import { createFileRoute, Navigate } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: () => <Navigate to="/deepread" />,
})
```

### 17. DeepRead Index Route (`src/routes/deepread/index.tsx`)

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { Container } from '@/components/layout/Container'

export const Route = createFileRoute('/deepread/')({
  component: DeepReadPage,
})

function DeepReadPage() {
  return (
    <Container>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">DeepRead</h1>
          <p className="text-muted-foreground">
            Speed reading with RSVP technology
          </p>
        </div>

        {/* Import form will go here in Session 6 */}
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-muted-foreground">
            Import form coming in Session 6
          </p>
        </div>

        {/* Recent sessions will go here in Session 9 */}
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-muted-foreground">
            Recent sessions coming in Session 9
          </p>
        </div>
      </div>
    </Container>
  )
}
```

### 18. App Entry (`src/App.tsx`)

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,  // 1 minute
      retry: 1,
    },
  },
})

const router = createRouter({
  routeTree,
  context: { queryClient },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
```

### 19. Main Entry (`src/main.tsx`)

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

---

## shadcn/ui Setup

```bash
# Initialize shadcn/ui
pnpm dlx shadcn@latest init

# When prompted:
# - Style: Default
# - Base color: Slate
# - CSS variables: Yes

# Install components we'll need
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add input
pnpm dlx shadcn@latest add select
pnpm dlx shadcn@latest add slider
pnpm dlx shadcn@latest add card
pnpm dlx shadcn@latest add textarea
pnpm dlx shadcn@latest add tabs
pnpm dlx shadcn@latest add progress
pnpm dlx shadcn@latest add tooltip
```

---

## Verification Checklist

- [ ] `pnpm dev` starts server at `http://localhost:5173`
- [ ] Dark theme displays correctly
- [ ] `/` redirects to `/deepread`
- [ ] `/deepread` shows placeholder page
- [ ] API proxy works (`/api/health` returns data)
- [ ] TanStack Router generates route tree
- [ ] Zustand stores initialize with defaults
- [ ] shadcn/ui components render correctly
- [ ] TypeScript compiles without errors

---

## Context for Next Session

**What exists after Session 5:**

- Running React frontend with dark theme
- TanStack Router with file-based routing
- TanStack Query for API caching
- Zustand stores for state
- API client with type-safe functions
- Layout components (shell, header, container)
- shadcn/ui components installed

**Session 6 will need:**

- Layout components for page structure
- API functions for document creation
- Query hooks for data fetching
- Zustand store for app state
