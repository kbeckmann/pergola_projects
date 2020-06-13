from nmigen import *
from nmigen.build import *

from .. import Applet
from ...gateware.gearbox import Gearbox
from ...util.clock import ClockDivider


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

        m.submodules += ClockDivider(
            divisor=platform.default_clk_frequency / 2, # 2Hz
            cd_out="slow",
        )

        m.submodules += ClockDivider(
            divisor=width_in,
            cd_in="slow",
            cd_out="gb_in",
        )

        m.submodules += ClockDivider(
            divisor=width_out,
            cd_in="slow",
            cd_out="gb_out",
        )

        m.submodules.gearbox = gearbox = Gearbox(
            width_in=width_in,
            width_out=width_out,
            domain_in="gb_in",
            domain_out="gb_out",
            depth=3,
        )

        m.d.comb += gearbox.data_in.eq(data_in)

        leds = [platform.request("led", i) for i in range(8)]

        leds_in = Cat(leds[:width_in])
        leds_out = Cat(leds[-width_out:])
        m.d.comb += leds_in.eq(gearbox.data_in)
        m.d.comb += leds_out.eq(gearbox.data_out)

        return m
