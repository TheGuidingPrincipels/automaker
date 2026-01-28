import { describe, expect, it } from 'vitest';

import { truncateFileName } from './sessions-dropdown';

describe('truncateFileName', () => {
  it('returns the original name when it is within the limit', () => {
    expect(truncateFileName('short.md', 20)).toBe('short.md');
  });

  it('truncates long names while preserving the extension', () => {
    expect(truncateFileName('1234567890.md', 10)).toBe('1234....md');
  });

  it('truncates long names without an extension', () => {
    expect(truncateFileName('1234567890', 8)).toBe('12345...');
  });

  it('supports dotfiles with extensions', () => {
    expect(truncateFileName('.env.production.local', 12)).toBe('.en....local');
  });
});
