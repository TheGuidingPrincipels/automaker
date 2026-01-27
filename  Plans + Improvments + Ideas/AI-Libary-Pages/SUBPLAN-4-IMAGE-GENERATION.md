# Sub-Plan 4: Automatic Image Generation for Domains and Pages

## Objective

Implement automatic AI-powered image generation for knowledge library domains and pages using **Google Imagen 3.0** via Vertex AI. Images are generated when sufficient context exists (title + overview), stored in team storage for transferability, and displayed in the UI.

## Prerequisites

- **Sub-Plans 1-3 completed**: Domain types, gallery, and detail views exist
- **Google Cloud Platform (GCP) account** with billing enabled
- **Vertex AI API enabled** in your GCP project
- Understanding of team storage patterns

## Important: Google Image Generation Requirements

**Google's dedicated image generation model is Imagen 3.0**, accessed via Vertex AI. This is different from Gemini (which handles text/multimodal but NOT image generation).

| Aspect | Gemini API | Imagen 3.0 (Vertex AI) |
|--------|------------|------------------------|
| Package | `@google/generative-ai` | `@google-cloud/vertexai` |
| Capabilities | Text generation, image understanding | **Image generation** |
| Authentication | API key | Service account / ADC |
| Setup | Simple | Requires GCP project |

## Deliverables

1. GCP project setup with Vertex AI enabled
2. Service account credentials storage
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
GOOGLE_APPLICATION_CREDENTIALS=/path/to/automaker-imagen-key.json

# Alternative: Store key content directly (for deployment)
# GOOGLE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"..."}
```

---

## Step 2: Install Dependencies

```bash
npm install @google-cloud/vertexai --workspace=apps/server
```

---

## Step 3: Update Credentials Types

**File:** `libs/types/src/settings.ts`

Find the `Credentials` interface and add Google Cloud fields:

```typescript
export interface Credentials {
  version: number;
  apiKeys: {
    anthropic: string;
    anthropic_oauth_token: string;
    google: string;
    openai: string;
    gemini: string;
  };
  /** Google Cloud configuration for Vertex AI (Imagen) */
  googleCloud?: {
    projectId: string;
    /** Base64-encoded service account key JSON */
    serviceAccountKey?: string;
  };
}
```

Update `DEFAULT_CREDENTIALS`:

```typescript
export const DEFAULT_CREDENTIALS: Credentials = {
  version: 1,
  apiKeys: {
    anthropic: '',
    anthropic_oauth_token: '',
    google: '',
    openai: '',
    gemini: '',
  },
  googleCloud: {
    projectId: '',
    serviceAccountKey: '',
  },
};
```

---

## Step 4: Update Settings Service

**File:** `apps/server/src/services/settings-service.ts`

Add methods for Google Cloud credentials:

```typescript
/**
 * Get Google Cloud Project ID
 */
getGoogleCloudProjectId(): string | null {
  // Check credentials storage first
  const credentials = this.getCredentials();
  if (credentials.googleCloud?.projectId) {
    return credentials.googleCloud.projectId;
  }

  // Fall back to environment variable
  return process.env.GOOGLE_CLOUD_PROJECT || null;
}

/**
 * Get Google Cloud service account credentials
 * Returns the path to credentials file or the credentials object
 */
getGoogleCloudCredentials(): { type: 'file'; path: string } | { type: 'key'; credentials: object } | null {
  // Check for credentials file path in environment
  const credentialsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (credentialsPath) {
    return { type: 'file', path: credentialsPath };
  }

  // Check for stored service account key
  const credentials = this.getCredentials();
  if (credentials.googleCloud?.serviceAccountKey) {
    try {
      const keyJson = JSON.parse(
        Buffer.from(credentials.googleCloud.serviceAccountKey, 'base64').toString('utf-8')
      );
      return { type: 'key', credentials: keyJson };
    } catch {
      return null;
    }
  }

  // Check for inline key in environment
  const keyEnv = process.env.GOOGLE_SERVICE_ACCOUNT_KEY;
  if (keyEnv) {
    try {
      return { type: 'key', credentials: JSON.parse(keyEnv) };
    } catch {
      return null;
    }
  }

  return null;
}

/**
 * Check if Imagen (Vertex AI) is available
 */
isImagenAvailable(): boolean {
  return !!(this.getGoogleCloudProjectId() && this.getGoogleCloudCredentials());
}
```

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

import { VertexAI } from '@google-cloud/vertexai';
import { createLogger } from '@automaker/utils/logger';
import { TeamStorageService } from '../lib/team-storage';
import { SettingsService } from './settings-service';
import crypto from 'crypto';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

const logger = createLogger('ImageGenerationService');

export interface ImageGenerationOptions {
  /** Type of entity (domain or page) */
  entityType: 'domain' | 'page';
  /** Unique entity ID */
  entityId: string;
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
  private vertexAI: VertexAI | null = null;
  private teamStorage: TeamStorageService;
  private settingsService: SettingsService;
  private tempCredentialsPath: string | null = null;

  constructor(teamStorage: TeamStorageService, settingsService: SettingsService) {
    this.teamStorage = teamStorage;
    this.settingsService = settingsService;
  }

  /**
   * Initialize the Vertex AI client
   */
  private async initializeClient(): Promise<VertexAI> {
    if (this.vertexAI) return this.vertexAI;

    const projectId = this.settingsService.getGoogleCloudProjectId();
    if (!projectId) {
      throw new Error(
        'Google Cloud Project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable or configure in settings.'
      );
    }

    const credentialsConfig = this.settingsService.getGoogleCloudCredentials();
    if (!credentialsConfig) {
      throw new Error(
        'Google Cloud credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS environment variable or configure service account key in settings.'
      );
    }

    // If credentials are stored as key object, write to temp file
    // (Vertex AI SDK requires file path or ADC)
    if (credentialsConfig.type === 'key') {
      this.tempCredentialsPath = path.join(os.tmpdir(), `automaker-gcloud-${Date.now()}.json`);
      await fs.writeFile(
        this.tempCredentialsPath,
        JSON.stringify(credentialsConfig.credentials),
        { mode: 0o600 }
      );
      process.env.GOOGLE_APPLICATION_CREDENTIALS = this.tempCredentialsPath;
    }

    this.vertexAI = new VertexAI({
      project: projectId,
      location: 'us-central1', // Imagen is available in us-central1
    });

    return this.vertexAI;
  }

  /**
   * Cleanup temporary credentials file
   */
  async cleanup(): Promise<void> {
    if (this.tempCredentialsPath) {
      try {
        await fs.unlink(this.tempCredentialsPath);
      } catch {
        // Ignore cleanup errors
      }
      this.tempCredentialsPath = null;
    }
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

    // Initialize client
    const vertexAI = await this.initializeClient();

    // Get Imagen 3.0 model
    const model = vertexAI.preview.getGenerativeModel({
      model: 'imagen-3.0-generate-001',
    });

    // Build prompt
    const prompt = this.buildPrompt(options);
    const inputHash = this.generateInputHash(title, overview, keywords);

    try {
      // Generate image with Imagen 3.0
      const result = await model.generateContent({
        contents: [
          {
            role: 'user',
            parts: [{ text: prompt }],
          },
        ],
        generationConfig: {
          // Imagen-specific parameters
          candidateCount: 1,
          // Note: Actual Imagen parameters may differ - check Vertex AI docs
        } as any,
      });

      const response = result.response;

      // Extract image data from response
      let imageBase64: string | null = null;
      let mimeType = 'image/png';

      for (const candidate of response.candidates || []) {
        for (const part of candidate.content?.parts || []) {
          if ((part as any).inlineData) {
            imageBase64 = (part as any).inlineData.data;
            mimeType = (part as any).inlineData.mimeType || 'image/png';
            break;
          }
        }
        if (imageBase64) break;
      }

      if (!imageBase64) {
        throw new Error('No image data in Imagen response');
      }

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

      // Provide helpful error messages
      if (error.message?.includes('PERMISSION_DENIED')) {
        throw new Error('Vertex AI permission denied. Check service account permissions.');
      }
      if (error.message?.includes('RESOURCE_EXHAUSTED')) {
        throw new Error('Imagen API quota exceeded. Try again later.');
      }
      if (error.message?.includes('NOT_FOUND')) {
        throw new Error('Imagen model not found. Ensure Vertex AI API is enabled.');
      }

      throw error;
    }
  }

  /**
   * Check if image generation is available
   */
  isAvailable(): boolean {
    return this.settingsService.isImagenAvailable();
  }

  /**
   * Get image URL for serving
   */
  getImageUrl(entityType: 'domain' | 'page', entityId: string, filename: string): string {
    return `/api/generated-media/${entityType}/${entityId}/${filename}`;
  }
}
```

---

## Step 6: Update Team Storage for Generated Media

**File:** `apps/server/src/lib/team-storage.ts`

Find the `StorageCollection` type and add:

```typescript
export type StorageCollection =
  | 'agents'
  | 'systems'
  | 'blueprints'
  | 'knowledge-entries'
  | 'learnings'
  | 'domain-images'    // ADD
  | 'page-images';     // ADD
```

In the `initialize()` method, add directories for new collections:

```typescript
async initialize(): Promise<void> {
  // ... existing directories ...

  // Generated media directories
  await mkdir(join(this.basePath, 'domain-images'), { recursive: true });
  await mkdir(join(this.basePath, 'page-images'), { recursive: true });
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
 */

import { Router, Request, Response } from 'express';
import { TeamStorageService } from '../../lib/team-storage';
import { ImageGenerationService } from '../../services/image-generation-service';
import { SettingsService } from '../../services/settings-service';
import { authMiddleware } from '../../lib/auth';
import { createLogger } from '@automaker/utils/logger';

const logger = createLogger('GeneratedMediaRoutes');

export function createGeneratedMediaRoutes(
  teamStorage: TeamStorageService,
  settingsService: SettingsService
): Router {
  const router = Router();
  const imageService = new ImageGenerationService(teamStorage, settingsService);

  // Serve generated images
  router.get('/:entityType/:entityId/:filename', authMiddleware, async (req: Request, res: Response) => {
    const { entityType, entityId, filename } = req.params;

    if (entityType !== 'domain' && entityType !== 'page') {
      return res.status(400).json({ error: 'Invalid entity type' });
    }

    try {
      const collection = entityType === 'domain' ? 'domain-images' : 'page-images';
      const imageBuffer = await teamStorage.readFile(collection as any, entityId, filename);

      if (!imageBuffer) {
        return res.status(404).json({ error: 'Image not found' });
      }

      // Determine content type
      const ext = filename.split('.').pop()?.toLowerCase();
      const contentType = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : 'image/png';

      res.setHeader('Content-Type', contentType);
      res.setHeader('Cache-Control', 'public, max-age=31536000'); // Cache for 1 year
      res.send(imageBuffer);
    } catch (error) {
      logger.error('Failed to serve image', error);
      res.status(500).json({ error: 'Failed to serve image' });
    }
  });

  // Generate image for domain
  router.post('/generate/domain/:domainId', authMiddleware, async (req: Request, res: Response) => {
    const { domainId } = req.params;
    const { title, overview, keywords, forceRegenerate } = req.body;

    if (!title || !overview) {
      return res.status(400).json({ error: 'Title and overview are required' });
    }

    if (!imageService.isAvailable()) {
      return res.status(503).json({
        error: 'Image generation not available',
        message: 'Google Cloud credentials not configured. Set GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS.'
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
        url: imageService.getImageUrl('domain', domainId, result.filename),
      });
    } catch (error: any) {
      logger.error('Failed to generate domain image', error);
      res.status(500).json({ error: error.message || 'Failed to generate image' });
    }
  });

  // Generate image for page
  router.post('/generate/page/:pageId', authMiddleware, async (req: Request, res: Response) => {
    const { pageId } = req.params;
    const { title, overview, keywords, forceRegenerate } = req.body;

    if (!title || !overview) {
      return res.status(400).json({ error: 'Title and overview are required' });
    }

    if (!imageService.isAvailable()) {
      return res.status(503).json({
        error: 'Image generation not available',
        message: 'Google Cloud credentials not configured.'
      });
    }

    try {
      const result = await imageService.generateImage({
        entityType: 'page',
        entityId: pageId,
        title,
        overview,
        keywords,
        forceRegenerate,
      });

      res.json({
        success: true,
        image: result,
        url: imageService.getImageUrl('page', pageId, result.filename),
      });
    } catch (error: any) {
      logger.error('Failed to generate page image', error);
      res.status(500).json({ error: error.message || 'Failed to generate image' });
    }
  });

  // Check if image generation is available
  router.get('/status', authMiddleware, async (_req: Request, res: Response) => {
    const available = imageService.isAvailable();
    const projectId = settingsService.getGoogleCloudProjectId();

    res.json({
      available,
      provider: 'google-imagen',
      projectId: available ? projectId : null,
      message: available
        ? 'Imagen 3.0 via Vertex AI is configured and available'
        : 'Configure GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS to enable image generation',
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
import { createGeneratedMediaRoutes } from './routes/generated-media';

// After teamStorage and settingsService are initialized:
app.use('/api/generated-media', createGeneratedMediaRoutes(teamStorage, settingsService));
```

---

## Step 9: Create Frontend Hook

**File:** `apps/ui/src/hooks/queries/use-generated-images.ts` (NEW FILE)

```typescript
/**
 * Generated Images Hooks
 *
 * React Query hooks for managing AI-generated images via Imagen 3.0.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

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

interface GenerateImageResponse {
  success: boolean;
  image: GeneratedImage;
  url: string;
}

interface ImageGenerationStatus {
  available: boolean;
  provider: string;
  projectId: string | null;
  message: string;
}

/**
 * Check if image generation is available
 */
export function useImageGenerationStatus() {
  return useQuery({
    queryKey: ['generated-media', 'status'],
    queryFn: async (): Promise<ImageGenerationStatus> => {
      const response = await apiClient.get('/api/generated-media/status');
      return response.json();
    },
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
      const response = await apiClient.post(`/api/generated-media/generate/domain/${domainId}`, {
        body: JSON.stringify(request),
        headers: { 'Content-Type': 'application/json' },
      });
      return response.json();
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['domain-images', variables.domainId] });
    },
  });
}

/**
 * Generate image for a page
 */
export function useGeneratePageImage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      pageId,
      ...request
    }: GenerateImageRequest & { pageId: string }): Promise<GenerateImageResponse> => {
      const response = await apiClient.post(`/api/generated-media/generate/page/${pageId}`, {
        body: JSON.stringify(request),
        headers: { 'Content-Type': 'application/json' },
      });
      return response.json();
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['page-images', variables.pageId] });
    },
  });
}

/**
 * Build image URL for display
 */
export function getGeneratedImageUrl(
  entityType: 'domain' | 'page',
  entityId: string,
  filename: string
): string {
  return `/api/generated-media/${entityType}/${entityId}/${filename}`;
}
```

---

## Step 10: Update Domain Card with Image Support

**File:** `apps/ui/src/components/views/knowledge-library/components/domain-gallery/domain-card.tsx`

Update to show generated image when available:

```tsx
// Add to imports
import { useEffect, useState } from 'react';
import { useGenerateDomainImage, useImageGenerationStatus } from '@/hooks/queries/use-generated-images';
import { Spinner } from '@/components/ui/spinner';

// Update DomainCard component
export function DomainCard({ domain, onClick }: DomainCardProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(domain.imageUrl || null);
  const { data: imageStatus } = useImageGenerationStatus();
  const generateImage = useGenerateDomainImage();

  // Auto-generate image when sufficient context exists
  useEffect(() => {
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
  }, [imageUrl, imageStatus?.available, domain.fileCount, domain.description, domain.id]);

  return (
    <Card className="..." onClick={onClick}>
      <div className={cn('h-32 bg-gradient-to-br flex items-center justify-center relative', domain.gradientClasses)}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={domain.name}
            className="w-full h-full object-cover"
            onError={() => setImageUrl(null)} // Fallback to icon on load error
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

## Storage Structure

After implementation, generated images will be stored in team storage:

```
TEAM_DATA_DIR/
├── domain-images/
│   └── {domainId}/
│       ├── metadata.json
│       └── thumbnail-{timestamp}.png
├── page-images/
│   └── {pageId}/
│       ├── metadata.json
│       └── thumbnail-{timestamp}.png
└── ... other collections ...
```

---

## Environment Variables Summary

```bash
# Required for Imagen 3.0 via Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Alternative: Inline service account key (for containers/deployment)
GOOGLE_SERVICE_ACCOUNT_KEY={"type":"service_account","project_id":"..."}
```

---

## Verification Checklist

- [ ] GCP project created with billing enabled
- [ ] Vertex AI API enabled in GCP project
- [ ] Service account created with `aiplatform.user` role
- [ ] Service account key downloaded and configured
- [ ] `@google-cloud/vertexai` package installed
- [ ] Environment variables set correctly
- [ ] Image generation service initializes without errors
- [ ] Images generated from title + overview prompts
- [ ] Images stored in team storage
- [ ] Images served via API endpoint
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
