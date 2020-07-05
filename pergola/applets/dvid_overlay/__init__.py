from nmigen import *
from nmigen.lib.cdc import *
from nmigen.build import *
from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig
# from ...util.cdc import SafeFFSynchronizer
from ...gateware.tmds import *

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

        dvid_in = platform.request("pmod1_lvds", 0, xdr=4)

        dvid_out = platform.request("pmod2_lvds", 0, xdr=4)
        dvid_out_clk = platform.request("pmod2_lvds_clk", 0, xdr=4)

        m = Module()

        m.submodules.pll = pll = ECP5PLL([
            ECP5PLLConfig("shift_x2", (pixel_clk_freq / 1e6) * 10 / 2),
            ECP5PLLConfig("shift", (pixel_clk_freq / 1e6) * 10 / 2 / 2),
            ECP5PLLConfig("sync", pixel_clk_freq / 1e6),
        ], clock_signal_name="pmod1_lvds_clk")


        m.d.comb += [
            dvid_in.i_clk.eq(ClockSignal("shift")),
            dvid_in.i_eclk.eq(ClockSignal("shift_x2")),

            dvid_out.o_clk.eq(ClockSignal("shift")),
            dvid_out.o_eclk.eq(ClockSignal("shift_x2")),

            dvid_out_clk.o_clk.eq(ClockSignal("shift")),
            dvid_out_clk.o_eclk.eq(ClockSignal("shift_x2")),
        ]

        sampled_b = Signal(20)
        sampled_g = Signal(20)
        sampled_r = Signal(20)

        sampled_b_r = Signal(20)
        sampled_g_r = Signal(20)
        sampled_r_r = Signal(20)

        m.d.shift += [
            sampled_b.eq(~Cat(dvid_in.i0[0], dvid_in.i1[0], dvid_in.i2[0], dvid_in.i3[0], sampled_b[:-4])),
            sampled_g.eq( Cat(dvid_in.i0[1], dvid_in.i1[1], dvid_in.i2[1], dvid_in.i3[1], sampled_g[:-4])),
            sampled_r.eq(~Cat(dvid_in.i0[2], dvid_in.i1[2], dvid_in.i2[2], dvid_in.i3[2], sampled_r[:-4])),

            sampled_b_r.eq(sampled_b),
            sampled_g_r.eq(sampled_g),
            sampled_r_r.eq(sampled_r),
        ]

        latch_clock = Signal()
        m.d.sync += latch_clock.eq(~latch_clock)

        # shift -> sync domian
        sampled_b_r_r = Signal(20)
        sampled_g_r_r = Signal(20)
        sampled_r_r_r = Signal(20)

        sampled_b_r_r_r = Signal(20)
        sampled_g_r_r_r = Signal(20)
        sampled_r_r_r_r = Signal(20)

        with m.If(latch_clock):
            m.d.sync += [
                sampled_b_r_r.eq(sampled_b_r),
                sampled_g_r_r.eq(sampled_g_r),
                sampled_r_r_r.eq(sampled_r_r),

                sampled_b_r_r_r.eq(sampled_b_r_r),
                sampled_g_r_r_r.eq(sampled_g_r_r),
                sampled_r_r_r_r.eq(sampled_r_r_r),
            ]
        with m.Else():
            m.d.sync += [
                sampled_b_r_r_r.eq(sampled_b_r_r_r[10:20]),
                sampled_g_r_r_r.eq(sampled_g_r_r_r[10:20]),
                sampled_r_r_r_r.eq(sampled_r_r_r_r[10:20]),
            ]

        shift_clock_initial = 0b00000111110000011111
        C_shift_clock_initial = Const(shift_clock_initial)
        shift_clock = Signal(20, reset=shift_clock_initial)

        m.d.shift += shift_clock.eq(Cat(shift_clock[4:], shift_clock[:4]))

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
            data_in=sampled_b_r_r_r[:10],
            data_out=pixel_b,
            c=c_b,
            active_data=active_b,
        )

        m.submodules.decoder_g = decoder_g = TMDSDecoder(
            data_in=sampled_g_r_r_r[:10],
            data_out=pixel_g,
            c=c_g,
            active_data=active_g,
        )

        m.submodules.decoder_r = decoder_r = TMDSDecoder(
            data_in=sampled_r_r_r_r[:10],
            data_out=pixel_r,
            c=c_r,
            active_data=active_r,
        )


        encoded_blue = Signal(10)
        encoded_red = Signal(10)
        encoded_green = Signal(10)

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


        encoded_red_r = Signal(10)
        encoded_green_r = Signal(10)
        encoded_blue_r = Signal(10)

        shift_red   = Signal(20)
        shift_green = Signal(20)
        shift_blue  = Signal(20)

        latched_red   = Signal(20)
        latched_green = Signal(20)
        latched_blue  = Signal(20)

        # encoded_r <= encoded on posedge of the pixel clock
        m.d.sync += encoded_red_r.eq(encoded_red)
        m.d.sync += encoded_green_r.eq(encoded_green)
        m.d.sync += encoded_blue_r.eq(encoded_blue)

        # latched_red <= {encoded_red, encoded_red_r} on every 2nd posedge pixel clock
        with m.If(latch_clock):
            m.d.sync += latched_red.eq(Cat(encoded_red_r, encoded_red))
            m.d.sync += latched_green.eq(Cat(encoded_green_r, encoded_green))
            m.d.sync += latched_blue.eq(Cat(encoded_blue_r, encoded_blue))

        with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
            m.d.shift += shift_red.eq(latched_red)
            m.d.shift += shift_green.eq(latched_green)
            m.d.shift += shift_blue.eq(latched_blue)
        with m.Else():
            m.d.shift += shift_red.eq(Cat(shift_red[4:], 0))
            m.d.shift += shift_green.eq(Cat(shift_green[4:], 0))
            m.d.shift += shift_blue.eq(Cat(shift_blue[4:], 0))

        # m.d.comb += [
        #     self.out_r.eq(shift_red[:xdr]),
        #     self.out_g.eq(shift_green[:xdr]),
        #     self.out_b.eq(shift_blue[:xdr]),
        #     self.out_clock.eq(shift_clock[:xdr])
        # ]

        # Output the re-encoded signal
        m.d.comb += dvid_out.o0.eq(Cat(shift_blue[0], ~shift_green[0], ~shift_red[0]))
        m.d.comb += dvid_out.o1.eq(Cat(shift_blue[1], ~shift_green[1], ~shift_red[1]))
        m.d.comb += dvid_out.o2.eq(Cat(shift_blue[2], ~shift_green[2], ~shift_red[2]))
        m.d.comb += dvid_out.o3.eq(Cat(shift_blue[3], ~shift_green[3], ~shift_red[3]))



        # Just to test input sampling:
        # Output sampled data from shift domain directly (not using decoded, encoded data)
        # m.d.comb += dvid_out.o0.eq(Cat(sampled_b_r[0], ~sampled_g_r[0], ~sampled_r_r[0]))
        # m.d.comb += dvid_out.o1.eq(Cat(sampled_b_r[1], ~sampled_g_r[1], ~sampled_r_r[1]))
        # m.d.comb += dvid_out.o2.eq(Cat(sampled_b_r[2], ~sampled_g_r[2], ~sampled_r_r[2]))
        # m.d.comb += dvid_out.o3.eq(Cat(sampled_b_r[3], ~sampled_g_r[3], ~sampled_r_r[3]))



        leds = Cat([platform.request("led", i) for i in range(8)])
        # m.d.sync += leds.eq(shift_clock[:8])
        m.d.comb += leds.eq(shift_blue[:8])
        # m.d.comb += leds.eq(sampled_b_r[:8])


        m.d.comb += dvid_out_clk.o0.eq(shift_clock[0])
        m.d.comb += dvid_out_clk.o1.eq(shift_clock[1])
        m.d.comb += dvid_out_clk.o2.eq(shift_clock[2])
        m.d.comb += dvid_out_clk.o3.eq(shift_clock[3])

        return m
