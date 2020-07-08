from nmigen import *
from nmigen.lib.cdc import *
from .tmds import TMDSEncoder, TMDSDecoder
from ..util.test import FHDLTestCase


class DVID2VGA(Elaboratable):
    """
    Inputs are in the `shift` domain

    in_d0:     TMDS encoded xdr-bit input for d0
    in_d1:     TMDS encoded xdr-bit input for d1
    in_d2:     TMDS encoded xdr-bit input for d2

    Outputs are in the `sync` domain

    out_r:     8-bit red pixel value
    out_g:     8-bit Green pixel value
    out_b:     8-bit Blue pixel value

    out_de0:   Data-enable 0, acts as blanking signal
    out_hsync: Horizontal sync signal
    out_vsync: Vertical sync signal

    out_de1:  Data-enable 1
    out_ctl0: CTL0
    out_ctl1: CTL1

    out_de2:  Data-enable 2
    out_ctl2: CTL2
    out_ctl3: CTL3

    xdr:       Data rate. SDR=1, DDR=2, QDR=4

    Clock domains
    sync:      Pixel clock
    shift:     TMDS output shift clock, multiplier of pixel clock: SDR=10x, DDR=5x, QDR=2.5x
    """


    def __init__(self, in_d0, in_d1, in_d2, out_r, out_g, out_b, out_de0, out_hsync, out_vsync,
                 out_de1, out_ctl0, out_ctl1, out_de2, out_ctl2, out_ctl3, xdr=1):
        assert(len(in_d0) == xdr)
        assert(len(in_d1) == xdr)
        assert(len(in_d2) == xdr)

        assert(len(out_r) == 8)
        assert(len(out_g) == 8)
        assert(len(out_b) == 8)

        self.in_d0 = in_d0
        self.in_d1 = in_d1
        self.in_d2 = in_d2

        self.out_r = out_r
        self.out_g = out_g
        self.out_b = out_b
        self.out_de0 = out_de0
        self.out_hsync = out_hsync
        self.out_vsync = out_vsync
        self.out_de1 = out_de1
        self.out_ctl0 = out_ctl0
        self.out_ctl1 = out_ctl1
        self.out_de2 = out_de2
        self.out_ctl2 = out_ctl2
        self.out_ctl3 = out_ctl3

        self.xdr = xdr

        self.d0_full = Signal(20)
        self.d0_offset = Signal(4)
        self.d0_offset_ctr = Signal(16, reset=2**12-1)
        self.d0 = Signal(10)
        self.d0_r = Signal(10)

    def elaborate(self, platform):
        in_d0 = self.in_d0
        in_d1 = self.in_d1
        in_d2 = self.in_d2

        xdr = self.xdr

        m = Module()

        d0_full = self.d0_full
        d0_offset = self.d0_offset
        d0_offset_ctr = self.d0_offset_ctr
        d0 = self.d0
        d0_r = self.d0_r

        # sync -> shift domain
        d0_offset_shift = Signal(4)

        d1_full = Signal(20)
        # d1_offset = Signal(4)
        d1 = Signal(10)
        d1_r = Signal(10)

        d2_full = Signal(20)
        # d2_offset = Signal(4)
        d2 = Signal(10)
        d2_r = Signal(10)

        m.d.shift += d0_full.eq(Cat(d0_full[xdr:], in_d0))
        m.d.shift += d1_full.eq(Cat(d1_full[xdr:], in_d1))
        m.d.shift += d2_full.eq(Cat(d2_full[xdr:], in_d2))

        for (sig, sig_full, sig_offset) in [
            (d0, d0_full, d0_offset_shift),
            (d1, d1_full, d0_offset_shift),   # TODO: Individual phase alignment
            (d2, d2_full, d0_offset_shift)]:  # TODO: Individual phase alignment
            with m.Switch(sig_offset):
                for i in range(10):
                    with m.Case(i):
                        m.d.comb += sig.eq(sig_full[i:10+i])
                with m.Case():
                    m.d.comb += sig.eq(sig_full[0:10])

        d0_r_r = Signal(10)
        d1_r_r = Signal(10)
        d2_r_r = Signal(10)
        m.submodules += FFSynchronizer(d0, d0_r, o_domain="shift")
        m.submodules += FFSynchronizer(d1, d1_r, o_domain="shift")
        m.submodules += FFSynchronizer(d2, d2_r, o_domain="shift")

        # shift -> sync (10x !)
        m.submodules += FFSynchronizer(d0_r, d0_r_r)
        m.submodules += FFSynchronizer(d1_r, d1_r_r)
        m.submodules += FFSynchronizer(d2_r, d2_r_r)

        m.submodules.tmds_dec_d0 = TMDSDecoder(d0_r_r, self.out_b, Cat(self.out_hsync, self.out_vsync), self.out_de0)
        m.submodules.tmds_dec_d1 = TMDSDecoder(d1_r_r, self.out_g, Cat(self.out_ctl0,  self.out_ctl1),  self.out_de1)
        m.submodules.tmds_dec_d2 = TMDSDecoder(d2_r_r, self.out_r, Cat(self.out_ctl2,  self.out_ctl3),  self.out_de2)

        # Recover the signal by searching for two (pixel-)clock cycles
        # of ~de0 (any sync word on d0)
        de0_r = Signal()
        m.d.sync += de0_r.eq(self.out_de0)
        with m.If(self.out_de0):
            m.d.sync += d0_offset_ctr.eq(d0_offset_ctr - 1)
        with m.Elif(~de0_r & ~self.out_de0):
            m.d.sync += d0_offset_ctr.eq(2**12 - 1)

        with m.If(d0_offset_ctr == 0):
            # No sync found in 4095 cycles. Slip one bit.
            m.d.sync += d0_offset_ctr.eq(2**12 - 1)
            with m.If(d0_offset == 9):
                m.d.sync += d0_offset.eq(0)
            with m.Else():
                m.d.sync += d0_offset.eq(d0_offset + 1)

        # Move to shift cd safely
        m.submodules += FFSynchronizer(d0_offset, d0_offset_shift)

        return m


from .vga import VGAParameters, VGAOutputSubtarget
from .vga2dvid import VGA2DVID
from .vga_testimage import TestImageGenerator
from nmigen.back import cxxrtl

class DVID2VGATest(FHDLTestCase):

    vga_configs = {
        "640x480p60": VGAParameters(
                h_front=16,
                h_sync=96,
                h_back=44,
                h_active=640,
                v_front=10,
                v_sync=2,
                v_back=31,
                v_active=480,
            ),
    }


    def test_dvid2vga_cxxrtl(self):

        import os
        import subprocess

        m = Module()

        vga_output = Record([
            ('hs', 1),
            ('vs', 1),
            ('blank', 1),
        ])

        src_r = Signal(8)
        src_g = Signal(8)
        src_b = Signal(8)

        # Generate vga hsync/vsync/blank signals
        m.submodules.vga = VGAOutputSubtarget(
            output=vga_output,
            vga_parameters=self.vga_configs["640x480p60"],
        )

        vs = vga_output.vs
        v_en = m.submodules.vga.v_en
        h_en = m.submodules.vga.h_en

        # Generate vga test image
        m.submodules.imagegen = TestImageGenerator(
            vsync=vga_output.vs,
            h_ctr=m.submodules.vga.h_ctr,
            v_ctr=m.submodules.vga.v_ctr,
            r=src_r,
            g=src_g,
            b=src_b,
            speed=0)

        xdr = 1

        tmds_d0 = Signal(xdr)
        tmds_d1 = Signal(xdr)
        tmds_d2 = Signal(xdr)
        tmds_clk = Signal(xdr)

        # Convert vga signal to DVID TMDS signals
        m.submodules.vga2dvid = vga2dvid = VGA2DVID(
            in_r = src_r,
            in_g = src_g,
            in_b = src_b,
            in_blank = vga_output.blank,
            in_hsync = vga_output.hs,
            in_vsync = vga_output.vs,
            in_c1=Signal(2),
            in_c2=Signal(2),
            out_r = tmds_d2,
            out_g = tmds_d1,
            out_b = tmds_d0,
            out_clock = tmds_clk,
            xdr=xdr
        )

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
            in_d0=tmds_d0,
            in_d1=tmds_d1,
            in_d2=tmds_d2,

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

            xdr=xdr,
        )

        decoded_hsync_r = Signal()
        decoded_vsync_r = Signal()
        decoded_hen = Signal()
        decoded_ven = Signal()

        m.d.sync += decoded_hsync_r.eq(decoded_hsync)
        m.d.sync += decoded_vsync_r.eq(decoded_vsync)

        with m.If(~decoded_hsync_r & decoded_hsync):
            m.d.sync += decoded_hen.eq(0)
        with m.Elif(decoded_hsync_r & ~decoded_hsync):
            m.d.sync += decoded_hen.eq(1)

        with m.If(~decoded_vsync_r & decoded_vsync):
            m.d.sync += decoded_ven.eq(0)
        with m.Elif(decoded_vsync_r & ~decoded_vsync):
            m.d.sync += decoded_ven.eq(1)


        # Show decoded vga signals in SDL window
        m.submodules.vga_phy = Instance("vga_phy",
            p_width=640,
            p_height=480,
            i_clk=ClockSignal(),
            i_hen=decoded_hen & decoded_de0,
            i_ven=decoded_ven & decoded_de0,
            i_r=decoded_r,
            i_g=decoded_g,
            i_b=decoded_b)

        output = cxxrtl.convert(m, 
                                ports=(
                                    decoded_de0,
                                    decoded_hsync,
                                    decoded_vsync,
                                    dvid2vga.d0_full,
                                    dvid2vga.d0_offset,
                                    dvid2vga.d0_offset_ctr,
                                    dvid2vga.d0,
                                    dvid2vga.d0_r
                                ),
                                black_boxes={"vga_phy": r"""
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
            std::cout << "Frame " << frames << std::endl;
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
            for (unsigned i = 0; i < 5; i++) {
                top.p_shift__clk.set<uint32_t>(0);
                top.step();
                if (argc == 2)
                    w.sample(globalTime++);

                top.p_shift__clk.set<uint32_t>(1);
                if (i < 5) {
                    top.step();
                    if (argc == 2)
                        w.sample(globalTime++);
                }
            }

            top.p_clk.set<uint32_t>(0);
            top.step();
            if (argc == 2)
                w.sample(globalTime++);

            for (unsigned i = 0; i < 5; i++) {
                top.p_shift__clk.set<uint32_t>(0);
                top.step();
                if (argc == 2)
                    w.sample(globalTime++);

                top.p_shift__clk.set<uint32_t>(1);
                if (i < 5) {
                    top.step();
                    if (argc == 2)
                        w.sample(globalTime++);
                }
            }

            top.p_clk.set<uint32_t>(1);
            top.step();
            if (argc == 2)
                w.sample(globalTime++);
        }

        //break; // TODO: Remove

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
            # "clang++", "-I", "/usr/share/yosys/include",
            "clang++", "-I", "/home/konrad/dev/yosys",
            "-ggdb", "-O3", "-fno-exceptions", "-std=c++11", "-lSDL2", "-o", elfname, filename]))

        print(subprocess.check_call([elfname, "build/top.vcd"]))
