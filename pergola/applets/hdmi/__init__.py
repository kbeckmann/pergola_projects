from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen.back.pysim import Simulator, Active
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT, DIR_NONE
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *
from nmigen.build.dsl import *
from nmigen.build.res import ResourceManager

from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

from ...gateware.vga import VGAOutput, VGAOutputSubtarget
from ...gateware.vga2dvi import VGA2DVI


class HDMITest(FHDLTestCase):
    '''
    TODO: Write actual test cases. These are just to generate a waveforms to analyze.
    '''
    def test_hdmi(self):
        output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
            ('r',  8),
            ('g',  8),
            ('b',  8),
        ])

        sync = ClockDomain()
        pixel = ClockDomain()
        m = Module()
        m.domains += sync, pixel

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        blank = Signal()
        hsync = Signal()
        vsync = Signal()

        pixel_r = Signal()
        pixel_g = Signal()
        pixel_b = Signal()
        pixel_clk = Signal()

        m.submodules.vga = VGAOutputSubtarget(
            output=output,
            h_front=16,
            h_sync=96,
            h_back=44,
            h_active=640,
            v_front=10,
            v_sync=2,
            v_back=31,
            v_active=480,
        )

        m.submodules.vga2dvi = VGA2DVI(
            in_r = r,
            in_g = g,
            in_b = b,
            in_blank = output.blank,
            in_hsync = output.hs,
            in_vsync = output.vs,
            out_r = pixel_r,
            out_g = pixel_g,
            out_b = pixel_b,
            out_clock = pixel_clk,
        )

        sim = Simulator(m)
        sim.add_clock(period=1/25e6, phase=0, domain="sync")
        sim.add_clock(period=1/250e6, phase=0, domain="pixel")
        def process():
            for _ in range(100):
                yield

        sim.add_sync_process(process)
        with sim.write_vcd("hdmi.vcd"):
            sim.run()

    def test_vga2dvi(self):

        sync = ClockDomain()
        pixel = ClockDomain()

        m = Module()
        m.domains += sync, pixel

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        blank = Signal()
        hs = Signal()
        vs = Signal()

        pixel_r = Signal()
        pixel_g = Signal()
        pixel_b = Signal()
        pixel_clk = Signal()

        m.submodules.vga2dvi = VGA2DVI(
            in_r = r,
            in_g = g,
            in_b = b,
            in_blank = blank,
            in_hsync = hs,
            in_vsync = vs,
            out_r = pixel_r,
            out_g = pixel_g,
            out_b = pixel_b,
            out_clock = pixel_clk,
        )

        sim = Simulator(m)
        sim.add_clock(1/25e6, domain="sync")
        sim.add_clock(1/250e6, domain="shift", phase=0)
        def process():
            for _ in range(1000):
                yield

        sim.add_sync_process(process)
        with sim.write_vcd("hdmi_vga2dvi.vcd"):
            sim.run()


    def test_tmds(self):

        sync = ClockDomain()
        pixel = ClockDomain()

        m = Module()
        m.domains += sync, pixel

        data = Signal(8, reset=3)

        c = Signal(2)
        blank = Signal()
        encoded = Signal(10)

        m.submodules.tmds = TMDSEncoder(data, c, blank, encoded)

        sim = Simulator(m)
        sim.add_clock(1/25e6, domain="sync")
        sim.add_clock(1/250e6, domain="pixel")
        def process():
            for _ in range(1000):
                yield

        sim.add_sync_process(process)
        with sim.write_vcd("hdmi_tmds.vcd"):
            sim.run()


    def test_hdmi_formal(self):
        from nmigen.compat.fhdl.specials import TSTriple
        btn = Signal()
        led = TSTriple()

        m = Module()
        m.submodules.blinky = d(led, btn)

        # If the button is pressed, the led should always be on
        # m.d.comb += Assert(btn.implies(led.o))

        self.assertFormal(m, depth=10)


class HDMIApplet(Applet, applet_name="hdmi"):
    description = "HDMI source"
    help = "HDMI source"
    test_class = HDMITest

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("L1 J1 G1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
            Resource("pmod1_lvds_clk", 0, Pins("N1", dir="o"),
                     Attrs(IO_TYPE="LVDS")),
        ])

        hdmi_out = platform.request("pmod1_lvds", 0)
        hdmi_out_clk = platform.request("pmod1_lvds_clk", 0)

        led = platform.request("led", 0)
        btn = platform.request("button", 0)

        m = Module()

        m.submodules.pll1 = ECP5PLL([
            ECP5PLLConfig("clk100", 100),
        ])

        m.submodules.pll2 = ECP5PLL([
            ECP5PLLConfig("shift", 250),
            ECP5PLLConfig("sync", 25),
        ], clock_signal_name="clk100", clock_signal_freq=100e6)


        vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        pixel_r = Signal()
        pixel_g = Signal()
        pixel_b = Signal()
        pixel_clk = Signal()

        m.submodules.vga = VGAOutputSubtarget(
            output=vga_output,
            h_front=16,
            h_sync=96,
            h_back=44,
            h_active=640,
            v_front=10,
            v_sync=2,
            v_back=31,
            v_active=480,
        )

        m.submodules.vga2dvi = VGA2DVI(
            in_r = r,
            in_g = g,
            in_b = b,
            in_blank = vga_output.blank,
            in_hsync = vga_output.hs,
            in_vsync = vga_output.vs,
            out_r = pixel_r,
            out_g = pixel_g,
            out_b = pixel_b,
            out_clock = pixel_clk,
        )

        # Store output bits in separate registers
        pixel_clk_r = Signal()
        pixel_r_r = Signal()
        pixel_g_r = Signal()
        pixel_b_r = Signal()
        m.d.shift += pixel_clk_r.eq(~pixel_clk)
        m.d.shift += pixel_r_r.eq(~pixel_r)
        m.d.shift += pixel_g_r.eq(~pixel_g)
        m.d.shift += pixel_b_r.eq(pixel_b)

        m.d.comb += [
            hdmi_out_clk.eq(pixel_clk_r),
            hdmi_out.eq(Cat(pixel_b_r, pixel_g_r, pixel_r_r)),
        ]

        # Test image generator
        frame = Signal(16)
        vsync_r = Signal()
        m.d.sync += vsync_r.eq(vga_output.vs)
        with m.If(~vsync_r & vga_output.vs):
            m.d.sync += frame.eq(frame + 1)

        frame_tri = Mux(frame[8], ~frame[:8], frame[:8])
        frame_tri2 = Mux(frame[9], ~frame[1:9], frame[1:9])

        v_ctr = m.submodules.vga.v_ctr
        h_ctr = m.submodules.vga.h_ctr

        dir1 = Mux(v_ctr[6], 1, -1)
        X = (h_ctr + dir1 * frame[1:])
        Y = (v_ctr * 2) >> 1

        m.d.sync += r.eq(frame_tri[1:])
        m.d.sync += g.eq(v_ctr * Mux(X & Y, 255, 0))
        m.d.sync += b.eq(~(frame_tri2+(X ^ Y))*255)

        # Cycle colors in the top left corner
        # m.d.sync += r.eq(Mux(frame[5], 255, 0))
        # m.d.sync += g.eq(Mux(frame[6], 255, 0))
        # m.d.sync += b.eq(Mux(frame[7], 255, 0))

        return m
