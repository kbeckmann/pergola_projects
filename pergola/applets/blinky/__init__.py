from nmigen import *
from nmigen.back.pysim import Active
from .. import Applet


class BlinkyImpl(Elaboratable):
    description = "Blinks some LEDs"
    help = "Blinks some LEDs"

    def __init__(self, led, btn):
        self.led = led
        self.btn = btn
        self.blink = Signal()
        self.timer = Signal(24)

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.timer.eq(self.timer + 1)
        m.d.comb += self.led.o.eq(self.blink)

        with m.If(self.btn):
            m.d.comb += self.blink.eq(1)
        with m.Else():
            m.d.comb += self.blink.eq(self.timer[-1])

        return m


class BlinkyTest(Elaboratable):
    def __init__(self, args):
        pass

    def elaborate(self, platform):
        from nmigen.compat.fhdl.specials import TSTriple
        led = TSTriple()
        btn = Signal()

        m = Module()

        self.tm = BlinkyImpl(led, btn)
        m.submodules.blinky = self.tm

        return m

    def testbench(self, sim):
        sim.add_clock(1e-6)

        def loopback_proc():
            yield Active()
            assert (yield self.tm.timer) == 0
            yield
            assert (yield self.tm.timer) == 1
            yield
            assert (yield self.tm.timer) == 2
            yield
            assert (yield self.tm.timer) == 3
            yield

        sim.add_sync_process(loopback_proc)


class Blinky(Applet, applet_name="blinky"):
    description = "Blinks some LEDs"
    help = "Blinks some LEDs"
    test_class = BlinkyTest

    def __init__(self, args):
        pass

    def elaborate(self, platform):
        led = platform.request("led", 0)
        btn = platform.request("button", 0)

        m = Module()

        m.submodules.blinky = BlinkyImpl(led, btn)

        return m
