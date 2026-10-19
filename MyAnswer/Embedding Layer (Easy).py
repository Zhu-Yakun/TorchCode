import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

class MyEmbedding(nn.Module):
    def __init__(self, num_embeddings, embedding_dim):
        super().__init__()
        # 创建权重矩阵，形状 [词表大小, 向量维度]
        weight = torch.randn(num_embeddings, embedding_dim)
        # 包装成 nn.Parameter，标记为可训练参数
        self.weight = nn.Parameter(weight)

    def forward(self, indices):
        out = self.weight[indices]
        return out