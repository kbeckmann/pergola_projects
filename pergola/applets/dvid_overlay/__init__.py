from nmigen import *
from nmigen.lib.cdc import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig
from nmigen.back.pysim import Simulator, Active
from ...util.test import FHDLTestCase
# from ...util.cdc import SafeFFSynchronizer
from ...gateware.tmds import TMDSEncoder, TMDSDecoder
from ...gateware.dvid2vga import DVID2VGA
from ...gateware.vga2dvid import VGA2DVID

class DVIDOverlay(Elaboratable):
    def __init__(self, dvid_in, dvid_out, dvid_clk_out, debug):
        self.dvid_in = dvid_in
        self.dvid_out = dvid_out
        self.dvid_clk_out = dvid_clk_out
        self.debug = debug

    def elaborate(self, platform):
        dvid_in = self.dvid_in
        dvid_out = self.dvid_out
        dvid_clk_out = self.dvid_clk_out
        xdr = 1

        m = Module()
        
        # shift_clock_initial = 0b0000011111
        # C_shift_clock_initial = Const(0b0000011111)
        # shift_clock = Signal(10, reset=shift_clock_initial)
        # m.d.shift += shift_clock.eq(Cat(shift_clock[xdr:], shift_clock[:xdr]))

        # m.d.shift += [
        #     dvid_out.eq(dvid_in),
        #     dvid_clk_out.eq(shift_clock[xdr:])
        # ]

        decoded_r = Signal(8)
        decoded_g = Signal(8)
        decoded_b = Signal(8)
        decoded_de0 = Signal()
        decoded_hsync = Signal()
        decoded_vsync = Signal()
        decoded_de1 = Signal()
        decoded_ctl0 = Signal()
        decoded_ctl1 = Signal()
        decoded_de1 = Signal()
        decoded_ctl2 = Signal()
        decoded_ctl3 = Signal()

        m.submodules.dvid2vga = dvid2vga = DVID2VGA(
            in_d0=self.dvid_in[0],
            in_d1=self.dvid_in[1],
            in_d2=self.dvid_in[2],

            out_r=decoded_r,
            out_g=decoded_g,
            out_b=decoded_b,
            out_de0=decoded_de0,
            out_hsync=decoded_hsync,
            out_vsync=decoded_vsync,
            out_de1=decoded_de1,
            out_ctl0=decoded_ctl0,
            out_ctl1=decoded_ctl1,
            out_de2=decoded_de1,
            out_ctl2=decoded_ctl2,
            out_ctl3=decoded_ctl3,

            xdr=xdr
        )

        tmds_d0 = Signal(xdr)
        tmds_d1 = Signal(xdr)
        tmds_d2 = Signal(xdr)

        m.d.comb += dvid_out.eq(Cat(tmds_d0, tmds_d1, tmds_d2))

        m.submodules.vga2dvid = vga2dvid = VGA2DVID(
            in_r=decoded_r,
            in_g=decoded_g,
            in_b=decoded_b,
            in_blank=~decoded_de0,
            in_hsync=decoded_hsync,
            in_vsync=decoded_vsync,

            out_r=tmds_d2,
            out_g=tmds_d1,
            out_b=tmds_d0,
            out_clock=dvid_clk_out,

            xdr=xdr
        )

        # m.d.comb += self.debug.eq(Cat(decoded_de0, decoded_hsync, decoded_vsync))
        # m.d.comb += self.debug.eq(dvid2vga.d0_offset)


        return m



class DVIDOverlayTest(FHDLTestCase):

    def test_overlay_simulation(self):
        m = Module()

        data = Signal(8, reset=0x3)
        c = Signal(2)
        blank = Signal()
        encoded = Signal(10)
        m.submodules.tmds_encoder = TMDSEncoder(data, c, blank, encoded)

        encoded_shift = Signal(10)
        re_encoded = Signal(3)
        re_encoded_clk = Signal()

        ctr = Signal(16, reset=9)
        with m.If(ctr == 0):
            m.d.shift += encoded_shift.eq(encoded)
            m.d.shift += ctr.eq(9)
        with m.Else():
            m.d.shift += ctr.eq(ctr - 1)
            m.d.shift += encoded_shift.eq(Cat(encoded_shift[1:], 0))

        m.submodules.overlay = DVIDOverlay(Cat(encoded_shift[0], 0, 0), re_encoded, re_encoded_clk)

        sim = Simulator(m)
        sim.add_clock(1/25e6,  domain="sync")
        sim.add_clock(1/250e6, domain="shift")

        def process():
            for i in range(0x20 * 10):
                yield data.eq(i // 10)
                yield c.eq(11)
                yield blank.eq((i // 10) % 5 == 0)
                yield

        sim.add_sync_process(process)
        with sim.write_vcd("dvid-overlay.vcd"):
            sim.run()



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
        # D0  J2/J1 (b)  inverted
        # D1  L1/L2 (g)
        # D2  P2/N1 (r)  inverted

        # PMOD2 pinout:
        # CLK B1/B2
        # D0  C1/C2 (b)
        # D1  E2/D1 (g)  inverted
        # D2  G2/F1 (r)  inverted

        pixel_clk_freq = 25e6

        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("J1 L1 N1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100)),
            Resource("pmod1_lvds_clk", 0, Pins("G1", dir="i"),
                     Attrs(IO_TYPE="LVDS", DIFFRESISTOR=100),
                     Clock(pixel_clk_freq)),

            Resource("pmod2_lvds", 0, Pins("C1 D1 F1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod2_lvds_clk", 0, Pins("B1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
        ])

        dvid_in = platform.request("pmod1_lvds", 0)

        dvid_out = platform.request("pmod2_lvds", 0)
        dvid_clk_out = platform.request("pmod2_lvds_clk", 0)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("shift", (pixel_clk_freq / 1e6) * 10),
            ECP5PLLConfig("sync", pixel_clk_freq / 1e6),
        ], clock_signal_name="pmod1_lvds_clk")


        leds = Cat([platform.request("led", i) for i in range(8)])

        dvid_in_tmp = Signal(3)
        dvid_out_tmp = Signal(3)
        m.d.comb += [
            dvid_in_tmp.eq(Cat(~dvid_in[0], dvid_in[1], ~dvid_in[2])),
            dvid_out.eq(Cat(dvid_out_tmp[0], ~dvid_out_tmp[1], ~dvid_out_tmp[2])),
        ]
        m.submodules.overlay = DVIDOverlay(dvid_in_tmp, dvid_out_tmp, dvid_clk_out, leds)




        return m
