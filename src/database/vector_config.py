from typing import Dict, Any

# 1. 高效能 GPU 組: RTX 4050 6GB VRAM
# 核心策略: 壓榨 GPU 矩陣運算，使用較大的 Batch 和 適度併發
RTX_4050_6G: Dict[str, Any] = {
    "sub_batch_size": 17,
    "max_concurrency": 8,
    "force_gpu": True,
}

# 2. 高核心 CPU 組: 16 實體線程 + 64GB RAM
# 核心策略: 頻率較低但核心數多且記憶體充足，以高併發 (High Concurrency) 為主，並降低單次 Batch 大小以減少 CPU 壓力
CPU_16C_64G: Dict[str, Any] = {
    "sub_batch_size": 8,
    "max_concurrency": 12,
    "force_gpu": False,
}

# 3. 極低階組: 2c4t CPU + 4GB RAM
# 核心策略: 安全第一，避免記憶體溢出導致 Ollama 或系統崩潰。一次只處理一條文本
LOW_END_2C4T: Dict[str, Any] = {
    "sub_batch_size": 1,
    "max_concurrency": 1,
    "force_gpu": False,
}
