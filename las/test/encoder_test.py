import torch
from las.models.encoder import Encoder

inputs = torch.rand(3, 80, 100)  # BxDxT
input_lengths = [100, 90, 80]
input_lengths = torch.IntTensor(input_lengths)

encoder = Encoder(2000, 80, 256)
encoder_output, encoder_log_prob, encoder_output_lengths = encoder(inputs, input_lengths)

print(encoder_output)
# tensor([[[-0.0201,  0.0175, -0.0062,  ...,  0.0259, -0.0036,  0.0333],
#          [-0.0349,  0.0187, -0.0126,  ...,  0.0215, -0.0163,  0.0202],
#          [-0.0311,  0.0179, -0.0133,  ...,  0.0302, -0.0200,  0.0116],
#          ...,
#          [-0.0359,  0.0129, -0.0246,  ...,  0.0310, -0.0304,  0.0346],
#          [-0.0495,  0.0307, -0.0283,  ...,  0.0110, -0.0036,  0.0267],
#          [-0.0756,  0.0414, -0.0266,  ...,  0.0102, -0.0091,  0.0137]],
#
#         [[-0.0019,  0.0216,  0.0080,  ...,  0.0305, -0.0067,  0.0058],
#          [-0.0116,  0.0057, -0.0103,  ...,  0.0176, -0.0268, -0.0047],
#          [-0.0195, -0.0164, -0.0087,  ...,  0.0296, -0.0491, -0.0045],
#          ...,
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000],
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000],
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000]],
#
#         [[-0.0284,  0.0130, -0.0055,  ...,  0.0014,  0.0144,  0.0097],
#          [-0.0194,  0.0131, -0.0101,  ...,  0.0279,  0.0023,  0.0172],
#          [-0.0388,  0.0096,  0.0179,  ...,  0.0476,  0.0027,  0.0045],
#          ...,
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000],
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000],
#          [ 0.0000,  0.0000,  0.0000,  ...,  0.0000,  0.0000,  0.0000]]]

print(encoder_output.size())  # torch.Size([3, 50, 512])

print(encoder_output_lengths)  # tensor([50, 45, 40], dtype=torch.int32)
