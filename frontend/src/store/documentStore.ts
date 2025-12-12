/**
 * 文档状态管理
 */
import { create } from 'zustand'

interface DocumentState {
  currentDocumentId: string | null
  currentTaskId: string | null
  setCurrentDocument: (documentId: string | null, taskId?: string | null) => void
  clearCurrentDocument: () => void
}

export type { DocumentState }

export const useDocumentStore = create<DocumentState>((set) => ({
  currentDocumentId: null,
  currentTaskId: null,
  setCurrentDocument: (documentId, taskId = null) =>
    set({ currentDocumentId: documentId, currentTaskId: taskId }),
  clearCurrentDocument: () => set({ currentDocumentId: null, currentTaskId: null })
}))

