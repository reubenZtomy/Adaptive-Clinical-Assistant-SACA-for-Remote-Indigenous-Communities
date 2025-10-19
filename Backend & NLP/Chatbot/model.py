try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except (ImportError, OSError):
    torch = None
    nn = None
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    class NeuralNet(nn.Module):
        def __init__(self, input_size, hidden_size, output_size):
            super(NeuralNet, self).__init__()
            self.net = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(p=0.1),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, output_size),
            )

        def forward(self, x):
            return self.net(x)

        def to(self, device):
            return super(NeuralNet, self).to(device)

        def load_state_dict(self, state_dict):
            super(NeuralNet, self).load_state_dict(state_dict)

        def eval(self):
            super(NeuralNet, self).eval()
else:
    class NeuralNet:
        def __init__(self, input_size, hidden_size, output_size):
            # Dummy implementation when torch is not available
            self.input_size = input_size
            self.hidden_size = hidden_size
            self.output_size = output_size

        def to(self, device):
            return self

        def load_state_dict(self, state_dict):
            pass

        def eval(self):
            pass

        def forward(self, x):
            # Return dummy output when torch is not available
            return None
