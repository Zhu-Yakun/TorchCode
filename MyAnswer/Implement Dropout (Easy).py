import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

class MyDropout(nn.Module):
    def __init__(self, p=0.5):
        super().__init__()  # 继承 nn.Module，必须写
        self.p = p

    def forward(self, x):
        # self.training: nn.Module内置的flag，True=训练模式，False=评估模式
        if self.training:
            # 生成和x同shape的0~1随机数
            mask = torch.rand_like(x)
            # 这里最好加上.float()，torch.bool是独立的数据类型，而且bool张量不能直接做除法
            mask = (mask >= self.p).float()
            x = x * mask / (1 - self.p)
        return x