import { describe, expect, it } from 'vitest';

import type { KLBlockRoutingItemResponse } from '@automaker/types';
import { collectCreateFileProposals, groupRoutingBlocks } from './plan-review.utils';

const createBlock = (
  overrides: Partial<KLBlockRoutingItemResponse>
): KLBlockRoutingItemResponse => ({
  block_id: 'block-1',
  heading_path: ['Section'],
  content_preview: 'Preview',
  options: [],
  selected_option_index: null,
  custom_destination_file: null,
  custom_destination_section: null,
  custom_action: null,
  status: 'pending',
  ...overrides,
});

describe('plan-review utils', () => {
  describe('groupRoutingBlocks', () => {
    it('groups blocks by selected option destination file when available', () => {
      const blocks = [
        createBlock({
          block_id: 'block-a',
          options: [
            {
              destination_file: 'docs/a.md',
              destination_section: null,
              action: 'append',
              confidence: 0.9,
              reasoning: 'Reason A',
            },
          ],
        }),
        createBlock({
          block_id: 'block-b',
          selected_option_index: 1,
          options: [
            {
              destination_file: 'docs/a.md',
              destination_section: null,
              action: 'append',
              confidence: 0.7,
              reasoning: 'Reason A2',
            },
            {
              destination_file: 'docs/b.md',
              destination_section: null,
              action: 'append',
              confidence: 0.8,
              reasoning: 'Reason B',
            },
          ],
        }),
      ];

      const groups = groupRoutingBlocks(blocks);
      const groupKeys = groups.map((group) => group.key);

      expect(groupKeys).toContain('docs/a.md');
      expect(groupKeys).toContain('docs/b.md');
      expect(groups.find((group) => group.key === 'docs/a.md')?.blocks).toHaveLength(1);
      expect(groups.find((group) => group.key === 'docs/b.md')?.blocks).toHaveLength(1);
    });

    it('falls back to an unassigned group when no options exist', () => {
      const blocks = [createBlock({ block_id: 'block-empty', options: [] })];

      const groups = groupRoutingBlocks(blocks);

      expect(groups).toHaveLength(1);
      expect(groups[0].key).toBe('unassigned');
      expect(groups[0].blocks[0].block_id).toBe('block-empty');
    });
  });

  describe('collectCreateFileProposals', () => {
    it('returns unique create-file proposals with titles and overviews', () => {
      const blocks = [
        createBlock({
          block_id: 'block-create-1',
          options: [
            {
              destination_file: 'docs/new.md',
              destination_section: null,
              action: 'create_file',
              confidence: 0.9,
              reasoning: 'Create',
              proposed_file_title: 'New Doc',
              proposed_file_overview: '## Overview ' + 'a'.repeat(60),
            },
          ],
        }),
        createBlock({
          block_id: 'block-create-2',
          options: [
            {
              destination_file: 'docs/new.md',
              destination_section: null,
              action: 'create_file',
              confidence: 0.6,
              reasoning: 'Same file',
              proposed_file_title: 'New Doc Duplicate',
              proposed_file_overview: '## Overview ' + 'b'.repeat(60),
            },
          ],
        }),
      ];

      const proposals = collectCreateFileProposals(blocks);

      expect(proposals).toHaveLength(1);
      expect(proposals[0]).toEqual({
        destinationFile: 'docs/new.md',
        title: 'New Doc',
        overview: '## Overview ' + 'a'.repeat(60),
      });
    });
  });
});
