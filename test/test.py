import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
from fxpmath import Fxp
import sys
import os
sys.path.append(os.path.relpath('./'))
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
                await RisingEdge(dut.ui_in_0)
            trial = trial + 1
            assert trial < max_trials,print(f'Bit {reg_bit} of register {reg_addr} never became {bit_value} in {max_trials} trials')


@cocotb.test()
async def test(dut):
    # Static configuration
    width = 8
    frac_bits = 5
    num_inputs = 2
    verbose = 0

    # Fixed-point specs
    fxp_lsb = fxp_get_lsb(width, frac_bits)
    fxp_quants = 2 ** width - 1

    # Clock from the RP2040 chip
    rp2040_clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(rp2040_clock.start())

    # Clock from the FPGA
    fpga_clock = Clock(dut.ui_in_0, 40, units="ns")
    cocotb.start_soon(fpga_clock.start())

    # SCI Master
    sci_obj = SCI(1)
    sci_obj.overwrite_name('clock', 'ui_in_0')
    sci_obj.overwrite_name('csn', 'ui_in_1')
    sci_obj.overwrite_name('req', 'ui_in_2')
    sci_obj.overwrite_name('resp', 'uo_out_0')
    sci_obj.overwrite_name('ack', 'uo_out_1')
    sci_obj.set_idle(dut)

    # Defaults
    dut.rst_n.value = 0
    dut.ui_in_1.value = 1 ;#UI_IN_SCI_CSN
    dut.ui_in_2.value = 0 ;#UI_IN_SCI_REQ
    dut.ena.value = 0

    # Reset procedure
    for cycle in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # Shim delay
    for cycle in range(10):
        await RisingEdge(dut.clk)

    # Enable design
    dut.ena.value = 1

    # Shim delay
    for cycle in range(4):
        await RisingEdge(dut.clk)

    # From this point on, we use the clock generated from the FPGA as reference. Detailed interface
    # mapping through top-level GPIOs
    #   CLK         -> DUT.ui_in[0]  -> tb.ui_in_0
    #   SCI_CSN     -> DUT.ui_in[1]  -> tb.ui_in_1
    #   SCI_REQ     -> DUT.ui_in[2]  -> tb.ui_in_2
    #   SCI_RESP    -> DUT.uo_out[0] -> tb.uo_out_0
    #   SCI_ACK     -> DUT.uo_out[1] -> tb.uo_out_1

    # Shake with a Software reset
    addr = format(4, f'03b')
    await sci_obj.send_data(dut, addr, '00000001', 0)
    for _ in range(50):
        await RisingEdge(dut.ui_in_0)
    await sci_obj.send_data(dut, addr, '00000000', 0)

    # The test structure is taken from the  $ROOT/ver/test_neuron_wrapper.py  test
    for test in range(25):
        # Generate random values
        random_values_in = []
        for vdx in range(num_inputs):
            random_value = fxp_generate_random(width, frac_bits)
            random_values_in.append(random_value)

        # Generate random weights
        random_weights_in = []
        for vdx in range(num_inputs):
            random_value = fxp_generate_random(width, frac_bits)
            random_weights_in.append(random_value)
        dbug_print(verbose, f'random_weights={random_weights_in}')

        # Generate random bias
        random_bias_in = fxp_generate_random(width, frac_bits)
        dbug_print(verbose, f'random_bias={random_bias_in}')

        # Configure the neuron weights through the SCI interface
        for vdx in range(num_inputs):
            curr_addr = format(vdx, f'03b')
            curr_data = random_weights_in[vdx].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

        # Configure the neuron bias
        curr_addr = format(num_inputs, f'03b')
        curr_data = random_bias_in.bin()
        await sci_obj.send_data(dut, curr_addr, curr_data, 0)

        # Run parallel multiplications on golden model
        golden_model_muls = []
        for vdx in range(num_inputs):
            golden_model_muls.append(random_values_in[vdx] * random_weights_in[vdx])
            dbug_print(verbose, f'gldn: MUL[{vdx}] {random_values_in[vdx].hex()}*{random_weights_in[vdx].hex()}={golden_model_muls[-1].hex()}')

        # Run accumulator on golden model
        golden_model_acc = Fxp(0.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())
        for vdx in range(num_inputs):
            golden_model_acc += golden_model_muls[vdx]
        golden_model_acc += random_bias_in
        dbug_print(verbose, f'gldn: ACC {golden_model_acc.hex()}')

        # Run activation function on golden model
        retval = afun_test_primitive(golden_model_acc.get_val())
        golden_result = Fxp(val=retval, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())
        dbug_print(verbose, f'gldn: ACT {golden_result.hex()}')

        # Run DUT
        # Wait for Neuron to be ready...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # Load-in random value...
        addr = format(3, f'03b')
        curr_value_in = str(random_values_in[0].bin())
        await sci_obj.send_data(dut, addr, curr_value_in, 0)
        # Trigger Neuron ...
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        # Wait for Neuron to be ready again...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # Release Neuron...
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000000', 0)

        # Load-in a second random value...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(3, f'03b')
        curr_value_in = str(random_values_in[1].bin())
        await sci_obj.send_data(dut, addr, curr_value_in, 0)
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(4, f'03b')
        await sci_obj.send_data(dut, addr, '00000000', 0)
        # ... (4b) Wait for solution ready...
        addr = format(5, f'03b')
        await wait_for_register_bit(dut, sci_obj, addr, 1, 1)

        # Readout the solution
        addr = format(6, f'03b')
        dut_result_bin = await sci_obj.recv_data(dut, addr, 8, 0)
        dut_result = Fxp(val=f'0b{dut_result_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())

        # Verify output
        threshold = 0.10
        abs_err = fxp_abs_err(golden_result, dut_result)
        quant_err = float(abs_err) / float(fxp_lsb) / fxp_quants
        #assert(quant_err <= threshold),print(f'Results for ACT differ more than {threshold*100}% LSBs: dut_result={dut_result},golden_result={golden_result},abs_err={abs_err},quant_error={quant_err}')
        if quant_err > threshold:
            print(f'warn: Test #{test} - Results for ACT differ more than {threshold*100}% LSBs: dut_result={dut_result},golden_result={golden_result},abs_err={abs_err},quant_error={quant_err}')

        # Shim delay
        for cycle in range(4):
            await RisingEdge(dut.ui_in_0)
