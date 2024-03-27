import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
from fxpmath import Fxp
import sys
import os
sys.path.append(os.path.relpath('../'))
from utils.my_utils import *
from utils.NativeInterface import *
from utils.activations import afun_test_primitive
import random

@cocotb.test()
async def test_regpool(dut):
    # Clock
    clock = Clock(dut.CLK, 40, units="ns")
    cocotb.start_soon(clock.start())

    # NativeInterface Master
    ni_obj = NativeInterface()
    ni_obj.set_idle(dut)

    # Reset procedure
    dut.RSTN.value = 0
    for cycle in range(4):
        await RisingEdge(dut.CLK)
    dut.RSTN.value = 1

    for test in range(25):
        # Write random data to random register
        random_addr = random.randint(0,2)
        random_data = random.randint(0,255)
        await ni_obj.write_access(dut, random_addr, random_data)

        # Random wait
        rand_cycles = random.randint(10, 25)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)

        # Read back from same address
        readout = await ni_obj.read_access(dut, random_addr)
        assert(readout == random_data),print(f'Readout mismatch at address {random_addr}: {readout} (expected: {random_data})')

        # Random wait
        rand_cycles = random.randint(1, 10)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)
 
    # Tail
    for cycle in range(10):
        await RisingEdge(dut.CLK)

