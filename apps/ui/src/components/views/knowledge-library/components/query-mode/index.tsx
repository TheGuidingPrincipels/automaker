/**
 * Query Mode - Ask questions about your knowledge base
 *
 * Features:
 * - Question input with submit
 * - Answer display with source citations
 * - Conversation history
 * - Related topics suggestions
 */

import { useState, useRef, useEffect } from 'react';
import {
  useKLAsk,
  useKLConversations,
  useKLDeleteConversation,
} from '@/hooks/queries/use-knowledge-library';
import { useKnowledgeLibraryStore } from '@/store/knowledge-library-store';
import { ChatInterface } from './chat-interface';
import { AnswerCard } from './answer-card';
import { SourceCitation } from './source-citation';
import { ConversationList } from './conversation-list';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Loader2, MessageSquare, Plus, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KLAskResponse, KLConversation } from '@automaker/types';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: KLAskResponse['sources'];
  relatedTopics?: string[];
  confidence?: number;
  timestamp: Date;
}

export function QueryMode() {
  const askMutation = useKLAsk();
  const { data: conversationsData, isLoading: isLoadingConversations } = useKLConversations();
  const deleteConversationMutation = useKLDeleteConversation();

  // Local state
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showConversationList, setShowConversationList] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submitQuestion = async (nextQuestion?: string) => {
    const userQuestion = (nextQuestion ?? question).trim();
    if (!userQuestion || askMutation.isPending) return;

    setQuestion('');

    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userQuestion,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await askMutation.mutateAsync({
        question: userQuestion,
        conversation_id: conversationId ?? undefined,
        max_sources: 5,
      });

      // Store conversation ID for follow-up questions
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        relatedTopics: response.related_topics,
        confidence: response.confidence,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your question. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    await submitQuestion();
  };

  const handleRelatedTopicClick = (topic: string) => {
    setQuestion(topic);
    void submitQuestion(topic);
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    inputRef.current?.focus();
  };

  const handleSelectConversation = (conv: KLConversation) => {
    // Load conversation messages
    setConversationId(conv.id);
    setMessages(
      conv.turns.map((turn, idx) => ({
        id: `${conv.id}-${idx}`,
        role: turn.role as 'user' | 'assistant',
        content: turn.content,
        sources: turn.sources.map((s) => ({ file_path: s })),
        timestamp: new Date(turn.timestamp),
      }))
    );
    setShowConversationList(false);
  };

  const handleDeleteConversation = async (convId: string) => {
    await deleteConversationMutation.mutateAsync(convId);
    if (convId === conversationId) {
      handleNewConversation();
    }
  };

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <h2 className="font-medium">Ask Questions</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowConversationList(!showConversationList)}
          >
            <MessageSquare className="h-4 w-4 mr-2" />
            History
          </Button>
        </div>

        {/* Main content */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="max-w-lg w-full text-center">
            {/* Icon */}
            <div className="mx-auto mb-6 p-6 bg-primary/10 rounded-full w-fit">
              <MessageSquare className="h-12 w-12 text-primary" />
            </div>

            {/* Title */}
            <h2 className="text-xl font-semibold mb-2">Ask Your Knowledge Base</h2>

            {/* Description */}
            <p className="text-muted-foreground mb-8">
              Ask questions about your documents and get AI-powered answers with source citations.
            </p>

            {/* Question input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                ref={inputRef}
                type="text"
                placeholder="What would you like to know?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="flex-1"
              />
              <Button type="submit" disabled={!question.trim() || askMutation.isPending}>
                {askMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>

            {/* Suggestions */}
            <div className="mt-8">
              <p className="text-xs text-muted-foreground mb-3">Try asking:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {['What are the main topics?', 'Summarize the key concepts', 'How do I...?'].map(
                  (suggestion) => (
                    <Button
                      key={suggestion}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setQuestion(suggestion);
                        inputRef.current?.focus();
                      }}
                    >
                      {suggestion}
                    </Button>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Chat view
  return (
    <div className="h-full flex">
      {/* Conversation list sidebar (toggleable) */}
      {showConversationList && (
        <div className="w-64 border-r">
          <ConversationList
            conversations={conversationsData?.conversations ?? []}
            currentConversationId={conversationId}
            isLoading={isLoadingConversations}
            onSelectConversation={handleSelectConversation}
            onDeleteConversation={handleDeleteConversation}
            onNewConversation={handleNewConversation}
          />
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowConversationList(!showConversationList)}
            >
              <MessageSquare className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground">
              {conversationId ? 'Conversation' : 'New conversation'}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleNewConversation}>
            <Plus className="h-4 w-4 mr-1" />
            New
          </Button>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-6" ref={scrollRef}>
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onRelatedTopicClick={handleRelatedTopicClick}
              />
            ))}
            {askMutation.isPending && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="p-4 border-t">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-2">
            <Input
              ref={inputRef}
              type="text"
              placeholder="Ask a follow-up question..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={!question.trim() || askMutation.isPending}>
              {askMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

/**
 * Single chat message component
 */
interface ChatMessageProps {
  message: ChatMessage;
  onRelatedTopicClick: (topic: string) => void;
}

function ChatMessage({ message, onRelatedTopicClick }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%]', isUser && 'text-right')}>
        {isUser ? (
          <div className="bg-primary text-primary-foreground rounded-lg px-4 py-2">
            <p>{message.content}</p>
          </div>
        ) : (
          <AnswerCard
            answer={message.content}
            sources={message.sources}
            relatedTopics={message.relatedTopics}
            confidence={message.confidence}
            onRelatedTopicClick={onRelatedTopicClick}
          />
        )}
        <p className="text-xs text-muted-foreground mt-1">
          {message.timestamp.toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
