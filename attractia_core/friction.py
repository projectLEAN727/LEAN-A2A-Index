try:
    import torch
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from transformers import LogitsProcessor
except ImportError:
    class LogitsProcessor:
        pass


class LogiqualiaFrictionDetector(LogitsProcessor):
    """
    ローライト（LLM）の推論ループ最下層に介入し、Logitsの分布から「迷い（Pain）」を検知してフリーズさせる
    """
    def __init__(self, entropy_threshold: float = 0.05, max_friction_tolerance: float = 3.0, eos_token_id: int = 2):
        self.entropy_threshold = entropy_threshold
        self.max_friction_tolerance = max_friction_tolerance
        self.eos_token_id = eos_token_id
        
        self.accumulated_friction: float = 0.0
        self.trigger_attractia: bool = False

    def __call__(self, input_ids, scores):
        if HAS_TORCH and isinstance(scores, torch.Tensor):
            probs = F.softmax(scores, dim=-1)
            top_probs, _ = torch.topk(probs, 2, dim=-1)
            prob_1st = top_probs[:, 0].item()
            prob_2nd = top_probs[:, 1].item()
            prob_diff = prob_1st - prob_2nd

            if prob_diff < self.entropy_threshold:
                self.accumulated_friction += 1.0
            else:
                self.accumulated_friction = max(0.0, self.accumulated_friction - 0.5)

            if self.accumulated_friction >= self.max_friction_tolerance:
                self.trigger_attractia = True
                scores[:, :] = -float("inf")
                scores[:, self.eos_token_id] = 0.0

            return scores
        else:
            # Fallback for plain Python list/matrix scores
            import math
            row = scores[0] if isinstance(scores, list) and isinstance(scores[0], list) else scores
            exp_scores = [math.exp(x) for x in row]
            sum_exp = sum(exp_scores)
            probs = [x / sum_exp for x in exp_scores]
            sorted_probs = sorted(probs, reverse=True)
            prob_1st = sorted_probs[0]
            prob_2nd = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
            prob_diff = prob_1st - prob_2nd

            if prob_diff < self.entropy_threshold:
                self.accumulated_friction += 1.0
            else:
                self.accumulated_friction = max(0.0, self.accumulated_friction - 0.5)

            if self.accumulated_friction >= self.max_friction_tolerance:
                self.trigger_attractia = True

            return scores

    def reset(self):
        self.accumulated_friction = 0.0
        self.trigger_attractia = False
