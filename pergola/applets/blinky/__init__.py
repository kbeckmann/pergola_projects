from nmigen import *
from nmigen.back.pysim import Simulator, Active
from nmigen.back import cxxrtl
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *

from .. import Applet


class Blinky(Elaboratable):
    def __init__(self, led, btn, timer_width=24):
        self.led = led
        self.btn = btn
        self.timer = Signal(timer_width)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)

        with m.If(self.btn):
            m.d.comb += self.led.eq(1)
        with m.Else():
            m.d.comb += self.led.eq(self.timer[-1])

        return m


class BlinkyTest(FHDLTestCase):
    def test_blinky(self):
        btn = Signal()
        led = Signal()
        m = Module()
        blinky = m.submodules.blinky = Blinky(led, btn)

        sim = Simulator(m)
        sim.add_clock(1e-6)
        def process():
            yield Active()
            assert (yield blinky.timer) == 0
            yield
            assert (yield blinky.timer) == 1
            yield
            assert (yield blinky.timer) == 2
            yield
            assert (yield blinky.timer) == 3
            yield

        sim.add_sync_process(process)
        with sim.write_vcd("blinky.vcd"):
            sim.run()

    def test_blinky_formal(self):
        btn = Signal()
        led = Signal()

        m = Module()
        m.submodules.blinky = Blinky(led, btn)

        # If the button is pressed, the led should always be on
        m.d.comb += Assert(btn.implies(led))

        self.assertFormal(m, depth=10)

class BlinkySim(FHDLTestCase):
    def test_blinky_cxxrtl(self):

        import os
        import subprocess

        led = Signal()
        btn = Signal()

        m = Module()
        m.submodules.blinky = Blinky(led, btn, 2)

        # output, mapping = cxxrtl.convert_fragment(Fragment.get(m, None).prepare())
        # print(mapping)
        output = cxxrtl.convert(m, ports=(led, btn, m.submodules.blinky.timer))

        root = os.path.join("build")
        if not os.path.exists(root):
            os.mkdir("build")

        filename = os.path.join(root, "top.cpp")
        elfname = os.path.join(root, "top.elf")

        with open(filename, "w") as f:
            f.write(output)
            f.write('''

#include <iostream>
#include <fstream>
#include <backends/cxxrtl/cxxrtl_vcd.h>

int main(int argc, char *argv[])
{
    cxxrtl_design::p_top top;

    vcd_writer w;

    if (argc != 2) {
        std::cout << "Usage: " << argv[0] << " out.vcd" << std::endl;
        return 1;
    }

    debug_items items;
    top.debug_info(items);
    w.add(items);

    std::cout << "timer" << "	" << "btn" << "	" << "led" << std::endl;
    for (int i=0; i < 16; i++) {

        if (i >= 8) {
            top.p_btn = value<1>{1u};
        }

        top.step();
        top.p_clk = value<1>{0u};
        top.step();
        top.p_clk = value<1>{1u};

        std::cout << top.p_timer << "	" << top.p_btn << "	" << top.p_led << std::endl;
        w.sample(i);
    }

    std::cout << "Writing " << argv[1] << std::endl;
    std::ofstream outfile (argv[1]);

    outfile << w.buffer;

    outfile.close();

    return 0;
}''')
            f.close()

        print(subprocess.check_call([
            "clang++", "-I", "/usr/share/yosys/include",
            "-O3", "-std=c++11", "-o", elfname, filename]))

        print(subprocess.check_call([elfname, "build/top.vcd"]))


class BlinkyApplet(Applet, applet_name="blinky"):
    description = "Blinks some LEDs"
    help = "Blinks some LEDs"

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        led = platform.request("led", 0)
        btn = platform.request("button", 0)

        m = Module()

        m.submodules.blinky = Blinky(led.o, btn)

        return m
