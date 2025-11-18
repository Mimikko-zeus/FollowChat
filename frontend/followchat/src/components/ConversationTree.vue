<script setup lang="ts">
import { computed } from 'vue'
import type { ConversationNode } from '../types/conversation'

defineOptions({ name: 'ConversationTree' })

const props = defineProps<{
  nodeId: string
  nodes: Record<string, ConversationNode>
  activeId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  delete: [id: string, event: Event]
}>()

const node = computed(() => props.nodes[props.nodeId])

const handleSelect = () => {
  emit('select', props.nodeId)
}

const handleDelete = (event: Event) => {
  event.stopPropagation() // Prevent triggering parent node selection
  emit('delete', props.nodeId, event)
}
</script>

<template>
  <div v-if="node" class="tree-node">
    <div class="tree-node__content">
      <button
        type="button"
        class="tree-node__label"
        :class="{ active: node.id === activeId, user: node.author === 'user' }"
        @click="handleSelect"
      >
        <span class="tree-node__role">
          {{ node.author === 'user' ? '🙋' : '🤖' }}
        </span>
        <span class="tree-node__text">{{ node.content }}</span>
      </button>
      <button
        type="button"
        class="tree-node__delete"
        @click="handleDelete"
        title="删除消息"
      >
        ×
      </button>
      <span v-if="node.children.length" class="tree-node__connector" aria-hidden="true" />
    </div>
    <div v-if="node.children.length" class="tree-node__children">
      <ConversationTree
        v-for="childId in node.children"
        :key="childId"
        :node-id="childId"
        :nodes="nodes"
        :active-id="activeId"
        @select="emit('select', $event)"
        @delete="(id, event) => emit('delete', id, event)"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-node {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
  position: relative;
}

.tree-node__content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tree-node__label {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem 0.9rem;
  border-radius: 0.8rem;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.05);
  color: #f8f9fb;
  text-align: left;
  min-width: 180px;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
  cursor: pointer;
}

.tree-node__label:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.tree-node__label.active {
  border-color: #5cc5ff;
  background: rgba(92, 197, 255, 0.15);
  box-shadow: 0 8px 24px rgba(92, 197, 255, 0.25);
}

.tree-node__label.user {
  border-color: rgba(255, 170, 51, 0.5);
}

.tree-node__role {
  font-size: 1rem;
}

.tree-node__text {
  font-size: 0.9rem;
  line-height: 1.3;
}

.tree-node__delete {
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
  margin-left: 0.5rem;
  position: relative;
  z-index: 10;
  pointer-events: auto;
}

.tree-node__delete:hover {
  background: rgba(255, 100, 100, 0.4);
  color: rgba(255, 200, 200, 1);
  transform: scale(1.1);
}

.tree-node__connector {
  width: 48px;
  height: 2px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.2), rgba(92, 197, 255, 0.6));
  border-radius: 999px;
}

.tree-node__children {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding-left: 0.5rem;
  position: relative;
}

.tree-node__children::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.75rem;
  bottom: 0.75rem;
  width: 1px;
  background: rgba(255, 255, 255, 0.15);
}

@media (max-width: 900px) {
  .tree-node {
    flex-direction: column;
    gap: 0.75rem;
  }

  .tree-node__content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .tree-node__connector {
    width: 2px;
    height: 36px;
  }
}
</style>


