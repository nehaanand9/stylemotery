import numpy
import six

import chainer
from deep_ast.s_lstm import slstm_func
from chainer import initializers
from chainer import link
from chainer.links.connection import linear
from chainer import variable
import numpy as np

class LSTMBase(link.Chain):
    def __init__(self, in_size, out_size,
                 init=None,upward_init=None,lateral_init=None, inner_init=None, bias_init=0, forget_bias_init=0):
        super(LSTMBase, self).__init__(
            W_i=linear.Linear(in_size, out_size,initialW=upward_init, initial_bias=bias_init),
            U_i=linear.Linear(out_size, out_size,initialW=lateral_init, nobias=True),

            W_f=linear.Linear(in_size, out_size,initialW=upward_init, initial_bias=forget_bias_init),
            U_f=linear.Linear(out_size, out_size,initialW=lateral_init, nobias=True),

            W_c=linear.Linear(in_size, out_size,initialW=upward_init, initial_bias=bias_init),
            U_c=linear.Linear(out_size, out_size,initialW=lateral_init, nobias=True),

            W_o=linear.Linear(in_size, out_size,initialW=upward_init, initial_bias=bias_init),
            U_o=linear.Linear(out_size, out_size,initialW=lateral_init, nobias=True),
        )
        self.state_size = out_size


class LSTM(LSTMBase):
    def __init__(self, in_size, out_size, **kwargs):
        super(LSTM, self).__init__(in_size, out_size, **kwargs)

    def __call__(self, c, h, x):
        """Returns new cell state and updated output of LSTM.

        Args:
            c (~chainer.Variable): Cell states of LSTM units.
            h (~chainer.Variable): Output at the previous time step.
            x (~chainer.Variable): A new batch from the input sequence.

        Returns:
            tuple of ~chainer.Variable: Returns ``(c_new, h_new)``, where
                ``c_new`` represents new cell state, and ``h_new`` is updated
                output of LSTM units.

        """
        lstm_in = self.upward(x)
        if h is not None:
            lstm_in += self.lateral(h)
        if c is None:
            xp = self.xp
            c = variable.Variable(
                xp.zeros((len(x.data), self.state_size), dtype=x.data.dtype),
                volatile='auto')
        return slstm_func.LSTM()(c, lstm_in)

    def upward(self, x):
        a = self.W_a(x)
        i = self.W_i(x)
        f = self.W_f(x)
        o = self.W_o(x)
        return np.concatenate([a, i, f, o])


    def lateral(self, x):
        a = self.W_a(x)
        i = self.W_i(x)
        f = self.W_f(x)
        o = self.W_o(x)
        return np.concatenate([a, i, f, o])


