from nmigen import *
from nmigen.back.pysim import Simulator
from nmigen.test.utils import FHDLTestCase


class ProcessingUnit(Elaboratable):
    """Performs multiply accumulate and passes data.

                top_in
                   v
                +-----+
     left_in -> |     | -> right_out
     done_in -> | P E | -> done_out
                |     |
                +-----+
                   v
               bottom_out

    Each cycle, `acc + top_in * left_in` is stored in `acc`.

    `done_in` should be asserted for one cycle after the last input has been shifted in.
    `left_in` and `top_in` should also be `0` during this cycle.

    The result will arrive 2*N cycles later with the left-most PE's accumulator value first,
    where N is the number of elements in the horizontal chain.

    """
    def __init__(self, shape, suffix):
        self.top_in = Signal(shape, name=f"top_in_{suffix}")
        self.left_in = Signal(shape, name=f"left_in_{suffix}")
        self.acc = Signal(shape, name=f"acc_{suffix}")
        self.bottom_out = Signal(shape, name=f"bottom_out_{suffix}")
        self.right_out = Signal(shape, name=f"right_out_{suffix}")

        self.done_in = Signal(name=f"done_in_{suffix}")
        self.done_in_r = Signal(name=f"done_in_r_{suffix}")
        self.done_out = Signal(name=f"done_out_{suffix}")

    def elaborate(self, platform):
        m = Module()
        mac = Signal.like(self.acc)
        m.d.comb += mac.eq(self.acc + self.top_in * self.left_in)
        m.d.sync += [
            self.bottom_out.eq(self.top_in),
            self.done_out.eq(self.done_in_r),
            self.done_in_r.eq(self.done_in),
        ]
        with m.If(self.done_in):
            # Pass computed mac, store left_in
            m.d.sync += self.right_out.eq(mac),
            m.d.sync += self.acc.eq(self.left_in),
        with m.Elif(self.done_in_r):
            # Pass previous left_in, clear acc
            m.d.sync += self.right_out.eq(self.acc),
            m.d.sync += self.acc.eq(0),
        with m.Else():
            # Pass left_in, store mac in acc
            m.d.sync += self.right_out.eq(self.left_in),
            m.d.sync += self.acc.eq(mac),

        return m


class Delay(Elaboratable):
    """Delays a signal

    Delays the input signal with `depth` clock cycles.
    """
    def __init__(self, shape, depth):
        self.shape = shape
        self.depth = depth

        self.w_data = Signal(shape)
        self.r_data = Signal(shape)

    def elaborate(self, platform):
        depth = self.depth

        m = Module()

        if depth == 0:
            m.d.comb += self.r_data.eq(self.w_data)
        elif depth == 1:
            m.d.sync += self.r_data.eq(self.w_data)
        else:
            buffer = [Signal.like(self.w_data, name=f"buf_{n}") for n in range(depth)]
            m.d.sync += buffer[0].eq(self.w_data)
            m.d.comb += self.r_data.eq(buffer[-1])
            for i in range(1, depth):
                m.d.sync += buffer[i].eq(buffer[i - 1])

        return m

class SystolicMatMul(Elaboratable):
    """Matrix Multiplication using systolic arrays

    Creates a mesh of processing units to perform a matrix multiplication of left @ top.

    When `buffered` is set, input and and output signals are delayed so that rows and columns
    can be shifted in and out one full row/column per cycle.

    Features:

    Multiplies two square matrices of size n x n in 2n+1 cycles (plus n initial cycles of loading).

    Uses n*n multipliers and accumulators.

    TODO:

    Improve utilization with better pipelining. Currently it takes 2n+1 cycles to multiply two n x n matrices.

    Add support for mixed precision. Accumulate and pass signals with more bits, but muliply with fewer.

    Add support for various floating point data types. bfloat16 or tf32 (19 bits) would be suitable.

    """
    def __init__(self, rows, cols, shape, buffered=True):
        self.rows = rows
        self.cols = cols
        self.shape = shape
        self.buffered = buffered

        self.left_in = []
        self.done_in = []
        self.right_out = []
        for n in range(rows):
            self.left_in.append(Signal(shape, name=f"matmul_left_in_{n}"))
            self.done_in.append(Signal(shape, name=f"matmul_done_in_{n}"))
            self.right_out.append(Signal(shape, name=f"matmul_right_out_{n}"))

        self.top_in = []
        for n in range(cols):
            self.top_in.append(Signal(shape, name=f"matmul_top_in_{n}"))

        # Create the processing units
        self.pu = []
        for r in range(rows):
            temp = []
            for c in range(cols):
                pu = ProcessingUnit(shape, f"r{r}_c{c}")
                temp.append(pu)
            self.pu.append(temp)


    def elaborate(self, platform):
        rows = self.rows
        cols = self.cols
        shape = self.shape
        pu = self.pu

        m = Module()

        for r in range(rows):
            for c in range(cols):
                # Add PEs and connect them together in a mesh.
                setattr(m.submodules, f"pu_r{r}_c{c}", pu[r][c])
                if c > 0:
                    m.d.comb += pu[r][c].done_in.eq(pu[r][c-1].done_out)
                    m.d.comb += pu[r][c].left_in.eq(pu[r][c-1].right_out)
                if r > 0:
                    m.d.comb += pu[r][c].top_in.eq(pu[r-1][c].bottom_out)

        if self.buffered:
            # Inputs and outputs are delayed so that rows and columns
            # can be shifted in and out one full row/column per cycle.
            for r in range(rows):
                delay = Delay(shape, r)
                setattr(m.submodules, f"delay_left_row_{r}", delay)
                m.d.comb += delay.w_data.eq(self.left_in[r])
                m.d.comb += pu[r][0].left_in.eq(delay.r_data)

                delay_final = Delay(shape, r)
                setattr(m.submodules, f"delay_final_{r}", delay_final)
                m.d.comb += delay_final.w_data.eq(self.done_in[r])
                m.d.comb += pu[r][0].done_in.eq(delay_final.r_data)

                delay_right = Delay(shape, rows - r)
                setattr(m.submodules, f"delay_right_{r}", delay_right)
                m.d.comb += delay_right.w_data.eq(pu[r][-1].right_out)
                m.d.comb += self.right_out[r].eq(delay_right.r_data)

            for c in range(cols):
                delay = Delay(shape, c)
                setattr(m.submodules,f"delay_top_col_{c}", delay)
                m.d.comb += delay.w_data.eq(self.top_in[c])
                m.d.comb += pu[0][c].top_in.eq(delay.r_data)
        else:
            # No delays. Uses fewer registers, but requires the user to
            # order the data accordingly.
            for r in range(rows):
                m.d.comb += pu[r][0].left_in.eq(self.left_in[r])
                m.d.comb += pu[r][0].done_in.eq(self.done_in[r])
                m.d.comb += self.right_out[r].eq(pu[r][-1].right_out)

            for c in range(cols):
                m.d.comb += pu[0][c].top_in.eq(self.top_in[c])

        return m


# Only used for testing
import importlib
if importlib.util.find_spec("numpy") is not None:
    import numpy as np

class MatMulTest(FHDLTestCase):

    def test_delay(self):
        # Tests the Delay() class

        m = Module()

        bits = 8
        max_depth = 8

        shape = unsigned(bits)
        counter = Signal(shape)
        delays_mem = []
        for i in range(max_depth):
            delays_mem.append(Delay(shape, i))
            setattr(m.submodules, f"delay_{i}", delays_mem[-1])
            m.d.comb += delays_mem[-1].w_data.eq(counter)

        sim = Simulator(m)
        sim.add_clock(1/10e6, domain="sync")

        def process():
            for i in range(100):
                yield counter.eq(i)
                yield
                if i > max_depth:
                    for n in range(len(delays_mem)):
                        value_mem = (yield delays_mem[n].r_data)
                        value_no_mem = (yield delays_mem[n].r_data)
                        # Check that the output of the buffer is delayed correctly
                        # print(value_mem, i, n)
                        # print(value_no_mem, i, n)
                        assert value_mem == i - n
                        assert value_no_mem == i - n

        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd"):
            sim.run()

    def test_pe_chained(self):
        # Test multiple ProcessingUnits that are chained together horizontally.

        m = Module()

        shape = unsigned(32)
        cols = 4

        pu = []
        for i in range(cols):
            elem = ProcessingUnit(shape, f"{i}")
            pu.append(elem)
            setattr(m.submodules, f"pe_{i}", elem)
            if i > 0:
                m.d.comb += [
                    pu[i].left_in.eq(pu[i - 1].right_out),
                    pu[i].done_in.eq(pu[i - 1].done_out),
                ]

        sim = Simulator(m)
        sim.add_clock(1/10e6, domain="sync")

        def process():
            # Start shifting in the first set
            for i in range(1, cols):
                yield pu[0].left_in.eq(i)
                yield

            yield pu[0].left_in.eq(cols)
            for i in range(cols):
                yield pu[i].top_in.eq(10)

            yield

            # End the set by strobing done_in and resetting input signals
            yield pu[0].done_in.eq(1)
            yield pu[0].left_in.eq(0)

            for i in range(cols):
                yield pu[i].top_in.eq(0)

            yield

            # Deassert done_in
            yield pu[0].done_in.eq(0)

            # Let the signals propagate
            for i in range(cols):
                yield


            for i in range(cols, 0, -1):
                # Strobe done_in for the second set
                if i == 0:
                    yield pu[0].done_in.eq(1)
                elif i == 1:
                    yield pu[0].done_in.eq(0)

                # Results of the first set are shifted out
                # print((yield pu[-1].right_out))
                assert (yield pu[-1].right_out) == i * 10
                yield


        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd"):
            sim.run()

    def test_matmul_single(self):
        # Test a single matrix multiplication using SystolicMatMul()

        print("")

        m = Module()

        bits = 32
        rows = 8
        cols = 8

        shape = unsigned(bits)
        counter = Signal(32)
        m.d.sync += counter.eq(counter + 1)

        m.submodules.matmul = matmul = SystolicMatMul(rows, cols, shape)

        np.random.seed(1234)
        M = np.random.randint(1, 255, size=(rows, cols))
        N = np.random.randint(1, 255, size=(rows, cols))

        print("M:\n", M)
        print("N:\n", N)
        print("M @ N:\n", M @ N)

        sim = Simulator(m)
        sim.add_clock(1/10e6, domain="sync")

        def process():

            def print_state(matmul):
                top_in = np.zeros((rows, cols))
                left_in = np.zeros((rows, cols))
                right_out = np.zeros((rows, cols))
                bottom_out = np.zeros((rows, cols))
                done_out = np.zeros((rows, cols))
                matmul_right_out = np.zeros((rows))
                for r in range(rows):
                    matmul_right_out[r] = (yield matmul.right_out[r])
                    for c in range(cols):
                        top_in[r, c] = (yield matmul.pu[r][c].top_in)
                        left_in[r, c] = (yield matmul.pu[r][c].left_in)
                        right_out[r, c] = (yield matmul.pu[r][c].right_out)
                        bottom_out[r, c] = (yield matmul.pu[r][c].bottom_out)
                        done_out[r, c] = (yield matmul.pu[r][c].done_out)

                # print(top_in)
                # print(left_in)
                # print(right_out)
                # print(bottom_out)
                # print(done_out)
                print("matmul.right_out =", matmul_right_out)
                print("")

            # Perform M @ N by loading M into the left column, right column first
            # and loading N into the top, bottom row first.
            # Assumes a square matrix
            for k in range(rows - 1, -1, -1):
                for c in range(cols):
                    yield matmul.top_in [c].eq(int(N[k][c].item()))
                for r in range(rows):
                    yield matmul.left_in[r].eq(int(M[r][k].item()))
                yield

            # Clear inputs and strobe final flags
            for r in range(rows):
                yield matmul.top_in [r].eq(0)
            for c in range(cols):
                yield matmul.left_in[c].eq(0)
                yield matmul.done_in[c].eq(1)

            yield

            # Deassert final flags
            for c in range(cols):
                yield matmul.done_in[c].eq(0)

            # Wait for the signals to propagate
            for _ in range(rows * 2):
                yield

            # The result will now arrive with the first column first (slightly confusing!)
            C = np.zeros((rows, cols), dtype=np.int64)
            for c in range(cols):
                # yield from print_state(matmul)
                for r in range(rows):
                    C[r][c] = (yield matmul.right_out[r])
                yield

            print("Calculated result:\n", C)

            assert np.array_equal(M @ N, C)

            yield
            yield
            yield


        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd", traces=[counter]):
            sim.run()

    def test_matmul_multi(self):
        print("")

        m = Module()

        bits = 32
        rows = 8
        cols = 8

        shape = unsigned(bits)
        counter = Signal(32)
        m.d.sync += counter.eq(counter + 1)

        m.submodules.matmul = matmul = SystolicMatMul(rows, cols, shape)

        # M = np.array([[1, 2], [3, 4]])
        # N = np.array([[5, 6], [7, 8]])

        # M = np.arange( 1 * rows * cols,  2 * rows * cols).reshape((rows, cols))
        # N = np.arange( 2 * rows * cols,  3 * rows * cols).reshape((rows, cols))

        # M1 = np.arange(1, rows * cols + 1).reshape((rows, cols))
        # N1 = np.eye(rows, cols) * 2

        # M2 = np.arange(10, rows * cols + 10).reshape((rows, cols))
        # N2 = np.eye(rows, cols) * 2

        # M3 = np.arange(20, rows * cols + 20).reshape((rows, cols))
        # N3 = np.eye(rows, cols) * 2

        np.random.seed(1234)
        M1 = np.random.randint(1, 255, size=(rows, cols))
        N1 = np.random.randint(1, 255, size=(rows, cols))

        M2 = np.random.randint(1, 255, size=(rows, cols))
        N2 = np.random.randint(1, 255, size=(rows, cols))

        M3 = np.random.randint(1, 255, size=(rows, cols))
        N3 = np.random.randint(1, 255, size=(rows, cols))

        M4 = np.random.randint(1, 255, size=(rows, cols))
        N4 = np.random.randint(1, 255, size=(rows, cols))

        # print("M1:\n", M1)
        # print("N1:\n", N1)
        # print("M1 @ N1:\n", M1 @ N1)

        # print("M2:\n", M2)
        # print("N2:\n", N2)
        # print("M2 @ N2:\n", M2 @ N2)


        sim = Simulator(m)
        sim.add_clock(1/10e6, domain="sync")

        def do_matmul(M, N):
            # Perform M @ N by loading M into the left edge, right edge first
            # and loading N into the top, bottom edge first.
            # Assumes a square matrix
            steps = max(rows, cols)
            for k in range(steps - 1, -1, -1):
                for c in range(cols):
                    yield matmul.top_in[c].eq(int(N[k][c].item()))
                for r in range(rows):
                    yield matmul.left_in[r].eq(int(M[r][k].item()))
                yield

            # Clear inputs and strobe final flags
            for r in range(rows):
                yield matmul.top_in[r].eq(0)
            for c in range(cols):
                yield matmul.left_in[c].eq(0)
                yield matmul.done_in[c].eq(1)

            yield

            # Deassert final flags
            for c in range(cols):
                yield matmul.done_in[c].eq(0)

        def proc_matmul():
            for (M, N) in [(M1, N1), (M2, N2), (M3, N3), (M4, N4)]:
                yield from do_matmul(M, N)
                for _ in range(rows):
                    yield

        def do_check(M, N):
            C = np.zeros((rows, cols), dtype=np.int64)
            for c in range(cols):
                # yield from print_state(matmul)
                for r in range(rows):
                    C[r][c] = (yield matmul.right_out[r])
                yield

            # print("Calculated result:\n", C)

            assert np.array_equal(M @ N, C)

        def proc_checker():
            t0 = 0

            # Initial delay is rows * 3:
            #   rows to load
            #   rows to process
            #   + 1 for the final flag
            #   rows to shift out the data
            for _ in range(rows * 3 + 1):
                yield

            for (M, N) in [(M1, N1), (M2, N2), (M3, N3), (M4, N4)]:
                yield from do_check(M, N)
                t1 = (yield counter)
                print(f"Result ready at {t1}, delta {t1 - t0}")
                t0 = t1

                # Subsequent results arrive after rows + 1 cycles
                for _ in range(rows + 1):
                    yield

        sim.add_sync_process(proc_matmul)
        sim.add_sync_process(proc_checker)
        with sim.write_vcd("test.vcd", traces=[counter]):
            sim.run()
