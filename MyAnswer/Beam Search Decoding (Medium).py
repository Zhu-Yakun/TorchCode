import torch
import torch.nn as nn
import torch.nn.functional as F
import math

# ✏️ YOUR IMPLEMENTATION HERE

def beam_search(log_prob_fn, start_token, max_len, beam_width, eos_token):
    # maintain beams, expand, prune, return best
    # beams: list of tuple (total_log_prob: float, seq: list[int])
    beams = [ (0.0, [start_token]) ]

    for _ in range(max_len):
        all_candidates = []

        # 遍历每一个当前beam进行扩展
        for score, seq in beams:
            # 如果这条序列已经遇到了eos，不再继续生成，直接保留进候选
            if seq[-1] == eos_token:
                all_candidates.append( (score, seq) )
                continue
            
            # 拿到当前序列下，下一个token所有词的log概率
            log_probs = log_prob_fn(seq) # shape (V,)
            # log_probs 是tensor，转化成cpu float方便处理
            log_probs = log_probs.detach().cpu()

            # 把这个beam扩展：每个可能token接在后面
            for token_id in range(log_probs.shape[0]):
                new_score = score + log_probs[token_id].item()
                new_seq = seq + [token_id]
                all_candidates.append( (new_score, new_seq) )
        
        # 全部候选按分数降序排序，保留前 beam_width 个
        all_candidates.sort(key=lambda x: x[0], reverse=True)
        beams = all_candidates[:beam_width]

        # 检查最优beam是不是已经结束，提前退出
        best_score, best_seq = beams[0]
        if best_seq[-1] == eos_token:
            return best_seq

    # 循环达到max_len上限，返回当前最好的
    return beams[0][1]


