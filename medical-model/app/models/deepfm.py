import torch
import torch.nn as nn
from typing import List, Tuple

class FM(nn.Module):
    def __init__(self, field_dims: List[int], embed_dim: int):
        super().__init__()
        self.embeddings = nn.ModuleList([
            nn.Embedding(dim, embed_dim) for dim in field_dims
        ])
        self.linear = nn.Linear(sum(field_dims), 1)
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        linear_part = self.linear(x.float())
        
        embeds = [emb(x[:, i].long()) for i, emb in enumerate(self.embeddings)]
        embeds = torch.stack(embeds, dim=1)
        
        square_of_sum = embeds.sum(dim=1).pow(2)
        sum_of_square = embeds.pow(2).sum(dim=1)
        fm_part = 0.5 * (square_of_sum - sum_of_square).sum(dim=1, keepdim=True)
        
        return linear_part + fm_part, embeds

class Deep(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: List[int]):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_dim),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.mlp = nn.Sequential(*layers)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.mlp(x)

class DeepFM(nn.Module):
    def __init__(self, field_dims: List[int], embed_dim: int = 16, 
                 hidden_dims: List[int] = [128, 64, 32]):
        super().__init__()
        self.fm = FM(field_dims, embed_dim)
        deep_input_dim = len(field_dims) * embed_dim
        self.deep = Deep(deep_input_dim, hidden_dims)
        self.output_layer = nn.Sigmoid()
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        fm_out, embeds = self.fm(x)
        deep_input = embeds.view(embeds.size(0), -1)
        deep_out = self.deep(deep_input)
        output = fm_out + deep_out
        return self.output_layer(output), embeds

class DPSGD:
    def __init__(self, model: nn.Module, lr: float = 0.01, 
                 max_grad_norm: float = 1.0, noise_multiplier: float = 1.0):
        self.model = model
        self.lr = lr
        self.max_grad_norm = max_grad_norm
        self.noise_multiplier = noise_multiplier
        
    def step(self, loss: torch.Tensor):
        loss.backward()
        
        with torch.no_grad():
            for param in self.model.parameters():
                if param.grad is not None:
                    grad = param.grad.data
                    grad_norm = torch.norm(grad)
                    if grad_norm > self.max_grad_norm:
                        grad.mul_(self.max_grad_norm / grad_norm)
                    noise = torch.randn_like(grad) * self.noise_multiplier * self.max_grad_norm
                    param.grad.data = grad + noise
                    param.data -= self.lr * param.grad.data
                    param.grad.data.zero_()
