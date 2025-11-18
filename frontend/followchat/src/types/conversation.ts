export interface ConversationNode {
  id: string
  parentId: string | null
  author: 'user' | 'assistant' | 'system'
  content: string
  summary?: string | null
  assistant_reply?: string | null
  children: string[]
}
