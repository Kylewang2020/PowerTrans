import torch
import torch.backends
import torch.backends.cudnn

print(torch.__version__)
print(torch.cuda.is_available())
print(torch.version.cuda)
print(torch.backends.cudnn.version())