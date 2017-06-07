import numpy as np
import theano
import theano.tensor as T

# def softmax(x):
#     return np.exp(x) / np.sum(np.exp(x), axis=0)


class RNN(object):
    """ Recurrent Neural Network.
    Code is adapted from 
    http://www.wildml.com/2015/09/recurrent-neural-networks-tutorial-part-2-implementing-a-language-model-rnn-with-
                                    python-numpy-and-theano/
    """
    def __init__(self, xdim, ydim, hidden_dim=500, bptt_trunc=10):
        self.xdim = xdim
        self.ydim = ydim
        self.hidden_dim = hidden_dim
        self.bptt_trunc = bptt_trunc

        U = np.random.uniform(-1, 1, (hidden_dim, xdim)) / np.sqrt(xdim)
        V = np.random.uniform(-1, 1, (ydim, hidden_dim)) / np.sqrt(hidden_dim)
        W = np.random.uniform(-1, 1, (hidden_dim, hidden_dim)) / np.sqrt(hidden_dim)

        self.U = theano.shared(name='U', value=U.astype(theano.config.floatX))
        self.V = theano.shared(name='V', value=V.astype(theano.config.floatX))
        self.W = theano.shared(name='W', value=W.astype(theano.config.floatX))
        self.theano = {}

        U, V, W = self.U, self.V, self.W
        x = T.ivector('x')
        y = T.ivector('y')

        def forward_prop_step(x_t, s_t_prev, U, V, W):
            s_t = T.tanh(U[:, x_t] + W.dot(s_t_prev))
            o_t = T.nnet.softmax(V.dot(s_t))
            return [o_t[0], s_t]

        [o, s], updates = theano.scan(
            forward_prop_step,
            sequences=x,
            outputs_info=[None, dict(initial=T.zeros(self.hidden_dim))],
            non_sequences=[U, V, W],
            truncate_gradient=self.bptt_trunc,
            strict=True)

        prediction = T.argmax(o, axis=1)
        o_error = T.sum(T.nnet.categorical_crossentropy(o, y))

        # Gradients
        dU = T.grad(o_error, U)
        dV = T.grad(o_error, V)
        dW = T.grad(o_error, W)

        # Assign functions
        self.forward_propagation = theano.function([x], o)
        self.predict = theano.function([x], prediction)
        self.ce_error = theano.function([x, y], o_error)
        self.bptt = theano.function([x, y], [dU, dV, dW])

        # SGD
        learning_rate = T.scalar('learning_rate')
        self.sgd_step = theano.function([x, y, learning_rate], [],
                                        updates=[(self.U, self.U - learning_rate * dU),
                                                 (self.V, self.V - learning_rate * dV),
                                                 (self.W, self.W - learning_rate * dW)])

    def forward(self, x):
        T = len(x)

        s = np.zeros((T+1, self.hidden_dim))
        s[-1] = np.zeros(self.hidden_dim)

        o = np.zeros((T, self.xdim))

        for t in np.arange(T):
            s[t] = np.tanh(self.U[:, x[t]] + self.W.dot(s[t - 1]))

            smx = self.V.dot(s[t])
            # softmax function
            o[t] = np.exp(smx) / np.sum(np.exp(smx), axis=0)

        return [o, s]

    def predict(self, x):
        o, s = self.forward(x)
        return np.argmax(o, axis=1)

    def cost(self, xt, yt):
        return np.sum([self.ce_error(x, y) for (x, y) in zip(xt, yt)]) / \
                np.sum([len(y) for y in yt])

    def sgd_train(self, X, y, alpha=0.005, epochs=100):
        losses = []
        for e in range(epochs):

            loss = self.cost(X, y)
            losses.append(loss)
            print 'Loss: ', loss

            if (len(losses) > 2) and (losses[-1] > losses[-2]):
                print 'Going backwards!'
                break

            for (xs, ys) in zip(X, y):
                assert(len(xs) == self.xdim)
                assert(len(ys) == self.ydim)
                self.sgd_step(xs, ys, alpha)
