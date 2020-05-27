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

    Audio samples from a file can be loaded using the --file and
    --file-sample-rate arguments. Convert an audio file to raw
    samples first, e.g:
      sox audio.wav --bits 8 --encoding signed-integer out.raw
      python -m pergola run radio-tx --file out.raw

    Disclaimer: This should only be used in a controlled and shielded
                RF environment.

    """

    @classmethod
    def add_run_arguments(cls, parser):
        parser.add_argument(
            "--freq", default=440, type=int,
            help="Frequency of the generated tone (Hz)")

        parser.add_argument(
            "--file", type=str,
            help="File with audio samples")

        parser.add_argument(
            "--file-sample-rate", default=22050, type=int,
            help="Sample rate of the audio file")

    def __init__(self, args):
        self.freq = args.freq
        self.file = args.file
        self.file_sample_rate = args.file_sample_rate

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

        # First order "sigma-delta" @ 16MHz (sync_clk_freq)
        pdm_in = Signal(8)
        pdm = Signal(pdm_in.shape().width + 1)
        m.d.sync += pdm.eq(pdm[:-1] + pdm_in)

        if self.file:
            samples_raw = [(128 + x) % 256 for x in open(self.file, "rb").read()]
            samples = Memory(width=8, depth=len(samples_raw), init=samples_raw)
            m.submodules.samp_rd = samp_rd = samples.read_port(domain="sync", transparent=False)
            samp_rate = self.file_sample_rate
            audio_ctr = Signal(range(len(samples_raw)))
            m.d.comb += pdm_in.eq(samp_rd.data)
            m.d.comb += samp_rd.addr.eq(audio_ctr)
            audio_ctr_increment = 1
        else:
            # This can be done 4x better, but I'm lazy
            sintable_size = 4096
            sintable = Memory(width=8, depth=sintable_size, init= \
                [int(127 + 127 * math.sin(x * math.pi * 2. / sintable_size)) for x in range(sintable_size)])
            m.submodules.sin_rd = sin_rd = sintable.read_port(domain="sync", transparent=False)

            # Fixed point, N.8 bits, to increase precision in the target frequency
            audio_ctr = Signal(range(sintable_size << 8))

            # Generate audio samples with a lower sample rate than the pdm
            samp_rate = 100e3

            m.d.comb += pdm_in.eq(sin_rd.data)
            m.d.comb += sin_rd.addr.eq(audio_ctr[8:])

            audio_ctr_increment = int((self.freq / (samp_rate / sintable_size)) * 2**8)

        samp_rate_factor = int(sync_clk_freq / samp_rate)
        ctr = Signal(range(samp_rate_factor + 1))
        m.d.sync += ctr.eq(ctr + 1)

        with m.If(ctr == samp_rate_factor):
            m.d.sync += ctr.eq(0)
            m.d.sync += audio_ctr.eq(audio_ctr + audio_ctr_increment)

        m.d.comb += pmod2.eq(ClockSignal("clk_rf") & pdm[-1] & btn)

        return m
