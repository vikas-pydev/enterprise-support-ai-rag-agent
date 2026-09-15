import { CitationSource } from './api';

export type MessageRole = 'user' | 'assistant';

export interface PolicyChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isRefusal?: boolean;
  sources?: CitationSource[];
  durationMs?: number;
  error?: string | null;
}
