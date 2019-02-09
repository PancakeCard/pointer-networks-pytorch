from torch.nn import Parameter
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from scaled_dot_attention import ScaledDotAttention


class Encoder(torch.nn.Module):
    """
    Takes as input the raw features, projects them, passes through an LSTM to produce hidden states (encodings: e1 .... eT).
    """
    def __init__(self, n_in: int, n_embed: int, n_hidden: int, birnn: bool = False, n_layers: int = 1) -> None:
        super().__init__()
        if birnn or n_layers > 1:
            raise NotImplementedError()

        self.proj = torch.nn.Linear(n_in, n_embed)
        self.rnn = torch.nn.LSTM(input_size=n_embed, hidden_size=n_hidden, num_layers=n_layers, bidirectional=birnn, batch_first=True)
    
    def forward(self, inputs: torch.Tensor):
        # inputs: batch * seq_len * n_dim
        embedded = self.proj(inputs)
        # FIXME: should we add relu?
        
        hiddens, _ = self.rnn(embedded)  # outputs: batch * seq_len * (num_directions * n_hidden)
        return hiddens


class Decoder(torch.nn.Module):
    """
    Uses the encoder hidden states, produces target_length outputs.
    """
    def __init__(self, n_hidden: int = 64, d_k: int = 256) -> None:
        super().__init__()

        self.rnn = torch.nn.LSTMCell(input_size=n_hidden, hidden_size=n_hidden)
        
        # For attention, key - encoder hidden state, query - decoder hidden state, value=one-hot for each position
        self.sda = ScaledDotAttention(d_k=d_k, d_q=n_hidden, model_dim=64)
    
    @staticmethod
    def _get_identity_matrix(n_side: int):
        """ Returns a tensor containing an n_side*n_side identity matrix """
        values = torch.from_numpy(np.diag(np.ones(n_side)).astype(np.float32))
        return values
        
    def forward(self, max_length: int, encoder_hiddens):
        """
        target_length: the length of the sequence to produce: FIXME: need <EOS>
        """
        if encoder_hiddens.shape[0] > 1:
            raise NotImplementedError('batching not supported yet')

        input_len = encoder_hiddens.shape[1]
    
        # For getting the probabilities using attention, we supply one-hot vectors the size of the input seq as the values
        identity = self._get_identity_matrix(input_len).to(encoder_hiddens.device).view(1, input_len, input_len)
        
        output_hiddens, pointers = [], []
        
        hidden_prev = encoder_hiddens[0][-1].detach()
        for ix in range(max_length):
            # FIXME: Usually, the outputs of the network are passed as the next input. However, the outputs are of varying sizes here
            # So, that's not possible.. For now, I'll pass the previous hidden state.
            hidden, _ = self.rnn(hidden_prev.view(1, -1))  # FIXME: pass the hidden state as well, initialize the hidden state
            
            # Calculate attention weights
            att_weights = self.sda(K=encoder_hiddens, V=identity, Q=hidden.view(1, -1))
            att_weights = att_weights.view(1, -1)
            
            # Store
            output_hiddens.append(hidden)
            pointers.append(att_weights)
            hidden_prev = hidden
            
            # FIXME: break if <EOS>
        
        output_hiddens = torch.cat(output_hiddens, dim=0)
        pointers = torch.cat(pointers)
        return pointers, output_hiddens

class PointerNet(torch.nn.Module):
    def __init__(self, n_in=2) -> None:
        super().__init__()
        self.encoder = Encoder(n_in=n_in, n_embed=128, n_hidden=256)
        self.decoder = Decoder(n_hidden=256)

        self.n_in = n_in
    
    def forward(self, sequence, max_output_len):
        bsz = sequence.shape[0]
        if bsz > 1:
            raise NotImplementedError

        encoder_hiddens = self.encoder(sequence.view(1, -1, self.n_in))
        assert len(encoder_hiddens[0]) == len(sequence[0])

        pointers, _ = self.decoder(max_length=max_output_len, encoder_hiddens=encoder_hiddens)
        
        assert encoder_hiddens.shape[1] == pointers.shape[-1]  # No of classes in the pointers is the seq length of the input
        assert max_output_len == pointers.shape[0]  # Number of outputs (pointers) should be max_len
        
        return pointers.view(bsz, max_output_len, -1)