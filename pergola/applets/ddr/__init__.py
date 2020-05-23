from nmigen import *
from nmigen.build import *

from .. import Applet


class DDRExample(Elaboratable):
    def __init__(self, ddr1x_led, ddr2x_led):
        self.ddr1x_led = ddr1x_led
        self.ddr2x_led = ddr2x_led
        self.timer = Signal(25)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)

        m.d.comb += self.ddr1x_led.o_clk.eq(self.timer[-1])
        m.d.comb += self.ddr1x_led.o0.eq(0b1)
        m.d.comb += self.ddr1x_led.o1.eq(0b0)

        m.d.comb += self.ddr2x_led.o_clk.eq(self.timer[-1])
        m.d.comb += self.ddr2x_led.o_eclk.eq(self.timer[-2])
        m.d.comb += self.ddr2x_led.o0.eq(0b1)
        m.d.comb += self.ddr2x_led.o1.eq(0b0)
        m.d.comb += self.ddr2x_led.o2.eq(0b1)
        m.d.comb += self.ddr2x_led.o3.eq(0b0)

        return m


class DDRExampleApplet(Applet, applet_name="ddr"):
    description = "DDR example (xdr=4 requires a patched nmigen)"
    help = "DDR example"

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        ddr1x_led = platform.request("led", 0, xdr=2)

        ddr2x_led = platform.request("led", 7, xdr=4)

        m = Module()

        m.submodules.ddr_example = DDRExample(ddr1x_led, ddr2x_led)

        return m
