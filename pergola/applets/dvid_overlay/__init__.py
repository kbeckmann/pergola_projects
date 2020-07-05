from nmigen import *
from nmigen.lib.cdc import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig
from nmigen.back.pysim import Simulator, Active
from ...util.test import FHDLTestCase
# from ...util.cdc import SafeFFSynchronizer
from ...gateware.tmds import TMDSEncoder, TMDSDecoder

class DVIDOverlay(Elaboratable):
    def __init__(self, dvid_in, dvid_out, dvid_clk_out):
        self.dvid_in = dvid_in
        self.dvid_out = dvid_out
        self.dvid_clk_out = dvid_clk_out

    def elaborate(self, platform):
        dvid_in = self.dvid_in
        dvid_out = self.dvid_out
        dvid_clk_out = self.dvid_clk_out

        m = Module()

        sampled_b = Signal(10)
        sampled_g = Signal(10)
        sampled_r = Signal(10)

        sampled_b_r = Signal(10)
        sampled_g_r = Signal(10)
        sampled_r_r = Signal(10)

        sampled_b_r_r = Signal(10)
        sampled_g_r_r = Signal(10)
        sampled_r_r_r = Signal(10)

        sampled_b_r_r_r = Signal(10)
        sampled_g_r_r_r = Signal(10)
        sampled_r_r_r_r = Signal(10)

        m.d.shift += [
            sampled_b.eq(Cat(~dvid_in[0], sampled_b[:-1])),
            sampled_g.eq(Cat( dvid_in[1], sampled_g[:-1])),
            sampled_r.eq(Cat(~dvid_in[2], sampled_r[:-1])),

            sampled_b_r.eq(sampled_b),
            sampled_g_r.eq(sampled_g),
            sampled_r_r.eq(sampled_r),
        ]

        m.d.sync += [
            sampled_b_r_r.eq(sampled_b_r),
            sampled_g_r_r.eq(sampled_g_r),
            sampled_r_r_r.eq(sampled_r_r),

            sampled_b_r_r_r.eq(sampled_b_r_r),
            sampled_g_r_r_r.eq(sampled_g_r_r),
            sampled_r_r_r_r.eq(sampled_r_r_r),
        ]

        shift_clock_initial = 0b0000011111
        C_shift_clock_initial = Const(shift_clock_initial)
        shift_clock = Signal(10, reset=shift_clock_initial)

        m.d.shift += shift_clock.eq(Cat(shift_clock[1:], shift_clock[:1]))

        pixel_b = Signal(8)
        active_b = Signal()
        c_b = Signal(2)
        pixel_g = Signal(8)
        active_g = Signal()
        c_g = Signal(2)
        pixel_r = Signal(8)
        active_r = Signal()
        c_r = Signal(2)

        m.submodules.decoder_b = decoder_b = TMDSDecoder(
            data_in=sampled_b_r_r_r,
            data_out=pixel_b,
            c=c_b,
            active_data=active_b,
        )

        m.submodules.decoder_g = decoder_g = TMDSDecoder(
            data_in=sampled_g_r_r_r,
            data_out=pixel_g,
            c=c_g,
            active_data=active_g,
        )

        m.submodules.decoder_r = decoder_r = TMDSDecoder(
            data_in=sampled_r_r_r_r,
            data_out=pixel_r,
            c=c_r,
            active_data=active_r,
        )


        encoded_blue = Signal(10)
        encoded_red = Signal(10)
        encoded_green = Signal(10)

        encoded_blue_r = Signal(10)
        encoded_red_r = Signal(10)
        encoded_green_r = Signal(10)

        encoded_blue_r_r = Signal(10)
        encoded_red_r_r = Signal(10)
        encoded_green_r_r = Signal(10)

        m.submodules.encoder_b = encoder_b = TMDSEncoder(
            data=pixel_b,
            c=c_b,
            blank=~active_b,
            encoded=encoded_blue,
        )

        m.submodules.encoder_g = encoder_g = TMDSEncoder(
            data=pixel_g,
            c=c_g,
            blank=~active_g,
            encoded=encoded_green,
        )

        m.submodules.encoder_r = encoder_r = TMDSEncoder(
            data=pixel_r,
            c=c_r,
            blank=~active_r,
            encoded=encoded_red,
        )

        m.d.sync += [
            encoded_blue_r.eq(encoded_blue),
            encoded_green_r.eq(encoded_green),
            encoded_red_r.eq(encoded_red),

            encoded_blue_r_r.eq(encoded_blue_r),
            encoded_green_r_r.eq(encoded_green_r),
            encoded_red_r_r.eq(encoded_red_r),
        ]


        shift_red   = Signal(10)
        shift_green = Signal(10)
        shift_blue  = Signal(10)

        with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
            m.d.shift += shift_blue.eq(encoded_blue_r_r)
            m.d.shift += shift_green.eq(encoded_green_r_r)
            m.d.shift += shift_red.eq(encoded_red_r_r)
        with m.Else():
            m.d.shift += shift_blue.eq(Cat(shift_blue[1:], 0))
            m.d.shift += shift_green.eq(Cat(shift_green[1:], 0))
            m.d.shift += shift_red.eq(Cat(shift_red[1:], 0))

        # Output the re-encoded signal
        # m.d.comb += dvid_out.eq(Cat(~dvid_in[0], ~dvid_in[1], dvid_in[2]))
        m.d.comb += dvid_out.eq(Cat(shift_blue[0], ~shift_green[0], ~shift_red[0]))

        # Just to test input sampling:
        # Output sampled data from shift domain directly (not using decoded, encoded data)
        # m.d.comb += dvid_out.eq(Cat(sampled_b[0], ~sampled_g[0], ~sampled_r[0]))



        # leds = Cat([platform.request("led", i) for i in range(8)])
        # # m.d.sync += leds.eq(shift_clock[:8])
        # # m.d.comb += leds.eq(shift_clock[:8])
        # m.d.comb += leds.eq(shift_blue[:8])

        m.d.comb += dvid_clk_out.eq(shift_clock[0])

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

        ctr = Signal(16)
        with m.If(ctr == 0):
            m.d.shift += encoded_shift.eq(encoded)
            m.d.shift += ctr.eq(10)
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


        m.submodules += DVIDOverlay(dvid_in, dvid_out, dvid_clk_out)

        return m
