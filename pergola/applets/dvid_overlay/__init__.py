from nmigen import *
from nmigen.lib.cdc import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig
# from ...util.cdc import SafeFFSynchronizer

class DVIDOverlayApplet(Applet, applet_name="dvid-overlay"):
    help = "Adds an overlay on top of a DVID input stream"
    description = """
    Adds an overlay on top of a DVID input stream

    PMOD1 is input
    PMOD2 is output
    """

    def __init__(self, args):
        self.blink = Signal()

    def elaborate(self, platform):
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

        pixel_clk_freq = 25e6

        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("N1 L1 J1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100)),
            Resource("pmod1_lvds_clk", 0, Pins("G1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100),
                     Clock(pixel_clk_freq)),

            Resource("pmod2_lvds", 0, Pins("F1 D1 C1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod2_lvds_clk", 0, Pins("B1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
        ])

        dvid_in = platform.request("pmod1_lvds", 0, xdr=4)

        dvid_out = platform.request("pmod2_lvds", 0, xdr=4)
        dvid_out_clk = platform.request("pmod2_lvds_clk", 0, xdr=4)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("shift_x2", (pixel_clk_freq / 1e6) * 10 / 2),
            ECP5PLLConfig("shift", (pixel_clk_freq / 1e6) * 10 / 2 / 2),
            ECP5PLLConfig("pixel", pixel_clk_freq / 1e6),
        ], clock_signal_name="pmod1_lvds_clk")


        m.d.comb += [
            dvid_in.i_clk.eq(ClockSignal("shift")),
            dvid_in.i_eclk.eq(ClockSignal("shift_x2")),

            dvid_out.o_clk.eq(ClockSignal("shift")),
            dvid_out.o_eclk.eq(ClockSignal("shift_x2")),

            dvid_out_clk.o_clk.eq(ClockSignal("shift")),
            dvid_out_clk.o_eclk.eq(ClockSignal("shift_x2")),
        ]

        sampled_bgr = Signal(3 * 20)
        m.d.shift += [
            sampled_bgr.eq(Cat(dvid_in.i0, dvid_in.i1, dvid_in.i2, dvid_in.i3, sampled_bgr[:-4*3]))
        ]

        shift_clock_initial = 0b00000111110000011111
        C_shift_clock_initial = Const(shift_clock_initial)
        shift_clock = Signal(20, reset=shift_clock_initial)

        m.d.shift += shift_clock.eq(Cat(shift_clock[4:], shift_clock[:4]))

        # ctr = Signal(30)
        # with m.If(ctr == 0):
        #     m.d.shift += shift_clock.eq(Cat(shift_clock[3:], shift_clock[:3]))
        # m.d.shift += ctr.eq(ctr - 1)


        m.d.comb += dvid_out.o0.eq(Cat(sampled_bgr[0], ~sampled_bgr[1],  ~sampled_bgr[2]))
        m.d.comb += dvid_out.o1.eq(Cat(sampled_bgr[3], ~sampled_bgr[4],  ~sampled_bgr[5]))
        m.d.comb += dvid_out.o2.eq(Cat(sampled_bgr[6], ~sampled_bgr[7],  ~sampled_bgr[8]))
        m.d.comb += dvid_out.o3.eq(Cat(sampled_bgr[9], ~sampled_bgr[10], ~sampled_bgr[11]))


        leds = Cat([platform.request("led", i) for i in range(8)])
        m.d.pixel += leds.eq(shift_clock[:8])


        m.d.comb += dvid_out_clk.o0.eq(shift_clock[0])
        m.d.comb += dvid_out_clk.o1.eq(shift_clock[1])
        m.d.comb += dvid_out_clk.o2.eq(shift_clock[2])
        m.d.comb += dvid_out_clk.o3.eq(shift_clock[3])

        # m.d.comb += dvid_out_clk.o0.eq(~ClockSignal("pixel"))
        # m.d.comb += dvid_out_clk.o1.eq(~ClockSignal("pixel"))
        # m.d.comb += dvid_out_clk.o2.eq(~ClockSignal("pixel"))
        # m.d.comb += dvid_out_clk.o3.eq(~ClockSignal("pixel"))


        # m.d.comb += dvid_out.eq(Cat(dvid_in[0], ~dvid_in[1], ~dvid_in[2]))
        # m.d.comb += dvid_out_clk.eq(~ClockSignal("pixel"))

        return m
