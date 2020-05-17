from nmigen import *
from nmigen_boards.pergola import *
from ecp5pll import ECP5PLL, ECP5PLLConfig

class Top(Elaboratable):
    def __init__(self):
        self.blink = Signal()

    def elaborate(self, platform):
        led   = platform.request("led", 0)
        btn   = platform.request("button", 0)
        timer1 = Signal(1)
        timer2 = Signal(1)
        timer3 = Signal(1)
        timer4 = Signal(1)

        m = Module()

        m.submodules.pll = ECP5PLL([
            ECP5PLLConfig("sync", 64),
            ECP5PLLConfig("fast", 32, phase=13),
            ECP5PLLConfig("fast2", 210, error=100),
            ECP5PLLConfig("fast3", 114, error=2),
        ])

        m.d.sync += timer1.eq(timer1 + 1)
        m.d.fast += timer2.eq(timer2 + 1)
        m.d.fast2 += timer3.eq(timer3 + 1)
        m.d.fast3 += timer4.eq(timer4 + 1)
        m.d.comb += led.o.eq(self.blink)

        with m.If(btn):
            m.d.comb += self.blink.eq(timer2[-1] | timer3[-1] | timer4[-1])
        with m.Else():
            m.d.comb += self.blink.eq(timer1[-1])

        return m


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    p_action = parser.add_subparsers(dest="action")
    p_action.add_parser("build")
    p_action.add_parser("program")
    p_action.add_parser("dot")
    p_action.add_parser("simulate")

    args = parser.parse_args()

    platform = PergolaPlatform()
    if args.action == "build":
        platform.build(Top(), do_program=False)
    elif args.action == "program":
        platform.build(Top(), do_program=True)
    elif args.action == "dot":
        platform.build(Top(), do_program=False, yosys_opts="-p show")
    elif args.action == "simulate":
        pass

