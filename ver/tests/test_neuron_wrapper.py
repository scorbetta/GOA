import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
from fxpmath import Fxp
import sys
import os
sys.path.append(os.path.relpath('../'))
from utils.my_utils import *
from utils.SCI import *
from utils.activations import afun_test_primitive
import random

# Polls a register until desired bit is set. Polling is done through the SCI interface
async def wait_for_register_bit(dut, sci_obj, reg_addr, reg_bit, bit_value, wait_cycles=10, max_trials=20):
    trial = 0
    bit_str = 7 - reg_bit
    while 1:
        readout = await sci_obj.recv_data(dut, reg_addr, 8, 0)
        if readout[bit_str] == str(bit_value):
            break
        else:
            for _ in range(wait_cycles):
                await RisingEdge(dut.CLK)
            trial = trial + 1
            assert trial < max_trials,print(f'Bit {reg_bit} of register {reg_addr} never became {bit_value} in {max_trials} trials')

@cocotb.test()
async def test_neuron_wrapper(dut):
    # Clock
    clock = Clock(dut.CLK, 40, units="ns")
    cocotb.start_soon(clock.start())

    # SCI Slave
    sci_obj = SCI(1, prefix="SCI_")
    sci_obj.set_idle(dut)
    cocotb.start_soon(sci_obj.start_slave(dut, [3], [8]))

    # Reset procedure
    dut.RSTN.value = 0
    for cycle in range(4):
        await RisingEdge(dut.CLK)
    dut.RSTN.value = 1

    # Basic connectivity tests
    for test in range(4):
        # Write random data to random register
        random_addr = format(random.randint(0,2), f'03b') ;# Available Write registers
        random_data = format(random.randint(0,255), f'08b')
        await sci_obj.send_data(dut, random_addr, random_data, 0)

        # Random wait
        rand_cycles = random.randint(10, 25)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)

        # Read back from same address
        readout = await sci_obj.recv_data(dut, random_addr, 8, 0)
        assert(readout == random_data),print(f'Readout mismatch at address {random_addr}: {readout} (expected: {random_data})')

        # Random wait
        rand_cycles = random.randint(1, 10)
        for _ in range(rand_cycles):
            await RisingEdge(dut.CLK)

    # Every test runs through a number of steps...
    for test in range(100):
        for reg in range(3):
            # ... (1) Configure the Neuron with random weights and bias...
            addr = format(reg, f'03b')
            random_data = format(random.randint(0,255), f'08b')
            await sci_obj.send_data(dut, addr, random_data, 0)
            rand_cycles = random.randint(10, 25)
            for _ in range(rand_cycles):
                await RisingEdge(dut.CLK)

            # ... (2) Readback and verify written configuration values...
            readout = await sci_obj.recv_data(dut, addr, 8, 0)
            assert(readout == random_data),print(f'Readout mismatch at address {addr}: {readout} (expected: {random_data})')
            rand_cycles = random.randint(1, 10)
            for _ in range(rand_cycles):
                await RisingEdge(dut.CLK)

        # ... (3a) Wait for Neuron to be ready...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # ... (3b) Load-in random value...
        addr = format(3, f'03b')
        random_data = format(random.randint(0,255), f'08b')
        await sci_obj.send_data(dut, addr, random_data, 0)
        # ... (3c) Trigger Neuron ...
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        # ... (3d) Wait for Neuron to be ready again...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # ... (3e) Release Neuron...
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000000', 0)

        # ... (4a) Load-in a second random value...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(3, f'03b')
        random_data = format(random.randint(0,255), f'08b')
        await sci_obj.send_data(dut, addr, random_data, 0)
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000000', 0)
        # ... (4b) Wait for solution ready...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 1, 1)

        # ... (5) Readout the solution
        addr = format(6, f'03b')
        readout = await sci_obj.recv_data(dut, addr, 8, 0)

    # Tail
    for cycle in range(10):
        await RisingEdge(dut.CLK)

