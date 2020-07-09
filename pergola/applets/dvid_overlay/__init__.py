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
from ...gateware.vga import *
from ...gateware.vga_testimage import *

class DVIDOverlay(Elaboratable):
    def __init__(self, dvid_in_d0, dvid_in_d1, dvid_in_d2, dvid_out_d0, dvid_out_d1, dvid_out_d2, dvid_clk_out, xdr, debug):
        self.dvid_in_d0 = dvid_in_d0
        self.dvid_in_d1 = dvid_in_d1
        self.dvid_in_d2 = dvid_in_d2
        self.dvid_out_d0 = dvid_out_d0
        self.dvid_out_d1 = dvid_out_d1
        self.dvid_out_d2 = dvid_out_d2
        self.dvid_clk_out = dvid_clk_out
        self.xdr = xdr
        self.debug = debug

    def elaborate(self, platform):
        dvid_in_d0 = self.dvid_in_d0
        dvid_in_d1 = self.dvid_in_d1
        dvid_in_d2 = self.dvid_in_d2
        dvid_out_d0 = self.dvid_out_d0
        dvid_out_d1 = self.dvid_out_d1
        dvid_out_d2 = self.dvid_out_d2
        dvid_clk_out = self.dvid_clk_out
        xdr = self.xdr

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
        decoded_de2 = Signal()
        decoded_ctl2 = Signal()
        decoded_ctl3 = Signal()

        m.submodules.dvid2vga = dvid2vga = DVID2VGA(
            in_d0=self.dvid_in_d0,
            in_d1=self.dvid_in_d1,
            in_d2=self.dvid_in_d2,

            out_r=decoded_r,
            out_g=decoded_g,
            out_b=decoded_b,
            out_de0=decoded_de0,
            out_hsync=decoded_hsync,
            out_vsync=decoded_vsync,
            out_de1=decoded_de1,
            out_ctl0=decoded_ctl0,
            out_ctl1=decoded_ctl1,
            out_de2=decoded_de2,
            out_ctl2=decoded_ctl2,
            out_ctl3=decoded_ctl3,

            xdr=xdr
        )

        tmds_d0 = Signal(xdr)
        tmds_d1 = Signal(xdr)
        tmds_d2 = Signal(xdr)

        m.d.comb += dvid_out_d0.eq(tmds_d0)
        m.d.comb += dvid_out_d1.eq(tmds_d1)
        m.d.comb += dvid_out_d2.eq(tmds_d2)

        vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])


        vga_configs = {
            "640x480p60": VGAParameters(
                    h_front=0,
                    h_sync=96,
                    h_back=48+16,
                    h_active=640,
                    v_front=10,
                    v_sync=2,
                    v_back=33,
                    v_active=480,
                ),
        }

        m.submodules.vga = vga = DynamicVGAOutputSubtarget(
            output=vga_output,
        )

        # m.d.sync += vga.h_front.eq(0)
        # m.d.sync += vga.h_sync.eq(96)
        # m.d.sync += vga.h_back.eq(48+16)
        m.d.sync += vga.h_sync.eq(96 + 48 + 16)
        m.d.sync += vga.h_active.eq(640)
        # m.d.sync += vga.v_front.eq(10)
        # m.d.sync += vga.v_sync.eq(2)
        # m.d.sync += vga.v_back.eq(33)
        m.d.sync += vga.v_sync.eq(10+2+33)
        m.d.sync += vga.v_active.eq(480)

        # Count and detect h_sync and v_sync lengths
        ctr = Signal(16, reset=0)
        with m.If(~decoded_de0):
            m.d.sync += ctr.eq(ctr + 1)
        with m.Else():
            m.d.sync += ctr.eq(0)
            with m.If(ctr > 10000):
                # First data enabled after vsync
                m.d.sync += m.submodules.vga.reset.eq(1)

        # Generate vga test image
        secondary_r = Signal(8)
        secondary_g = Signal(8)
        secondary_b = Signal(8)

        m.submodules.imagegen = TestImageGenerator(
        # m.submodules.imagegen = StaticTestImageGenerator(
            vsync=vga_output.vs,
            h_ctr=m.submodules.vga.h_ctr,
            v_ctr=m.submodules.vga.v_ctr,
            r=secondary_r,
            g=secondary_g,
            b=secondary_b,
            speed=0
        )

        overlay_r = Signal(8)
        overlay_g = Signal(8)
        overlay_b = Signal(8)
        # m.d.comb += [
        #     overlay_r.eq(decoded_r),
        #     overlay_g.eq(decoded_g),
        #     overlay_b.eq(decoded_b),
        # ]

        m.d.comb += [
            overlay_r.eq((decoded_r >> 1) + (secondary_r >> 1)),
            overlay_g.eq((decoded_g >> 1) + (secondary_g >> 1)),
            overlay_b.eq((decoded_b >> 1) + (secondary_b >> 1)),
        ]

        # m.d.comb += [
        #     overlay_r.eq(secondary_r),
        #     overlay_g.eq(secondary_g),
        #     overlay_b.eq(secondary_b),
        # ]

        # m.d.comb += [
        #     overlay_r.eq((decoded_r >> 1) + Mux(decoded_de0, 127, 0)),
        #     overlay_g.eq((decoded_g >> 1) + Mux(decoded_hsync, 127, 0)),
        #     overlay_b.eq((decoded_b >> 1) + Mux(decoded_vsync, 127, 0)),
        # ]

        # m.d.comb += [
        #     overlay_r.eq(Mux(decoded_de0, 255, 0)),
        #     overlay_g.eq(Mux(decoded_hsync, 255, 0)),
        #     overlay_b.eq(Mux(decoded_vsync, 255, 0)),
        # ]


        m.submodules.vga2dvid = vga2dvid = VGA2DVID(
            # in_r=Const(127, 8),
            # in_g=Const(63, 8),
            # in_b=Const(31, 8),
            in_r=overlay_r,
            in_g=overlay_g,
            in_b=overlay_b,
            # in_blank=~decoded_de0,
            # in_hsync=decoded_hsync,
            # in_vsync=decoded_vsync,
            # in_blank = ~(decoded_hsync | decoded_vsync),
            in_blank = vga_output.blank,
            # in_hsync = vga_output.hs,
            # in_vsync = vga_output.vs,
            in_hsync = 0,
            in_vsync = 0,
            in_c1=Cat(decoded_ctl0, decoded_ctl1),
            in_c2=Cat(decoded_ctl2, decoded_ctl3),

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
        xdr = 1

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

        dvid_in = platform.request("pmod1_lvds", 0, xdr=xdr)

        dvid_out = platform.request("pmod2_lvds", 0, xdr=xdr)
        dvid_out_clk = platform.request("pmod2_lvds_clk", 0, xdr=xdr)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("shift", (pixel_clk_freq / 1e6) * 10.),
            ECP5PLLConfig("sync", pixel_clk_freq / 1e6),
        ], clock_signal_name="pmod1_lvds_clk")


        leds = Cat([platform.request("led", i) for i in range(8)])

        dvid_in_d0 = Signal(xdr)
        dvid_in_d1 = Signal(xdr)
        dvid_in_d2 = Signal(xdr)
        dvid_out_d0 = Signal(xdr)
        dvid_out_d1 = Signal(xdr)
        dvid_out_d2 = Signal(xdr)
        dvid_out_clk_d = Signal(xdr)
        m.d.comb += [
            dvid_in.i_clk.eq(ClockSignal("shift")),
            dvid_in_d0.eq(~dvid_in.i[0]),
            dvid_in_d1.eq( dvid_in.i[1]),
            dvid_in_d2.eq(~dvid_in.i[2]),

            dvid_out.o_clk.eq(ClockSignal("shift")),
            dvid_out.o.eq(Cat(dvid_out_d0[0], ~dvid_out_d1[0], ~dvid_out_d2[0])),

            dvid_out_clk.o_clk.eq(ClockSignal("shift")),
            dvid_out_clk.o.eq(Cat(dvid_out_clk_d))
        ]
        m.submodules.overlay = DVIDOverlay(
            dvid_in_d0, 
            dvid_in_d1, 
            dvid_in_d2, 
            dvid_out_d0,
            dvid_out_d1,
            dvid_out_d2,
            dvid_out_clk_d,
            xdr,
            leds)

        return m
