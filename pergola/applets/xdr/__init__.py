from nmigen import *
from nmigen.build import *

from .. import Applet


class DDRExampleApplet(Applet, applet_name="xdr"):
    description = "XDR example (ODDRX1F, ODDRX2F, ODDR71B)"
    help = "XDR example"


    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--xdr", default=2, type=int, choices=[2, 4, 7],
            help="ddr=2, ddrx2=4, ddrx7=7")

    def __init__(self, args):
        self.xdr = args.xdr

    def elaborate(self, platform):

        xdr = self.xdr
        timer = Signal(25)

        m = Module()

        led = platform.request("led", 0, xdr=xdr)

        m.d.sync += timer.eq(timer + 1)

        m.d.comb += led.o_clk.eq(timer[-1])
        m.d.comb += led.o0.eq(0b1)
        m.d.comb += led.o1.eq(0b0)
        if xdr > 2:
            m.d.comb += led.o_fclk.eq(timer[-2])
            m.d.comb += led.o2.eq(0b1)
            m.d.comb += led.o3.eq(0b0)
        if xdr == 7:
            m.d.comb += led.o4.eq(0b1)
            m.d.comb += led.o5.eq(0b0)
            m.d.comb += led.o6.eq(0b1)

        return m
