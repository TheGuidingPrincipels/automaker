/**
 * GET /image endpoint - Serve image files
 *
 * Requires authentication via:
 * - apiKey query parameter (Electron mode)
 * - token query parameter (web mode)
 * - session cookie (web mode)
 * - X-API-Key header (Electron mode)
 * - X-Session-Token header (web mode)
 */

import type { Request, Response } from 'express';
import * as secureFs from '../../../lib/secure-fs.js';
import path from 'path';
import { PathNotAllowedError } from '@automaker/platform';
import { validateApiKey, validateSession } from '../../../lib/auth.js';
import { getErrorMessage, logError } from '../common.js';

const SESSION_COOKIE_NAME = 'automaker_session';

export function createImageHandler() {
  return async (req: Request, res: Response): Promise<void> => {
    try {
      // Authenticate the request
      const isAuthenticated = checkImageAuthentication(req);
      if (!isAuthenticated) {
        res.status(401).json({ success: false, error: 'Authentication required' });
        return;
      }

      const { path: imagePath, projectPath } = req.query as {
        path?: string;
        projectPath?: string;
      };

      if (!imagePath) {
        res.status(400).json({ success: false, error: 'path is required' });
        return;
      }

      // Resolve full path
      const fullPath = path.isAbsolute(imagePath)
        ? imagePath
        : projectPath
          ? path.join(projectPath, imagePath)
          : imagePath;

      // Check if file exists
      try {
        await secureFs.access(fullPath);
      } catch (accessError) {
        if (accessError instanceof PathNotAllowedError) {
          res.status(403).json({ success: false, error: 'Path not allowed' });
          return;
        }
        res.status(404).json({ success: false, error: 'Image not found' });
        return;
      }

      // Read the file
      const buffer = await secureFs.readFile(fullPath);

      // Determine MIME type from extension
      const ext = path.extname(fullPath).toLowerCase();
      const mimeTypes: Record<string, string> = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.bmp': 'image/bmp',
      };

      res.setHeader('Content-Type', mimeTypes[ext] || 'application/octet-stream');
      res.setHeader('Cache-Control', 'public, max-age=3600');
      res.send(buffer);
    } catch (error) {
      logError(error, 'Serve image failed');
      res.status(500).json({ success: false, error: getErrorMessage(error) });
    }
  };
}

/**
 * Check if image request is authenticated
 * Supports multiple authentication methods
 */
function checkImageAuthentication(req: Request): boolean {
  // Check for API key in header (Electron mode)
  const headerKey = req.get('x-api-key');
  if (headerKey && validateApiKey(headerKey)) {
    return true;
  }

  // Check for session token in header (web mode)
  const sessionTokenHeader = req.get('x-session-token');
  if (sessionTokenHeader && validateSession(sessionTokenHeader)) {
    return true;
  }

  // Check for API key in query parameter (fallback)
  const queryKey = req.query.apiKey as string | undefined;
  if (queryKey && validateApiKey(queryKey)) {
    return true;
  }

  // Check for session token in query parameter (web mode with token)
  const queryToken = req.query.token as string | undefined;
  if (queryToken && validateSession(queryToken)) {
    return true;
  }

  // Check for session cookie (web mode)
  const sessionCookie = req.cookies?.[SESSION_COOKIE_NAME];
  if (sessionCookie && validateSession(sessionCookie)) {
    return true;
  }

  return false;
}
