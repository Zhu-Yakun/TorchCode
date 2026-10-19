import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def my_gelu(x):
    return x * 0.5 * (1 + torch.erf(x / math.sqrt(2)))