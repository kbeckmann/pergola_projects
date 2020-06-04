from nmigen import *
from nmigen.build import *

from .. import Applet
from ...gateware.gearbox import Gearbox


class GearboxExampleApplet(Applet, applet_name="gearbox"):
    help = "Gearbox example"
    description = "Gearbox example"


    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--data-in", default=0b101, type=int,
            help="input data")

        parser.add_argument(
            "--width-in", default=3, type=int,
            help="input width")

        parser.add_argument(
            "--width-out", default=2, type=int,
            help="output width")

    def __init__(self, args):
        self.data_in = args.data_in
        self.width_in = args.width_in
        self.width_out = args.width_out

        assert(self.width_in + self.width_out <= 8)

    def elaborate(self, platform):

        data_in = self.data_in
        width_in = self.width_in
        width_out = self.width_out

        m = Module()

        ### TODO: Fix this messy slow clock generator..
        timer = Signal(21)
        m.d.sync += timer.eq(timer + 1)
        m.domains += ClockDomain("slow")
        m.d.comb += ClockSignal("slow").eq(timer[-1])

        m.domains += ClockDomain("in")
        cnt_in = Signal(range(width_out))
        clk_in = Signal()
        with m.If(cnt_in == (width_out - 1)):
            m.d.slow += cnt_in.eq(0)
        with m.Else():
            m.d.slow += cnt_in.eq(cnt_in + 1)
        m.d.comb += clk_in.eq(cnt_in == 0)
        m.d.comb += ClockSignal("in").eq(clk_in)

        m.domains += ClockDomain("out")
        cnt_out = Signal(range(width_in))
        clk_out = Signal()
        with m.If(cnt_out == (width_in - 1)):
            m.d.slow += cnt_out.eq(0)
        with m.Else():
            m.d.slow += cnt_out.eq(cnt_out + 1)
        m.d.comb += clk_out.eq(cnt_out == 0)
        m.d.comb += ClockSignal("out").eq(clk_out)
        ####

        m.submodules.gearbox = gearbox = Gearbox(
            width_in=width_in,
            width_out=width_out,
            domain_in="in",
            domain_out="out",
            depth=3,
        )

        m.d.comb += gearbox.data_in.eq(data_in)

        leds = [platform.request("led", i) for i in range(8)]

        leds_in = Cat(leds[:width_in])
        leds_out = Cat(leds[-width_out:])
        m.d.comb += leds_in.eq(gearbox.data_in)
        m.d.comb += leds_out.eq(gearbox.data_out)

        return m
