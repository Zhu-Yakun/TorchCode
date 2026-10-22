import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

class MyAdam:
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8):
        # store params, init m and v to zeros
        # 把传入的模型参数迭代器转成列表，方便后面按索引一一对应 m、v
        self.params = list(params)
        self.lr = lr
        self.beta1, self.beta2 = betas
        self.eps = eps
        self.t = 0  # 时间步 t，从0开始，step的时候+1

        # 给每个参数配套m，v，初始为0
        self.m = []
        self.v = []
        for p in self.params:
            # 对每一个参数，创建和它形状一样、初始值全 0 的 m、v 张量
            self.m.append(torch.zeros_like(p))
            self.v.append(torch.zeros_like(p))

    def step(self):
        # update params using Adam rule
        self.t += 1
        for i,p in enumerate(self.params):
            if p.grad is None:
                continue  # 没有梯度的参数跳过
            g = p.grad
            m = self.m[i]
            v = self.v[i]

            # 更新一阶矩、二阶矩
            m = self.beta1 * m + (1 - self.beta1) * g
            v = self.beta2 * v + (1 - self.beta2) * (g**2)
            self.m[i] = m
            self.v[i] = v

            # bias correction 偏差修正
            m_hat = m / (1 - self.beta1 ** self.t)
            v_hat = v / (1 - self.beta2 ** self.t)

            p.data -= self.lr * m_hat / (torch.sqrt(v_hat)+self.eps)

    def zero_grad(self):
        # zero all gradients
        for p in self.params:
            if p.grad is not None:
                # 原地清零（zero_下划线 in-place）
                p.grad.zero_()




