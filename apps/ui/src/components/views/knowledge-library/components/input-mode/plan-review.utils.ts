import type { KLDestinationOptionResponse, KLBlockRoutingItemResponse } from '@automaker/types';

export interface RoutingBlockGroup {
  key: string;
  destinationFile: string;
  blocks: KLBlockRoutingItemResponse[];
}

export interface CreateFileProposal {
  destinationFile: string;
  title: string;
  overview: string;
}

const getPrimaryOption = (
  block: KLBlockRoutingItemResponse
): KLDestinationOptionResponse | null => {
  if (block.selected_option_index !== null) {
    return block.options[block.selected_option_index] ?? null;
  }
  return block.options[0] ?? null;
};

export const groupRoutingBlocks = (blocks: KLBlockRoutingItemResponse[]): RoutingBlockGroup[] => {
  const groups = new Map<string, RoutingBlockGroup>();

  for (const block of blocks) {
    const option = getPrimaryOption(block);
    const key = option?.destination_file ?? 'unassigned';
    const destinationFile = option?.destination_file ?? 'Unassigned';

    const group = groups.get(key) ?? { key, destinationFile, blocks: [] };
    group.blocks.push(block);
    groups.set(key, group);
  }

  return Array.from(groups.values());
};

const getCreateFileOption = (
  block: KLBlockRoutingItemResponse
): KLDestinationOptionResponse | null => {
  if (block.selected_option_index !== null) {
    const selected = block.options[block.selected_option_index];
    if (selected?.action === 'create_file') return selected;
  }
  return block.options.find((option) => option.action === 'create_file') ?? null;
};

export const collectCreateFileProposals = (
  blocks: KLBlockRoutingItemResponse[]
): CreateFileProposal[] => {
  const proposals = new Map<string, CreateFileProposal>();

  for (const block of blocks) {
    const option = getCreateFileOption(block);
    if (!option?.destination_file || proposals.has(option.destination_file)) {
      continue;
    }

    proposals.set(option.destination_file, {
      destinationFile: option.destination_file,
      title: option.proposed_file_title ?? '',
      overview: option.proposed_file_overview ?? '',
    });
  }

  return Array.from(proposals.values());
};
