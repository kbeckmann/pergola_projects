from nmigen import *


class ChaChaFSM1(Elaboratable):
    """
    State-machine based implementation of ChaCha20.
    Each round takes a single cycle.
    A full block takes 23 clock cycles to complete.
    May use less than 1586 slices and run at ~60 MHz.
    > 1270 Mb/s throughput
    """

    def __init__(self):
        self.i_key = [Signal(Shape(32)) for _ in range(8)]
        self.i_nonce = [Signal(Shape(32)) for _ in range(3)]
        self.i_counter = Signal(Shape(32))
        self.i_en = Signal()
        self.o_ready = Signal()
        self.o_stream = [Signal(Shape(32)) for _ in range(16)]

        self.state = [Signal(shape=Shape(32), name=f"state_{i}") for i in range(16)]
        self.round = Signal(16)

    def elaborate(self, platform):
        m = Module()

        key = self.i_key
        counter = self.i_counter
        nonce = self.i_nonce
        state = self.state
        round = self.round

        o_stream = self.o_stream

        state_initial = [Signal(shape=Shape(32), name=f"state_initial{i}") for i in range(16)]

        def QR(m, a, b, c, d):
            a1 = Signal(32)
            a2 = Signal(32)
            b1 = Signal(32)
            b2 = Signal(32)
            b3 = Signal(32)
            b4 = Signal(32)
            c1 = Signal(32)
            c2 = Signal(32)
            d1 = Signal(32)
            d2 = Signal(32)
            d3 = Signal(32)
            d4 = Signal(32)
            m.d.comb += [
                a1.eq(a + b),
                d1.eq(a1 ^ d),
                d2.eq(d1.rotate_left(16)),
                c1.eq(c + d2),
                b1.eq(b ^ c1),
                b2.eq(b1.rotate_left(12)),
                a2.eq(a1 + b2),
                d3.eq(a2 ^ d2),
                d4.eq(d3.rotate_left(8)),
                c2.eq(c1 + d4),
                b3.eq(b2 ^ c2),
                b4.eq(b3.rotate_left(7))
            ]
            m.d.sync += [
                a.eq(a2),
                b.eq(b4),
                c.eq(c2),
                d.eq(d4),
            ]

        m.d.comb += [
            state_initial[0].eq(0x61707865), # expa
            state_initial[1].eq(0x3320646e), # nd 3
            state_initial[2].eq(0x79622d32), # 2-by
            state_initial[3].eq(0x6b206574), # te k

            [state_initial[i+4].eq(v) for i, v in enumerate(key)],
            state_initial[12].eq(counter),
            [state_initial[i+13].eq(v) for i, v in enumerate(nonce)],
        ]

        with m.FSM() as fsm_perm:
            with m.State("IDLE"):
                with m.If(self.i_en):

                    m.d.sync += [

                        [state[i].eq(state_initial[i]) for i in range(16)],

                        round.eq(1),
                        self.o_ready.eq(0),
                    ]
                    m.next = "ROUND_ODD"
            with m.State("ROUND_ODD"):
                QR(m, state[0], state[4], state[ 8], state[12])
                QR(m, state[1], state[5], state[ 9], state[13])
                QR(m, state[2], state[6], state[10], state[14])
                QR(m, state[3], state[7], state[11], state[15])
                m.d.sync += round.eq(round + 1),
                m.next = "ROUND_EVEN"
            with m.State("ROUND_EVEN"):
                QR(m, state[0], state[5], state[10], state[15])
                QR(m, state[1], state[6], state[11], state[12])
                QR(m, state[2], state[7], state[ 8], state[13])
                QR(m, state[3], state[4], state[ 9], state[14])
                with m.If(round == 20):
                    m.d.sync += self.o_ready.eq(1)
                    m.next = "FINAL"
                with m.Else():
                    m.d.sync += round.eq(round + 1),
                    m.next = "ROUND_ODD"
            with m.State("FINAL"):
                m.d.sync += [
                    [o_stream[i].eq(state[i] + state_initial[i]) for i in range(16)],
                ]
                m.next = "DONE"
            with m.State("DONE"):
                pass

        return m
