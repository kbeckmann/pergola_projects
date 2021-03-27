from nmigen import *
from nmigen.sim import Simulator
from ...util.test import FHDLTestCase

from .chacha20_fsm1 import ChaChaFSM1
from .chacha20_fsm2 import ChaChaFSM2

class ChaCha20Cipher(Elaboratable):
    def __init__(self, implementation=ChaChaFSM1):
        self.i_key = [Signal(Shape(32)) for _ in range(8)]
        self.i_nonce = [Signal(Shape(32)) for _ in range(3)]
        self.i_counter = Signal(Shape(32))
        self.i_en = Signal()

        self.o_stream = [Signal(Shape(32)) for _ in range(16)]
        self.o_ready = Signal()

        self.permute = implementation()

    def elaborate(self, platform):
        m = Module()

        key = self.i_key
        counter = self.i_counter
        nonce = self.i_nonce

        m.submodules.permute = permute = self.permute
        m.d.comb += [
            [permute.i_key[i].eq(v) for i, v in enumerate(key)],
            [permute.i_nonce[i].eq(v) for i, v in enumerate(nonce)],
            [self.o_stream[i].eq(v) for i, v in enumerate(permute.o_stream)],
            self.o_ready.eq(permute.o_ready)
        ]

        with m.FSM() as fsm:
            with m.State("IDLE"):
                with m.If(self.i_en):
                    m.d.sync += [
                        permute.i_counter.eq(counter),
                        permute.i_en.eq(1),
                    ]
                    m.next = "RUN"
            with m.State("RUN"):
                with m.If(~self.i_en):
                    permute.i_en.eq(0),
                    m.next = "IDLE"

        return m

class ChaCha20Test(FHDLTestCase):

    def generic_chacha20(self, implementation):
        print("")

        # Encrypt a test message with a known good implementation
        import json
        from base64 import b64encode
        from Crypto.Cipher import ChaCha20
        from Crypto.Random import get_random_bytes
        from struct import pack, unpack
        from binascii import hexlify

        def byte_xor(ba1, ba2):
            """ XOR two byte strings """
            return bytes([_a ^ _b for _a, _b in zip(ba1, ba2)])

        plaintext = b'A'*64
        # key = get_random_bytes(32)
        key = bytes([i for i in range(32)])

        # nonce = get_random_bytes(12)
        nonce = bytes([(i*16 + i) for i in range(12)])
        cipher = ChaCha20.new(key=key, nonce=nonce)
        ciphertext = cipher.encrypt(plaintext)

        nonceb64 = b64encode(cipher.nonce).decode('utf-8')
        ciphertextb64 = b64encode(ciphertext).decode('utf-8')
        keystream = byte_xor(plaintext, ciphertext)
        keystream_hex = hexlify(keystream).decode('utf8')
        result = json.dumps({'nonce':nonceb64, 'ciphertext':ciphertextb64, 'keystream':keystream_hex})
        # print(result)

        # cipher = ChaCha20.new(key=key, nonce=nonce)
        # cipher.seek(0)
        # print(cipher.decrypt(ciphertext))



        m = Module()

        m.submodules.chacha20 = chacha20 = ChaCha20Cipher(implementation)

        key_words = unpack("<8I", key)
        m.d.comb += [chacha20.i_key[i].eq(key_words[i]) for i in range(len(key_words))]

        nonce_words = unpack("<3I", nonce)
        m.d.comb += [chacha20.i_nonce[i].eq(nonce_words[i]) for i in range(len(nonce_words))]

        sim = Simulator(m)
        sim.add_clock(1e-6, domain="sync")


        def process():
            ks = []
            iterations = 0
            yield chacha20.i_en.eq(1)
            yield
            for i in range(30 * 4):
                # Simulate until it'd finished
                iterations += 1
                if (yield chacha20.o_ready) != 0:
                    yield
                    yield
                    yield
                    break
                yield
            for i in range(16):
                ks.append((yield chacha20.o_stream[i]))
            keystream_hdl = pack("<16I", *ks)
            print(f"Took {iterations} iterations")
            print("Keystream generated by simulation: ", hexlify(keystream_hdl))
            print("Decryption using simulation: ", byte_xor(keystream_hdl, ciphertext))

            self.assertEqual(keystream_hdl, keystream)
            self.assertEqual(plaintext, byte_xor(keystream_hdl, ciphertext))

        sim.add_sync_process(process)
        with sim.write_vcd("test.vcd", "test.gtkw"):
            sim.run()

    def test_chacha20_fsm1(self):
        self.generic_chacha20(ChaChaFSM1)

    def test_chacha20_fsm2(self):
        self.generic_chacha20(ChaChaFSM2)
