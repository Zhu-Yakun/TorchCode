import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def cross_entropy_loss(logits, targets):
    # logits shape: (B,C) B=batch样本数量，C=类别数量
    # targets shape: (B,) 每个元素是真实类别的索引，long类型
    B = logits.shape[0]

    # 1. logsumexp，数值稳定计算 log(sum(exp(logits)))，计算得到的维度是(B,1)
    log_sum_exp = torch.logsumexp(logits, dim=-1, keepdim=True)

    # 2. log softmax = logits - log(sum(exp(logits)))
    # 这里是(B,C)-(B,1)，(B,1)会自动复制扩充成(B,C)，得到的log_probs还是(B,C)
    log_probs = logits - log_sum_exp

    # 3. 取出每个样本对应真实标签位置的log概率
    # 这里是 PyTorch 的整数数组索引，两个数组长度必须相等。
    # 得到的形状是(B,)，一维 tensor，每个元素是对应样本真实标签的 log 概率
    selectd_log_probs = log_probs[torch.arange(B), targets]

    # 4. 计算负对数，然后batch求平均
    loss = -selectd_log_probs.mean()

    return loss