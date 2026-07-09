import numpy as np
import hashlib
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, dimension: int = 100):
        self.dimension = dimension
        self.cache = {}

    def get_vector(self, qid: str) -> np.ndarray:
        """
        Lấy vector nhúng cho một QID.
        Tạo một vector ngẫu nhiên xác định (deterministic) dựa trên mã MD5 hash của QID nếu không có file dữ liệu thật.
        Returns a deterministic unit vector based on the QID hash as a fallback.
        """
        if qid in self.cache:
            return self.cache[qid]
        
        # Generate deterministic mock vector
        hasher = hashlib.md5(qid.encode("utf-8"))
        seed = int(hasher.hexdigest(), 16) % (2**32 - 1)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        self.cache[qid] = vec
        return vec

    def calculate_heuristics(self, nodes: list, target_qid: str) -> dict:
        """
        Tính toán song song (vectorization) khoảng cách Cosine từ danh sách nút đến nút đích.
        h(n) = 1.0 - Cosine_Similarity(V_node, V_target)
        Parallel calculation using NumPy dot product and norm.
        """
        if not nodes:
            return {}

        v_target = self.get_vector(target_qid)  # shape (100,)
        
        # Tạo ma trận vector cho tất cả các nút: shape (num_nodes, 100)
        vectors = np.array([self.get_vector(node) for node in nodes])
        
        # Tính dot product song song: shape (num_nodes,)
        dot_products = np.dot(vectors, v_target)
        
        # Do các vector đã được chuẩn hóa độ dài về 1 ở get_vector, 
        # nên Cosine Similarity chính là dot product.
        # Để đảm bảo an toàn, ta vẫn chia cho tích các norm:
        norms = np.linalg.norm(vectors, axis=1)
        target_norm = np.linalg.norm(v_target)
        
        # Tránh lỗi chia cho 0
        norms[norms == 0.0] = 1.0
        if target_norm == 0.0:
            target_norm = 1.0
            
        cosine_similarities = dot_products / (norms * target_norm)
        
        # Heuristic h(n) = 1.0 - similarity
        heuristics = 1.0 - cosine_similarities
        
        return {node: float(h) for node, h in zip(nodes, heuristics)}

# Singleton instance
embedding_service = EmbeddingService(dimension=100)
