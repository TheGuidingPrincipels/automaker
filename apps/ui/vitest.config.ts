import * as path from 'path';
import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    name: 'ui',
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts'],
    setupFiles: ['tests/vitest.setup.ts'],
  },
});
