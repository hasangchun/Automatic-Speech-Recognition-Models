from torch import Tensor
import torch
import torch.nn as nn


class GreedySearch(nn.Module):
    def __init__(
            self,
            device: torch.device,
    ) -> None:
        super(GreedySearch, self).__init__()
        self.device = device

    def forward(
            self,
            model: nn.Module,
            feature: Tensor,
            feature_lengths: Tensor,
            result: Tensor,
    ) -> Tensor:
        encoder_output_prob, encoder_output_lens, decoder_output_prob = model(feature, feature_lengths, None, 0.0)

        decoder_output_prob = decoder_output_prob.to(self.device)
        decoder_output_prob = decoder_output_prob[:, :result.size(1), :]
        y_hat = decoder_output_prob.max(2)[1]

        return y_hat
