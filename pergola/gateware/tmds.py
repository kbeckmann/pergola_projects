from nmigen import *

"""

nMigen port of the following VHDL code, retrieved from
https://github.com/daveshah1/prjtrellis-dvi/blob/master/hdl/tmds_encoder.vhd
Original source seems to be unavailable.

Copyright (C) 2020 Konrad Beckmann
Copyright (C) 2012 Mike Field <hamster@snap.net.nz>

License from the original source:

----------------------------------------------------------------------------------
-- Engineer: Mike Field <hamster@snap.net.nz>
-- 
-- Description: TMDS Encoder 
--     8 bits colour, 2 control bits and one blanking bits in
--       10 bits of TMDS encoded data out
--     Clocked at the pixel clock
--
----------------------------------------------------------------------------------
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


class TMDSEncoder(Elaboratable):
    def __init__(self, data, c, blank, encoded):
        assert(data.shape().width == 8)
        assert(c.shape().width == 2)
        assert(blank.shape().width == 1)
        assert(encoded.shape().width == 10)

        self.data = data
        self.c = c
        self.blank = blank
        self.encoded = encoded

    def elaborate(self, platform):
        m = Module()

        data = self.data

        data_copy = Signal(8)
        m.d.comb += data_copy.eq(data)

        xored = Signal(9)
        m.d.comb += xored.eq(Cat(
            data[0],
            data[1] ^ xored[0],
            data[2] ^ xored[1],
            data[3] ^ xored[2],
            data[4] ^ xored[3],
            data[5] ^ xored[4],
            data[6] ^ xored[5],
            data[7] ^ xored[6],
            1
        ))

        xnored = Signal(9)
        m.d.comb += xnored.eq(Cat(
            data[0],
            ~(data[1] ^ xnored[0]),
            ~(data[2] ^ xnored[1]),
            ~(data[3] ^ xnored[2]),
            ~(data[4] ^ xnored[3]),
            ~(data[5] ^ xnored[4]),
            ~(data[6] ^ xnored[5]),
            ~(data[7] ^ xnored[6]),
            0
        ))

        ones = Signal(4)
        m.d.comb += ones.eq(sum(data))

        data_word = Signal(9)
        data_word_inv = Signal(9)
        
        with m.If((ones > 4) | ((ones == 4) & (data[0] == 0))):
            m.d.sync += data_word.eq(xnored)
            m.d.sync += data_word_inv.eq(~xnored)
        with m.Else():
            m.d.sync += data_word.eq(xored)
            m.d.sync += data_word_inv.eq(~xored)

        data_word_disparity = Signal(4)
        m.d.comb += data_word_disparity.eq(0b1100 + sum(data_word[:8]))

        dc_bias = Signal(4)
        with m.If(self.blank):
            with m.Switch(self.c):
                with m.Case(0b00):
                    m.d.sync += self.encoded.eq(0b1101010100)
                with m.Case(0b01):
                    m.d.sync += self.encoded.eq(0b0010101011)
                with m.Case(0b10):
                    m.d.sync += self.encoded.eq(0b0101010100)
                with m.Case(0b11):
                    m.d.sync += self.encoded.eq(0b1010101011)
            m.d.sync += dc_bias.eq(0)
        with m.Else():
            with m.If((dc_bias == 0) | (data_word_disparity == 0)):
                with m.If(data_word[8]):
                    m.d.sync += self.encoded.eq(Cat(data_word[:8], 0b01))
                    m.d.sync += dc_bias.eq(dc_bias + data_word_disparity)
                with m.Else():
                    m.d.sync += self.encoded.eq(Cat(data_word[:8], 0b10))
                    m.d.sync += dc_bias.eq(dc_bias - data_word_disparity)
            with m.Elif(((dc_bias[3] == 0) & (data_word_disparity[3] == 0)) |
                        ((dc_bias[3] == 1) & (data_word_disparity[3] == 1))):
                m.d.sync += self.encoded.eq(Cat(data_word_inv[:8], data_word[8], 0b1))
                m.d.sync += dc_bias.eq(dc_bias + data_word[8] - data_word_disparity)
            with m.Else():
                m.d.sync += self.encoded.eq(Cat(data_word, 0b0))
                m.d.sync += dc_bias.eq(dc_bias - data_word_inv[8] + data_word_disparity)

        return m
