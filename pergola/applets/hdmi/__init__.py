from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen.back.pysim import Simulator, Active
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *
from nmigen.build.dsl import *

from .. import Applet
from ...gateware.vga import VGAOutput, VGAOutputSubtarget, VGAParameters
from ...gateware.vga2dvi import VGA2DVI
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig


class HDMISignalGeneratorXDR(Elaboratable):
    def __init__(self, hdmi_out_clk, hdmi_out, vga_parameters, pll1_freq_mhz, pixel_freq_mhz, xdr=1, skip_pll_checks=False):
        self.hdmi_out_clk = hdmi_out_clk
        self.hdmi_out = hdmi_out
        self.vga_parameters = vga_parameters
        self.pll1_freq_mhz = pll1_freq_mhz
        self.pixel_freq_mhz = pixel_freq_mhz
        self.xdr = xdr
        self.skip_pll_checks = skip_pll_checks

    def elaborate(self, platform):
        m = Module()

        xdr = self.xdr

        m.submodules.pll1 = ECP5PLL([
            ECP5PLLConfig("clk_pll1", self.pll1_freq_mhz),
        ], skip_checks=self.skip_pll_checks)

        if xdr == 1:
            pll_config = [
                ECP5PLLConfig("shift", self.pixel_freq_mhz * 10),
                ECP5PLLConfig("sync", self.pixel_freq_mhz),
            ]
        elif xdr == 2:
            pll_config = [
                ECP5PLLConfig("shift", self.pixel_freq_mhz * 10 / 2),
                ECP5PLLConfig("sync", self.pixel_freq_mhz),
            ]
        elif xdr == 4:
            if True:
                pll_config = [
                    ECP5PLLConfig("shift_x2", self.pixel_freq_mhz * 10 / 2),
                    ECP5PLLConfig("shift", self.pixel_freq_mhz * 10 / 2 / 2),
                    ECP5PLLConfig("sync", self.pixel_freq_mhz),
                ]
            else:
                # Generate sclk(shift) from eclk(shift_x2)
                # This unfortunately reduces timing of the shift_x2 from 400 to 350 MHz or so
                pll_config = [
                    ECP5PLLConfig("shift_x2", self.pixel_freq_mhz * 10 / 2),
                    ECP5PLLConfig("sync", self.pixel_freq_mhz),
                ]
                shift_clk = Signal()
                m.domains += ClockDomain("shift")
                m.submodules.clkdiv2 = Instance("CLKDIVF",
                    i_CLKI=ClockSignal("shift_x2"),
                    i_RST=0,
                    i_ALIGNWD=0,

                    o_CDIVX=ClockSignal(domain="shift"),

                    p_DIV=2.0
                )
        elif xdr == 7:
            if True:
                pll_config = [
                    ECP5PLLConfig("shift_x2", self.pixel_freq_mhz * 10 / 2),
                    ECP5PLLConfig("shift", self.pixel_freq_mhz * 10 / 2. / 3.5),
                    ECP5PLLConfig("sync", self.pixel_freq_mhz),
                ]

        m.submodules.pll2 = ECP5PLL(
            pll_config,
            clock_signal_name="clk_pll1",
            clock_signal_freq=self.pll1_freq_mhz * 1e6,
            skip_checks=self.skip_pll_checks)

        vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        r_r = Signal(8)
        g_r = Signal(8)
        b_r = Signal(8)

        blank_r = Signal()
        hs_r = Signal()
        vs_r = Signal()

        m.submodules += FFSynchronizer(r, r_r, o_domain="sync", stages=3)
        m.submodules += FFSynchronizer(g, g_r, o_domain="sync", stages=3)
        m.submodules += FFSynchronizer(b, b_r, o_domain="sync", stages=3)

        m.submodules += FFSynchronizer(vga_output.blank, blank_r, o_domain="sync", stages=5)
        m.submodules += FFSynchronizer(vga_output.hs, hs_r, o_domain="sync", stages=5)
        m.submodules += FFSynchronizer(vga_output.vs, vs_r, o_domain="sync", stages=5)

        pixel_r = Signal(xdr)
        pixel_g = Signal(xdr)
        pixel_b = Signal(xdr)
        pixel_clk = Signal(xdr)


        m.submodules.vga = VGAOutputSubtarget(
            output=vga_output,
            vga_parameters=self.vga_parameters,
        )

        m.submodules.vga2dvi = VGA2DVI(
            in_r = r_r,
            in_g = g_r,
            in_b = b_r,
            in_blank = blank_r,
            in_hsync = hs_r,
            in_vsync = vs_r,
            out_r = pixel_r,
            out_g = pixel_g,
            out_b = pixel_b,
            out_clock = pixel_clk,
            xdr=xdr
        )

        # Store output bits in separate registers
        #
        # Also node that pixel_clk, pixel_r, pixel_g are inverted.
        # This is because on PMOD1 on the Pergola board, they are routed
        # this way.
        pixel_clk_r = Signal(xdr)
        pixel_r_r = Signal(xdr)
        pixel_g_r = Signal(xdr)
        pixel_b_r = Signal(xdr)
        m.d.shift += pixel_clk_r.eq(~pixel_clk)
        m.d.shift += pixel_r_r.eq(~pixel_r)
        m.d.shift += pixel_g_r.eq(~pixel_g)
        m.d.shift += pixel_b_r.eq(pixel_b)

        if xdr == 1:
            m.d.comb += [
                self.hdmi_out_clk.eq(pixel_clk_r[0]),
                self.hdmi_out.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
            ]
        elif xdr == 2:
            m.d.comb += [
                self.hdmi_out_clk.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out_clk.o0.eq(pixel_clk_r[0]),
                self.hdmi_out_clk.o1.eq(pixel_clk_r[1]),

                self.hdmi_out.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.hdmi_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
            ]
        elif xdr == 4:
            m.d.comb += [
                self.hdmi_out_clk.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out_clk.o_eclk.eq(ClockSignal("shift_x2")),
                self.hdmi_out_clk.o0.eq(pixel_clk_r[0]),
                self.hdmi_out_clk.o1.eq(pixel_clk_r[1]),
                self.hdmi_out_clk.o2.eq(pixel_clk_r[2]),
                self.hdmi_out_clk.o3.eq(pixel_clk_r[3]),

                self.hdmi_out.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out.o_eclk.eq(ClockSignal("shift_x2")),
                self.hdmi_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.hdmi_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
                self.hdmi_out.o2.eq(Cat(pixel_b_r[2], pixel_g_r[2], pixel_r_r[2])),
                self.hdmi_out.o3.eq(Cat(pixel_b_r[3], pixel_g_r[3], pixel_r_r[3])),
            ]
        elif xdr == 7:
            m.d.comb += [
                self.hdmi_out_clk.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out_clk.o_eclk.eq(ClockSignal("shift_x2")),
                self.hdmi_out_clk.o0.eq(pixel_clk_r[0]),
                self.hdmi_out_clk.o1.eq(pixel_clk_r[1]),
                self.hdmi_out_clk.o2.eq(pixel_clk_r[2]),
                self.hdmi_out_clk.o3.eq(pixel_clk_r[3]),
                self.hdmi_out_clk.o4.eq(pixel_clk_r[4]),
                self.hdmi_out_clk.o5.eq(pixel_clk_r[5]),
                self.hdmi_out_clk.o6.eq(pixel_clk_r[6]),

                self.hdmi_out.o_clk.eq(ClockSignal("shift")),
                self.hdmi_out.o_eclk.eq(ClockSignal("shift_x2")),
                self.hdmi_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.hdmi_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
                self.hdmi_out.o2.eq(Cat(pixel_b_r[2], pixel_g_r[2], pixel_r_r[2])),
                self.hdmi_out.o3.eq(Cat(pixel_b_r[3], pixel_g_r[3], pixel_r_r[3])),
                self.hdmi_out.o4.eq(Cat(pixel_b_r[4], pixel_g_r[4], pixel_r_r[4])),
                self.hdmi_out.o5.eq(Cat(pixel_b_r[5], pixel_g_r[5], pixel_r_r[5])),
                self.hdmi_out.o6.eq(Cat(pixel_b_r[6], pixel_g_r[6], pixel_r_r[6])),
            ]


        # Test image generator
        frame = Signal(16)
        vsync_r = Signal()
        m.d.sync += vsync_r.eq(vga_output.vs)
        with m.If(~vsync_r & vga_output.vs):
            m.d.sync += frame.eq(frame + 1)

        # Blink an LED for each frame
        led = platform.request("led", 0)
        m.d.comb += led.eq(frame[0])

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

        # Cycle colors
        # m.d.sync += r.eq(Mux(frame[5], 255, 0))
        # m.d.sync += g.eq(Mux(frame[6], 255, 0))
        # m.d.sync += b.eq(Mux(frame[7], 255, 0))

        return m



class HDMIParameters():
    def __init__(self, vga_parameters, pll1_freq_mhz, pixel_freq_mhz):
        self.vga_parameters = vga_parameters
        self.pll1_freq_mhz = pll1_freq_mhz
        self.pixel_freq_mhz = pixel_freq_mhz

    def __repr__(self):
        return "(HDMIParameters ({}) {})".format(
            self.vga_parameters,
            self.pll1_freq_mhz,
            self.pixel_freq_mhz)

hdmi_configs = {
    "640x480p60": HDMIParameters(VGAParameters(
            h_front=16,
            h_sync=96,
            h_back=44,
            h_active=640,
            v_front=10,
            v_sync=2,
            v_back=31,
            v_active=480,
        ), 100, 25),

    # This uses a clock that is compatible with xdr=7
    "640x480p60_7": HDMIParameters(VGAParameters(
            h_front=16,
            h_sync=96,
            h_back=44,
            h_active=640,
            v_front=10,
            v_sync=2,
            v_back=31,
            v_active=480,
        ), 100, 28),

    "1280x720p60": HDMIParameters(VGAParameters(
            h_front=82,
            h_sync=80,
            h_back=202,
            h_active=1280,
            v_front=3,
            v_sync=5,
            v_back=22,
            v_active=720,
        ), 100, 74),

    # This uses a clock that is compatible with xdr=7
    "1280x720p60_7": HDMIParameters(VGAParameters(
            h_front=82,
            h_sync=80,
            h_back=202,
            h_active=1280,
            v_front=3,
            v_sync=5,
            v_back=22,
            v_active=720,
        ), 100, 70),

    "1920x1080p30": HDMIParameters(VGAParameters(
            h_front=80,
            h_sync=44,
            h_back=148,
            h_active=1920,
            v_front=4,
            v_sync=5,
            v_back=36,
            v_active=1080,
        ), 100, 74),

    # This uses a clock that is compatible with xdr=7
    "1920x1080p30_7": HDMIParameters(VGAParameters(
            h_front=100,
            h_sync=44,
            h_back=215,
            h_active=1920,
            v_front=4,
            v_sync=5,
            v_back=36,
            v_active=1080,
        ), 100, 77),

    "1920x1080p60": HDMIParameters(VGAParameters(
            h_front=109,
            h_sync=44,
            h_back=148,
            h_active=1920,
            v_front=4,
            v_sync=5,
            v_back=36,
            v_active=1080,
        ), 100, 150),

    "2560x1440p30": HDMIParameters(VGAParameters(
            h_front=48,
            h_sync=32,
            h_back=80,
            h_active=2560,
            v_front=3,
            v_sync=5,
            v_back=33,
            v_active=1440,
        ), 100, 122),

    # Generates a 60Hz signal but needs 1.2V on VCC.
    # Needs a simpler test image to meet timing on the sync/pixel cd.
    # Can run at 205MHz@1.1V
    "2560x1440p60": HDMIParameters(VGAParameters(
            h_front=20,
            h_sync=20,
            h_back=20,
            h_active=2560,
            v_front=3,
            v_sync=5,
            v_back=5,
            v_active=1440,
        ), 100, 228),
}

class HDMIApplet(Applet, applet_name="hdmi"):
    help = "HDMI/DVID signal generator"
    description = """
    HDMI/DVID signal generator

    Can use SDR, DDR, DDRx2, DDRx7:1 to serialize the output.

    DDRx7:1 was made just to see if it works - it does, but it's really not a 
    good fit because of the odd ratio 7:1.

    1920x1080p60 can be achieved with DDRx2, however it violates the timings of
    the I/O blocks. But it works!

    """

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--xdr", default=1, type=int, choices=[1, 2, 4, 7],
            help="sdr=1, ddr=2, ddrx2=4, ddrx7=7")

        parser.add_argument(
            "--config", choices=hdmi_configs.keys(), required=True,
            help="Set resolution and pixel clock")

        parser.add_argument(
            "--skip-pll-checks", default=0, action="count",
            help="Allow PLL to be configured out of spec")

    def __init__(self, args):
        self.xdr = args.xdr
        self.hdmi_config = args.config
        self.skip_pll_checks = args.skip_pll_checks

    def elaborate(self, platform):

        platform.add_resources([
            Resource("pmod1_lvds", 0, Pins("L1 J1 G1", dir="o"),
                    Attrs(IO_TYPE="LVDS", DIFFRESISTOR="100")),
            Resource("pmod1_lvds_clk", 0, Pins("N1", dir="o"),
                    Attrs(IO_TYPE="LVDS", DIFFRESISTOR="100")),
        ])

        xdr = self.xdr
        hdmi_config = hdmi_configs[self.hdmi_config]

        hdmi_out_clk = platform.request("pmod1_lvds_clk", 0, xdr=xdr if xdr > 1 else 0)
        hdmi_out = platform.request("pmod1_lvds", 0, xdr=xdr if xdr > 1 else 0)

        m = Module()

        m.submodules.hdmi_signal_generator = HDMISignalGeneratorXDR(
            hdmi_out_clk=hdmi_out_clk,
            hdmi_out=hdmi_out,
            vga_parameters=hdmi_config.vga_parameters,
            pll1_freq_mhz=hdmi_config.pll1_freq_mhz,
            pixel_freq_mhz=hdmi_config.pixel_freq_mhz,
            xdr=xdr,
            skip_pll_checks=self.skip_pll_checks)

        return m


#####################


class HDMITest(FHDLTestCase):
    '''
    TODO: Write actual test cases. These are just to generate waveforms to analyze.
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
