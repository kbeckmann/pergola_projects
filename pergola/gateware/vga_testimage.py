from nmigen import *

class StaticTestImageGenerator(Elaboratable):
    def __init__(self, vsync, v_ctr, h_ctr, r, g, b):
        self.vsync = vsync
        self.v_ctr = v_ctr
        self.h_ctr = h_ctr
        self.r = r
        self.g = g
        self.b = b

    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.r.eq(self.h_ctr)
        m.d.sync += self.g.eq(self.v_ctr)
        m.d.sync += self.b.eq(127)

        return m


class TestImageGenerator(Elaboratable):
    def __init__(self, vsync, v_ctr, h_ctr, r, g, b, speed=1):
        self.vsync = vsync
        self.v_ctr = v_ctr
        self.h_ctr = h_ctr
        self.r = r
        self.g = g
        self.b = b
        self.frame = Signal(16)
        self.speed = speed

    def elaborate(self, platform):
        m = Module()

        vsync = self.vsync
        v_ctr = self.v_ctr
        h_ctr = self.h_ctr
        r = self.r
        g = self.g
        b = self.b

        frame = self.frame
        vsync_r = Signal()
        m.d.sync += vsync_r.eq(vsync)
        with m.If(~vsync_r & vsync):
            m.d.sync += frame.eq(frame + 1)

        frame_tri = Mux(frame[8], ~frame[:8], frame[:8])
        frame_tri2 = Mux(frame[9], ~frame[1:9], frame[1:9])

        X = Mux(v_ctr[6], h_ctr + frame[self.speed:], h_ctr - frame[self.speed:])
        Y = v_ctr

        m.d.sync += r.eq(frame_tri[1:])
        m.d.sync += g.eq(v_ctr * Mux(X & Y, 255, 0))
        m.d.sync += b.eq(~(frame_tri2 + (X ^ Y)) * 255)

        return m
