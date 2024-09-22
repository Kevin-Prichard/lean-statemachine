from lean import StateMachine, State


class CoinToss(StateMachine):
    def __init__(self):
        super().__init__()

    heads = State('heads', initial=True)
    tails = State('tails')

    heads_to_tails = heads.to(tails, cond="is_heads")
    tails_to_heads = tails.to(heads, cond="is_tails")

    def is_heads(self):
        return self.state == self.heads

    def is_tails(self):
        return self.state == self.tails

    def on_enter_heads(self):
        print('Heads!')

    def on_enter_tails(self):
        print('Tails!')
