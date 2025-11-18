<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { marked } from 'marked'
import ConversationTree from './components/ConversationTree.vue'
import type { ConversationNode } from './types/conversation'

const API_BASE_URL = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

type ConversationOut = {
  id: number
  title: string
  created_at: string
}

type MessageOut = {
  id: number
  conversation_id: number
  content: string
  order_index: number
  summary: string | null
  parent_id: number | null
  assistant_reply: string | null
  created_at: string
}

type LLMReplyResponse = {
  user_message: MessageOut
}

const conversations = ref<ConversationOut[]>([])
const nodes = reactive<Record<string, ConversationNode>>({})
const messageOrder = ref<string[]>([])
const activeConversationId = ref<number | null>(null)
const activeNodeId = ref<string | null>(null)
const activeRootId = ref<string | null>(null)
const isTreeView = ref(false)
const isLoading = ref(true)
const isSending = ref(false)
const isCreatingConversation = ref(false)
const errorMessage = ref('')
const messageInput = ref('')
const composerTextareaRef = ref<HTMLTextAreaElement | null>(null)
const fullscreenTextareaRef = ref<HTMLTextAreaElement | null>(null)
const chatHistoryRef = ref<HTMLDivElement | null>(null)
const composerLineCount = ref(1)
const isComposerFullscreen = ref(false)
const COMPOSER_LINE_THRESHOLD = 5
const copiedMessageId = ref<string | null>(null)
let copyTimer: number | null = null

const messageNodeId = (messageId: number) => `message-${messageId}`

// Configure marked for safe rendering
marked.setOptions({
  breaks: true, // Convert line breaks to <br>
  gfm: true, // GitHub Flavored Markdown
})

// Parse markdown to HTML
const parseMarkdown = (text: string): string => {
  if (!text) return ''
  return marked.parse(text) as string
}

const getUserRootId = (startId: string | null) => {
  if (!startId) return null
  let cursor: ConversationNode | undefined = nodes[startId]
  // Traverse up to find the root (parent_id is null)
  while (cursor && cursor.parentId) {
    cursor = nodes[cursor.parentId]
  }
  return cursor?.id ?? null
}

// Function to get path from current node to root
const getPathToRoot = (nodeId: string | null): ConversationNode[] => {
  const path: ConversationNode[] = []
  if (!nodeId) return path
  let cursor: ConversationNode | undefined = nodes[nodeId]
  while (cursor) {
    path.push(cursor)
    if (!cursor.parentId) {
      break
    }
    cursor = nodes[cursor.parentId]
  }
  return path.reverse()
}

const currentPath = computed(() => {
  return getPathToRoot(activeNodeId.value)
})

const isDescendantOfRoot = (nodeId: string, rootId: string) => {
  let cursor: ConversationNode | undefined = nodes[nodeId]
  while (cursor) {
    if (cursor.id === rootId) {
      return true
    }
    cursor = cursor.parentId ? nodes[cursor.parentId] : undefined
  }
  return false
}

const rootNodeIds = computed(() => {
  return messageOrder.value.filter((id) => {
    const node = nodes[id]
    if (!node || node.author !== 'user') return false
    if (!node.parentId) return true
    const parent = nodes[node.parentId]
    return !parent || parent.author !== 'user'
  })
})

const treeNodes = computed<Record<string, ConversationNode>>(() => {
  const filtered: Record<string, ConversationNode> = {}
  const pendingChildren: Record<string, string[]> = {}

  messageOrder.value.forEach((id) => {
    const node = nodes[id]
    if (!node || node.author !== 'user') return
    let parentId = node.parentId
    while (parentId) {
      const parentNode = nodes[parentId]
      if (!parentNode) break
      if (parentNode.author === 'user') {
        break
      }
      parentId = parentNode.parentId
    }

    filtered[id] = {
      ...node,
      parentId,
      content: node.summary ?? node.content,
      children: [],
    }

    if (parentId) {
      if (!pendingChildren[parentId]) {
        pendingChildren[parentId] = []
      }
      pendingChildren[parentId].push(id)
    }
  })

  Object.entries(pendingChildren).forEach(([parentId, children]) => {
    if (filtered[parentId]) {
      filtered[parentId].children = children
    }
  })

  return filtered
})

const treeRootIds = computed(() => rootNodeIds.value.filter((id) => Boolean(treeNodes.value[id])))

const toggleView = () => {
  isTreeView.value = !isTreeView.value
}

const handleSelect = async (id: string) => {
  if (!nodes[id]) return
  activeNodeId.value = id
  
  // Get path to root from backend
  try {
    const messageId = parseInt(id.replace('message-', ''), 10)
    const pathMessages = await apiFetch<MessageOut[]>(`/messages/${messageId}/path-to-root`)
    
    // Update nodes with path information
    pathMessages.forEach((message) => {
      const msgId = messageNodeId(message.id)
      const parentId = message.parent_id ? messageNodeId(message.parent_id) : null
      
      if (!nodes[msgId]) {
        nodes[msgId] = {
          id: msgId,
          parentId,
          author: 'user', // All messages are user messages now
          content: message.content,
          summary: message.summary,
          assistant_reply: message.assistant_reply,
          children: [],
        }
      } else {
        // Update parentId and assistant_reply if they're different
        nodes[msgId].parentId = parentId
        nodes[msgId].assistant_reply = message.assistant_reply
      }
      
      // Update children relationship
      if (parentId && nodes[parentId]) {
        if (!nodes[parentId].children.includes(msgId)) {
          nodes[parentId].children.push(msgId)
        }
      }
    })
    
    // Update root ID
    const rootId = getUserRootId(id)
    if (rootId) {
      activeRootId.value = rootId
    }
  } catch (error) {
    console.error('Failed to get path to root:', error)
    // Fallback to local calculation
    const rootId = getUserRootId(id)
    if (rootId) {
      activeRootId.value = rootId
    }
  }
  
  isTreeView.value = false
  
  // Scroll to bottom after switching to chat view
  // Wait for DOM to update and currentPath to be computed
  await nextTick()
  await nextTick() // Double nextTick to ensure computed properties are updated
  
  const scrollToBottom = () => {
    if (chatHistoryRef.value) {
      const container = chatHistoryRef.value
      // Try multiple methods to ensure scrolling works
      container.scrollTop = container.scrollHeight
      // Also try scrollTo method
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'auto'
      })
      // Try scrolling to the last child element if it exists
      const lastChild = container.lastElementChild
      if (lastChild) {
        lastChild.scrollIntoView({ behavior: 'auto', block: 'end' })
      }
    }
  }
  
  // Try scrolling multiple times with increasing delays to ensure it works
  requestAnimationFrame(() => {
    scrollToBottom()
    setTimeout(() => {
      scrollToBottom()
      setTimeout(() => {
        scrollToBottom()
        // One more attempt after a longer delay to catch any late rendering
        setTimeout(() => {
          scrollToBottom()
        }, 200)
      }, 100)
    }, 50)
  })
}

const treeCanvasRef = ref<HTMLElement | null>(null)
const pan = reactive({ x: 0, y: 0 })
const lastPointer = reactive({ x: 0, y: 0 })
const isPanning = ref(false)
const zoom = ref(1)
let panAnimationFrame: number | null = null
const pendingPan = { x: 0, y: 0 }

const MIN_ZOOM = 0.45
const MAX_ZOOM = 2.2
const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const panTransform = computed(
  () => `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${zoom.value})`
)

const beginPan = (event: PointerEvent) => {
  const target = event.target as HTMLElement | null
  // Don't start panning if clicking on tree node elements (label, delete button, etc.)
  if (target?.closest('.tree-node__label') || target?.closest('.tree-node__delete') || target?.closest('.tree-node')) return
  isPanning.value = true
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
  ;(event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId)
}

const panMove = (event: PointerEvent) => {
  if (!isPanning.value) return
  const deltaX = event.clientX - lastPointer.x
  const deltaY = event.clientY - lastPointer.y
  pendingPan.x += deltaX
  pendingPan.y += deltaY
  lastPointer.x = event.clientX
  lastPointer.y = event.clientY
  if (panAnimationFrame === null) {
    panAnimationFrame = window.requestAnimationFrame(() => {
      pan.x += pendingPan.x
      pan.y += pendingPan.y
      pendingPan.x = 0
      pendingPan.y = 0
      panAnimationFrame = null
    })
  }
}

const endPan = (event: PointerEvent) => {
  if (!isPanning.value) return
  isPanning.value = false
  ;(event.currentTarget as HTMLElement | null)?.releasePointerCapture(event.pointerId)
}

const resetPan = () => {
  pan.x = 0
  pan.y = 0
  zoom.value = 1
  pendingPan.x = 0
  pendingPan.y = 0
}

const handleWheel = (event: WheelEvent) => {
  if (event.ctrlKey) return
  const delta = event.deltaY > 0 ? -0.08 : 0.08
  const nextZoom = clamp(zoom.value + delta, MIN_ZOOM, MAX_ZOOM)
  if (nextZoom === zoom.value) return

  const canvas = treeCanvasRef.value
  if (!canvas) {
    zoom.value = Math.round(nextZoom * 100) / 100
    return
  }

  const rect = canvas.getBoundingClientRect()
  const centerX = rect.width / 2
  const centerY = rect.height / 2
  const offsetX = event.clientX - rect.left - centerX
  const offsetY = event.clientY - rect.top - centerY
  const scale = nextZoom / zoom.value

  pan.x = pan.x + offsetX - offsetX * scale
  pan.y = pan.y + offsetY - offsetY * scale
  zoom.value = Math.round(nextZoom * 100) / 100
}

const updateComposerMetrics = () => {
  const textarea = composerTextareaRef.value
  if (!textarea) return
  textarea.style.height = 'auto'
  const styles = window.getComputedStyle(textarea)
  const lineHeight = parseFloat(styles.lineHeight || '20')
  const maxHeight = lineHeight * COMPOSER_LINE_THRESHOLD
  const fullHeight = textarea.scrollHeight
  composerLineCount.value = Math.max(1, Math.round(fullHeight / lineHeight))
  const newHeight = Math.min(fullHeight, maxHeight)
  textarea.style.height = `${newHeight}px`
}

const handleComposerKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const closeComposerFullscreen = () => {
  isComposerFullscreen.value = false
}

const openComposerFullscreen = () => {
  isComposerFullscreen.value = true
}

const apiFetch = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  if (!response.ok) {
    let detail = ''
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      try {
        const data = await response.json()
        detail = data?.detail || data?.message || ''
      } catch {
        detail = ''
      }
    } else {
      detail = await response.text()
    }
    throw new Error(detail || `请求失败 (${response.status})`)
  }
  // Handle 204 No Content responses (e.g., DELETE requests)
  if (response.status === 204) {
    return undefined as T
  }
  // Check if response has content
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    const text = await response.text()
    if (!text || text.trim() === '') {
      return undefined as T
    }
    try {
      return JSON.parse(text) as T
    } catch {
      return undefined as T
    }
  }
  // For non-JSON responses, try to parse as JSON anyway (fallback)
  try {
    const text = await response.text()
    if (!text || text.trim() === '') {
      return undefined as T
    }
    return JSON.parse(text) as T
  } catch {
    return undefined as T
  }
}

const hydrateNodes = (messages: MessageOut[]) => {
  Object.keys(nodes).forEach((key) => delete nodes[key])
  messageOrder.value = []
  const sorted = [...messages].sort((a, b) => a.order_index - b.order_index)
  sorted.forEach((message) => {
    const id = messageNodeId(message.id)
    const parentId = message.parent_id ? messageNodeId(message.parent_id) : null
    nodes[id] = {
      id,
      parentId,
      author: 'user', // All messages are user messages now
      content: message.content,
      summary: message.summary,
      assistant_reply: message.assistant_reply,
      children: [],
    }
    if (parentId && nodes[parentId]) {
      if (!nodes[parentId].children.includes(id)) {
        nodes[parentId].children.push(id)
      }
    }
    messageOrder.value.push(id)
  })
  activeNodeId.value = messageOrder.value[messageOrder.value.length - 1] ?? null
  activeRootId.value = getUserRootId(activeNodeId.value)
}

const loadConversations = async () => {
  const list = await apiFetch<ConversationOut[]>('/conversations')
  if (!list.length) {
    const conversation = await apiFetch<ConversationOut>('/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    conversations.value = [conversation]
    activeConversationId.value = conversation.id
    return
  }
  conversations.value = list
  const hasActive = list.some((item) => item.id === activeConversationId.value)
  if (!hasActive) {
    activeConversationId.value = list[0]?.id ?? null
  }
}

const resolveBranchAnchor = () => {
  if (activeNodeId.value && nodes[activeNodeId.value]) {
    return activeNodeId.value
  }
  return messageOrder.value[messageOrder.value.length - 1] ?? null
}

const loadMessages = async () => {
  if (!activeConversationId.value) return
  const messages = await apiFetch<MessageOut[]>(`/conversations/${activeConversationId.value}/messages`)
  hydrateNodes(messages)
}

const refreshMessages = async () => {
  if (!activeConversationId.value) {
    hydrateNodes([])
    isLoading.value = false
    return
  }
  isLoading.value = true
  try {
    await loadMessages()
  } finally {
    isLoading.value = false
  }
}

const selectConversation = async (conversationId: number) => {
  // Always refresh if switching conversations, even if same ID (to reload messages)
  const wasActive = conversationId === activeConversationId.value
  activeConversationId.value = conversationId
  messageInput.value = ''
  isTreeView.value = false
  errorMessage.value = ''
  try {
    await refreshMessages()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载对话失败，请稍后重试'
  }
}

const deleteConversation = async (conversationId: number, event: Event) => {
  event.stopPropagation() // Prevent triggering selectConversation
  if (!confirm('确定要删除这个对话吗？')) return
  
  try {
    await apiFetch(`/conversations/${conversationId}`, {
      method: 'DELETE',
    })
    
    // Reload conversations list first to get updated state
    await loadConversations()
    
    // If deleted conversation was active, switch to another or clear
    if (conversationId === activeConversationId.value) {
      if (conversations.value.length > 0) {
        // Use selectConversation to properly switch and refresh
        await selectConversation(conversations.value[0].id)
      } else {
        activeConversationId.value = null
        hydrateNodes([])
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除对话失败，请稍后重试'
  }
}

const deleteMessage = async (nodeId: string, event: Event) => {
  event.stopPropagation() // Prevent triggering node selection
  const messageId = parseInt(nodeId.replace('message-', ''), 10)
  if (isNaN(messageId)) {
    console.error('Invalid message ID:', nodeId)
    return
  }
  
  if (!confirm('确定要删除这条消息吗？删除后，该消息的所有子消息也会被删除。')) return
  
  try {
    // Save node info before deletion
    const node = nodes[nodeId]
    const parentId = node?.parentId
    
    // Call API to delete message (backend will cascade delete children)
    await apiFetch(`/messages/${messageId}`, {
      method: 'DELETE',
    })
    
    // Reload messages to sync with backend (this will handle all cascaded deletions)
    await refreshMessages()
    
    // Update active node if the deleted node was active
    if (activeNodeId.value === nodeId) {
      // Find a new active node
      const remainingIds = messageOrder.value.filter(id => id !== nodeId)
      if (remainingIds.length > 0) {
        activeNodeId.value = remainingIds[remainingIds.length - 1]
      } else {
        activeNodeId.value = null
      }
      activeRootId.value = getUserRootId(activeNodeId.value)
    }
  } catch (error) {
    console.error('Failed to delete message:', error)
    errorMessage.value = error instanceof Error ? error.message : '删除消息失败，请稍后重试'
  }
}

const startNewConversation = async () => {
  if (isCreatingConversation.value) return
  isCreatingConversation.value = true
  errorMessage.value = ''
  isTreeView.value = false
  try {
    const conversation = await apiFetch<ConversationOut>('/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    activeConversationId.value = conversation.id
    messageInput.value = ''
    await loadConversations()
    await refreshMessages()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '新建对话失败，请稍后再试'
  } finally {
    isCreatingConversation.value = false
  }
}

const appendMessages = (messages: MessageOut[], anchorId?: string | null) => {
  const sorted = [...messages].sort((a, b) => a.order_index - b.order_index)
  sorted.forEach((message) => {
    const id = messageNodeId(message.id)
    if (nodes[id]) {
      // Update existing node with assistant_reply if it exists
      if (message.assistant_reply) {
        nodes[id].assistant_reply = message.assistant_reply
      }
      return
    }
    const parentId = message.parent_id ? messageNodeId(message.parent_id) : (anchorId ?? resolveBranchAnchor())
    nodes[id] = {
      id,
      parentId,
      author: 'user', // All messages are user messages now
      content: message.content,
      summary: message.summary,
      assistant_reply: message.assistant_reply,
      children: [],
    }
    if (parentId && nodes[parentId]) {
      if (!nodes[parentId].children.includes(id)) {
        nodes[parentId].children.push(id)
      }
    }
    if (!messageOrder.value.includes(id)) {
      messageOrder.value.push(id)
    }
  })
  if (sorted.length) {
    activeNodeId.value = messageNodeId(sorted[sorted.length - 1].id)
    activeRootId.value = getUserRootId(activeNodeId.value)
  }
}

const loadInitialData = async () => {
  errorMessage.value = ''
  try {
    await loadConversations()
    await refreshMessages()
  } catch (error) {
    isLoading.value = false
    errorMessage.value = error instanceof Error ? error.message : '无法连接后端服务'
  }
}

const sendMessage = async () => {
  const content = messageInput.value.trim()
  if (!content || !activeConversationId.value || isSending.value) return

  isSending.value = true
  errorMessage.value = ''
  try {
    // Get current active node ID and convert to message ID
    const branchAnchorId = resolveBranchAnchor()
    let parentId: number | null = null
    if (branchAnchorId) {
      // Extract message ID from node ID (format: "message-123")
      const match = branchAnchorId.match(/^message-(\d+)$/)
      if (match) {
        parentId = parseInt(match[1], 10)
      }
    }
    
    const payload: { content: string; parent_id?: number | null } = { content }
    if (parentId !== null) {
      payload.parent_id = parentId
    }
    
    // 发送流式请求
    const response = await fetch(
      `${API_BASE_URL}/conversations/${activeConversationId.value}/llm-reply`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }
    )
    
    if (!response.ok) {
      let detail = ''
      const contentType = response.headers.get('content-type') ?? ''
      if (contentType.includes('application/json')) {
        try {
          const data = await response.json()
          detail = data?.detail || data?.message || ''
        } catch {
          detail = ''
        }
      } else {
        detail = await response.text()
      }
      throw new Error(detail || `请求失败 (${response.status})`)
    }
    
    // 处理流式响应
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('无法读取响应流')
    }
    
    let userMessageId: number | null = null
    let userMessageNodeId: string | null = null
    let assistantReplyContent = ''
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 保留最后一个不完整的行
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (!line.trim()) continue
        
        try {
          const data = JSON.parse(line)
          if (data.type === 'message_id') {
            // 收到消息 ID，刷新消息以获取用户消息节点
            userMessageId = data.message_id
            userMessageNodeId = messageNodeId(userMessageId)
            // 刷新消息以获取新创建的用户消息
            await refreshMessages()
          } else if (data.type === 'delta') {
            assistantReplyContent += data.content
            // 实时更新 assistant_reply
            if (userMessageNodeId && nodes[userMessageNodeId]) {
              nodes[userMessageNodeId].assistant_reply = assistantReplyContent
            }
          } else if (data.type === 'error') {
            throw new Error(data.content)
          } else if (data.type === 'done') {
            // 流式输出完成
          }
        } catch (e) {
          // 忽略 JSON 解析错误（可能是部分数据）
          if (e instanceof SyntaxError) {
            console.warn('Failed to parse stream chunk:', line)
          } else {
            throw e
          }
        }
      }
    }
    
    // 处理剩余的 buffer
    if (buffer.trim()) {
      try {
        const data = JSON.parse(buffer)
        if (data.type === 'delta') {
          assistantReplyContent += data.content
          if (userMessageNodeId && nodes[userMessageNodeId]) {
            nodes[userMessageNodeId].assistant_reply = assistantReplyContent
          }
        }
      } catch (e) {
        // 忽略解析错误
      }
    }
    
    // 流式输出完成后，刷新消息以获取完整数据（包括 ID 等）
    await refreshMessages()
    messageInput.value = ''
    if (isComposerFullscreen.value) {
      closeComposerFullscreen()
    }
    await nextTick()
    updateComposerMetrics()
    await loadConversations()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '发送失败，请稍后再试'
    await refreshMessages()
  } finally {
    isSending.value = false
  }
}

const copyMessage = async (nodeId: string, text: string) => {
  if (!text) return
  try {
    await navigator.clipboard?.writeText(text)
    copiedMessageId.value = nodeId
    if (copyTimer) {
      window.clearTimeout(copyTimer)
    }
    copyTimer = window.setTimeout(() => {
      copiedMessageId.value = null
      copyTimer = null
    }, 2000)
  } catch (error) {
    console.warn('复制失败', error)
    copiedMessageId.value = null
  }
}

onMounted(() => {
  updateComposerMetrics()
  loadInitialData()
})

watch(
  [() => rootNodeIds.value, () => activeNodeId.value],
  ([roots, activeId]) => {
    const rootFromActive = getUserRootId(activeId)
    if (rootFromActive) {
      activeRootId.value = rootFromActive
      return
    }
    if (!activeRootId.value || !roots.includes(activeRootId.value)) {
      activeRootId.value = roots[0] ?? null
    }
  },
  { immediate: true }
)

watch(messageInput, () => {
  nextTick(() => {
    updateComposerMetrics()
    if (isComposerFullscreen.value && fullscreenTextareaRef.value) {
      fullscreenTextareaRef.value.scrollTop = fullscreenTextareaRef.value.scrollHeight
    }
  })
})

// Watch for tree view to chat view transition and scroll to bottom
watch(isTreeView, async (newValue, oldValue) => {
  // When switching from tree view to chat view
  if (oldValue === true && newValue === false) {
    // Wait for DOM to update
    await nextTick()
    await nextTick() // Double nextTick to ensure computed properties are updated
    
    const scrollToBottom = () => {
      if (chatHistoryRef.value) {
        const container = chatHistoryRef.value
        // Try multiple methods to ensure scrolling works
        container.scrollTop = container.scrollHeight
        // Also try scrollTo method
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'auto'
        })
        // Try scrolling to the last child element if it exists
        const lastChild = container.lastElementChild
        if (lastChild) {
          lastChild.scrollIntoView({ behavior: 'auto', block: 'end' })
        }
      }
    }
    
    // Try scrolling multiple times with increasing delays to ensure it works
    requestAnimationFrame(() => {
      scrollToBottom()
      setTimeout(() => {
        scrollToBottom()
        setTimeout(() => {
          scrollToBottom()
          // One more attempt after a longer delay to catch any late rendering
          setTimeout(() => {
            scrollToBottom()
          }, 200)
        }, 100)
      }, 50)
    })
  }
})

// Watch currentPath changes and scroll to bottom when it updates
watch(currentPath, async () => {
  // Only scroll if we're in chat view (not tree view)
  if (!isTreeView.value && chatHistoryRef.value) {
    await nextTick()
    requestAnimationFrame(() => {
      if (chatHistoryRef.value) {
        const container = chatHistoryRef.value
        container.scrollTop = container.scrollHeight
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'auto'
        })
        const lastChild = container.lastElementChild
        if (lastChild) {
          lastChild.scrollIntoView({ behavior: 'auto', block: 'end' })
        }
      }
    })
  }
}, { flush: 'post' })

watch(isComposerFullscreen, () => {
  nextTick(() => {
    if (isComposerFullscreen.value) {
      fullscreenTextareaRef.value?.focus()
      const position = messageInput.value.length
      fullscreenTextareaRef.value?.setSelectionRange(position, position)
    } else {
      composerTextareaRef.value?.focus()
    }
  })
  document.body.style.overflow = isComposerFullscreen.value ? 'hidden' : ''
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  if (panAnimationFrame !== null) {
    window.cancelAnimationFrame(panAnimationFrame)
    panAnimationFrame = null
  }
})

const zoomPercent = computed(() => Math.round(zoom.value * 100))
</script>

<template>
  <div class="page">
    <main v-if="!isTreeView" class="immersive-shell">
      <aside class="root-sidebar">
        <div class="root-sidebar__header">
          <h3>历史记录</h3>
          <div class="root-sidebar__actions">
            <button
              type="button"
              class="root-sidebar__action"
              :disabled="isCreatingConversation"
              @click="startNewConversation"
            >
              {{ isCreatingConversation ? '创建中…' : '新对话' }}
            </button>
            <button type="button" class="root-sidebar__action root-sidebar__action--ghost" @click="toggleView">
              查看树
            </button>
  </div>
        </div>
        <template v-if="conversations.length">
          <ul class="root-sidebar__list">
            <li v-for="conversation in conversations" :key="conversation.id">
              <div
                class="root-sidebar__item"
                :class="{ active: conversation.id === activeConversationId }"
                @click="selectConversation(conversation.id)"
              >
                <span class="root-sidebar__emoji">🗂️</span>
                <span class="root-sidebar__title">{{ conversation.title || '新对话' }}</span>
                <span v-if="conversation.id === activeConversationId" class="root-sidebar__badge">当前</span>
                <button
                  type="button"
                  class="root-sidebar__delete"
                  @click="deleteConversation(conversation.id, $event)"
                  title="删除对话"
                >
                  ×
                </button>
              </div>
            </li>
          </ul>
        </template>
        <p v-else class="root-sidebar__empty">暂无历史记录，先创建一个新对话吧。</p>
      </aside>

      <section class="conversation-surface">
        <div class="conversation-scroll" id="chat-history" ref="chatHistoryRef">
          <div v-if="isLoading" class="loading-state">
            <p class="loading-state__text">正在从数据库加载历史对话...</p>
          </div>
          <div v-else-if="!currentPath.length" class="empty-state">
            <p class="empty-state__eyebrow">与 FollowChat 的对话</p>
            <h2>发送第一个问题</h2>
            <p>例如：“帮我想一个人工智能方向的本科毕业设计选题”</p>
          </div>
          <template v-else>
            <template v-for="node in currentPath" :key="node.id">
              <!-- User message -->
              <article
                class="message-block message-block--user"
              >
                <div class="message-block__avatar">
                  <span>你</span>
                </div>

                <div class="message-card message-card--user">
                  <div class="message-card__header">
                    <span class="message-card__author">你</span>
                  </div>
                  <div class="message-card__body" v-html="parseMarkdown(node.content)"></div>
                  <div class="message-card__toolbar">
                    <button type="button" class="toolbar-btn" @click="copyMessage(node.id, node.content)">
                      {{ copiedMessageId === node.id ? '已复制' : '复制' }}
                    </button>
                  </div>
                </div>
              </article>

              <!-- Assistant reply (if exists) -->
              <article
                v-if="node.assistant_reply"
                class="message-block message-block--assistant"
              >
                <div class="message-block__avatar">
                  <span>FC</span>
                </div>

                <div class="message-card message-card--assistant">
                  <div class="message-card__header">
                    <span class="message-card__author">FollowChat</span>
                  </div>
                  <div class="message-card__body" v-html="parseMarkdown(node.assistant_reply || '')"></div>
                  <div class="message-card__toolbar">
                    <button type="button" class="toolbar-btn" @click="copyMessage(node.id + '-reply', node.assistant_reply || '')">
                      {{ copiedMessageId === node.id + '-reply' ? '已复制' : '复制' }}
                    </button>
                  </div>
                </div>
              </article>
            </template>
          </template>
        </div>

        <div class="composer-surface">
          <div class="composer-box">
            <textarea
              ref="composerTextareaRef"
              v-model="messageInput"
              class="composer-input composer-textarea"
              placeholder="输入你的问题开始对话..."
              @keydown="handleComposerKeydown"
            />
            <div class="composer-actions">
              <button
                v-if="composerLineCount > COMPOSER_LINE_THRESHOLD || isComposerFullscreen"
                type="button"
                class="composer-expand"
                @click="isComposerFullscreen ? closeComposerFullscreen() : openComposerFullscreen()"
              >
                {{ isComposerFullscreen ? '退出全屏' : '全屏' }}
              </button>
              <button
                type="button"
                class="composer-send"
                :disabled="isSending || !messageInput.trim() || !activeConversationId"
                @click="sendMessage"
              >
                {{ isSending ? '发送中…' : '发送' }}
              </button>
            </div>
          </div>
          <p v-if="errorMessage" class="feedback feedback--error">
            {{ errorMessage }}
            <button type="button" class="toolbar-btn feedback__retry" @click="loadInitialData">重试</button>
          </p>
        </div>
      </section>
    </main>

    <main v-else class="tree-layout">
      <div class="tree-toolbar">
        <div class="tree-toolbar__info">
          <h2>对话树</h2>
          <p>按住空白区域拖拽，滚轮缩放，点击节点可回到对话路径</p>
        </div>
        <div class="tree-toolbar__actions">
          <span class="tree-toolbar__zoom">缩放 {{ zoomPercent }}%</span>
          <button type="button" class="tree-toolbar__action" @click="resetPan">重置视图</button>
          <button type="button" class="tree-toolbar__action tree-toolbar__action--accent" @click="toggleView">
            返回对话
          </button>
        </div>
      </div>
      <section
        ref="treeCanvasRef"
        class="tree-canvas"
        :class="{ 'is-panning': isPanning }"
        @pointerdown="beginPan"
        @pointermove="panMove"
        @pointerup="endPan"
        @pointerleave="endPan"
        @dblclick="resetPan"
        @wheel.prevent="handleWheel"
      >
        <div class="tree-space" :style="{ transform: panTransform }">
          <template v-if="treeRootIds.length">
            <ConversationTree
              v-for="rootId in treeRootIds"
              :key="rootId"
              :node-id="rootId"
              :nodes="treeNodes"
              :active-id="activeNodeId"
              @select="handleSelect"
              @delete="deleteMessage"
            />
          </template>
          <p v-else class="tree-empty-state">暂无可视化内容，先发送一条消息吧。</p>
        </div>
      </section>
    </main>
  </div>

  <div v-if="isComposerFullscreen" class="composer-fullscreen">
    <div class="composer-fullscreen__backdrop" @click="closeComposerFullscreen"></div>
    <section class="composer-fullscreen__panel">
      <div class="composer-fullscreen__body">
        <textarea
          ref="fullscreenTextareaRef"
          v-model="messageInput"
          class="composer-fullscreen__textarea"
          placeholder="输入你的问题开始对话..."
          @keydown="handleComposerKeydown"
        />
      </div>
      <footer class="composer-fullscreen__footer">
        <button type="button" class="toolbar-btn composer-fullscreen__footer-btn" @click="closeComposerFullscreen">
          取消
        </button>
        <button type="button" class="composer-send composer-fullscreen__footer-btn" @click="sendMessage">发送</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 2rem clamp(1.5rem, 4vw, 3rem) 3rem;
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  background: radial-gradient(circle at 20% 0%, rgba(92, 197, 255, 0.18), transparent 45%),
    radial-gradient(circle at 80% 0%, rgba(255, 139, 110, 0.18), transparent 45%), #05050b;
  color: #eff4ff;
  box-sizing: border-box;
}

.page__actions {
  position: sticky;
  top: 1rem;
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
  z-index: 5;
}

.masthead__action {
  padding: 0.55rem 1.4rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.masthead__action:hover {
  border-color: rgba(92, 197, 255, 0.8);
  background: rgba(92, 197, 255, 0.15);
}

.immersive-shell {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.root-sidebar {
  width: 260px;
  border-radius: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  padding: 1rem;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 2rem;
  align-self: flex-start;
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.root-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.root-sidebar__header h3 {
  margin: 0;
  font-size: 1rem;
}

.root-sidebar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  justify-content: flex-end;
}

.root-sidebar__action {
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  border-radius: 999px;
  padding: 0.25rem 0.9rem;
  cursor: pointer;
  font-size: 0.85rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.root-sidebar__action:hover:not(:disabled) {
  border-color: rgba(92, 197, 255, 0.8);
  background: rgba(92, 197, 255, 0.15);
}

.root-sidebar__action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.root-sidebar__action--ghost {
  background: transparent;
}

.root-sidebar__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.root-sidebar__item {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
  border-radius: 1rem;
  padding: 0.65rem;
  color: inherit;
  text-align: left;
  display: flex;
  gap: 0.5rem;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.root-sidebar__item:hover {
  border-color: rgba(92, 197, 255, 0.5);
  background: rgba(92, 197, 255, 0.1);
  transform: translateY(-1px);
}

.root-sidebar__item.active {
  border-color: rgba(92, 197, 255, 0.7);
  background: rgba(92, 197, 255, 0.18);
  box-shadow: 0 10px 30px rgba(92, 197, 255, 0.25);
}

.root-sidebar__emoji {
  font-size: 1.1rem;
}

.root-sidebar__title {
  flex: 1;
  font-size: 0.9rem;
  line-height: 1.35;
}

.root-sidebar__badge {
  font-size: 0.75rem;
  align-self: flex-start;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  padding: 0.1rem 0.5rem;
}

.root-sidebar__delete {
  align-self: flex-start;
  border: none;
  background: rgba(255, 100, 100, 0.2);
  color: rgba(255, 150, 150, 0.9);
  border-radius: 50%;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.2rem;
  line-height: 1;
  padding: 0;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
  flex-shrink: 0;
}

.root-sidebar__delete:hover {
  background: rgba(255, 100, 100, 0.4);
  color: rgba(255, 200, 200, 1);
  transform: scale(1.1);
}

.root-sidebar__empty {
  margin: 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.6);
}

.conversation-surface {
  border-radius: 1.75rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(5, 5, 11, 0.85);
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.45);
  min-height: 70vh;
  width: min(960px, 100%);
}

.conversation-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-right: 0.5rem;
  padding-bottom: 2rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(92, 197, 255, 0.4) transparent;
}

.conversation-scroll::-webkit-scrollbar {
  width: 6px;
}

.conversation-scroll::-webkit-scrollbar-thumb {
  background: rgba(92, 197, 255, 0.4);
  border-radius: 999px;
}

.loading-state,
.tree-empty-state {
  padding: 2rem 1rem;
  text-align: center;
  color: rgba(239, 244, 255, 0.8);
}

.loading-state__text {
  font-size: 1rem;
  letter-spacing: 0.02em;
}

.empty-state {
  border-radius: 1.5rem;
  padding: 2rem;
  border: 1px dashed rgba(255, 255, 255, 0.2);
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
}

.empty-state__eyebrow {
  margin: 0 0 0.3rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.8rem;
}

.empty-state h2 {
  margin: 0 0 0.5rem;
}

.message-block {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
  width: 100%;
}

.message-block--user {
  justify-content: flex-end;
}

.message-block--user .message-block__avatar {
  order: 2;
}

.message-block--user .message-card {
  order: 1;
  align-self: flex-end;
}

.message-block__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 600;
  font-size: 0.85rem;
  background: rgba(92, 197, 255, 0.2);
  color: #fff;
}

.message-block--user .message-block__avatar {
  background: rgba(255, 255, 255, 0.15);
}

.message-card {
  border-radius: 1.25rem;
  padding: 1.1rem 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
  width: fit-content;
  max-width: min(720px, calc(100% - 120px));
}

.message-card--assistant {
  background: rgba(15, 16, 30, 0.85);
}

.message-card--user {
  background: rgba(92, 197, 255, 0.1);
  border-color: rgba(92, 197, 255, 0.3);
}

.message-card__header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 0.25rem;
  font-size: 0.88rem;
  color: rgba(255, 255, 255, 0.7);
}

.message-card__body {
  margin: 0;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.92);
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* Markdown styles */
.message-card__body :deep(h1),
.message-card__body :deep(h2),
.message-card__body :deep(h3),
.message-card__body :deep(h4),
.message-card__body :deep(h5),
.message-card__body :deep(h6) {
  margin: 1.2em 0 0.6em;
  font-weight: 600;
  line-height: 1.3;
  color: rgba(255, 255, 255, 0.95);
}

.message-card__body :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 0.3em;
}

.message-card__body :deep(h2) {
  font-size: 1.3em;
}

.message-card__body :deep(h3) {
  font-size: 1.15em;
}

.message-card__body :deep(p) {
  margin: 0.8em 0;
}

.message-card__body :deep(p:first-child) {
  margin-top: 0;
}

.message-card__body :deep(p:last-child) {
  margin-bottom: 0;
}

.message-card__body :deep(ul),
.message-card__body :deep(ol) {
  margin: 0.8em 0;
  padding-left: 1.8em;
}

.message-card__body :deep(li) {
  margin: 0.4em 0;
}

.message-card__body :deep(blockquote) {
  margin: 0.8em 0;
  padding: 0.5em 1em;
  border-left: 3px solid rgba(92, 197, 255, 0.5);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.85);
}

.message-card__body :deep(code) {
  padding: 0.2em 0.4em;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 0.9em;
  color: rgba(255, 255, 255, 0.9);
}

.message-card__body :deep(pre) {
  margin: 0.8em 0;
  padding: 1em;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.message-card__body :deep(pre code) {
  padding: 0;
  background: transparent;
  border-radius: 0;
  font-size: 0.9em;
}

.message-card__body :deep(a) {
  color: rgba(92, 197, 255, 0.9);
  text-decoration: none;
  border-bottom: 1px solid rgba(92, 197, 255, 0.3);
}

.message-card__body :deep(a:hover) {
  color: rgba(92, 197, 255, 1);
  border-bottom-color: rgba(92, 197, 255, 0.6);
}

.message-card__body :deep(strong) {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
}

.message-card__body :deep(em) {
  font-style: italic;
}

.message-card__body :deep(hr) {
  margin: 1.5em 0;
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.message-card__body :deep(table) {
  margin: 0.8em 0;
  border-collapse: collapse;
  width: 100%;
}

.message-card__body :deep(th),
.message-card__body :deep(td) {
  padding: 0.5em 0.8em;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.message-card__body :deep(th) {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
}

.message-card__body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 0.8em 0;
}

.message-card__toolbar {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
}

.toolbar-btn {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  border-radius: 999px;
  padding: 0.35rem 0.9rem;
  font-size: 0.85rem;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.toolbar-btn:hover {
  border-color: rgba(92, 197, 255, 0.8);
  background: rgba(92, 197, 255, 0.15);
}

.composer-surface {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  position: sticky;
  bottom: 0;
  padding: 1rem 0 0;
  background: linear-gradient(180deg, rgba(5, 5, 11, 0), rgba(5, 5, 11, 0.95));
}

.composer-box {
  border-radius: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  padding: 0.55rem 0.55rem 0.55rem 1.25rem;
  gap: 0.75rem;
}

.composer-input {
  flex: 1;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 1rem;
  outline: none;
  padding: 0.15rem 0;
}

.composer-textarea {
  resize: none;
  min-height: 2.5rem;
  max-height: 8.5rem;
  line-height: 1.5;
  font-family: inherit;
  padding: 0;
  overflow: auto;
  scrollbar-width: none;
}

.composer-textarea::-webkit-scrollbar {
  display: none;
}

.composer-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 0.4rem;
  flex-shrink: 0;
  width: 120px;
}

.composer-expand {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: inherit;
  padding: 0.4rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
  width: 100%;
}

.composer-send {
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  border: none;
  font-weight: 600;
  background: linear-gradient(120deg, #5cc5ff, #ab7bff);
  color: #05050b;
  cursor: pointer;
  box-shadow: 0 15px 35px rgba(92, 197, 255, 0.25);
  width: 100%;
}

.composer-send:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.feedback {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.feedback--error {
  color: #ffb3c1;
}

.feedback__retry {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  padding: 0.2rem 0.9rem;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.composer-fullscreen {
  position: fixed;
  inset: 0;
  padding: clamp(1rem, 4vw, 2.5rem);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99;
}

.composer-fullscreen__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(2, 4, 10, 0.7);
  backdrop-filter: blur(6px);
}

.composer-fullscreen__panel {
  position: relative;
  width: min(960px, 90vw);
  max-width: 90vw;
  border-radius: 1.75rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: linear-gradient(135deg, rgba(5, 6, 15, 0.96), rgba(9, 12, 28, 0.9));
  padding: clamp(1.25rem, 3vw, 1.75rem);
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.55);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.composer-fullscreen__body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.composer-fullscreen__textarea {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.04);
  padding: 1.1rem 1.25rem;
  color: inherit;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  min-height: 42vh;
  max-height: 60vh;
  resize: none;
  outline: none;
  scrollbar-width: thin;
}

.composer-fullscreen__textarea::-webkit-scrollbar {
  width: 6px;
}

.composer-fullscreen__textarea::-webkit-scrollbar-thumb {
  background: rgba(92, 197, 255, 0.4);
  border-radius: 999px;
}

.composer-fullscreen__footer {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: 0.5rem;
}

.composer-fullscreen__footer-btn {
  flex: 1;
}

.composer-fullscreen__footer .toolbar-btn,
.composer-fullscreen__footer .composer-send {
  width: 100%;
}

.tree-layout {
  position: relative;
  min-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
  border-radius: 1.75rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1.5rem;
  background: rgba(5, 5, 11, 0.85);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.45);
}

.tree-toolbar {
  position: absolute;
  top: 1.5rem;
  left: 1.5rem;
  right: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(10, 10, 18, 0.9);
  z-index: 2;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
}

.tree-toolbar__info h2 {
  margin: 0;
  font-size: 1.25rem;
}

.tree-toolbar__info p {
  margin: 0.1rem 0 0;
  color: rgba(255, 255, 255, 0.65);
}

.tree-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tree-toolbar__zoom {
  padding: 0.25rem 0.85rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.75);
}

.tree-toolbar__action {
  padding: 0.45rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: inherit;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.tree-toolbar__action--accent {
  border-color: rgba(92, 197, 255, 0.5);
  background: rgba(92, 197, 255, 0.15);
}

.tree-canvas {
  flex: 1;
  margin-top: 4.5rem;
  border-radius: 1.25rem;
  background: radial-gradient(circle at 20% 20%, rgba(92, 197, 255, 0.1), transparent 45%),
    radial-gradient(circle at 80% 0, rgba(255, 171, 123, 0.12), transparent 50%),
    #05050b;
  overflow: hidden;
  cursor: grab;
  border: 1px solid rgba(255, 255, 255, 0.03);
  position: relative;
  touch-action: none;
}

.tree-canvas::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 120px 120px;
  pointer-events: none;
  opacity: 0.7;
}

.tree-canvas.is-panning {
  cursor: grabbing;
}

.tree-space {
  position: absolute;
  top: 50%;
  left: 50%;
  display: inline-flex;
  flex-direction: column;
  gap: 1.25rem;
  will-change: transform;
  transform-origin: center;
}

@media (max-width: 1100px) {
  .page {
    padding: 1.5rem;
  }

  .root-sidebar {
    width: 100%;
  }
}

@media (max-width: 720px) {
  .conversation-surface {
    padding: 1rem;
  }

  .tree-layout {
    padding: 1rem;
  }

  .tree-toolbar {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }

  .tree-toolbar__actions {
    width: 100%;
    justify-content: center;
  }
}
</style>
