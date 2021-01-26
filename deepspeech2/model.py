import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Tuple
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class MaskConv(nn.Module):
    """
        Masking Convolutional Neural Network

        Refer to https://github.com/sooftware/KoSpeech/blob/jasper/kospeech/models/modules.py
        Copyright (c) 2020 Soohwan Kim

    """

    def __init__(
            self,
            sequential: nn.Sequential
    ) -> None:
        super(MaskConv, self).__init__()
        self.sequential = sequential

    def forward(
            self,
            inputs: Tensor,
            seq_lens: Tensor
    ) -> Tuple[Tensor, Tensor]:
        output = None

        for module in self.sequential:
            output = module(inputs)

            mask = torch.BoolTensor(output.size()).fill_(0)
            if output.is_cuda:
                mask = mask.cuda()

            seq_lens = self.get_seq_lens(module, seq_lens)

            for idx, seq_len in enumerate(seq_lens):
                seq_len = seq_len.item()

                if (mask[idx].size(2) - seq_len) > 0:
                    mask[idx].narrow(2, seq_len, mask[idx].size(2) - seq_len).fill_(1)

            output = output.masked_fill(mask, 0)
            inputs = output

        return output, seq_lens

    def get_seq_lens(
            self,
            module: nn.Module,
            seq_lens: Tensor
    ) -> Tensor:
        if isinstance(module, nn.Conv2d):
            seq_lens = seq_lens + (2 * module.padding[1]) - module.dilation[1] * (module.kernel_size[1] - 1) - 1
            seq_lens = seq_lens.float() / float(module.stride[1])
            seq_lens = seq_lens.int() + 1

        if isinstance(module, nn.MaxPool2d):
            seq_lens >>= 1

        return seq_lens.int()


class DeepSpeech2(nn.Module):
    supported_rnns = {'rnn': nn.RNN,
                      'lstm': nn.LSTM,
                      'gru': nn.GRU
                      }

    def __init__(self,
                 num_vocabs: int,
                 input_size: int = 80,
                 hidden_size: int = 512,
                 num_layers: int = 5,
                 dropout: float = 0.3,
                 bidirectional: bool = True,
                 rnn_type: str = 'gru',
                 device: str = 'cpu'
                 ) -> None:
        super(DeepSpeech2, self).__init__()
        input_size = int(math.floor(input_size + 2 * 20 - 41) / 2 + 1)
        input_size = int(math.floor(input_size + 2 * 10 - 21) / 2 + 1)
        input_size <<= 5
        rnn_cell = self.supported_rnns[rnn_type]
        self.rnn = rnn_cell(input_size, hidden_size, num_layers, True, True, dropout, bidirectional)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.bidirectional = bidirectional
        self.device = device
        self.conv = MaskConv(nn.Sequential(
            nn.Conv2d(in_channels=1, out_channels=32, kernel_size=(41, 11), stride=(2, 2), padding=(20, 5)),
            nn.BatchNorm2d(num_features=32),
            nn.Hardtanh(min_val=0, max_val=20, inplace=True),
            nn.Conv2d(in_channels=32, out_channels=32, kernel_size=(21, 11), stride=(2, 1), padding=(10, 5)),
            nn.BatchNorm2d(num_features=32),
            nn.Hardtanh(min_val=0, max_val=20, inplace=True)
        ))
        self.rnn_output_size = hidden_size << 1 if bidirectional else hidden_size
        self.fc = nn.Linear(self.rnn_output_size, num_vocabs)

    def forward(self,
                inputs: Tensor,
                input_lengths: Tensor
                ) -> Tuple[Tensor, Tensor]:
        inputs = inputs.unsqueeze(1)
        conv_output, output_lengths = self.conv(inputs, input_lengths)  # conv_output shape : (B, C, D, T)

        conv_output = conv_output.permute(0, 3, 1, 2)
        batch, seq_len, num_channels, hidden_size = conv_output.size()
        conv_output = conv_output.view(batch, seq_len, -1).contiguous()  # (B, T, C * D)

        conv_output = pack_padded_sequence(conv_output, output_lengths, batch_first=True)
        rnn_output, _ = self.rnn(conv_output)
        rnn_output, _ = pad_packed_sequence(rnn_output, batch_first=True)

        rnn_output_prob = self.fc(rnn_output)
        rnn_output_prob = F.log_softmax(rnn_output_prob, dim=-1)  # (B, T, num_vocabs)

        return rnn_output_prob, output_lengths


"""
model = DeepSpeech2(input_size, output_size, hidden_size=512, num_layers=5, dropout=0.3, bidirectional=True,
                    rnn_type='gru')
input_data =
output = model(input_data)
output = output.view(seq_len, batch, -1).contiguous()
output_lengths = torch.full(size=(batch,), fill_value=seq_len)
target =
target_lengths =                  # shape : (batch,)   각 target의 길이를 표현
learning_rate = 1e-4
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
ctc_loss = nn.CTCloss()
loss = ctc_loss(output, target, output_lengths, target_lengths)

optimizer.zero_grad()
loss.backward()
optimizer.step()
"""
