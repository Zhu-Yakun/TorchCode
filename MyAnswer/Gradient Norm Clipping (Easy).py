import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def clip_grad_norm(parameters, max_norm):
    # parameters: 模型参数的迭代器，一般传model.parameters()
    # max_norm：我们设定的梯度最大允许范数阈值
    # compute total norm, clip if needed, return original norm
    grad_norms_sq = []
    for p in parameters:
        if p.grad is not None:  # 有的参数可能没有梯度，要跳过
            norm_sq = p.grad.norm() ** 2
            grad_norms_sq.append(norm_sq)
    
    # torch.stack：把列表里一个个标量 tensor 堆成一个 tensor
    # .sum()：全部平方加起来
    # torch.sqrt()：开根号，得到原始总范数
    total_norm = torch.sqrt(torch.stack(grad_norms_sq).sum())

    if total_norm > max_norm:
        scale = max_norm / total_norm
        for p in parameters:
            if p.grad is not None:
                p.grad *= scale
    
    return float(total_norm)

    