from nmigen import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

class DVIDSplitterApplet(Applet, applet_name="dvid-splitter"):
    help = "Forwards a DVID input to two outputs"
    description = """
    Forwards a DVID input to two outputs

    PMOD1 is input
    PMOD2 is output 1
    PMOD5 is output 2
    """

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("N1 L1 J1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100)),
            Resource("pmod1_lvds_clk", 0, Pins("G1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100),
                     Clock(75e6)),

            Resource("pmod2_lvds", 0, Pins("F1 D1 C1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod2_lvds_clk", 0, Pins("B1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),

            Resource("pmod5_lvds", 0, Pins("F16 G16 J16", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod5_lvds_clk", 0, Pins("L16", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
        ])

        dvid_in = platform.request("pmod1_lvds", 0)

        dvid_out = platform.request("pmod2_lvds", 0)
        dvid_out_clk = platform.request("pmod2_lvds_clk", 0)

        dvid_out2 = platform.request("pmod5_lvds", 0)
        dvid_out2_clk = platform.request("pmod5_lvds_clk", 0)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("pixel", 75),
        ], clock_signal_name="pmod1_lvds_clk")

        # PMOD1 pinout:
        # CLK H2/G1      inverted
        # D2  P2/N1 (r)  inverted
        # D1  L1/L2 (g)
        # D0  J2/J1 (b)  inverted

        # PMOD2 pinout:
        # CLK B1/B2
        # D2  G2/F1 (r)  inverted
        # D1  E2/D1 (g)  inverted
        # D0  C1/C2 (b)

        # PMOD5 pinout:
        # CLK L16/L15
        # D2  J16/J15 (r)
        # D1  G16/H15 (g)
        # D0  F16/G15 (b)

        m.d.comb += dvid_out.eq(Cat(dvid_in[0], ~dvid_in[1], ~dvid_in[2]))
        m.d.comb += dvid_out_clk.eq(~ClockSignal("pixel"))

        m.d.comb += dvid_out2.eq(Cat(~dvid_in[0], dvid_in[1], ~dvid_in[2]))
        m.d.comb += dvid_out2_clk.eq(~ClockSignal("pixel"))

        return m
