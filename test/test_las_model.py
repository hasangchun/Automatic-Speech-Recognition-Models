import torch
from models.las.encoder import Encoder
from models.las.decoder import Decoder
from models.las.model import ListenAttendSpell

inputs = torch.rand(3, 80, 100)  # BxDxT
input_lengths = [100, 90, 80]
input_lengths = torch.IntTensor(input_lengths)

targets = torch.ones(3, 20).to(torch.long)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

encoder = Encoder(2000, 80, 256)
decoder = Decoder(device, 2000, 512, 512)

model = ListenAttendSpell(encoder, decoder)

encoder_output_prob, encoder_output_lengths, decoder_output_prob = model(inputs, input_lengths, targets, 0.9)

print(encoder_output_prob.size())  # torch.Size([3, 50, 2000])
print(encoder_output_lengths)  # tensor([50, 45, 40], dtype=torch.int32)
print(decoder_output_prob)
# tensor([[[-7.5937, -7.6149, -7.6390,  ..., -7.5849, -7.5910, -7.5638],
#          [-7.5822, -7.6199, -7.6344,  ..., -7.5717, -7.5843, -7.5553],
#          [-7.5918, -7.6211, -7.6392,  ..., -7.5932, -7.5889, -7.5490],
#          ...,
#          [-7.5795, -7.6202, -7.6256,  ..., -7.5867, -7.5861, -7.5538],
#          [-7.5901, -7.6142, -7.6391,  ..., -7.5860, -7.5799, -7.5621],
#          [-7.5950, -7.6168, -7.6361,  ..., -7.5902, -7.5839, -7.5740]],
#
#         [[-7.5975, -7.6306, -7.6370,  ..., -7.5837, -7.5922, -7.5524],
#          [-7.5903, -7.6212, -7.6271,  ..., -7.5939, -7.5880, -7.5623],
#          [-7.5959, -7.6074, -7.6389,  ..., -7.5786, -7.5956, -7.5586],
#          ...,
#          [-7.5839, -7.6255, -7.6431,  ..., -7.5968, -7.5819, -7.5603],
#          [-7.5923, -7.6220, -7.6417,  ..., -7.5805, -7.5946, -7.5690],
#          [-7.5896, -7.6279, -7.6256,  ..., -7.5887, -7.5962, -7.5617]],
#
#         [[-7.5863, -7.6297, -7.6262,  ..., -7.5865, -7.5856, -7.5618],
#          [-7.5946, -7.6182, -7.6295,  ..., -7.5597, -7.5881, -7.5606],
#          [-7.5958, -7.6150, -7.6280,  ..., -7.5738, -7.5936, -7.5667],
#          ...,
#          [-7.5965, -7.6313, -7.6431,  ..., -7.5817, -7.5930, -7.5572],
#          [-7.5886, -7.6163, -7.6335,  ..., -7.5883, -7.5705, -7.5632],
#          [-7.5990, -7.6173, -7.6267,  ..., -7.5816, -7.5799, -7.5629]]]

print(decoder_output_prob.size())  # torch.Size([3, 20, 2000])

