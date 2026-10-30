import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def my_conv2d(x, weight, bias=None, stride=1, padding=0):
    # x: (B, C_in, H, W), weight: (C_out, C_in, kH, kW)
    # Returns: (B, C_out, H_out, W_out)
    B, C_in, H, W = x.shape
    C_out, C_in_w, kH, kW = weight.shape
    assert C_in == C_in_w, "输入通道要和卷积核通道匹配"

    # 1. 零填充
    # F.pad顺序：(左, 右, 上, 下)
    x_pad = F.pad(x, (padding, padding, padding, padding), mode="constant", value=0)

    # 2. unfold抽取所有滑动窗口patch
    # unfold参数：维度，核大小，步长
    # out shape: [B, C_in * kH * kW, num_patches]
    patches = F.unfold(x_pad, kernel_size=(kH, kW), stride=stride)

    # 3. 把weight reshape，准备矩阵相乘
    # weight: [C_out, C_in, kH, kW] -> [C_out, C_in*kH*kW]
    # C_out：输出通道数，我们保留这个维度不动
    # -1 在 reshape /view 里的含义：自动计算这个维度该是多大，把剩下所有元素全部摊平到这一维
    w_flat = weight.reshape(C_out, -1)

    # 4. 矩阵乘法：w_flat @ patches
    # [C_out, C_in*kH*kW] @ [B, C_in*kH*kW, N] = [B, C_out, N]
    # torch.matmul 不是单纯二维矩阵乘法，它支持批量矩阵乘法（batch matmul）
    # 后面两个维度，当成真正的矩阵，前面所有维度，都叫batch 维度，跟着一起广播、一起配对运算
    out = torch.matmul(w_flat, patches)

    # 5. 加上bias（广播）
    if bias is not None:
        # out.shape = [B, C_out, N]
        # bias.shape原本 = [C_out]
        # bias.view(-1,1) → [C_out, 1]
        # 广播匹配顺序：从最右边（最后一维）往左对齐
        # out:         B , C_out , N
        # bias(广播后): 1 , C_out , 1
        # [1, C_out,1] 里的 1，会自动复制扩展成 B 和 N
        out = out + bias.view(-1, 1)

    # 6. 计算输出H_out, W_out，把N变回二维空间形状
    H_out = (H + 2*padding - kH) // stride + 1
    W_out = (W + 2*padding - kW) // stride + 1
    out = out.reshape(B, C_out, H_out, W_out)

    return out
    