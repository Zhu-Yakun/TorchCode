import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def relu(x: torch.Tensor) -> torch.Tensor:
    mask = x > 0
    out = x * mask
    return out
