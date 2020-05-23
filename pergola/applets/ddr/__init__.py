from nmigen import *
from nmigen.build import *

from .. import Applet


class DDRExample(Elaboratable):
    def __init__(self, ddr_led):
        self.ddr_led = ddr_led
        self.timer = Signal(24)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)

        m.d.comb += self.ddr_led.o_clk.eq(self.timer[-1])
        m.d.comb += self.ddr_led.o0.eq(0b1)
        m.d.comb += self.ddr_led.o1.eq(0b0)

        return m


class DDRExampleApplet(Applet, applet_name="ddr"):
    description = "DDR example"
    help = "DDR example"

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        ddr_led = platform.request("led", 0, xdr=2)

        m = Module()

        m.submodules.ddr_example = DDRExample(ddr_led)

        return m
