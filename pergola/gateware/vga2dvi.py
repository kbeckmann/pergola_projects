from nmigen import *
from .tmds import TMDSEncoder

"""

nMigen port of the following VHDL code, retrieved from
https://github.com/daveshah1/prjtrellis-dvi/blob/master/hdl/vga2dvid.vhd
Original source seems to be unavailable.

Copyright (C) 2020 Konrad Beckmann
Copyright (C) 2012 Mike Field <hamster@snap.net.nz>

License from the original source:

--------------------------------------------------------------------------------
-- Engineer:    Mike Field <hamster@snap.net.nz>
-- Description: Converts VGA signals into DVID bitstreams.
--
--  'clk_shift' 10x clk_pixel for SDR
--  'clk_shift'  5x clk_pixel for DDR
--
--  'blank' should be asserted during the non-display 
--  portions of the frame
--------------------------------------------------------------------------------
-- See: http://hamsterworks.co.nz/mediawiki/index.php/Dvid_test
--      http://hamsterworks.co.nz/mediawiki/index.php/FPGA_Projects
--
-- Copyright (c) 2012 Mike Field <hamster@snap.net.nz>
--
-- Permission is hereby granted, free of charge, to any person obtaining a copy
-- of this software and associated documentation files (the "Software"), to deal
-- in the Software without restriction, including without limitation the rights
-- to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
-- copies of the Software, and to permit persons to whom the Software is
-- furnished to do so, subject to the following conditions:
--
-- The above copyright notice and this permission notice shall be included in
-- all copies or substantial portions of the Software.
--
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
-- IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
-- FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
-- AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
-- LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
-- OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
-- THE SOFTWARE.
--


"""

class VGA2DVI(Elaboratable):
    """
    in_r:     Red pixel value (8 bits)
    in_g:     Green pixel value (8 bits)
    in_b:     Blue pixel value (8 bits)
    in_blank: Blanking signal
    in_hsync: Horizontal sync signal
    in_vsync: Vertical sync signal

    out_r:     TMDS encoded output in shift clock domain
    out_g:     TMDS encoded output in shift clock domain
    out_b:     TMDS encoded output in shift clock domain
    out_clock: Clock output in shift clock domain

    Clock domains
    sync:      Pixel clock
    shift:     TMDS output shift clock (10x pixel clock)

    TODO: Add DDR1x support
    TODO: Add DDR2x support
    TODO: Add clock synchronizer
    """

    def __init__(self, in_r, in_g, in_b, in_blank, in_hsync, in_vsync, out_r, out_g, out_b, out_clock):
        self.in_r = in_r
        self.in_g = in_g
        self.in_b = in_b
        self.in_blank = in_blank
        self.in_hsync = in_hsync
        self.in_vsync = in_vsync
        self.out_r = out_r
        self.out_g = out_g
        self.out_b = out_b
        self.out_clock = out_clock

    def elaborate(self, platform):
        m = Module()

        c_red = Signal(2)
        c_green = Signal(2)
        c_blue = Signal(2)
        m.d.comb += c_blue.eq(Cat(self.in_hsync, self.in_vsync))

        encoded_red = Signal(10)
        encoded_green = Signal(10)
        encoded_blue = Signal(10)

        m.submodules.tmds_r = tmds_r = TMDSEncoder(data=self.in_r, c=c_red,   blank=self.in_blank, encoded=encoded_red)
        m.submodules.tmds_g = tmds_g = TMDSEncoder(data=self.in_g, c=c_green, blank=self.in_blank, encoded=encoded_green)
        m.submodules.tmds_b = tmds_b = TMDSEncoder(data=self.in_b, c=c_blue,  blank=self.in_blank, encoded=encoded_blue)


        shift_clock_initial = 0b0000011111
        C_shift_clock_initial = Const(0b0000011111)
        shift_clock = Signal(10, reset=shift_clock_initial)

        shift_red   = Signal(10)
        shift_green = Signal(10)
        shift_blue  = Signal(10)
        
        # R_shift_clock_off_sync = Signal()
        # m.d.sync += R_shift_clock_off_sync.eq(shift_clock[4:5] != C_shift_clock_initial[4:5])

        # R_shift_clock_synchronizer = Signal(8, reset = 1<<7)
        R_shift_clock_synchronizer = Signal(8)

        latched_red   = Signal(10)
        latched_green = Signal(10)
        latched_blue  = Signal(10)
        m.d.sync += latched_red.eq(encoded_red)
        m.d.sync += latched_green.eq(encoded_green)
        m.d.sync += latched_blue.eq(encoded_blue)

        m.d.comb += [
            self.out_r.eq(shift_red[0]),
            self.out_g.eq(shift_green[0]),
            self.out_b.eq(shift_blue[0]),
            self.out_clock.eq(shift_clock[0])
        ]

        # with m.If(R_shift_clock_off_sync):
        #     with m.If(R_shift_clock_synchronizer[7]):
        #         m.d.shift += R_shift_clock_synchronizer.eq(0)
        #     with m.Else():
        #         m.d.shift += R_shift_clock_synchronizer.eq(R_shift_clock_synchronizer + 1)
        # with m.Else():
        #     m.d.shift += R_shift_clock_synchronizer.eq(0)

        with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
            m.d.shift += shift_red.eq(latched_red)
            m.d.shift += shift_green.eq(latched_green)
            m.d.shift += shift_blue.eq(latched_blue)
        with m.Else():
            m.d.shift += shift_red.eq(Cat(shift_red[1:], 0))
            m.d.shift += shift_green.eq(Cat(shift_green[1:], 0))
            m.d.shift += shift_blue.eq(Cat(shift_blue[1:], 0))
        

        m.d.shift += shift_clock.eq(Cat(shift_clock[1:], shift_clock[0]))
        # R_sync_fail = Signal(7, reset=1<<6)
        # with m.If(~R_shift_clock_synchronizer[7]):
        #     m.d.shift += shift_clock.eq(Cat(0, shift_clock[1:]))
        # with m.Else():
        #     with m.If(R_sync_fail[6]):
        #         m.d.shift += shift_clock.eq(C_shift_clock_initial)
        #         m.d.shift += R_sync_fail.eq(0)
        #     with m.Else():
        #         m.d.shift += R_sync_fail.eq(R_sync_fail + 1)

        return m

