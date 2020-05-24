from nmigen import *
from nmigen.back.pysim import Simulator, Active
from nmigen.test.utils import FHDLTestCase
from nmigen.asserts import *

import math

from .. import Applet
from ...util.ecp5pll import ECP5PLL, ECP5PLLConfig


class RadioTXApplet(Applet, applet_name="radio-tx"):
    help = "AM Radio TX"
    description = """

    Generates a carrier frequency close to 434MHz using the PLLs and
    modulates the power with a frequency, making it an AM transmitter.

    Disclaimer: This should only be used in a controlled and shielded
                RF environment.

    """

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--freq", default=440, type=int,
            help="Frequency of the generated tone (Hz)")

    def __init__(self, args):
        self.freq = args.freq

    def elaborate(self, platform):
        led = platform.request("led", 0)
        btn = platform.request("button", 0)

        pmod2 = platform.request("pmod", 1, dir="o")

        m = Module()

        pll1_freq_mhz = 147.2
        carrier_freq_mhz = 434

        sync_clk_freq = platform.lookup(platform.default_clk).clock.frequency

        m.submodules.pll1 = ECP5PLL([
                ECP5PLLConfig("clk_pll1", pll1_freq_mhz, error=0.0001),
            ],
            clock_signal_name="sync",
            clock_signal_freq=sync_clk_freq
        )

        m.submodules.pll2 = ECP5PLL([
                ECP5PLLConfig("clk_rf", carrier_freq_mhz, error=1),
            ],
            clock_signal_name="clk_pll1",
            clock_signal_freq=pll1_freq_mhz * 1e6
        )

        # This can be done 4x better, but I'm lazy
        sintable_size = 4096
        sintable = Memory(width=8, depth=sintable_size, init= \
            [int(127 + 127 * math.sin(x * math.pi * 2. / sintable_size)) for x in range(sintable_size)])
        m.submodules.sin_rd = sin_rd = sintable.read_port(domain="sync", transparent=False)

        # First order "sigma-delta" @ 16MHz (sync_clk_freq)
        pdm_in = Signal(8)
        pdm = Signal(9)
        m.d.sync += pdm.eq(pdm[:8] + pdm_in)

        # Generate audio samples with a lower sample rate than the pdm
        samp_rate = 100e3
        samp_rate_factor = int(sync_clk_freq / samp_rate)

        ctr = Signal(range(samp_rate_factor + 1))
        m.d.sync += ctr.eq(ctr + 1)

        # Fixed point, N.8 bits, to increase precision in the target frequency
        audio_ctr = Signal(range(sintable_size << 8))

        m.d.comb += pdm_in.eq(sin_rd.data)
        m.d.comb += sin_rd.addr.eq(audio_ctr[8:])

        with m.If(ctr == samp_rate_factor):
            m.d.sync += ctr.eq(0)
            m.d.sync += audio_ctr.eq(audio_ctr + \
                int((self.freq / (samp_rate / sintable_size)) * 2**8))

        m.d.comb += pmod2.eq(ClockSignal("clk_rf") & pdm[-1] & btn)

        return m
