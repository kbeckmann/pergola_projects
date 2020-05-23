from nmigen import *
from nmigen.build import *

from .. import Applet


class DDRx1Example(Elaboratable):
    def __init__(self, ddrx1_led):
        self.ddrx1_led = ddrx1_led
        self.timer = Signal(25)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)

        m.d.comb += self.ddrx1_led.o_clk.eq(self.timer[-1])
        m.d.comb += self.ddrx1_led.o0.eq(0b1)
        m.d.comb += self.ddrx1_led.o1.eq(0b0)

        return m

class DDRx2Example(Elaboratable):
    def __init__(self, ddrx2_led):
        self.ddrx2_led = ddrx2_led
        self.timer = Signal(25)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)

        m.d.comb += self.ddrx2_led.o_clk.eq(self.timer[-1])
        m.d.comb += self.ddrx2_led.o_eclk.eq(self.timer[-2])
        m.d.comb += self.ddrx2_led.o0.eq(0b1)
        m.d.comb += self.ddrx2_led.o1.eq(0b0)
        m.d.comb += self.ddrx2_led.o2.eq(0b1)
        m.d.comb += self.ddrx2_led.o3.eq(0b0)

        return m


class DDRExampleApplet(Applet, applet_name="ddr"):
    description = "DDR example (ddrx2 requires my branch of nmigen for the time being)"
    help = "DDR example"


    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--ddrx2", default=0, action="count",
            help="Use ddrx2 / qdr / ODDRX2F")

    def __init__(self, args):
        self.ddrx2 = args.ddrx2
        pass

    def elaborate(self, platform):

        m = Module()

        ddrx1_led = platform.request("led", 0, xdr=2)
        m.submodules.ddrx1_example = DDRx1Example(ddrx1_led)

        if self.ddrx2:
            ddrx2_led = platform.request("led", 7, xdr=4)
            m.submodules.ddrx2_example = DDRx2Example(ddrx2_led)

        return m
