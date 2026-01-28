# Sub-Plan 4: Automatic Image Generation for Domains and Pages

## Objective

Implement automatic AI-powered image generation for knowledge library domains and pages using **Google Imagen 3.0** via Vertex AI. Images are generated when sufficient context exists (title + overview), stored in team storage for transferability, and displayed in the UI.

## Prerequisites

- **Sub-Plans 1-3 completed**: Domain types, gallery, and detail views exist
- **Google Cloud Platform (GCP) account** with billing enabled
- **Vertex AI API enabled** in your GCP project
- Understanding of team storage patterns

## Preflight (STOP if failing)

This sub-plan is only executable **after Sub-Plans 1–3 have been implemented in code** (not just written).

Run from repo root:

```bash
# Sub-Plans 2–3: Domain UI files
test -d "apps/ui/src/components/views/knowledge-library/components/domain-gallery"
test -d "apps/ui/src/components/views/knowledge-library/components/domain-detail"
test -f "apps/ui/src/components/views/knowledge-library/components/domain-gallery/domain-card.tsx"
test -f "apps/ui/src/components/views/knowledge-library/components/domain-detail/page-card.tsx"

# Sub-Plan 1: Domain config + utils
test -f "apps/ui/src/config/domains.ts"
test -f "apps/ui/src/lib/domain-utils.ts"

# Sub-Plan 1: Shared types exported
rg -n "export type KLDomainId\\b" libs/types/src/knowledge-library.ts
rg -n "export interface KLPageCard\\b" libs/types/src/knowledge-library.ts

# Sanity: UI types resolve
npm run typecheck --workspace=apps/ui
```

**Stop condition:** If any command fails, STOP and complete Sub-Plans 1–3 first.

## Important: Google Image Generation Requirements

**Google's dedicated image generation model is Imagen 3.0**, accessed via Vertex AI. This is different from Gemini (which handles text/multimodal but NOT image generation).

| Aspect         | Gemini API                           | Imagen 3.0 (Vertex AI)                                                |
| -------------- | ------------------------------------ | --------------------------------------------------------------------- |
| Package        | `@google/generative-ai`              | Vertex AI **REST** (`:generateContent`) + `google-auth-library` (ADC) |
| Capabilities   | Text generation, image understanding | **Image generation**                                                  |
| Authentication | API key                              | Service account / ADC                                                 |
| Setup          | Simple                               | Requires GCP project                                                  |

## Deliverables

1. GCP project setup with Vertex AI enabled
2. Service account credentials configuration (ENV/ADC)
3. Image generation service using Imagen 3.0
4. Team storage integration for generated images
5. Automatic generation trigger when title + overview exist
6. Image display in Domain Cards and Page Cards
7. Caching and reuse of generated images

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   UI Component  │────▶│  Image Service   │────▶│   Vertex AI     │
│  (DomainCard)   │     │   (Backend)      │     │  (Imagen 3.0)   │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │   Team Storage   │
         │              │ (generated-media)│
         └──────────────┴──────────────────┘
```

---

## Step 1: GCP Project Setup

### 1.1 Create/Configure GCP Project

```bash
# Install Google Cloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create automaker-images --name="Automaker Images"

# Set the project as default
gcloud config set project automaker-images

# Enable billing (required for Vertex AI)
# Do this in the GCP Console: https://console.cloud.google.com/billing

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com
```

### 1.2 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create automaker-imagen \
    --display-name="Automaker Imagen Service Account"

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding automaker-images \
    --member="serviceAccount:automaker-imagen@automaker-images.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Create and download key file
gcloud iam service-accounts keys create ~/automaker-imagen-key.json \
    --iam-account=automaker-imagen@automaker-images.iam.gserviceaccount.com
```

### 1.3 Configure Environment Variables

Add to your `.env` file:

```bash
# Google Cloud / Vertex AI configuration
GOOGLE_CLOUD_PROJECT=automaker-images
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/automaker-imagen-key.json

# Optional overrides
AUTOMAKER_IMAGEN_MODEL=imagen-3.0-generate-002

# Kill switch (repo-aligned pattern: "true" disables)
AUTOMAKER_DISABLE_GENERATED_MEDIA=false
```

---

## Step 2: Install Dependencies

```bash
npm install google-auth-library --workspace=apps/server
```

---

## Step 3: Identifier Strategy (future-proof + reliable)

### 3.1 Domain IDs

Use the existing domain ID (from Sub-Plan 1) as `domainId` everywhere (routes, storage, caching).

### 3.2 Page IDs (safe + deterministic)

Pages are identified upstream by a **file path** (e.g. `technical/programming/js-basics.md`). File paths contain `/` and are **not safe** as URL params or TeamStorage entity IDs.

Define:

- `pageFilePath`: the Knowledge Library file path (available on `KLPageCard.path` in Sub-Plan 3)
- `pageStorageId`: `sha256hex(pageFilePath)` (UTF-8)

Rules:

- Store page images under the TeamStorage entity ID = `pageStorageId` (safe single path segment).
- Client-facing APIs should accept `pageFilePath` (no client-side hashing required); the server derives `pageStorageId`.

**Server helper (Node):**

```ts
import crypto from 'crypto';

export const getPageStorageId = (pageFilePath: string): string =>
  crypto.createHash('sha256').update(pageFilePath, 'utf8').digest('hex');
```

### 3.3 Cache busting

When returning thumbnail URLs to the UI, include `v=<inputHash>` as a query param to avoid stale browser caches after regeneration.

---

## Step 4: Configuration (ENV-only; no SettingsService/Credentials changes)

This sub-plan intentionally does **not** modify:

- `libs/types/src/settings.ts` (Credentials schema)
- `apps/server/src/services/settings-service.ts`

The backend reads Imagen/Vertex config from environment variables only:

- Required: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`
- Recommended: `GOOGLE_CLOUD_LOCATION=us-central1`
- Optional: `AUTOMAKER_IMAGEN_MODEL` (default: `imagen-3.0-generate-002`)
- Optional kill switch: `AUTOMAKER_DISABLE_GENERATED_MEDIA=true`

**Stop condition:** If required env vars are missing (or kill switch is enabled), `/api/generated-media/status` must report `available: false` and generation endpoints must return `503` (no external calls).

---

## Step 5: Create Image Generation Service

**File:** `apps/server/src/services/image-generation-service.ts` (NEW FILE)

```typescript
/**
 * Image Generation Service
 *
 * Generates images using Google Imagen 3.0 via Vertex AI for domains and pages
 * in the Knowledge Library. Stores generated images in team storage for
 * reusability and transferability.
 */

import { GoogleAuth } from 'google-auth-library';
import { createLogger } from '@automaker/utils';
import type { TeamStorageService } from '../lib/team-storage.js';
import crypto from 'crypto';

const logger = createLogger('ImageGenerationService');

export interface ImageGenerationOptions {
  /** Type of entity (domain or page) */
  entityType: 'domain' | 'page';
  /** Unique entity ID */
  entityId: string;
  /** Optional: for pages, original KL file path (debugging/traceability) */
  sourcePath?: string;
  /** Title for the image prompt */
  title: string;
  /** Overview/description for context */
  overview: string;
  /** Additional keywords for better prompts */
  keywords?: string[];
  /** Force regeneration even if cached */
  forceRegenerate?: boolean;
}

export interface GeneratedImage {
  /** Path to the stored image */
  path: string;
  /** Image filename */
  filename: string;
  /** MIME type */
  mimeType: string;
  /** Generation timestamp */
  generatedAt: string;
  /** Prompt used for generation */
  prompt: string;
  /** Hash of inputs for cache validation */
  inputHash: string;
}

interface ImageMetadata {
  entityType: string;
  entityId: string;
  /** Optional: for pages, the source KL file path (debugging/traceability) */
  sourcePath?: string;
  title: string;
  overview: string;
  generatedAt: string;
  prompt: string;
  inputHash: string;
  images: {
    thumbnail: GeneratedImage;
  };
}

export class ImageGenerationService {
  private teamStorage: TeamStorageService;
  private auth: GoogleAuth;
  private projectId: string;
  private location: string;
  private model: string;

  constructor(teamStorage: TeamStorageService) {
    this.teamStorage = teamStorage;
    this.auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/cloud-platform'] });

    // ENV-only configuration (Step 4)
    this.projectId = process.env.GOOGLE_CLOUD_PROJECT || '';
    this.location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';
    this.model = process.env.AUTOMAKER_IMAGEN_MODEL || 'imagen-3.0-generate-002';
  }

  /**
   * Check if image generation is available
   */
  isAvailable(): boolean {
    if (process.env.AUTOMAKER_DISABLE_GENERATED_MEDIA === 'true') return false;
    if (!this.projectId) return false;
    // ADC path is required for local dev; other ADC methods may exist, but don't guess here.
    if (!process.env.GOOGLE_APPLICATION_CREDENTIALS) return false;
    return true;
  }

  /**
   * Generate a hash of the inputs for cache validation
   */
  private generateInputHash(title: string, overview: string, keywords?: string[]): string {
    const input = JSON.stringify({ title, overview, keywords: keywords || [] });
    return crypto.createHash('md5').update(input).digest('hex').substring(0, 12);
  }

  /**
   * Build an optimized prompt for Imagen
   */
  private buildPrompt(options: ImageGenerationOptions): string {
    const { entityType, title, overview, keywords } = options;

    // Style instructions optimized for Imagen 3.0
    const styleInstructions = `
Professional digital illustration, clean minimalist design, soft gradients,
subtle shadows, modern aesthetic, suitable for a dashboard card thumbnail.
No text, no letters, no words in the image.
`.trim();

    // Entity-specific context
    let contextPrompt: string;
    if (entityType === 'domain') {
      const keywordContext = keywords?.slice(0, 3).join(', ') || 'knowledge';
      contextPrompt = `
Abstract symbolic illustration representing "${title}" knowledge domain.
Essence: ${overview.substring(0, 150)}
Visual themes: ${keywordContext}
Style: Metaphorical, not literal. Use shapes and colors to evoke the concept.
`.trim();
    } else {
      contextPrompt = `
Focused illustration for knowledge article: "${title}"
Topic context: ${overview.substring(0, 150)}
Style: Professional, topic-relevant, visually distinct.
`.trim();
    }

    return `${styleInstructions}\n\n${contextPrompt}`;
  }

  /**
   * Get the storage collection for generated media
   */
  private getCollection(entityType: 'domain' | 'page'): string {
    return entityType === 'domain' ? 'domain-images' : 'page-images';
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const client = await this.auth.getClient();
    const headers = await client.getRequestHeaders();
    return headers as Record<string, string>;
  }

  private getImagenGenerateContentUrl(): string {
    return `https://${this.location}-aiplatform.googleapis.com/v1/projects/${this.projectId}/locations/${this.location}/publishers/google/models/${this.model}:generateContent`;
  }

  private async callImagenGenerateContent(
    prompt: string
  ): Promise<{ base64: string; mimeType: string }> {
    const url = this.getImagenGenerateContentUrl();
    const authHeaders = await this.getAuthHeaders();

    const body = {
      contents: [
        {
          parts: [{ text: prompt }],
        },
      ],
      // Imagen uses "parameters" for image-generation options (NOT Gemini's candidateCount)
      parameters: {
        sampleCount: 1,
        aspectRatio: '1:1',
        outputOptions: { mimeType: 'image/png' },
      },
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      throw new Error(
        `Imagen generateContent failed: ${response.status} ${response.statusText} ${errorText}`
      );
    }

    const json = (await response.json()) as any;
    const candidates = json?.candidates || [];
    for (const candidate of candidates) {
      const parts = candidate?.content?.parts || [];
      for (const part of parts) {
        const inlineData = part?.inlineData;
        if (inlineData?.data) {
          return {
            base64: inlineData.data as string,
            mimeType: (inlineData.mimeType as string) || 'image/png',
          };
        }
      }
    }

    throw new Error('No inlineData image found in Imagen response');
  }

  /**
   * Check if a valid cached image exists
   */
  async getCachedImage(options: ImageGenerationOptions): Promise<GeneratedImage | null> {
    const { entityType, entityId, title, overview, keywords } = options;
    const collection = this.getCollection(entityType);
    const inputHash = this.generateInputHash(title, overview, keywords);

    try {
      // Try to read metadata
      const metadataBuffer = await this.teamStorage.readFile(
        collection as any,
        entityId,
        'metadata.json'
      );

      if (!metadataBuffer) return null;

      const metadata: ImageMetadata = JSON.parse(metadataBuffer.toString('utf-8'));

      // Validate cache by comparing input hash
      if (metadata.inputHash === inputHash && metadata.images?.thumbnail) {
        // Verify the image file still exists
        const imageBuffer = await this.teamStorage.readFile(
          collection as any,
          entityId,
          metadata.images.thumbnail.filename
        );

        if (imageBuffer) {
          logger.debug(`Cache hit for ${entityType}:${entityId}`);
          return metadata.images.thumbnail;
        }
      }
    } catch (error) {
      logger.debug(`No cached image for ${entityType}:${entityId}`);
    }

    return null;
  }

  /**
   * Generate an image using Imagen 3.0
   */
  async generateImage(options: ImageGenerationOptions): Promise<GeneratedImage> {
    const { entityType, entityId, title, overview, keywords, forceRegenerate } = options;

    if (!this.isAvailable()) {
      throw new Error('Image generation not available (missing env vars or disabled)');
    }

    // Check requirements
    if (!title || !overview || overview.length < 20) {
      throw new Error('Image generation requires both title and overview (min 20 chars)');
    }

    // Check cache first (unless forcing regeneration)
    if (!forceRegenerate) {
      const cached = await this.getCachedImage(options);
      if (cached) {
        return cached;
      }
    }

    logger.info(`Generating Imagen 3.0 image for ${entityType}:${entityId}`);

    // Build prompt
    const prompt = this.buildPrompt(options);
    const inputHash = this.generateInputHash(title, overview, keywords);

    try {
      const { base64: imageBase64, mimeType } = await this.callImagenGenerateContent(prompt);

      // Save to team storage
      const timestamp = Date.now();
      const filename = `thumbnail-${timestamp}.png`;
      const collection = this.getCollection(entityType);

      // Save image file
      const imageBuffer = Buffer.from(imageBase64, 'base64');
      await this.teamStorage.saveFile(collection as any, entityId, filename, imageBuffer);

      // Create metadata
      const generatedImage: GeneratedImage = {
        path: `${collection}/${entityId}/${filename}`,
        filename,
        mimeType,
        generatedAt: new Date().toISOString(),
        prompt,
        inputHash,
      };

      // Save metadata
      const metadata: ImageMetadata = {
        entityType,
        entityId,
        sourcePath: options.sourcePath,
        title,
        overview,
        generatedAt: generatedImage.generatedAt,
        prompt,
        inputHash,
        images: {
          thumbnail: generatedImage,
        },
      };

      await this.teamStorage.saveFile(
        collection as any,
        entityId,
        'metadata.json',
        Buffer.from(JSON.stringify(metadata, null, 2))
      );

      logger.info(`Generated and saved Imagen image for ${entityType}:${entityId}`);
      return generatedImage;
    } catch (error: any) {
      logger.error(`Failed to generate image for ${entityType}:${entityId}`, error);

      throw error;
    }
  }
}
```

---

## Step 6: Update Team Storage for Generated Media

**File:** `apps/server/src/lib/team-storage.ts`

This repo’s `TeamStorageService` requires **3** updates for any new `StorageCollection`:

1. Add the union member(s) to `StorageCollection`
2. Add directory mapping(s) in `collectionMap` (inside `getCollectionPath`)
3. Add filename mapping(s) in `fileNameMap` (inside `getEntityPath`)

### 6.1 Update `StorageCollection`

Find the `StorageCollection` type and add:

```typescript
export type StorageCollection =
  | 'agents'
  | 'systems'
  | 'blueprints'
  | 'knowledge-entries'
  | 'learnings'
  | 'domain-images' // ADD
  | 'page-images'; // ADD
```

### 6.2 Update `collectionMap`

In `getCollectionPath()`, add:

```ts
const collectionMap: Record<StorageCollection, string> = {
  // ...existing...
  'domain-images': 'knowledge/generated-media/domain-images',
  'page-images': 'knowledge/generated-media/page-images',
};
```

### 6.3 Update `fileNameMap`

In `getEntityPath()`, add:

```ts
const fileNameMap: Record<StorageCollection, string> = {
  // ...existing...
  'domain-images': 'metadata.json',
  'page-images': 'metadata.json',
};
```

### 6.4 Update `initialize()` directories

In `initialize()`, add the new directories to the existing `directories` array (repo-aligned pattern):

```typescript
async initialize(): Promise<void> {
  const directories = [
    // ... existing directories ...
    path.join(this.basePath, 'knowledge/generated-media'),
    path.join(this.basePath, 'knowledge/generated-media/domain-images'),
    path.join(this.basePath, 'knowledge/generated-media/page-images'),
  ];
}
```

---

## Step 7: Create API Routes for Generated Images

**File:** `apps/server/src/routes/generated-media/index.ts` (NEW FILE)

```typescript
/**
 * Generated Media API Routes
 *
 * Serves AI-generated images for domains and pages.
 *
 * NOTE: `authMiddleware` is applied globally in `apps/server/src/index.ts`
 * (all `/api/*` routes mounted after `app.use('/api', authMiddleware)`).
 */

import { Router } from 'express';
import type { Request, Response } from 'express';
import crypto from 'crypto';
import { createLogger } from '@automaker/utils';
import type { TeamStorageService } from '../../lib/team-storage.js';
import { ImageGenerationService } from '../../services/image-generation-service.js';

const logger = createLogger('GeneratedMediaRoutes');

const getPageStorageId = (pageFilePath: string): string =>
  crypto.createHash('sha256').update(pageFilePath, 'utf8').digest('hex');

type ThumbnailMetadata = {
  images?: {
    thumbnail?: { filename: string; mimeType: string; inputHash: string };
  };
  inputHash: string;
};

async function readThumbnailMetadata(
  teamStorage: TeamStorageService,
  collection: 'domain-images' | 'page-images',
  entityId: string
): Promise<ThumbnailMetadata | null> {
  const metadataBuffer = await teamStorage.readFile(collection, entityId, 'metadata.json');
  if (!metadataBuffer) return null;
  return JSON.parse(metadataBuffer.toString('utf-8')) as ThumbnailMetadata;
}

export function createGeneratedMediaRoutes(teamStorage: TeamStorageService): Router {
  const router = Router();
  const imageService = new ImageGenerationService(teamStorage);

  const serveThumbnailByEntityId = async (
    res: Response,
    collection: 'domain-images' | 'page-images',
    entityId: string
  ): Promise<void> => {
    const metadata = await readThumbnailMetadata(teamStorage, collection, entityId);
    if (!metadata?.images?.thumbnail?.filename) {
      res.status(404).json({ error: 'Image not found' });
      return;
    }

    const { filename, mimeType } = metadata.images.thumbnail;
    const imageBuffer = await teamStorage.readFile(collection, entityId, filename);
    if (!imageBuffer) {
      res.status(404).json({ error: 'Image not found' });
      return;
    }

    res.setHeader('Content-Type', mimeType || 'image/png');
    // URLs include ?v=<inputHash> from clients; safe to cache long-term.
    res.setHeader('Cache-Control', 'public, max-age=31536000');
    res.send(imageBuffer);
  };

  // Serve current domain thumbnail
  router.get('/domain/:domainId/thumbnail', async (req: Request, res: Response) => {
    try {
      await serveThumbnailByEntityId(res, 'domain-images', req.params.domainId);
    } catch (error) {
      logger.error('Failed to serve domain thumbnail', error);
      res.status(500).json({ error: 'Failed to serve image' });
    }
  });

  // Serve current page thumbnail by page file path (server derives pageStorageId)
  router.get('/page/thumbnail', async (req: Request, res: Response) => {
    const pageFilePath = req.query.path;
    if (typeof pageFilePath !== 'string' || !pageFilePath) {
      res.status(400).json({ error: 'Missing required query param: path' });
      return;
    }

    try {
      const pageStorageId = getPageStorageId(pageFilePath);
      await serveThumbnailByEntityId(res, 'page-images', pageStorageId);
    } catch (error) {
      logger.error('Failed to serve page thumbnail', error);
      res.status(500).json({ error: 'Failed to serve image' });
    }
  });

  // Generate image for domain
  router.post('/generate/domain/:domainId', async (req: Request, res: Response) => {
    const { domainId } = req.params;
    const { title, overview, keywords, forceRegenerate } = req.body;

    if (!title || !overview) {
      return res.status(400).json({ error: 'Title and overview are required' });
    }

    if (!imageService.isAvailable()) {
      return res.status(503).json({
        error: 'Image generation not available',
        message:
          'Imagen is disabled or not configured. Set GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS (and ensure AUTOMAKER_DISABLE_GENERATED_MEDIA is not true).',
      });
    }

    try {
      const result = await imageService.generateImage({
        entityType: 'domain',
        entityId: domainId,
        title,
        overview,
        keywords,
        forceRegenerate,
      });

      res.json({
        success: true,
        image: result,
        // URL path only; UI must add host + auth query params
        url: `/api/generated-media/domain/${domainId}/thumbnail?v=${encodeURIComponent(result.inputHash)}`,
      });
    } catch (error: any) {
      logger.error('Failed to generate domain image', error);
      res.status(500).json({ error: error.message || 'Failed to generate image' });
    }
  });

  // Generate image for page
  router.post('/generate/page', async (req: Request, res: Response) => {
    const { path: pageFilePath, title, overview, keywords, forceRegenerate } = req.body;

    if (!pageFilePath || typeof pageFilePath !== 'string') {
      return res.status(400).json({ error: 'path is required' });
    }
    if (!title || !overview) {
      return res.status(400).json({ error: 'Title and overview are required' });
    }

    if (!imageService.isAvailable()) {
      return res.status(503).json({
        error: 'Image generation not available',
        message:
          'Imagen is disabled or not configured. Set GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS.',
      });
    }

    try {
      const pageStorageId = getPageStorageId(pageFilePath);
      const result = await imageService.generateImage({
        entityType: 'page',
        entityId: pageStorageId,
        sourcePath: pageFilePath,
        title,
        overview,
        keywords,
        forceRegenerate,
      });

      res.json({
        success: true,
        image: result,
        // URL path only; UI must add host + auth query params
        url: `/api/generated-media/page/thumbnail?path=${encodeURIComponent(pageFilePath)}&v=${encodeURIComponent(
          result.inputHash
        )}`,
      });
    } catch (error: any) {
      logger.error('Failed to generate page image', error);
      res.status(500).json({ error: error.message || 'Failed to generate image' });
    }
  });

  // Check if image generation is available
  router.get('/status', async (_req: Request, res: Response) => {
    const available = imageService.isAvailable();
    const projectId = process.env.GOOGLE_CLOUD_PROJECT || null;
    const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';
    const model = process.env.AUTOMAKER_IMAGEN_MODEL || 'imagen-3.0-generate-002';
    const disabled = process.env.AUTOMAKER_DISABLE_GENERATED_MEDIA === 'true';

    res.json({
      available,
      provider: 'google-imagen',
      projectId: available ? projectId : null,
      location: available ? location : null,
      model: available ? model : null,
      disabled,
      message: available
        ? 'Imagen 3.0 via Vertex AI is configured and available'
        : disabled
          ? 'Generated media is disabled (AUTOMAKER_DISABLE_GENERATED_MEDIA=true)'
          : 'Configure GOOGLE_CLOUD_PROJECT + GOOGLE_APPLICATION_CREDENTIALS to enable image generation',
    });
  });

  return router;
}
```

---

## Step 8: Register Routes in Server

**File:** `apps/server/src/index.ts`

Add import and route registration:

```typescript
import { createGeneratedMediaRoutes } from './routes/generated-media/index.js';

// After auth middleware is applied and teamStorage is available:
app.use('/api/generated-media', createGeneratedMediaRoutes(teamStorage));
```

---

## Step 9: Create Frontend Hook

**File:** `apps/ui/src/hooks/queries/use-generated-images.ts` (NEW FILE)

Also update query keys (repo pattern):

**File:** `apps/ui/src/lib/query-keys.ts`

Add:

```ts
generatedMedia: {
  status: () => ['generatedMedia', 'status'] as const,
},
```

```typescript
/**
 * Generated Images Hooks
 *
 * React Query hooks for managing AI-generated images via Imagen 3.0.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/lib/api-fetch';
import { getApiKey, getSessionToken, getServerUrlSync } from '@/lib/http-api-client';
import { queryKeys } from '@/lib/query-keys';

interface GeneratedImage {
  path: string;
  filename: string;
  mimeType: string;
  generatedAt: string;
  prompt: string;
  inputHash: string;
}

interface GenerateImageRequest {
  title: string;
  overview: string;
  keywords?: string[];
  forceRegenerate?: boolean;
}

interface GeneratePageImageRequest extends GenerateImageRequest {
  /** Knowledge Library file path (e.g. "technical/programming/js-basics.md") */
  path: string;
}

interface GenerateImageResponse {
  success: boolean;
  image: GeneratedImage;
  /**
   * Authenticated URL for <img src="..."> usage.
   * (Server returns a URL path; this hook converts it to absolute + adds auth query params.)
   */
  url: string;
}

interface ImageGenerationStatus {
  available: boolean;
  provider: string;
  projectId: string | null;
  location?: string | null;
  model?: string | null;
  disabled?: boolean;
  message: string;
}

function toAuthenticatedGeneratedMediaUrl(urlPath: string): string {
  const serverUrl = getServerUrlSync();
  const url = new URL(urlPath, serverUrl);

  // Electron mode: apiKey query param (needed for <img> loads; headers can't be set)
  const apiKey = getApiKey();
  if (apiKey) url.searchParams.set('apiKey', apiKey);

  // Web mode: session token query param fallback for <img> loads
  const sessionToken = getSessionToken();
  if (sessionToken) url.searchParams.set('token', sessionToken);

  return url.toString();
}

/**
 * Check if image generation is available
 */
export function useImageGenerationStatus() {
  return useQuery({
    queryKey: queryKeys.generatedMedia.status(),
    queryFn: () => apiGet<ImageGenerationStatus>('/api/generated-media/status'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Generate image for a domain
 */
export function useGenerateDomainImage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      domainId,
      ...request
    }: GenerateImageRequest & { domainId: string }): Promise<GenerateImageResponse> => {
      const result = await apiPost<GenerateImageResponse>(
        `/api/generated-media/generate/domain/${domainId}`,
        request
      );
      return { ...result, url: toAuthenticatedGeneratedMediaUrl(result.url) };
    },
    onSuccess: (_data, _variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.generatedMedia.status() });
    },
  });
}

/**
 * Generate image for a page
 */
export function useGeneratePageImage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: GeneratePageImageRequest): Promise<GenerateImageResponse> => {
      const result = await apiPost<GenerateImageResponse>(
        `/api/generated-media/generate/page`,
        request
      );
      return { ...result, url: toAuthenticatedGeneratedMediaUrl(result.url) };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.generatedMedia.status() });
    },
  });
}

/**
 * Build authenticated thumbnail URLs for display (works for <img> in Electron + web)
 */
export function getGeneratedDomainThumbnailUrl(domainId: string, v?: string): string {
  const serverUrl = getServerUrlSync();
  const url = new URL(`/api/generated-media/domain/${domainId}/thumbnail`, serverUrl);
  if (v) url.searchParams.set('v', v);
  return toAuthenticatedGeneratedMediaUrl(url.pathname + url.search);
}

export function getGeneratedPageThumbnailUrl(pageFilePath: string, v?: string): string {
  const serverUrl = getServerUrlSync();
  const url = new URL(`/api/generated-media/page/thumbnail`, serverUrl);
  url.searchParams.set('path', pageFilePath);
  if (v) url.searchParams.set('v', v);
  return toAuthenticatedGeneratedMediaUrl(url.pathname + url.search);
}
```

---

## Step 10: Update Domain Card with Image Support

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-gallery/domain-card.tsx`

Update to show generated image when available:

```tsx
// Add to imports
import { useEffect, useRef, useState } from 'react';
import {
  useGenerateDomainImage,
  useImageGenerationStatus,
} from '@/hooks/queries/use-generated-images';
import { Spinner } from '@/components/ui/spinner';

// Update DomainCard component
export function DomainCard({ domain, onClick }: DomainCardProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(domain.imageUrl || null);
  const { data: imageStatus } = useImageGenerationStatus();
  const generateImage = useGenerateDomainImage();
  const hasAttemptedRef = useRef(false);

  // Auto-generate image when sufficient context exists
  useEffect(() => {
    if (hasAttemptedRef.current) return;

    // Only attempt if:
    // - No image exists yet
    // - Image generation is available
    // - We have file count (meaning domain has content)
    // - Description is long enough
    if (
      !imageUrl &&
      imageStatus?.available &&
      domain.fileCount > 0 &&
      domain.description &&
      domain.description.length >= 20 &&
      !generateImage.isPending
    ) {
      hasAttemptedRef.current = true;
      generateImage.mutate(
        {
          domainId: domain.id,
          title: domain.name,
          overview: domain.description,
          keywords: domain.keywords,
        },
        {
          onSuccess: (data) => {
            setImageUrl(data.url);
          },
          onError: (error) => {
            console.warn('Failed to generate domain image:', error);
          },
        }
      );
    }
  }, [
    imageUrl,
    imageStatus?.available,
    domain.fileCount,
    domain.description,
    domain.id,
    domain.name,
    generateImage,
  ]);

  return (
    <Card className="..." onClick={onClick}>
      <div
        className={cn(
          'h-32 bg-gradient-to-br flex items-center justify-center relative',
          domain.gradientClasses
        )}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={domain.name}
            className="w-full h-full object-cover"
            onError={() => {
              // Avoid retry loops; fall back to icon
              hasAttemptedRef.current = true;
              setImageUrl(null);
            }}
          />
        ) : generateImage.isPending ? (
          <div className="flex flex-col items-center gap-2">
            <Spinner size="lg" />
            <span className="text-xs text-muted-foreground">Generating...</span>
          </div>
        ) : (
          <IconComponent className="h-16 w-16 text-primary/60 group-hover:text-primary group-hover:scale-110 transition-all" />
        )}
        {/* ... rest of header content */}
      </div>
      {/* ... rest of card content */}
    </Card>
  );
}
```

---

## Step 11: Update Page Card with Image Support

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-detail/page-card.tsx`

Update the page card to auto-generate an image when sufficient context exists:

```tsx
// Add to imports
import { useEffect, useRef, useState } from 'react';
import {
  useGeneratePageImage,
  useImageGenerationStatus,
} from '@/hooks/queries/use-generated-images';
import { Spinner } from '@/components/ui/spinner';

export function PageCard({ page, onClick, isSelected }: PageCardProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(page.imageUrl || null);
  const { data: imageStatus } = useImageGenerationStatus();
  const generateImage = useGeneratePageImage();
  const hasAttemptedRef = useRef(false);

  useEffect(() => {
    if (hasAttemptedRef.current) return;

    if (
      !imageUrl &&
      imageStatus?.available &&
      page.overview &&
      page.overview.length >= 20 &&
      !generateImage.isPending
    ) {
      hasAttemptedRef.current = true;
      generateImage.mutate(
        {
          path: page.path,
          title: page.title,
          overview: page.overview,
          // keywords optional; omit unless you have them on KLPageCard
        },
        {
          onSuccess: (data) => setImageUrl(data.url),
          onError: (error) => console.warn('Failed to generate page image:', error),
        }
      );
    }
  }, [imageUrl, imageStatus?.available, page.path, page.title, page.overview, generateImage]);

  return (
    <Card className="..." onClick={onClick} data-testid={`page-card-${page.path}`}>
      <div className="h-32 bg-gradient-to-br from-muted/50 to-muted flex items-center justify-center relative">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={page.title}
            className="w-full h-full object-cover"
            onError={() => {
              hasAttemptedRef.current = true;
              setImageUrl(null);
            }}
          />
        ) : generateImage.isPending ? (
          <div className="flex flex-col items-center gap-2">
            <Spinner size="lg" />
            <span className="text-xs text-muted-foreground">Generating...</span>
          </div>
        ) : (
          <FileText className="h-12 w-12 text-muted-foreground/40" />
        )}
      </div>

      {/* ...existing PageCard content... */}
    </Card>
  );
}
```

---

## Storage Structure

After implementation, generated images will be stored in team storage:

```
TEAM_DATA_DIR/
├── knowledge/
│   └── generated-media/
│       ├── domain-images/
│       │   └── {domainId}/
│       │       ├── metadata.json
│       │       └── thumbnail-{timestamp}.png
│       └── page-images/
│           └── {pageStorageId}/
│               ├── metadata.json
│               └── thumbnail-{timestamp}.png
└── ... other collections (agents, systems, knowledge entries, etc.) ...
```

---

## Environment Variables Summary

```bash
# Required for Imagen 3.0 via Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional overrides
AUTOMAKER_IMAGEN_MODEL=imagen-3.0-generate-002

# Kill switch
AUTOMAKER_DISABLE_GENERATED_MEDIA=false
```

---

## Test Strategy (TDD)

### Server (unit tests)

**Create failing tests first (RED)**, then implement minimal code (GREEN).

Suggested unit test file:

- `apps/server/tests/unit/routes/generated-media.test.ts` (NEW FILE)

Suggested test cases:

- `GET /api/generated-media/status` returns `available: false` when `AUTOMAKER_DISABLE_GENERATED_MEDIA=true`
- `POST /api/generated-media/generate/domain/:domainId` returns `503` when not available
- `GET /api/generated-media/domain/:domainId/thumbnail` returns `404` when no metadata exists
- `GET /api/generated-media/page/thumbnail?path=...` returns `400` when `path` is missing

Run:

```bash
npm -w apps/server run test:unit -- tests/unit/routes/generated-media.test.ts
```

### UI (unit tests)

Suggested unit test file:

- `apps/ui/src/hooks/queries/use-generated-images.test.ts` (NEW FILE)

Suggested test cases:

- `getGeneratedPageThumbnailUrl()` includes `path` and preserves `v`
- Auth query params are appended (`apiKey` when present, otherwise `token` when present)

Run:

```bash
npx vitest run --root apps/ui -c vitest.config.ts src/hooks/queries/use-generated-images.test.ts
```

---

## Rollback / Disable

- Disable generation: set `AUTOMAKER_DISABLE_GENERATED_MEDIA=true` and restart the server; `/api/generated-media/status` must return `available: false`, and generation endpoints must return `503`.
- Optional cleanup: delete generated media from team storage:

```bash
rm -rf "${TEAM_DATA_DIR:-./data/team}/knowledge/generated-media"
```

_(No DB migrations; rollback is just disabling + removing generated files.)_

---

## Verification Checklist

- [ ] GCP project created with billing enabled
- [ ] Vertex AI API enabled in GCP project
- [ ] Service account created with `aiplatform.user` role
- [ ] Service account key downloaded and configured
- [ ] `google-auth-library` package installed in `apps/server`
- [ ] Environment variables set correctly
- [ ] `/api/generated-media/status` returns `available: true` when configured (and `available: false` when disabled/misconfigured)
- [ ] Image generation service initializes without errors (no silent fallbacks)
- [ ] Images generated from title + overview prompts
- [ ] Images stored in team storage
- [ ] Domain thumbnail served via `GET /api/generated-media/domain/:domainId/thumbnail`
- [ ] Page thumbnail served via `GET /api/generated-media/page/thumbnail?path=...`
- [ ] Domain cards display generated images
- [ ] Page cards display generated images
- [ ] Caching prevents duplicate generation
- [ ] Error handling for API failures

---

## Troubleshooting

### "Permission Denied" Error

- Verify service account has `roles/aiplatform.user` permission
- Check the project ID matches the service account's project

### "Model Not Found" Error

- Ensure Vertex AI API is enabled: `gcloud services enable aiplatform.googleapis.com`
- Verify you're using a supported region (us-central1 recommended)
- Verify `AUTOMAKER_IMAGEN_MODEL` matches an available Imagen model in your project/region

### "Quota Exceeded" Error

- Check Vertex AI quotas in GCP Console
- Request quota increase if needed

### Images Not Loading in UI

- Check browser console for CORS errors
- Verify authentication is working for `/api/generated-media/` endpoints

---

## Cost Considerations

**Imagen 3.0 Pricing (approximate):**

- Standard quality: ~$0.020 per image
- Higher quality: ~$0.040 per image

**Optimization strategies:**

- Cache images aggressively (inputHash comparison)
- Only generate when overview is meaningful (>20 chars)
- Batch generation during off-peak hours
- Set reasonable rate limits
