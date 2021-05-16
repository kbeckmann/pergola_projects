from nmigen import *

from random import randint


class GameOfLifeGenerator(Elaboratable):
    def __init__(self, r, g, b, vsync, vga):
        self.r = r
        self.g = g
        self.b = b
        self.vsync = vsync
        self.vga = vga
        self.frame = Signal(16)

        self.width = width = 32
        self.height = height = 32

        # initbuf = [0] * (width * height)
        # for y in range(height):
        #     for x in range(width):
        #         initbuf[y*width + x] = y & 1
        initbuf = [
            1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 
        ]

        # self.buf = Memory(width=1, depth=(32 * 32), init=[randint(0, 1) for _ in range(32 * 32)])
        self.buf = Memory(width=1, depth=(width * height), init=initbuf)
        #self.buf = Memory(width=1, depth=(width * height))

    def elaborate(self, platform):
        m = Module()

        vsync = self.vsync
        vga = self.vga
        h_en = vga.h_en
        v_en = vga.v_en
        r = self.r
        g = self.g
        b = self.b

        frame = self.frame
        pix_ctr = Signal(16)

        h_buf_ctr = Signal(range(32))
        v_buf_ctr = Signal(range(32))

        vsync_r = Signal()
        m.d.sync += vsync_r.eq(vsync)
        with m.If(~vsync_r & vsync):
            m.d.sync += frame.eq(frame + 1)
            m.d.sync += pix_ctr.eq(0)
            h_buf_ctr.eq(0)
            v_buf_ctr.eq(0)


        with m.If(h_en & v_en):
            m.d.sync += pix_ctr.eq(pix_ctr + 1)

        m.submodules.mem_rd = mem_rd = self.buf.read_port()

        pixel = Signal()
        skip_ctr_h = Signal(5) # count 0-20
        skip_ctr_v = Signal(5) # count 0-15

        # m.d.comb += [
        #     mem_rd.addr.eq(pix_ctr),
        #     pixel.eq(mem_rd.data),
        # ]

        # Increase skip_ctr_v on each row
        with m.If((vga.h_ctr == vga.h_total - 1) & vga.v_en):
            with m.If(skip_ctr_v == 14):
                m.d.sync += v_buf_ctr.eq(v_buf_ctr + 1)
                m.d.sync += skip_ctr_v.eq(0)
            with m.Else():
                m.d.sync += skip_ctr_v.eq(skip_ctr_v + 1)

        # Increase skip_ctr_h on each horizontal pixel
        with m.If(vga.h_en):
            with m.If(skip_ctr_h == 19):
                m.d.sync += h_buf_ctr.eq(h_buf_ctr + 1)
                m.d.sync += skip_ctr_h.eq(0)
            with m.Else():
                m.d.sync += skip_ctr_h.eq(skip_ctr_h + 1)

        # with m.If((self.vga.h_ctr < self.vga.h_active)):
        #with m.If((self.vga.h_ctr < self.vga.h_active) & (self.vga.v_ctr < self.vga.v_active)):
        with m.If(self.vga.h_en & self.vga.v_en):
            m.d.comb += [
                # mem_rd.addr.eq(self.vga.h_ctr + self.vga.v_ctr * 640),
                mem_rd.addr.eq(h_buf_ctr + v_buf_ctr * 32),
            ]
            m.d.sync += [
                pixel.eq(mem_rd.data),
            ]

#        with m.If(self.vga.h_ctr == 1):
#            m.d.sync += pixel.eq(0)



        # pixel_tint_r = Signal(8, reset=0xFF)
        # pixel_tint_g = Signal(8, reset=0xFF)
        # pixel_tint_b = Signal(8, reset=0x7F)

        pixel_r = Signal(8)
        pixel_g = Signal(8)
        pixel_b = Signal(8)

        m.d.comb += [
            pixel_r.eq(Mux(pixel, 0xFF, 0x00)),
            pixel_g.eq(Mux(pixel, 0xFF, 0x00)),
            pixel_b.eq(Mux(pixel, 0xFF, 0x00)),
        ]

        m.d.comb += r.eq(pixel_r)
        m.d.comb += g.eq(pixel_g)
        m.d.comb += b.eq(pixel_b)

        return m
