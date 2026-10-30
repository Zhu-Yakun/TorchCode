import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def my_batch_norm(
    x,
    gamma,
    beta,
    running_mean,
    running_var,
    eps=1e-5,
    momentum=0.1,
    training=True,
):
    if training:
        # 训练：用batch自己的统计量
        batch_mean = x.mean(dim=0, keepdim=True)
        # unbiased=False：有偏估计，分母是 N（样本数量）
        batch_var = x.var(dim=0, keepdim=True, unbiased=False)

        # 更新running均值、方差（in-place）
        # running_mean形状是[D]，batch_mean是[1,D]，所以用.squeeze(0)把第一维去掉变成[D]才能赋值
        running_mean[:] = (1 - momentum) * running_mean + momentum * batch_mean.squeeze(0)
        running_var[:] = (1 - momentum) * running_var + momentum * batch_var.squeeze(0)

        # 归一化
        x_norm = (x - batch_mean) / torch.sqrt(batch_var + eps)
    else:
        # 推理：直接用全局running统计量
        x_norm = (x - running_mean) / torch.sqrt(running_var + eps)
    
    out = gamma * x_norm + beta
    return out
