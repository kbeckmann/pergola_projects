from nmigen import *
from nmigen.build import *
from pergola_platform import *

class Foo(Elaboratable):
    def __init__(self, blink):
        self.blink = blink

    def elaborate(self, platform):
        timer = Signal(4)

        m = Module()

        m.d.sync += timer.eq(timer + 1)
        m.d.comb += self.blink.eq(timer[-1])

        return m


class HDMI(Elaboratable):
    def __init__(self):
        self.blink = Signal()

    def elaborate(self, platform):
        led   = platform.request("led", 0)
        btn   = platform.request("button", 0)
        pmod_lvds0 = platform.request("pmod_lvds", 0)
        timer = Signal(26)
        timer2 = Signal(26)

        m = Module()
        m.submodules.car = platform.clock_domain_generator()

        m.d.fast += timer.eq(timer + 1)
        m.d.sync += timer2.eq(timer2 + 1)
        m.d.comb += led.o.eq(self.blink)
        m.d.comb += pmod_lvds0.o.eq(Repl(self.blink, 4))

        with m.If(btn):
            m.d.comb += self.blink.eq(timer2[8])
        with m.Else():
            m.d.comb += self.blink.eq(timer[8])

        return m


if __name__ == "__main__":
    import argparse


    parser = argparse.ArgumentParser()
    p_action = parser.add_subparsers(dest="action")
    p_action.add_parser("simulate")
    p_action.add_parser("program")

    args = parser.parse_args()
    if args.action == "simulate":
        from nmigen.back.pysim import Simulator, Active

        blink = Signal()
        hdmi = Foo(blink)

        sim = Simulator(hdmi)
        sim.add_clock(1e-6)

        def loopback_proc():
            yield Active()
            for _ in range(1000):
                yield

        sim.add_sync_process(loopback_proc)

        with sim.write_vcd("hdmi.vcd", "hdmi.gtkw"):
            sim.run()

    elif args.action == "program":
        PergolaPlatform.resources += \
            Resource("pmod_lvds", 0, Pins("N1 L1 J1 G1", dir="o"),
                    Attrs(IO_TYPE="LVDS")),

        platform = PergolaPlatform()
        platform.build(HDMI(), do_program=True)
