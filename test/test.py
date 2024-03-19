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

@cocotb.test()
async def test_project_wrapper(dut):
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
    sci_obj.overwrite_name('reset', 'ui_in_1')
    sci_obj.overwrite_name('csn', 'ui_in_2')
    sci_obj.overwrite_name('req', 'ui_in_3')
    sci_obj.overwrite_name('resp', 'uo_out_0')
    sci_obj.overwrite_name('ack', 'uo_out_1')
    sci_obj.set_idle(dut)

    # Defaults
    dut.rst_n.value = 0
    dut.ui_in_1.value = 0 ;#UI_IN_RESET
    dut.ui_in_2.value = 1 ;#UI_IN_SCI_CSN
    dut.ui_in_4.value = 0 ;#UI_IN_LOAD_IN
    dut.ui_in_6.value = 0 ;#UI_IN_SHIFT_OUT
    dut.ui_in_7.value = 0 ;#UI_IN_START

    # Reset procedure
    for cycle in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.ui_in_1.value = 1 ;#UI_IN_RESET

    # Shim delay
    for cycle in range(4):
        await RisingEdge(dut.clk)

    # From this point on, we use the clock generated from the FPGA as reference. Detailed interface
    # mapping through top-level GPIOs
    #   CLK             -> DUT.ui_in[0]  -> tb.ui_in_0
    #   RSTN            -> DUT.ui_in[1]  -> tb.ui_in_1
    #   SCI_CSN         -> DUT.ui_in[2]  -> tb.ui_in_2
    #   SCI_REQ         -> DUT.ui_in[3]  -> tb.ui_in_3
    #   SCI_RESP        -> DUT.uo_out[0] -> tb.uo_out_0
    #   SCI_ACK         -> DUT.uo_out[1] -> tb.uo_out_1
    #   LOAD_IN         -> DUT.ui_in[4]  -> tb.ui_in_4
    #   LOAD_VALUE_IN   -> DUT.ui_in[5]  -> tb.ui_in_5
    #   SHIFT_OUT       -> DUT.ui_in[6]  -> tb.ui_in_6
    #   SHIFT_VALUE_OUT -> DUT.uo_out[2] -> tb.uo_out_2
    #   READY           -> DUT.uo_out[3] -> tb.uo_out_3
    #   START           -> DUT.ui_in[7]  -> tb.ui_in_7
    #   DONE            -> DUT.uo_out[4] -> tb.uo_out_4
    for test in range(1):
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
            await RisingEdge(dut.ui_in_0)
            curr_addr = format(vdx, f'02b')
            curr_data = random_weights_in[vdx].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

        # Configure the neuron bias
        await RisingEdge(dut.ui_in_0)
        curr_addr = format(num_inputs, f'02b')
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
        for vdx in range(num_inputs):
            await wait_for_value(dut.ui_in_0, dut.uo_out_3, 1)
            curr_value_in = str(random_values_in[vdx].bin())
            for bdx in reversed(range(8)):
                await RisingEdge(dut.ui_in_0)
                dut.ui_in_5.value = int(curr_value_in[bdx])
                dut.ui_in_4.value = 1
            await RisingEdge(dut.ui_in_0)
            dut.ui_in_4.value = 0

            for _ in range(10):
                await RisingEdge(dut.ui_in_0)
            dut.ui_in_7.value = 1
            await RisingEdge(dut.ui_in_0)
            dut.ui_in_7.value = 0

            # Ready handshake
            await wait_for_value(dut.ui_in_0, dut.uo_out_3, 0)

        # Wait for result
        await RisingEdge(dut.uo_out_4)
        for _ in range(2):
            await RisingEdge(dut.ui_in_0)

        # Verify accumulator
        threshold = 0.25
        dut_result = Fxp(val=f'0b{str(dut.DUT.NEURON_WRAPPER.NEURON.biased_acc_out.value.binstr)}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())
        abs_err = fxp_abs_err(golden_model_acc, dut_result)
        quant_err = float(abs_err) / float(fxp_lsb) / fxp_quants
        assert(quant_err <= threshold),print(f'Results for ACC differ more than {threshold*100}% LSBs: dut_result={dut_result},golden_result={golden_model_acc},abs_err={abs_err},quant_error={quant_err}')

        # Verify output
        dut_result = ''
        dut.ui_in_6.value = 1
        for bdx in reversed(range(8)):
            await RisingEdge(dut.ui_in_0)
            dut_result = f'{dut.uo_out_2.value}{dut_result}'
        await RisingEdge(dut.ui_in_0)
        dut.ui_in_6.value = 0
        abs_err = fxp_abs_err(golden_result, dut_result)
        quant_err = float(abs_err) / float(fxp_lsb) / fxp_quants
        assert(quant_err <= threshold),print(f'Results for ACT differ more than {threshold*100}% LSBs: dut_result={dut_result},golden_result={golden_result},abs_err={abs_err},quant_error={quant_err}')

        # Shim delay
        for cycle in range(4):
            await RisingEdge(dut.ui_in_0)
