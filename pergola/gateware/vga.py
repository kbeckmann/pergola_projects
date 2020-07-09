from nmigen import *


"""
nMigen port of VGAOutput and VGAOutputSubtarget from the Glasgow project.
https://github.com/GlasgowEmbedded/glasgow/blob/master/software/glasgow/applet/video/vga_output/__init__.py

Copyright (C) 2018 whitequark@whitequark.org
Copyright (C) 2020 Konrad Beckmann

Permission to use, copy, modify, and/or distribute this software for
any purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""

class VGAParameters:
    def __init__(self, h_front, h_sync, h_back, h_active, v_front, v_sync, v_back, v_active):
        self.h_front = h_front
        self.h_sync = h_sync
        self.h_back = h_back
        self.h_active = h_active
        self.v_front = v_front
        self.v_sync = v_sync
        self.v_back = v_back
        self.v_active = v_active

    def __repr__(self):
        return "(VGAParameters {} {} {} {} {} {} {} {})".format(
            self.h_front,
            self.h_sync,
            self.h_back,
            self.h_active,
            self.v_front,
            self.v_sync,
            self.v_back,
            self.v_active)


class VGAOutput(Elaboratable):
    def __init__(self, output):
        self.output = output
        self.hs = Signal()
        self.vs = Signal()
        self.blank = Signal()
        if hasattr(output, "r") and  hasattr(output, "g") and  hasattr(output, "b"):
            self.r = Signal(output.r.shape().width)
            self.g = Signal(output.g.shape().width)
            self.b = Signal(output.b.shape().width)

    def elaborate(self, platform):
        m = Module()
        output = self.output
        m.d.comb += [
            output.hs.eq(self.hs),
            output.vs.eq(self.vs),
            output.blank.eq(self.blank),
        ]

        if hasattr(self, "r") and  hasattr(self, "g") and  hasattr(self, "b"):
            m.d.comb += [
                output.r.eq(self.r),
                output.g.eq(self.g),
                output.b.eq(self.b),
            ]

        return m


class VGAOutputSubtarget(Elaboratable):
    def __init__(self, output, vga_parameters, r=None, g=None, b=None):

        self.output = output
        self.vga_parameters = params = vga_parameters
        self.h_front = params.h_front
        self.h_sync = params.h_sync
        self.h_active = params.h_active

        self.h_total = params.h_front + params.h_sync + params.h_back + params.h_active
        self.v_total = params.v_front + params.v_sync + params.v_back + params.v_active

        self.v_front = params.v_front
        self.v_sync = params.v_sync
        self.h_ctr = Signal(range(self.h_total + 1))
        self.v_ctr = Signal(range(self.v_total + 1))
        self.h_en  = Signal()
        self.v_en  = Signal()
        self.v_active = params.v_active

        self.r = r
        self.g = g
        self.b = b

        self.reset = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.output = output = VGAOutput(self.output)

        m.d.comb += [
            output.blank.eq(~((self.h_ctr < self.h_active) & (self.v_ctr < self.v_active))),
        ]

        with m.If(self.h_ctr == self.h_total - 1):
            with m.If(self.v_ctr == self.v_total - 1):
                m.d.sync += self.v_ctr.eq(0)
            with m.Else():
                m.d.sync += self.v_ctr.eq(self.v_ctr + 1)
            m.d.sync += self.h_ctr.eq(0)
        with m.Else():
            m.d.sync += self.h_ctr.eq(self.h_ctr + 1)
        with m.If(self.h_ctr == 0):
            m.d.sync += self.h_en.eq(1),
        with m.Elif(self.h_ctr == self.h_active):
            m.d.sync += self.h_en.eq(0),
        with m.Elif(self.h_ctr == self.h_active + self.h_front):
            m.d.sync += output.hs.eq(1)
        with m.Elif(self.h_ctr == self.h_active + self.h_front + self.h_sync):
            m.d.sync += output.hs.eq(0)
        with m.If(self.v_ctr == 0):
            m.d.sync += self.v_en.eq(1)
        with m.Elif(self.v_ctr == self.v_active):
            m.d.sync += self.v_en.eq(0)
        with m.Elif(self.v_ctr == self.v_active + self.v_front):
            m.d.sync += output.vs.eq(1)
        with m.Elif(self.v_ctr == self.v_active + self.v_front + self.v_sync):
            m.d.sync += output.vs.eq(0)

        # Improve timing by not connecting color signals unless they are used.
        if not type(None) in [type(x) for x in [self.r, self.g, self.b]]:
            with m.If(self.v_en & self.h_en):
                m.d.sync += output.r.eq(self.r)
                m.d.sync += output.g.eq(self.g)
                m.d.sync += output.b.eq(self.b)
            with m.Else():
                m.d.sync += output.r.eq(0),
                m.d.sync += output.g.eq(0),
                m.d.sync += output.b.eq(0),

        with m.If(self.reset):
            m.d.sync += self.reset.eq(0)
            m.d.sync += self.h_ctr.eq(self.h_total - 1) # hack to allow for a 1 clk delayed reset
            m.d.sync += self.v_ctr.eq(0)

        return m

class DynamicVGAOutputSubtarget(VGAOutputSubtarget):
    def __init__(self, output, r=None, g=None, b=None):

        self.output = output

        self.h_front = Signal(8)
        self.h_sync = Signal(8)
        self.h_back = Signal(8)
        self.h_active = Signal(12)

        self.v_front = Signal(8)
        self.v_sync = Signal(8)
        self.v_back = Signal(8)
        self.v_active = Signal(12)

        self.h_total = self.h_front + self.h_sync + self.h_back + self.h_active
        self.v_total = self.v_front + self.v_sync + self.v_back + self.v_active

        self.h_ctr = Signal(12)
        self.v_ctr = Signal(12)
        self.h_en  = Signal()
        self.v_en  = Signal()

        self.r = r
        self.g = g
        self.b = b

        self.reset = Signal()
