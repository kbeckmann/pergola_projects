from nmigen import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

class DVIDSplitterApplet(Applet, applet_name="dvid-splitter"):
    help = "Forwards a DVID input to two outputs"
    description = """
    Forwards a DVID input to two outputs

    PMOD1 is output 1
    PMOD2 is input
    PMOD5 is output 2
    """

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("L1 J1 G1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod1_lvds_clk", 0, Pins("N1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),

            Resource("pmod2_lvds", 0, Pins("D1 C1 B1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100)),
            Resource("pmod2_lvds_clk", 0, Pins("F1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100),
                     Clock(75e6)),

            Resource("pmod3_lvds", 0, Pins("G16 J16 L16", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod3_lvds_clk", 0, Pins("F16", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
        ])

        dvid_in = platform.request("pmod2_lvds", 0)

        dvid_out = platform.request("pmod1_lvds", 0)
        dvid_out_clk = platform.request("pmod1_lvds_clk", 0)

        dvid_out2 = platform.request("pmod3_lvds", 0)
        dvid_out2_clk = platform.request("pmod3_lvds_clk", 0)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("pixel", 75),
        ], clock_signal_name="pmod2_lvds_clk")

        m.d.comb += dvid_out.eq(~dvid_in)
        m.d.comb += dvid_out_clk.eq(ClockSignal("pixel"))

        m.d.comb += dvid_out2.eq(Cat(~dvid_in[0], dvid_in[1:]))
        m.d.comb += dvid_out2_clk.eq(ClockSignal("pixel"))

        return m