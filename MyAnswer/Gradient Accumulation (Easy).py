import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def accumulated_step(model, optimizer, loss_fn, micro_batches):
    # model: 我们的神经网络  optimizer: 优化器(SGD/Adam之类)
    # loss_fn: 损失函数  micro_batches: [(输入x, 标签y)]
    # zero_grad, loop (forward, scale loss, backward), step
    # 一开始清零梯度，只清一次
    optimizer.zero_grad()

    n = len(micro_batches)
    total_loss = 0.0

    for x,y in micro_batches:
        logits = model(x)
        loss = loss_fn(logits, y)

        # loss是tensor，挂在计算图上，.item() 把 tensor 里面的数值拿出来，
        # 变成普通 python 数字，脱离计算图，不会参与梯度
        total_loss += loss.item()

        scaled_loss = loss /n
        scaled_loss.backward()
    
    # 等所有 micro batch 全部跑完、梯度全部累加完成之后，只执行一次参数更新
    # 优化器拿着攒好的梯度，去更新权重
    optimizer.step()

    avg_loss = total_loss / n
    return avg_loss