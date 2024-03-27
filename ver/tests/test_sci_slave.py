import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
from fxpmath import Fxp
import sys
import os
sys.path.append(os.path.relpath('../'))
from utils.my_utils import *
from utils.SCI import *
from utils.NativeInterface import *
from utils.activations import afun_test_primitive
import random

@cocotb.test()
async def test_sci_slave(dut):
    addr_width = int(dut.ADDR_WIDTH.value)
    data_width = int(dut.DATA_WIDTH.value)

    # Clock
    clock = Clock(dut.CLK, 40, units="ns")
    cocotb.start_soon(clock.start())

    # SCI Slave
    sci_obj = SCI(1, prefix="SCI_")
    sci_obj.set_idle(dut)
    cocotb.start_soon(sci_obj.start_slave(dut, [ addr_width ], [ data_width ]))

    # NativeInterface Slave
    ni_obj = NativeInterface(prefix="NI_")
    ni_obj.set_idle(dut)
    cocotb.start_soon(ni_obj.start_slave(dut))

    # Reset procedure
    dut.RSTN.value = 0
    for cycle in range(4):
        await RisingEdge(dut.CLK)
    dut.RSTN.value = 1

    for test in range(250):
        # Write random data to random register
        random_addr = format(random.randint(0,2), f'0{addr_width}b') ;# Available Write registers
        random_data = format(random.randint(0,255), f'0{data_width}b')
        await sci_obj.send_data(dut, random_addr, random_data, 0)

        # Random wait
        rand_cycles = random.randint(1, 100)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)

        # Read back from same address
        readout = await sci_obj.recv_data(dut, random_addr, data_width, 0)
        assert(readout == random_data),print(f'Readout mismatch at address {random_addr}: {readout} (expected: {random_data})')

        # Random wait
        rand_cycles = random.randint(1, 10)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)

    # Tail
    for cycle in range(10):
        await RisingEdge(dut.CLK)

