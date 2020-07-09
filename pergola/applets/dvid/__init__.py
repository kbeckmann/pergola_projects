from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen.back.pysim import Simulator, Active
from nmigen.back import cxxrtl
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *
from nmigen.build.dsl import *

from .. import Applet
from ...gateware.vga import VGAOutput, VGAOutputSubtarget, VGAParameters
from ...gateware.vga2dvid import VGA2DVID
from ...gateware.vga_testimage import TestImageGenerator
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig


class DVIDSignalGeneratorXDR(Elaboratable):
    def __init__(self, dvid_out_clk, dvid_out, vga_parameters, pll1_freq_mhz, pixel_freq_mhz, xdr=1, skip_pll_checks=False, invert_outputs=[0, 0, 0, 0]):
        self.dvid_out_clk = dvid_out_clk
        self.dvid_out = dvid_out
        self.vga_parameters = vga_parameters
        self.pll1_freq_mhz = pll1_freq_mhz
        self.pixel_freq_mhz = pixel_freq_mhz
        self.xdr = xdr
        self.skip_pll_checks = skip_pll_checks
        self.invert_outputs = invert_outputs

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
                    ECP5PLLConfig("shift_fast", self.pixel_freq_mhz * 10 / 2),
                    ECP5PLLConfig("shift", self.pixel_freq_mhz * 10 / 2 / 2),
                    ECP5PLLConfig("sync", self.pixel_freq_mhz),
                ]
            else:
                # Generate sclk(shift) from fclk(shift_fast)
                # This unfortunately reduces timing of the shift_fast from 400 to 350 MHz or so
                pll_config = [
                    ECP5PLLConfig("shift_fast", self.pixel_freq_mhz * 10 / 2),
                    ECP5PLLConfig("sync", self.pixel_freq_mhz),
                ]
                shift_clk = Signal()
                m.domains += ClockDomain("shift")
                m.submodules.clkdiv2 = Instance("CLKDIVF",
                    i_CLKI=ClockSignal("shift_fast"),
                    i_RST=0,
                    i_ALIGNWD=0,

                    o_CDIVX=ClockSignal(domain="shift"),

                    p_DIV=2.0
                )
        elif xdr == 7:
            if True:
                pll_config = [
                    ECP5PLLConfig("shift_fast", self.pixel_freq_mhz * 10 / 2),
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

        pixel_r = Signal(xdr)
        pixel_g = Signal(xdr)
        pixel_b = Signal(xdr)
        pixel_clk = Signal(xdr)

        m.submodules.vga = VGAOutputSubtarget(
            output=vga_output,
            vga_parameters=self.vga_parameters,
        )

        m.submodules.vga2dvid = VGA2DVID(
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
            xdr=xdr
        )

        m.submodules += TestImageGenerator(
            vsync=vga_output.vs,
            h_ctr=m.submodules.vga.h_ctr,
            v_ctr=m.submodules.vga.v_ctr,
            r=r,
            g=g,
            b=b)

        # Store output bits in separate registers
        #
        # Also invert signals based on parameters
        pixel_clk_r = Signal(xdr)
        pixel_r_r = Signal(xdr)
        pixel_g_r = Signal(xdr)
        pixel_b_r = Signal(xdr)
        invert_outputs = self.invert_outputs
        m.d.shift += pixel_clk_r.eq(~pixel_clk if invert_outputs[0] else pixel_clk)
        m.d.shift += pixel_r_r  .eq(~pixel_r   if invert_outputs[3] else pixel_r)
        m.d.shift += pixel_g_r  .eq(~pixel_g   if invert_outputs[2] else pixel_g)
        m.d.shift += pixel_b_r  .eq(~pixel_b   if invert_outputs[1] else pixel_b)

        if xdr == 1:
            m.d.comb += [
                self.dvid_out_clk.eq(pixel_clk_r[0]),
                self.dvid_out.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
            ]
        elif xdr == 2:
            m.d.comb += [
                self.dvid_out_clk.o_clk.eq(ClockSignal("shift")),
                self.dvid_out_clk.o0.eq(pixel_clk_r[0]),
                self.dvid_out_clk.o1.eq(pixel_clk_r[1]),

                self.dvid_out.o_clk.eq(ClockSignal("shift")),
                self.dvid_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.dvid_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
            ]
        elif xdr == 4:
            m.d.comb += [
                self.dvid_out_clk.o_clk.eq(ClockSignal("shift")),
                self.dvid_out_clk.o_fclk.eq(ClockSignal("shift_fast")),
                self.dvid_out_clk.o0.eq(pixel_clk_r[0]),
                self.dvid_out_clk.o1.eq(pixel_clk_r[1]),
                self.dvid_out_clk.o2.eq(pixel_clk_r[2]),
                self.dvid_out_clk.o3.eq(pixel_clk_r[3]),

                self.dvid_out.o_clk.eq(ClockSignal("shift")),
                self.dvid_out.o_fclk.eq(ClockSignal("shift_fast")),
                self.dvid_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.dvid_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
                self.dvid_out.o2.eq(Cat(pixel_b_r[2], pixel_g_r[2], pixel_r_r[2])),
                self.dvid_out.o3.eq(Cat(pixel_b_r[3], pixel_g_r[3], pixel_r_r[3])),
            ]
        elif xdr == 7:
            m.d.comb += [
                self.dvid_out_clk.o_clk.eq(ClockSignal("shift")),
                self.dvid_out_clk.o_fclk.eq(ClockSignal("shift_fast")),
                self.dvid_out_clk.o0.eq(pixel_clk_r[0]),
                self.dvid_out_clk.o1.eq(pixel_clk_r[1]),
                self.dvid_out_clk.o2.eq(pixel_clk_r[2]),
                self.dvid_out_clk.o3.eq(pixel_clk_r[3]),
                self.dvid_out_clk.o4.eq(pixel_clk_r[4]),
                self.dvid_out_clk.o5.eq(pixel_clk_r[5]),
                self.dvid_out_clk.o6.eq(pixel_clk_r[6]),

                self.dvid_out.o_clk.eq(ClockSignal("shift")),
                self.dvid_out.o_fclk.eq(ClockSignal("shift_fast")),
                self.dvid_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.dvid_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
                self.dvid_out.o2.eq(Cat(pixel_b_r[2], pixel_g_r[2], pixel_r_r[2])),
                self.dvid_out.o3.eq(Cat(pixel_b_r[3], pixel_g_r[3], pixel_r_r[3])),
                self.dvid_out.o4.eq(Cat(pixel_b_r[4], pixel_g_r[4], pixel_r_r[4])),
                self.dvid_out.o5.eq(Cat(pixel_b_r[5], pixel_g_r[5], pixel_r_r[5])),
                self.dvid_out.o6.eq(Cat(pixel_b_r[6], pixel_g_r[6], pixel_r_r[6])),
            ]

        return m


class DVIDParameters():
    def __init__(self, vga_parameters, pll1_freq_mhz, pixel_freq_mhz):
        self.vga_parameters = vga_parameters
        self.pll1_freq_mhz = pll1_freq_mhz
        self.pixel_freq_mhz = pixel_freq_mhz

    def __repr__(self):
        return "(DVIDParameters ({}) {})".format(
            self.vga_parameters,
            self.pll1_freq_mhz,
            self.pixel_freq_mhz)

dvid_configs = {
    "640x480p60": DVIDParameters(VGAParameters(
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
    "640x480p60_7": DVIDParameters(VGAParameters(
            h_front=16,
            h_sync=96,
            h_back=44,
            h_active=640,
            v_front=10,
            v_sync=2,
            v_back=31,
            v_active=480,
        ), 100, 28),

    "1280x720p60": DVIDParameters(VGAParameters(
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
    "1280x720p60_7": DVIDParameters(VGAParameters(
            h_front=82,
            h_sync=80,
            h_back=202,
            h_active=1280,
            v_front=3,
            v_sync=5,
            v_back=22,
            v_active=720,
        ), 100, 70),

    "1920x1080p30": DVIDParameters(VGAParameters(
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
    "1920x1080p30_7": DVIDParameters(VGAParameters(
            h_front=100,
            h_sync=44,
            h_back=215,
            h_active=1920,
            v_front=4,
            v_sync=5,
            v_back=36,
            v_active=1080,
        ), 100, 77),

    # Should be 148.5 MHz but the PLL can't generate 742.5 MHz.
    "1920x1080p60": DVIDParameters(VGAParameters(
            h_front=88,
            h_sync=44,
            h_back=148,
            h_active=1920,
            v_front=4,
            v_sync=5,
            v_back=36,
            v_active=1080,
        ), 100, 150),

    "2560x1440p30": DVIDParameters(VGAParameters(
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
    "2560x1440p60": DVIDParameters(VGAParameters(
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

class DVIDApplet(Applet, applet_name="dvid"):
    help = "DVID/DVID signal generator"
    description = """
    DVID/DVID signal generator

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
            "--config", choices=dvid_configs.keys(), required=True,
            help="Set resolution and pixel clock")

        parser.add_argument(
            "--skip-pll-checks", default=0, action="count",
            help="Allow PLL to be configured out of spec")

    def __init__(self, args):
        self.xdr = args.xdr
        self.dvid_config = args.config
        self.skip_pll_checks = args.skip_pll_checks

    def elaborate(self, platform):

        # PMOD2 pinout:
        # CLK B1/B2
        # D0  C1/C2 (b)
        # D1  E2/D1 (g)  inverted
        # D2  G2/F1 (r)  inverted

        platform.add_resources([
            Resource("pmod2_lvds", 0, Pins("C1  D1  F1", dir="o"),
                    Attrs(IO_TYPE="LVDS", DIFFRESISTOR="100")),
            Resource("pmod2_lvds_clk", 0, Pins("B1", dir="o"),
                    Attrs(IO_TYPE="LVDS", DIFFRESISTOR="100")),
        ])

        xdr = self.xdr
        dvid_config = dvid_configs[self.dvid_config]

        dvid_out_clk = platform.request("pmod2_lvds_clk", 0, xdr=xdr if xdr > 1 else 0)
        dvid_out = platform.request("pmod2_lvds", 0, xdr=xdr if xdr > 1 else 0)

        m = Module()

        m.submodules.dvid_signal_generator = DVIDSignalGeneratorXDR(
            dvid_out_clk=dvid_out_clk,
            dvid_out=dvid_out,
            vga_parameters=dvid_config.vga_parameters,
            pll1_freq_mhz=dvid_config.pll1_freq_mhz,
            pixel_freq_mhz=dvid_config.pixel_freq_mhz,
            xdr=xdr,
            skip_pll_checks=self.skip_pll_checks,
            invert_outputs=[0, 0, 1, 1])

        return m


#####################


class DVIDTest(FHDLTestCase):
    '''
    TODO: Write actual test cases. These are just to generate waveforms to analyze.
    '''
    def test_dvid(self):
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

        m.submodules.vga2dvid = VGA2DVID(
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
        with sim.write_vcd("dvid.vcd"):
            sim.run()


    def test_vga2dvid(self):

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

        m.submodules.vga2dvid = VGA2DVID(
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
        with sim.write_vcd("dvid_vga2dvid.vcd"):
            sim.run()

class DVIDSim(FHDLTestCase):
    """
    This is not pretty but it works!
    """

    def test_dvid_cxxrtl(self):

        import os
        import subprocess

        led = Signal()
        btn = Signal()

        m = Module()

        vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        m.submodules.vga = VGAOutputSubtarget(
            output=vga_output,
            vga_parameters=dvid_configs["1280x720p60"].vga_parameters,
        )

        vs = vga_output.vs
        v_en = m.submodules.vga.v_en
        h_en = m.submodules.vga.h_en

        m.submodules.imagegen = TestImageGenerator(
            vsync=vga_output.vs,
            h_ctr=m.submodules.vga.h_ctr,
            v_ctr=m.submodules.vga.v_ctr,
            r=r,
            g=g,
            b=b,
            speed=0)

        m.submodules.vga_phy = Instance("vga_phy",
            p_width=1280,
            p_height=720,
            i_clk=ClockSignal(),
            i_hen=h_en,
            i_ven=v_en,
            i_r=r,
            i_g=g,
            i_b=b)

        output = cxxrtl.convert(m, black_boxes={"vga_phy": r"""
attribute \cxxrtl_blackbox 1
attribute \blackbox 1
module \vga_phy
  attribute \cxxrtl_edge "p"
  wire input 1 \clk
  wire input 2 \hen
  wire input 3 \ven
  wire width 8 input 4 \r
  wire width 8 input 5 \g
  wire width 8 input 6 \b
end
"""})

        root = os.path.join("build")
        filename = os.path.join(root, "top.cpp")
        elfname = os.path.join(root, "top.elf")

        with open(filename, "w") as f:
            f.write(output)
            f.write(r"""
#include <iostream>
#include <fstream>
#include <SDL2/SDL.h>
#include <backends/cxxrtl/cxxrtl_vcd.h>

struct sdl_vga_phy : public cxxrtl_design::bb_p_vga__phy {
    SDL_Window *window = nullptr;
    SDL_Renderer *renderer = nullptr;
    SDL_Texture *framebuffer = nullptr;
    size_t stride;

    std::vector<uint8_t> pixels;
    size_t beamAt = 0;
    size_t frames = 0;

    bool init(std::string name, unsigned width, unsigned height) {
        if (SDL_Init(SDL_INIT_VIDEO) != 0)
            return false;

        window = SDL_CreateWindow(name.c_str(),
            SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
            width, height,
            0);
        if (window == nullptr)
            return false;

        renderer = SDL_CreateRenderer(window, -1,
            SDL_RENDERER_PRESENTVSYNC);
        if (renderer == nullptr)
            return false;

        framebuffer = SDL_CreateTexture(renderer,
            SDL_PIXELFORMAT_RGB24, SDL_TEXTUREACCESS_STREAMING,
            width, height);
        if (framebuffer == nullptr)
            return false;

        pixels.resize(width * height * 3);
        stride = width * 3;
        return true;
    }

    ~sdl_vga_phy() {
        if (framebuffer)
            SDL_DestroyTexture(framebuffer);
        if (renderer)
            SDL_DestroyRenderer(renderer);
        if (window)
            SDL_DestroyWindow(window);
    }

  bool eval() override {
    if (posedge_p_clk()) {
        if (bool(p_hen) && bool(p_ven) && beamAt < pixels.size()) {
            pixels[beamAt++] = p_r.get<uint8_t>();
            pixels[beamAt++] = p_g.get<uint8_t>();
            pixels[beamAt++] = p_b.get<uint8_t>();
        }
        if (!bool(p_ven) && beamAt == pixels.size()) {
            SDL_UpdateTexture(framebuffer, NULL, pixels.data(), stride);
            SDL_RenderCopy(renderer, framebuffer, NULL, NULL);
            SDL_RenderPresent(renderer);
            beamAt = 0;
            frames++;
        }
    }
    return true;
  }
};

namespace cxxrtl_design {

std::unique_ptr<bb_p_vga__phy>
bb_p_vga__phy::create(std::string name,
                      cxxrtl::metadata_map parameters,
                      cxxrtl::metadata_map attributes) {
  std::unique_ptr<sdl_vga_phy> phy {new sdl_vga_phy};
  assert(phy->init(name, parameters.at("width").as_uint(), parameters.at("height").as_uint()));
  return phy;
}

}

int main(int argc, char *argv[])
{
    cxxrtl_design::p_top top;
    sdl_vga_phy *vga_phy = static_cast<sdl_vga_phy*>(top.cell_p_vga__phy.get());

    vcd_writer w;

    if (argc == 2) {
        debug_items items;
        top.debug_info(items);
        w.add(items);
    }

    unsigned lastTime = 0;
    unsigned globalTime = 0;
    while (1) {
        for (unsigned steps = 0; steps < 100000; steps++) {
            top.p_clk.set<uint32_t>(0);
            top.step();
            top.p_clk.set<uint32_t>(1);
            top.step();
            if (argc == 2)
                w.sample(globalTime++);
        }

        unsigned currentTime = SDL_GetTicks();
        float delta = currentTime - lastTime;
        if (delta >= 1000) {
            std::cout << "FPS: " << (vga_phy->frames / (delta / 1000.0f)) << std::endl;
            vga_phy->frames = 0;
            lastTime = currentTime;
        }

        SDL_Event event;
        if (SDL_PollEvent(&event)) {
            if (event.type == SDL_KEYDOWN)
                break;
        }
    }

    if (argc == 2) {
        std::cout << "Writing " << argv[1] << std::endl;
        std::ofstream outfile (argv[1]);
        outfile << w.buffer;
        outfile.close();
    }

    SDL_Quit();
    return 0;
}

            """)
            f.close()

        print(subprocess.check_call([
            "clang++", "-I", "/usr/share/yosys/include",
            "-ggdb", "-O3", "-fno-exceptions", "-std=c++11", "-lSDL2", "-o", elfname, filename]))

        print(subprocess.check_call([elfname]))
