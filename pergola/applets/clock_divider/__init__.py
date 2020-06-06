from nmigen import *
from nmigen.build import *

from .. import Applet
from ...util.clock import ClockDivider


class ClockDividerExample(Applet, applet_name="clock-divider"):
    help = "Clock divider example"
    description = "Clock divider example"


    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--divisor0", default=2**24, type=int,
            help="Divisor of first clock divider")

        parser.add_argument(
            "--divisor1", default=3, type=int,
            help="Divisor of second clock divider")

    def __init__(self, args):
        self.divisor0 = args.divisor0
        self.divisor1 = args.divisor1

    def elaborate(self, platform):

        divisor0 = self.divisor0
        divisor1 = self.divisor1

        m = Module()

        m.submodules.clock_divider0 = ClockDivider(
            divisor=divisor0,
            cd_out="slow",
        )

        m.submodules.clock_divider1 = ClockDivider(
            divisor=divisor1,
            cd_in="slow",
            cd_out="slower",
        )

        led0 = platform.request("led", 0)
        led1 = platform.request("led", 7)

        m.d.comb += led0.eq(ClockSignal("slow"))
        m.d.comb += led1.eq(ClockSignal("slower"))

        return m
