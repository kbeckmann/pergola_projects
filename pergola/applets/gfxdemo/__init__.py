from nmigen import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen.back.pysim import Simulator, Active
from nmigen.back import cxxrtl
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *
from nmigen.build.dsl import *

from nmigen.hdl.rec import Direction

from .. import Applet
from ...gateware.bus.buswrapper import BusWrapper
from ...gateware.vga import VGAOutput, VGAOutputSubtarget, VGAParameters
from ...gateware.vga2dvid import VGA2DVID
from ...gateware.vga_testimage import TestImageGenerator, RotozoomImageGenerator
from ...gateware.gameoflife import GameOfLifeGenerator
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig

from ...gateware.bus.buscontroller import Asm, BusController

class DVIDSignalGeneratorXDR(Elaboratable):
    def __init__(self, dvid_out_clk, dvid_out, r, g, b, vga_parameters, xdr=1, emulate_ddr=False, invert_outputs=[0, 0, 0, 0]):
        self.dvid_out_clk = dvid_out_clk
        self.dvid_out = dvid_out
        self.vga_parameters = vga_parameters
        self.xdr = xdr
        self.emulate_ddr = emulate_ddr
        self.invert_outputs = invert_outputs

        self.vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])

        self.r = r
        self.g = g
        self.b = b

        self.vga = VGAOutputSubtarget(
            output=self.vga_output,
            vga_parameters=self.vga_parameters,
        )

    def elaborate(self, platform):
        m = Module()

        xdr = self.xdr
        emulate_ddr = self.emulate_ddr
        vga_output = self.vga_output

        pixel_r = Signal(xdr)
        pixel_g = Signal(xdr)
        pixel_b = Signal(xdr)
        pixel_clk = Signal(xdr)

        m.submodules.vga = self.vga

        delay_cycles = 4
        blank_r = Signal(delay_cycles)
        hs_r = Signal(delay_cycles)
        vs_r = Signal(delay_cycles)
        m.d.sync += [
            blank_r.eq(Cat(blank_r[1:], vga_output.blank)),
            hs_r.eq(   Cat(hs_r[1:],    vga_output.hs)),
            vs_r.eq(   Cat(vs_r[1:],    vga_output.vs)),
        ]

        m.submodules.vga2dvid = VGA2DVID(
            in_r = self.r,
            in_g = self.g,
            in_b = self.b,
            in_blank = blank_r[0],
            in_hsync = hs_r[0],
            in_vsync = vs_r[0],
            in_c1 = Const(0, 2),
            in_c2 = Const(0, 2),
            out_r = pixel_r,
            out_g = pixel_g,
            out_b = pixel_b,
            out_clock = pixel_clk,
            xdr=xdr
        )




        # Store output bits in separate registers
        #
        # Also invert signals based on parameters
        pixel_clk_r = Signal(xdr)
        pixel_r_r = Signal(xdr)
        pixel_g_r = Signal(xdr)
        pixel_b_r = Signal(xdr)
        m.d.shift += pixel_clk_r.eq(pixel_clk)
        m.d.shift += pixel_r_r.eq(pixel_r)
        m.d.shift += pixel_g_r.eq(pixel_g)
        m.d.shift += pixel_b_r.eq(pixel_b)

        if xdr == 1:
            m.d.comb += [
                self.dvid_out_clk.eq(pixel_clk_r[0]),
                self.dvid_out.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
            ]
        elif xdr == 2 and emulate_ddr == True:
            m.d.comb += [
                self.dvid_out_clk.eq(Mux(
                    ClockSignal("shift"),
                    pixel_clk_r[0],
                    pixel_clk_r[1]
                )),

                self.dvid_out.eq(Mux(
                    ClockSignal("shift"),
                    Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0]),
                    Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])
                ))
            ]
        elif xdr == 2 and emulate_ddr == False:
            m.d.comb += [
                self.dvid_out_clk.o_clk.eq(ClockSignal("shift")),
                self.dvid_out_clk.o0.eq(pixel_clk_r[0]),
                self.dvid_out_clk.o1.eq(pixel_clk_r[1]),

                self.dvid_out.o_clk.eq(ClockSignal("shift")),
                self.dvid_out.o0.eq(Cat(pixel_b_r[0], pixel_g_r[0], pixel_r_r[0])),
                self.dvid_out.o1.eq(Cat(pixel_b_r[1], pixel_g_r[1], pixel_r_r[1])),
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

}

class GFXDemo(Elaboratable):
    '''
    Clock domains:
    sync:   25 MHz
    shift: 125 MHz
    '''
    def __init__(self, dvid_out, dvid_out_clk, pdm_out, vga_parameters, xdr, emulate_ddr, base_addr=0x3000_0000):
        self.dvid_out = dvid_out
        self.dvid_out_clk = dvid_out_clk
        self.pdm_out = pdm_out
        self.vga_parameters = vga_parameters
        self.xdr = xdr
        self.emulate_ddr = emulate_ddr
        self.base_addr = base_addr

        self.irq = Signal(2)
        self.irq_en = Signal(1)
        self.pdm_in = Signal(16)

        addr_width = 32
        data_width = 32
        granularity = 32

        layout = [
            ("adr",   addr_width, Direction.FANOUT),
            ("dat_w", data_width, Direction.FANOUT),
            ("dat_r", data_width, Direction.FANIN),
            ("sel",   data_width // granularity, Direction.FANOUT),
            ("cyc",   1, Direction.FANOUT),
            ("stb",   1, Direction.FANOUT),
            ("we",    1, Direction.FANOUT),
            ("ack",   1, Direction.FANIN),
        ]

        self.wb = Record(layout=layout)

    def elaborate(self, platform):

        wb = self.wb
        base_addr = self.base_addr

        m = Module()

        # First order "sigma-delta"
        pdm = Signal(len(self.pdm_in) + 1)
        m.d.sync += pdm.eq(pdm[:-1] + self.pdm_in)
        m.d.comb += self.pdm_out.eq(pdm[-1])

        # Graphics

        r = Signal(8)
        g = Signal(8)
        b = Signal(8)

        m.submodules.dvid_signal_generator = dvid = DVIDSignalGeneratorXDR(
            dvid_out_clk=self.dvid_out_clk,
            dvid_out=self.dvid_out,
            r=r,
            g=g,
            b=b,
            vga_parameters=self.vga_parameters,
            xdr=self.xdr,
            emulate_ddr=self.emulate_ddr)

        m.submodules.rotozoom = rotozoom = RotozoomImageGenerator(
            vsync=dvid.vga_output.vs,
            h_ctr=dvid.vga.h_ctr,
            v_ctr=dvid.vga.v_ctr,
            r=r,
            g=g,
            b=b,
            width=self.vga_parameters.h_active,
            height=self.vga_parameters.v_active)

        # Only assert IRQ if IRQ is enabled
        with m.If(self.irq_en):
            m.d.comb += self.irq.eq(Cat(
                (dvid.vga.h_ctr == 0),
                (dvid.vga.v_ctr == 0)
            ))

        m.submodules.wrapper = wrapper = BusWrapper(
            signals_w=[
                self.irq_en,
                rotozoom.intensity,
                self.pdm_in,
                g,
                b,
            ],
        )

        # print(wrapper)

        m.d.comb += wrapper.cs.eq(0)
        m.d.comb += wrapper.we.eq(wb.we)
        m.d.comb += wrapper.addr.eq(wb.adr[2:8])

        ack_r = Signal()

        with m.If(wb.stb & wb.cyc & (wb.adr[8:] == (base_addr >> 8))):
            m.d.comb += wrapper.cs.eq(1)
            m.d.comb += wb.dat_r.eq(wrapper.read_data)
            m.d.comb += wrapper.write_data.eq(wb.dat_w)
            m.d.sync += wb.ack.eq(ack_r)
            m.d.sync += ack_r.eq(0)
        with m.Else():
            m.d.sync += ack_r.eq(1)

        return m

class GFXDemoApplet(Applet, applet_name="gfxdemo"):
    help = "Graphics demo"
    description = """

    """

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--xdr", default=1, type=int, choices=[1, 2, 4],
            help="sdr=1, ddr=2, ddrx2=4")

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
 
        xdr = self.xdr
 
        m = Module()

        # PMOD2 pinout:
        # CLK B1/B2
        # D0  C1/C2 (b)
        # D1  E2/D1 (g)  inverted
        # D2  G2/F1 (r)  inverted

        platform.add_resources([
            Resource("pmod2", 0, Pins("C1  E2  G2", dir="o"),
                    Attrs(IO_TYPE="LVCMOS33")),
            Resource("pmod2_neg", 0, Pins("C2  D1  F1", dir="o"),
                    Attrs(IO_TYPE="LVCMOS33")),
            Resource("pmod2_clk", 0, Pins("B1", dir="o"),
                    Attrs(IO_TYPE="LVCMOS33")),
            Resource("pmod2_clk_neg", 0, Pins("B2", dir="o"),
                    Attrs(IO_TYPE="LVCMOS33")),
        ])

        dvid_config = dvid_configs[self.dvid_config]

        self.pll1_freq_mhz = dvid_config.pll1_freq_mhz
        self.pixel_freq_mhz = dvid_config.pixel_freq_mhz

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

        m.submodules.pll2 = ECP5PLL(
            pll_config,
            clock_signal_name="clk_pll1",
            clock_signal_freq=self.pll1_freq_mhz * 1e6,
            skip_checks=self.skip_pll_checks)

        # Force xdr=0 and emulate ddr to be closer to the asic setup
        dvid_out_clk = platform.request("pmod2_clk", 0, xdr=0)
        dvid_out_clk_neg = platform.request("pmod2_clk_neg", 0, xdr=0)
        dvid_out = platform.request("pmod2", 0, xdr=0)
        dvid_out_neg = platform.request("pmod2_neg", 0, xdr=0)

        pmod1 = platform.request("pmod", dir="o")

        m.d.comb += [
            dvid_out_clk_neg.eq(~dvid_out_clk),
            dvid_out_neg.eq(~dvid_out),
        ]

        m.submodules.gfxdemo = gfxdemo = GFXDemo(
            dvid_out=dvid_out,
            dvid_out_clk=dvid_out_clk,
            pdm_out=pmod1,
            vga_parameters=dvid_config.vga_parameters,
            xdr=xdr,
            emulate_ddr=True)

        from itertools import chain
        m.submodules.buscontroller = buscontroller = BusController(
            bus=gfxdemo.wb,
            irq=gfxdemo.irq,
            program=[
                # Enable interrupts
                Asm.MOV_R0(1),
                Asm.WRITE_R0(0x3000_0000),

                Asm.WFI(0b11),
                Asm.MOV_R0(0x3000_0004),
                Asm.WRITE_IMM(0x1),

                # Asm.WFI(0b01),
                # Asm.MOV_R0(0x3000_0004),
                # Asm.WRITE_IMM(0x80),

                *chain(*[[Asm.WFI(0b01), Asm.WRITE_IMM(i)] for i in range(255)]),
                Asm.WRITE_IMM(0xff),


                # 5
                #Asm.WFI(0b01),
                #Asm.ADD_R0(0x1),
                #Asm.WRITE(0x3000_0004),
                #Asm.JMP(5),


                # Asm.WRITE(0x3000_0004, 0xff),


                # Green row
                Asm.MOV_R0(0x3000_000C),
                Asm.WFI(0b01),
                *[Asm.WRITE_IMM(255 if i&1 else 0) for i in range(256)],
                Asm.WRITE_IMM(0),

                # Asm.WFI(0b01),
                # *[Asm.WRITE(0x3000_000C, i) for i in range(255)],
                # Asm.WRITE(0x3000_000C, 0),

                # Asm.WRITE(0x3000_0004, 0xff),
                Asm.JMP(0),
            ]
        )

        return m


#####################


class DVIDTest(FHDLTestCase):
    '''
    TODO: Write actual test cases. These are just to generate waveforms to analyze.
    '''
    def test_dvid(self):

        sync = ClockDomain()
        pixel = ClockDomain()
        m = Module()
        m.domains += sync, pixel

        dvid_config = dvid_configs["640x480p60"]

        dvid_out = Signal(3)
        dvid_out_clk = Signal(1)
        pdm_out = Signal(1)

        m.submodules.gfxdemo = gfxdemo = GFXDemo(
            dvid_out=dvid_out,
            dvid_out_clk=dvid_out_clk,
            pdm_out=pdm_out,
            vga_parameters=dvid_config.vga_parameters,
            xdr=2,
            emulate_ddr=True)


        from itertools import chain
        m.submodules.buscontroller = buscontroller = BusController(
            bus=gfxdemo.wb,
            irq=gfxdemo.irq,
            program=[
                Asm.NOP(),

                Asm.MOV_R0(1),
                Asm.WRITE_R0(0x3000_0000),

                Asm.WFI(0b11),
                Asm.MOV_R0(0x3000_0004),
                Asm.WRITE_IMM(0x40),

                Asm.WFI(0b01),
                Asm.MOV_R0(0x3000_0004),
                Asm.WRITE_IMM(0x80),

                Asm.JMP(0),
            ]
        )

        sim = Simulator(m)
        sim.add_clock(period=1/25e6, domain="sync")
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
            vga_parameters=dvid_configs["640x480p60"].vga_parameters,
        )

        vs = vga_output.vs
        v_en = m.submodules.vga.v_en
        h_en = m.submodules.vga.h_en

        m.submodules += GameOfLifeGenerator(
            r=r,
            g=g,
            b=b,
            vsync=vga_output.vs,
            vga=m.submodules.vga,
        )

        # Delay vga signals with 2 cycles
        h_en_r = Signal(2)
        v_en_r = Signal(2)
        m.d.sync += [
            h_en_r.eq(Cat(h_en_r[1:], h_en)),
            v_en_r.eq(Cat(v_en_r[1:], v_en)),
        ]

        # Workaround for CXXRTL bug. (Can't set i_hen=h_en_r[0])
        h_en_r_lsb = Signal()
        v_en_r_lsb = Signal()
        m.d.comb += [
            h_en_r_lsb.eq(h_en_r[0]),
            v_en_r_lsb.eq(v_en_r[0]),
        ]

        m.submodules.vga_phy = Instance("vga_phy",
            p_width=640,
            p_height=480,
            i_clk=ClockSignal(),
            i_hen=h_en_r_lsb,
            i_ven=v_en_r_lsb,
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

    void reset () override {
    }
    
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
