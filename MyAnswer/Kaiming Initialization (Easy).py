import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def kaiming_init(weight):
    # fill with normal(0, sqrt(2/fan_in))
    fan_in = weight.shape[1]
    std = math.sqrt(2.0 / fan_in)
    # normal_ 下划线代表原地操作，直接填充这个张量
    weight.normal_(mean=0.0, std=std)
    return weight