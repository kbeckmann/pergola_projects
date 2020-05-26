from nmigen import *
from sys import float_info
from math import fabs

"""
ECP5 PLL generator

Based on the tool ecppll in Project Trellis
https://github.com/SymbiFlow/prjtrellis/blob/master/libtrellis/tools/ecppll.cpp
which has the following license:

Copyright (C) 2018  The Project Trellis Authors. All rights reserved.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


Some inspiration comes from the Luna project
https://github.com/greatscottgadgets/luna/blob/master/luna/gateware/architecture/car.py
with the following license:

BSD 3-Clause License

Copyright (c) Katherine J. Temkin <ktemkin@greatscottgadgets.com>
Copyright (c) 2019, Great Scott Gadgets <info@greatscottgadgets.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

import logging
logger = logging.getLogger(__name__)

class ECP5PLLConfig():
    def __init__(self, cd_name, freq, phase=0, error=0):
        """
        Parameters:
            cd_name: Name of the clock domain
            freq:    Requested frequency
            phase:   Requested phase (not available on CLKOP)
            error:   Acceptable frequency error
        """
        self.cd_name = cd_name
        self.freq = freq
        self.phase = phase
        self.error = error

    def __repr__(self):
        return "(ECP5PLLConfig {} {} {} {})".format(self.cd_name, self.freq, self.phase, self.error)


class ECP5PLL(Elaboratable):
    INPUT_MIN = 8.0
    INPUT_MAX = 400.0
    OUTPUT_MIN = 10.0
    OUTPUT_MAX = 400.0
    PFD_MIN = 3.125
    PFD_MAX = 400.0
    VCO_MIN = 400.0
    VCO_MAX = 800.0

    def __init__(self, clock_config=None, clock_signal_name=None, clock_signal_freq=None, skip_checks=False):
        """
        Parameters:
            clock_config:      Array of ECP5PLLConfig objects. Must have 1 to 4 elements.
            clock_signal_name: Input clock signal name. Uses default clock if not specified.
            skip_checks:       Skips limit checks and allows out-of-spec usage
        """
        self.clock_name = clock_signal_name
        self.clock_signal_freq = clock_signal_freq

        assert(1 <= len(clock_config) <= 4)
        assert(clock_config[0].phase == 0)

        self.clock_config = clock_config.copy()
        self.skip_checks = skip_checks

    def calc_pll_params(self, input, output):
        if (not self.INPUT_MIN <= input <= self.INPUT_MAX):
            logger.warning("Input clock violates frequency range: {} <= {:.3f} <= {}".format(
                self.INPUT_MIN, freq, self.INPUT_MAX))

        params = {}
        error = float_info.max

        for input_div in range(1, 129):
            fpfd = input / input_div
            if fpfd < self.PFD_MIN or fpfd > self.PFD_MAX:
                continue

            for feedback_div in range(1, 81):
                for output_div in range(1, 129):
                    fvco = fpfd * feedback_div * output_div

                    if not self.skip_checks and (fvco < self.VCO_MIN or fvco > self.VCO_MAX):
                        continue

                    freq = fvco / output_div
                    if (fabs(freq - output) < error or \
                        (fabs(freq - output) == error and \
                        fabs(fvco - 600) < fabs(params["fvco"] - 600))):

                        error = fabs(freq - output)
                        params["refclk_div"] = input_div
                        params["feedback_div"] = feedback_div
                        params["output_div"] = output_div
                        params["freq"] = freq
                        params["freq_requested"] = output
                        params["fvco"] = fvco
                        # shift the primary by 180 degrees. Lattice seems to do this
                        ns_phase = 1.0 / (freq * 1e6) * 0.5
                        params["primary_cphase"] = ns_phase * (fvco * 1e6)

        if not self.skip_checks:
            assert(self.OUTPUT_MIN <= freq <= self.OUTPUT_MAX)

        params["secondary"] = [{
            "div": 0,
            "freq": 0,
            "freq_requested": 0,
            "phase": 0,
            "cphase": 0,
            "fphase": 0,
            "enabled": False,
            "error": 0,
            }]*3
        params["error"] = error
        return params

    def generate_secondary_output(self, params, channel, output, phase):
        div = int(0.5 + params["fvco"] / output)
        freq = params["fvco"] / div

        ns_shift = 1.0 / (freq * 1e6) * phase /  360.0
        phase_count = ns_shift * (params["fvco"] * 1e6)
        cphase = int(0.5 + phase_count)
        fphase = int(0.5 + (phase_count - cphase) * 8)

        ns_actual = 1.0 / (params["fvco"] * 1e6) * (cphase + fphase / 8.0)
        phase_shift = 360 * ns_actual / (1.0 / (freq * 1e6))

        params["secondary"][channel] = {}
        params["secondary"][channel]["enabled"] = True
        params["secondary"][channel]["div"] = div
        params["secondary"][channel]["freq"] = freq
        params["secondary"][channel]["freq_requested"] = output
        params["secondary"][channel]["phase"] = phase_shift
        params["secondary"][channel]["cphase"] = cphase + params["primary_cphase"]
        params["secondary"][channel]["fphase"] = fphase
        params["secondary"][channel]["error"] = fabs(freq - output)

        if (not self.OUTPUT_MIN <= freq <= self.OUTPUT_MAX):
            logger.warning("ClockDomain {} violates frequency range: {} <= {:.3f} <= {}".format(
                self.clock_config[channel + 1].cd_name, self.OUTPUT_MIN, freq, self.OUTPUT_MAX))


    def elaborate(self, platform):
        m = Module()

        # Create clock out signals
        self.clk = {cfg.cd_name: Signal() for cfg in self.clock_config}
        self._pll_lock = Signal()

        # Create our clock domains.
        for cfg in self.clock_config:
            m.domains += ClockDomain(cfg.cd_name)
            m.d.comb += ClockSignal(domain=cfg.cd_name).eq(self.clk[cfg.cd_name])
            m.d.comb += ResetSignal(cfg.cd_name).eq(~self._pll_lock),

        # Grab our input clock
        clock_name = self.clock_name if self.clock_name else platform.default_clk
        
        try:
            self.clkin_frequency = platform.lookup(clock_name).clock.frequency / 1e6
            input_clock_pin = platform.request(clock_name)
        except:
            input_clock_pin = ClockSignal(clock_name)
            # TODO: Make this nicer, remove clock_signal_freq
            self.clkin_frequency = self.clock_signal_freq / 1e6

        # Calculate configuration parameters
        params = self.calc_pll_params(self.clkin_frequency, self.clock_config[0].freq)
        if len(self.clock_config) > 1:
            self.generate_secondary_output(params, 0, self.clock_config[1].freq, self.clock_config[1].phase)
        if len(self.clock_config) > 2:
            self.generate_secondary_output(params, 1, self.clock_config[2].freq, self.clock_config[2].phase)
        if len(self.clock_config) > 3:
            self.generate_secondary_output(params, 2, self.clock_config[3].freq, self.clock_config[3].phase)

        for i, p in enumerate([
                params,
                params["secondary"][0],
                params["secondary"][1],
                params["secondary"][2]
            ]):
            if p["error"] > 0:
                logger.warning("ClockDomain {} has an error of {:.3f} MHz ({} instead of {})"
                    .format(self.clock_config[i].cd_name, p["error"], p["freq"], p["freq_requested"]))
                if not self.skip_checks:
                    assert(p["error"] <= self.clock_config[i].error)

        m.submodules.pll = Instance("EHXPLLL",
            # Clock in.
            i_CLKI=input_clock_pin,

            # Generated clock outputs.
            o_CLKOP=self.clk[self.clock_config[0].cd_name],
            o_CLKOS=self.clk[self.clock_config[1].cd_name] if len(self.clock_config) > 1 else Signal(),
            o_CLKOS2=self.clk[self.clock_config[2].cd_name] if len(self.clock_config) > 2 else Signal(),
            o_CLKOS3=self.clk[self.clock_config[3].cd_name] if len(self.clock_config) > 3 else Signal(),

            # Status.
            o_LOCK=self._pll_lock,

            # PLL parameters...
            p_PLLRST_ENA="DISABLED",
            p_INTFB_WAKE="DISABLED",
            p_STDBY_ENABLE="DISABLED",
            p_DPHASE_SOURCE="DISABLED",

            p_OUTDIVIDER_MUXA="DIVA",
            p_OUTDIVIDER_MUXB="DIVB",
            p_OUTDIVIDER_MUXC="DIVC",
            p_OUTDIVIDER_MUXD="DIVD",

            p_CLKI_DIV=params["refclk_div"],
            p_CLKOP_ENABLE="ENABLED",
            p_CLKOP_DIV=params["output_div"],
            p_CLKOP_CPHASE=params["primary_cphase"],
            p_CLKOP_FPHASE=0,

            p_CLKOS_ENABLE="ENABLED" if params["secondary"][0]["enabled"] else "DISABLED",
            p_CLKOS_FPHASE=params["secondary"][0]["fphase"],
            p_CLKOS_CPHASE=params["secondary"][0]["cphase"],
            p_CLKOS_DIV=params["secondary"][0]["div"],

            p_CLKOS2_ENABLE="ENABLED" if params["secondary"][1]["enabled"] else "DISABLED",
            p_CLKOS2_FPHASE=params["secondary"][1]["fphase"],
            p_CLKOS2_CPHASE=params["secondary"][1]["cphase"],
            p_CLKOS2_DIV=params["secondary"][1]["div"],

            p_CLKOS3_ENABLE="ENABLED" if params["secondary"][2]["enabled"] else "DISABLED",
            p_CLKOS3_FPHASE=params["secondary"][2]["fphase"],
            p_CLKOS3_CPHASE=params["secondary"][2]["cphase"],
            p_CLKOS3_DIV=params["secondary"][2]["div"],

            p_FEEDBK_PATH="CLKOP", # TODO: external feedback
            p_CLKFB_DIV=params["feedback_div"],

            # Internal feedback.
            i_CLKFB=self.clk[self.clock_config[0].cd_name],

            # TODO: Reset
            i_RST=0,

            # TODO: Standby
            i_STDBY=0,

            # TODO: Dynamic mode
            i_PHASESEL0=0,
            i_PHASESEL1=0,
            i_PHASEDIR=0,
            i_PHASESTEP=0,
            i_PHASELOADREG=0,

            i_PLLWAKESYNC=0,

            # Output Enables.
            i_ENCLKOP=0,
            i_ENCLKOS=0,
            i_ENCLKOS2=0,
            i_ENCLKOS3=0,

            # Synthesis attributes.
            a_FREQUENCY_PIN_CLKI=str(self.clkin_frequency),
            a_FREQUENCY_PIN_CLKOP=str(self.clock_config[0].freq),
            a_FREQUENCY_PIN_CLKOS=str(self.clock_config[1].freq) if len(self.clock_config) > 1 else "0",
            a_FREQUENCY_PIN_CLKOS2=str(self.clock_config[2].freq) if len(self.clock_config) > 2 else "0",
            a_FREQUENCY_PIN_CLKOS3=str(self.clock_config[3].freq) if len(self.clock_config) > 3 else "0",
            a_ICP_CURRENT="12",
            a_LPF_RESISTOR="8",
            a_MFG_ENABLE_FILTEROPAMP="1",
            a_MFG_GMCREF_SEL="2",
        )
        return m
