// Default System Instruction (User-editable part only)
export const DEFAULT_SYSTEM_INSTRUCTION = `You are a helpful AI assistant.`;

// Fixed RAG Template Structure (auto-appended, not editable by user)
export const RAG_TEMPLATE_SUFFIX = `

---
上下文:
{context}
---

問題: {query}`;

// Embedding model dimensions mapping
export const EMBEDDING_DIMENSIONS = {
    'nomic-embed-text': 768,
    'bge-m3:latest': 1024
};

// LLM Model token limits mapping (context window size)
export const LLM_MODEL_LIMITS = {
    'gemma3:1b': 4096,
    'gemma3:4b': 4096,
    'gemini-flash-lite-latest': 200000,  // 200k tokens
    'gemini-flash-lite-latest': 200000,  // 200k tokens
    'gemini-flash-latest': 200000  // 200k tokens
};
