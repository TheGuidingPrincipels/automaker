import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { KLProposedNewFile } from '@/store/knowledge-library-store';
import type { CreateFileProposal } from '../plan-review.utils';

interface ProposedFilesPanelProps {
  proposals: CreateFileProposal[];
  proposedFiles: Record<string, KLProposedNewFile>;
  onUpdate: (filePath: string, updates: Partial<KLProposedNewFile>) => void;
}

const ProposedFileEntry = ({
  proposal,
  entry,
  onUpdate,
}: {
  proposal: CreateFileProposal;
  entry: KLProposedNewFile | undefined;
  onUpdate: (filePath: string, updates: Partial<KLProposedNewFile>) => void;
}) => {
  const titleValue = entry?.title ?? proposal.title;
  const overviewValue = entry?.overview ?? proposal.overview;
  const errors = entry?.errors ?? [];
  const isInvalid = entry ? !entry.isValid : false;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs">
          {proposal.destinationFile}
        </Badge>
        {isInvalid && (
          <Badge variant="destructive" className="text-xs">
            Needs updates
          </Badge>
        )}
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Title</Label>
          <Input
            value={titleValue}
            onChange={(event) => onUpdate(proposal.destinationFile, { title: event.target.value })}
            aria-invalid={isInvalid}
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Overview</Label>
          <Textarea
            value={overviewValue}
            onChange={(event) =>
              onUpdate(proposal.destinationFile, { overview: event.target.value })
            }
            aria-invalid={isInvalid}
          />
        </div>
      </div>

      {errors.length > 0 && (
        <ul className="text-xs text-destructive space-y-1">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const ProposedFilesPanel = ({
  proposals,
  proposedFiles,
  onUpdate,
}: ProposedFilesPanelProps) => {
  if (proposals.length === 0) return null;

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="text-sm">Proposed New Files</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {proposals.map((proposal) => (
          <ProposedFileEntry
            key={proposal.destinationFile}
            proposal={proposal}
            entry={proposedFiles[proposal.destinationFile]}
            onUpdate={onUpdate}
          />
        ))}
      </CardContent>
    </Card>
  );
};
