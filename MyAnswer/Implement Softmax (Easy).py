import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def my_softmax(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
    # 数值稳定：在指定维度上减去最大值，keepdim=True方便广播
    # 这里不能用.item()，带dim的max函数返回一个 tuple：(values, indices)
    x_max = x.max(dim=dim, keepdim=True)[0]
    x_shifted = x - x_max

    exp_x = torch.exp(x_shifted)
    sum_exp = exp_x.sum(dim=dim, keepdim=True)

    softmax_out = exp_x / sum_exp

    return softmax_out
