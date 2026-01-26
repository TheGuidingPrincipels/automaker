/**
 * Answer Card - Display AI-generated answers with sources
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Markdown } from '@/components/ui/markdown';
import { SourceCitation } from './source-citation';
import { Sparkles, Lightbulb } from 'lucide-react';
import type { KLAskSourceInfo } from '@automaker/types';

interface AnswerCardProps {
  answer: string;
  sources?: KLAskSourceInfo[];
  relatedTopics?: string[];
  onRelatedTopicClick?: (topic: string) => void;
  confidence?: number;
}

export function AnswerCard({
  answer,
  sources,
  relatedTopics,
  onRelatedTopicClick,
  confidence,
}: AnswerCardProps) {
  const hasSources = sources && sources.length > 0;
  const hasRelatedTopics = relatedTopics && relatedTopics.length > 0;

  return (
    <Card className="border-l-4 border-l-primary/50">
      <CardContent className="pt-4">
        {/* Answer text */}
        <Markdown className="max-w-none">{answer}</Markdown>

        {/* Sources */}
        {hasSources && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Sources</span>
              {confidence !== undefined && (
                <Badge variant="secondary" className="text-xs">
                  {Math.round(confidence * 100)}% confidence
                </Badge>
              )}
            </div>
            <div className="space-y-2">
              {sources.map((source, idx) => (
                <SourceCitation key={idx} source={source} />
              ))}
            </div>
          </div>
        )}

        {/* Related topics */}
        {hasRelatedTopics && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-medium">Related Topics</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {relatedTopics.map((topic) => (
                <Button
                  key={topic}
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => onRelatedTopicClick?.(topic)}
                >
                  {topic}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
