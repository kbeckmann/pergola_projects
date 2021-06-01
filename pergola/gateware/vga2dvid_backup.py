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

class VGA2DVID(Elaboratable):
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

    xdr:       Data rate. SDR=1, DDR=2, QDR=4, 7DR=7

    Clock domains
    sync:      Pixel clock
    shift:     TMDS output shift clock, multiplier of pixel clock:
               SDR=10x, DDR=5x, QDR=2.5x, 7DR=10/7x
    """


    def __init__(self, in_r, in_g, in_b, in_blank, in_hsync, in_vsync, in_c1, in_c2, out_r, out_g, out_b, out_clock, xdr=1):
        self.in_r = in_r
        self.in_g = in_g
        self.in_b = in_b
        self.in_blank = in_blank
        self.in_hsync = in_hsync
        self.in_vsync = in_vsync
        self.in_c1 = in_c1
        self.in_c2 = in_c2
        self.out_r = out_r
        self.out_g = out_g
        self.out_b = out_b
        self.out_clock = out_clock
        self.xdr = xdr

    def elaborate(self, platform):
        m = Module()

        xdr = self.xdr

        c0 = Signal(2)
        m.d.comb += c0.eq(Cat(self.in_hsync, self.in_vsync))

        if xdr == 1 or xdr == 2:
            encoded_red = Signal(10)
            encoded_green = Signal(10)
            encoded_blue = Signal(10)

            m.submodules.tmds_b = tmds_b = TMDSEncoder(data=self.in_b, c=c0,         blank=self.in_blank, encoded=encoded_blue)
            m.submodules.tmds_g = tmds_g = TMDSEncoder(data=self.in_g, c=self.in_c1, blank=self.in_blank, encoded=encoded_green)
            m.submodules.tmds_r = tmds_r = TMDSEncoder(data=self.in_r, c=self.in_c2, blank=self.in_blank, encoded=encoded_red)

            shift_clock_initial = 0b0000011111
            C_shift_clock_initial = Const(0b0000011111)
            shift_clock = Signal(10, reset=shift_clock_initial)

            latched_red   = Signal(10)
            latched_green = Signal(10)
            latched_blue  = Signal(10)
            m.d.sync += latched_red.eq(encoded_red)
            m.d.sync += latched_green.eq(encoded_green)
            m.d.sync += latched_blue.eq(encoded_blue)

            # Synchronize signals with an extra register stage
            shift_red   = Signal(10)
            shift_green = Signal(10)
            shift_blue  = Signal(10)
            m.d.shift += [
                shift_red.eq(latched_red),
                shift_green.eq(latched_green),
                shift_blue.eq(latched_blue),
            ]

            shift_red_r   = Signal(10)
            shift_green_r = Signal(10)
            shift_blue_r  = Signal(10)
            m.d.comb += [
                self.out_r.eq(shift_red_r[:xdr]),
                self.out_g.eq(shift_green_r[:xdr]),
                self.out_b.eq(shift_blue_r[:xdr]),
                self.out_clock.eq(shift_clock[:xdr])
            ]

            with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
                m.d.shift += shift_red_r.eq(shift_red)
                m.d.shift += shift_green_r.eq(shift_green)
                m.d.shift += shift_blue_r.eq(shift_blue)
            with m.Else():
                m.d.shift += shift_red_r.eq(Cat(shift_red_r[xdr:], 0))
                m.d.shift += shift_green_r.eq(Cat(shift_green_r[xdr:], 0))
                m.d.shift += shift_blue_r.eq(Cat(shift_blue_r[xdr:], 0))
            

            m.d.shift += shift_clock.eq(Cat(shift_clock[xdr:], shift_clock[:xdr]))

        elif xdr == 4:
            encoded_red = Signal(10)
            encoded_green = Signal(10)
            encoded_blue = Signal(10)

            encoded_red_r = Signal(10)
            encoded_green_r = Signal(10)
            encoded_blue_r = Signal(10)

            m.submodules.tmds_b = tmds_b = TMDSEncoder(data=self.in_b, c=c0,  blank=self.in_blank, encoded=encoded_blue)
            m.submodules.tmds_g = tmds_g = TMDSEncoder(data=self.in_g, c=self.in_c1, blank=self.in_blank, encoded=encoded_green)
            m.submodules.tmds_r = tmds_r = TMDSEncoder(data=self.in_r, c=self.in_c2,   blank=self.in_blank, encoded=encoded_red)

            shift_clock_initial = 0b00000111110000011111
            C_shift_clock_initial = Const(shift_clock_initial)
            shift_clock = Signal(20, reset=shift_clock_initial)

            latched_red   = Signal(20)
            latched_green = Signal(20)
            latched_blue  = Signal(20)

            # encoded_r <= encoded on posedge of the pixel clock
            m.d.sync += encoded_red_r.eq(encoded_red)
            m.d.sync += encoded_green_r.eq(encoded_green)
            m.d.sync += encoded_blue_r.eq(encoded_blue)

            # latched_red <= {encoded_red, encoded_red_r} on every 2nd posedge pixel clock
            latch_clock = Signal()
            m.d.sync += latch_clock.eq(~latch_clock)
            with m.If(latch_clock):
                m.d.sync += latched_red.eq(Cat(encoded_red_r, encoded_red))
                m.d.sync += latched_green.eq(Cat(encoded_green_r, encoded_green))
                m.d.sync += latched_blue.eq(Cat(encoded_blue_r, encoded_blue))

            shift_red   = Signal(20)
            shift_green = Signal(20)
            shift_blue  = Signal(20)
            m.d.shift += [
                shift_red.eq(latched_red),
                shift_green.eq(latched_green),
                shift_blue.eq(latched_blue),
            ]
            
            shift_red_r   = Signal(20)
            shift_green_r = Signal(20)
            shift_blue_r  = Signal(20)
            m.d.comb += [
                self.out_r.eq(shift_red_r[:xdr]),
                self.out_g.eq(shift_green_r[:xdr]),
                self.out_b.eq(shift_blue_r[:xdr]),
                self.out_clock.eq(shift_clock[:xdr])
            ]

            with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
                m.d.shift += shift_red_r.eq(shift_red)
                m.d.shift += shift_green_r.eq(shift_green)
                m.d.shift += shift_blue_r.eq(shift_blue)
            with m.Else():
                m.d.shift += shift_red_r.eq(Cat(shift_red_r[xdr:], 0))
                m.d.shift += shift_green_r.eq(Cat(shift_green_r[xdr:], 0))
                m.d.shift += shift_blue_r.eq(Cat(shift_blue_r[xdr:], 0))

            m.d.shift += shift_clock.eq(Cat(shift_clock[xdr:], shift_clock[:xdr]))

        elif xdr == 7:
            # Don't actually use this, this wastes a lot of LUTs.

            encoded_red = Signal(10)
            encoded_green = Signal(10)
            encoded_blue = Signal(10)

            encoded_red_r = Signal(70)
            encoded_green_r = Signal(70)
            encoded_blue_r = Signal(70)

            m.submodules.tmds_r = tmds_r = TMDSEncoder(data=self.in_r, c=c_red,   blank=self.in_blank, encoded=encoded_red)
            m.submodules.tmds_g = tmds_g = TMDSEncoder(data=self.in_g, c=c_green, blank=self.in_blank, encoded=encoded_green)
            m.submodules.tmds_b = tmds_b = TMDSEncoder(data=self.in_b, c=c_blue,  blank=self.in_blank, encoded=encoded_blue)

            shift_clock_initial = 0b0000011111000001111100000111110000011111000001111100000111110000011111
            C_shift_clock_initial = Const(shift_clock_initial)
            shift_clock = Signal(70, reset=shift_clock_initial)

            shift_red   = Signal(70)
            shift_green = Signal(70)
            shift_blue  = Signal(70)
            
            latched_red   = Signal(70)
            latched_green = Signal(70)
            latched_blue  = Signal(70)

            m.d.sync += encoded_red_r.eq(Cat(encoded_red_r[10:], encoded_red))
            m.d.sync += encoded_green_r.eq(Cat(encoded_green_r[10:], encoded_green))
            m.d.sync += encoded_blue_r.eq(Cat(encoded_blue_r[10:], encoded_blue))

            m.d.sync += latched_red.eq(Cat(encoded_red_r))
            m.d.sync += latched_green.eq(Cat(encoded_green_r))
            m.d.sync += latched_blue.eq(Cat(encoded_blue_r))

            m.d.comb += [
                self.out_r.eq(shift_red[:xdr]),
                self.out_g.eq(shift_green[:xdr]),
                self.out_b.eq(shift_blue[:xdr]),
                self.out_clock.eq(shift_clock[:xdr])
            ]

            with m.If(shift_clock[4:6] == C_shift_clock_initial[4:6]):
                m.d.shift += shift_red.eq(latched_red)
                m.d.shift += shift_green.eq(latched_green)
                m.d.shift += shift_blue.eq(latched_blue)
            with m.Else():
                m.d.shift += shift_red.eq(Cat(shift_red[xdr:], 0))
                m.d.shift += shift_green.eq(Cat(shift_green[xdr:], 0))
                m.d.shift += shift_blue.eq(Cat(shift_blue[xdr:], 0))

            m.d.shift += shift_clock.eq(Cat(shift_clock[xdr:], shift_clock[:xdr]))

        return m

