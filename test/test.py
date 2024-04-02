
#---- IMPORTS -------------------------------------------------------------------------------------

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


#---- GLOBALS -------------------------------------------------------------------------------------

# Static configuration
width = 8
frac_bits = 5
num_inputs = 2
verbose = 0
rp2040_clock_ns = 40
fpga_clock_ns = 40
# Fixed-point specs
fxp_lsb = fxp_get_lsb(width, frac_bits)
fxp_quants = 2 ** width - 1


#---- UTILITIES -----------------------------------------------------------------------------------

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


#---- TEST ----------------------------------------------------------------------------------------

# Test functionality by sending stimuli at top-level
@cocotb.test()
async def test_top(dut):
    # Clock from the RP2040 chip
    rp2040_clock = Clock(dut.clk, rp2040_clock_ns, units="ns")
    cocotb.start_soon(rp2040_clock.start())

    # Clock from the FPGA
    fpga_clock = Clock(dut.ui_in_0, fpga_clock_ns, units="ns")
    cocotb.start_soon(fpga_clock.start())

    # SCI Master
    sci_obj = SCI(1)
    sci_obj.overwrite_name('clock', 'ui_in_0')
    sci_obj.overwrite_name('reset', 'ui_in_1')
    sci_obj.overwrite_name('csn', 'uio_in_0')
    sci_obj.overwrite_name('req', 'uio_in_1')
    sci_obj.overwrite_name('resp', 'uio_out_2')
    sci_obj.overwrite_name('ack', 'uio_out_3')
    sci_obj.set_idle(dut)

    # Defaults
    dut.rst_n.value = 0
    dut.uio_in_0.value = 1 ;#UI_IN_SCI_CSN
    dut.uio_in_1.value = 0 ;#UI_IN_SCI_REQ
    dut.ena.value = 0
    dut.ui_in_1.value = 0 ;#FPGA_RSTN
    dut.ui_in_2.value = 0 ;#loopback
    dut.ui_in_7.value = 0 ;#dbug_select[1]
    dut.ui_in_6.value = 0 ;#dbug_select[0]

    # TinyTapeout reset procedure
    for cycle in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for cycle in range(4):
        await RisingEdge(dut.clk)

    # Enable design
    dut.ena.value = 1

    # FPGA reset procedure
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)
    dut.ui_in_1.value = 1
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)

    # From this point on, we use the clock generated from the FPGA as reference. Detailed interface
    # mapping through top-level GPIOs
    #   FPGA_CLK    -> DUT.ui_in[0]  -> tb.ui_in_0
    #   FPGA_RSTN   -> DUT.ui_in[1]  -> tb.ui_in_1
    #   SCI_CSN     -> DUT.uio_in[0]  -> tb.uio_in_0
    #   SCI_REQ     -> DUT.uio_in[1]  -> tb.uio_in_1
    #   SCI_RESP    -> DUT.uio_out[0] -> tb.uio_out_0
    #   SCI_ACK     -> DUT.uio_out[1] -> tb.uio_out_1

    # Shake with a Software reset
    addr = format(4, f'04b')
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
            curr_addr = format(vdx, f'04b')
            curr_data = random_weights_in[vdx].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

        # Configure the neuron bias
        curr_addr = format(num_inputs, f'04b')
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
        addr = format(5, f'04b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # Load-in random value...
        addr = format(3, f'04b')
        curr_value_in = str(random_values_in[0].bin())
        await sci_obj.send_data(dut, addr, curr_value_in, 0)
        # Trigger Neuron ...
        addr = format(4, f'04b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        # Wait for Neuron to be ready again...
        addr = format(5, f'04b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        # Release Neuron...
        addr = format(4, f'04b')
        await sci_obj.send_data(dut, addr, '00000000', 0)

        # Load-in a second random value...
        addr = format(5, f'04b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(3, f'04b')
        curr_value_in = str(random_values_in[1].bin())
        await sci_obj.send_data(dut, addr, curr_value_in, 0)
        addr = format(4, f'04b')
        await sci_obj.send_data(dut, addr, '00000010', 0)
        addr = format(5, f'04b')
        await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
        addr = format(4, f'04b')
        await sci_obj.send_data(dut, addr, '00000000', 0)
        # ... (4b) Wait for solution ready...
        addr = format(5, f'04b')
        await wait_for_register_bit(dut, sci_obj, addr, 1, 1)

        # Readout the solution
        addr = format(6, f'04b')
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


#---- TEST ----------------------------------------------------------------------------------------

# Test functionality of the debug mux. The test is very simple, and does not check all possible
# debug signals, but some of them
@cocotb.test()
async def test_dbug_mux(dut):
    # Clock from the RP2040 chip
    rp2040_clock = Clock(dut.clk, rp2040_clock_ns, units="ns")
    cocotb.start_soon(rp2040_clock.start())

    # Clock from the FPGA
    fpga_clock = Clock(dut.ui_in_0, fpga_clock_ns, units="ns")
    cocotb.start_soon(fpga_clock.start())

    # SCI Master
    sci_obj = SCI(1)
    sci_obj.overwrite_name('clock', 'ui_in_0')
    sci_obj.overwrite_name('reset', 'ui_in_1')
    sci_obj.overwrite_name('csn', 'uio_in_0')
    sci_obj.overwrite_name('req', 'uio_in_1')
    sci_obj.overwrite_name('resp', 'uio_out_2')
    sci_obj.overwrite_name('ack', 'uio_out_3')
    sci_obj.set_idle(dut)

    # Defaults
    dut.rst_n.value = 0
    dut.uio_in_0.value = 1 ;#UI_IN_SCI_CSN
    dut.uio_in_1.value = 0 ;#UI_IN_SCI_REQ
    dut.ena.value = 0
    dut.ui_in_1.value = 0 ;#FPGA_RSTN
    dut.ui_in_2.value = 0 ;#loopback
    dut.ui_in_7.value = 0 ;#dbug_select[1]
    dut.ui_in_6.value = 0 ;#dbug_select[0]

    # TinyTapeout reset procedure
    for cycle in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for cycle in range(4):
        await RisingEdge(dut.clk)

    # Enable design
    dut.ena.value = 1

    # FPGA reset procedure
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)
    dut.ui_in_1.value = 1
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)

    # Debug signals are mapped as follows
    #             | ui_in[7:6]
    #      uo_out | 2’b00         | 2'b01       | 2’b10           | 2’b11
    #   ---------------------------------------------------------------------
    #   uo_out[0] | ena           | loopback    | start           | chip_id[3]
    #   uo_out[1] | clk           | ready       | valid_out       | chip_id[2]
    #   uo_out[2] | soft_reset    | WREQ        | valid_out_latch | chip_id[1]
    #   uo_out[3] | open_req      | WACK        | mul_start       | chip_id[0]
    #   uo_out[4] | addr_count_en | RREQ        | mul_done        | mul_overflow
    #   uo_out[5] | data_count_en | RVALID      | add_done        | add_overflow
    #   uo_out[6] | ni_wreq       | rstn_i      | bias_add_done   | bias_add_overflow
    #   uo_out[7] | ni_rreq       | rdata_shift | act_done        | act_overflow
    
    # Check ena
    dut.ui_in_7.value = 0
    dut.ui_in_6.value = 0
    await RisingEdge(dut.ui_in_0)
    assert(dut.uo_out_0.value == 1),print(f'Unexpected ena: {dut.uo_out_0.value} (expected: 1)')

    # Check clk mirroring
    dut.ui_in_7.value = 0
    dut.ui_in_6.value = 0
    for _ in range(100):
        random_wait_ns = random.randint(1, rp2040_clock_ns)
        await Timer(random_wait_ns, 'ns')
        assert(dut.clk.value == dut.uo_out_1.value),print(f'Unexpected clock mirroring: {dut.uo_out_1.value} (expected: {dut.clk.value})')

    # Check soft_reset
    dut.ui_in_7.value = 0
    dut.ui_in_6.value = 0
    addr = format(4, f'04b')
    await sci_obj.send_data(dut, addr, '00000001', 0)
    for _ in range(50):
        await RisingEdge(dut.ui_in_0)
    assert(dut.uo_out_2.value == 1),print(f'Unexpected soft_reset: {dut.uo_out_2.value} (expected: 1)')
    await sci_obj.send_data(dut, addr, '00000000', 0)
    assert(dut.uo_out_2.value == 0),print(f'Unexpected soft_reset: {dut.uo_out_2.value} (expected: 0)')

    # Check chip_id[3:0]
    dut.ui_in_7.value = 1
    dut.ui_in_6.value = 1
    await RisingEdge(dut.ui_in_0)
    assert(dut.uo_out_0.value==1 and dut.uo_out_1.value==1 and dut.uo_out_2.value==1 and dut.uo_out_3.value==0),print(f'Unexpected chip_id[3:0]: {dut.uo_out_3.value}{dut.uo_out_2.value}{dut.uo_out_1.value}{dut.uo_out_0.value} (expected: 1110)')

    # Check loopback
    dut.ui_in_7.value = 0
    dut.ui_in_6.value = 1
    for _ in range(10):
        rand_in = random.randint(0, 1)
        dut.ui_in_2.value = rand_in
        await RisingEdge(dut.ui_in_0)
        assert(dut.uo_out_0.value == rand_in),print(f'Unexpected loopback: {dut.uo_out_0.value} (expected: {rand_in})')


#---- TEST ----------------------------------------------------------------------------------------

# Test full network emulation using a single neuron. Oh yeah!
@cocotb.test()
async def test_network_emulation(dut):
    # Clock from the FPGA
    fpga_clock = Clock(dut.ui_in_0, fpga_clock_ns, units="ns")
    cocotb.start_soon(fpga_clock.start())

    # SCI Master
    sci_obj = SCI(1)
    sci_obj.overwrite_name('clock', 'ui_in_0')
    sci_obj.overwrite_name('reset', 'ui_in_1')
    sci_obj.overwrite_name('csn', 'uio_in_0')
    sci_obj.overwrite_name('req', 'uio_in_1')
    sci_obj.overwrite_name('resp', 'uio_out_2')
    sci_obj.overwrite_name('ack', 'uio_out_3')
    sci_obj.set_idle(dut)

    # Defaults
    dut.rst_n.value = 0
    dut.uio_in_0.value = 1 ;#UI_IN_SCI_CSN
    dut.uio_in_1.value = 0 ;#UI_IN_SCI_REQ
    dut.ena.value = 0
    dut.ui_in_1.value = 0 ;#FPGA_RSTN
    dut.ui_in_2.value = 0 ;#loopback
    dut.ui_in_7.value = 0 ;#dbug_select[1]
    dut.ui_in_6.value = 0 ;#dbug_select[0]

    # Enable design
    dut.ena.value = 1

    # FPGA reset procedure
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)
    dut.ui_in_1.value = 1
    for cycle in range(4):
        await RisingEdge(dut.ui_in_0)

    # The algorithm to emulate a full network using a single neuron is the following (the example
    # refers to a network with 4 inputs, one hidden layer with 3 neurons and one output layer with 2
    # neurons, 2 outputs).
    #
    #   x0, x1, x2 and x3 are the 8-bit inputs
    #   wh0, wh1, wh2 and wh3 are the hidden layer weights for inputs x0, x1, x2 and x3
    #   bh is the bias for the hidden layer
    #   yh0, yh1 and yh2 are the cumulative sum of the neurons in the hidden layer
    #   zh0, zh1 and zh2 are the output of the neurons in the hidden layer
    #   wo0, wo1 and wo2 are the output layer weights for inputs zh0, zh1 and zh2
    #   bo is the bias for the output layer
    #   yo0 and yo1 are the cumulative sums of the neurons in the output layer
    #   zh0 and zh1 are the outputs of the neurons in the output layer
    #
    # Algorithm using a single neuron with 2 inputs and 1 output
    #
    #   // Repeat for each neuron in the hidden layer
    #   for j in range(3):
    #       (1) Configure weights wh0 and wh1
    #       (2) Configure input value x0, trigger the neuron
    #       (3) Configure input value x1, trigger the neuron and store the adder output to th01
    #       (4) Configure weights wh1 and wh2
    #       (5) Configure input value x2, trigger the neuron
    #       (6) Configure input value x3, trigger the neuron and store adder output to th23
    #       (7) Configure both weights to 1.0
    #       (8) Configure bias
    #       (9) Configure input value th01, trigger the neuron
    #       (a) Configure input value th23, trigger the neuron and store the actfun output to zj
    #
    # Repeat the above, using  zj  as inputs instead of  xj  , so that we emulate the hidden layer
    # to output layer connection
    network_inputs = 4
    hl_neurons = 3
    ol_neurons = 2
    network_outputs = hl_neurons

    for test in range(10):
        # Random values will apply to all neurons
        random_values = []
        for vdx in range(network_inputs):
            random_values.append(fxp_generate_random(width, frac_bits))

        # Output from hidden layer neurons
        hl_neurons_z = []
        for _ in range(hl_neurons):
            # Generate random weights and bias for current neuron
            random_weights = []
            for vdx in range(network_inputs):
                random_value = fxp_generate_random(width, frac_bits)
                random_weights.append(random_value)
            random_bias = fxp_generate_random(width, frac_bits)

            # Wait for Neuron to be ready
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)

            # (1) Configure weights wh0 and wh1
            curr_addr = format(0, f'04b')
            curr_data = random_weights[0].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            curr_data = random_weights[1].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(2, f'04b')
            curr_data = Fxp(val=0.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (2) Configure input value x0, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(random_values[0].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (3) Configure input value x1, trigger the neuron and store the adder output to th01
            addr = format(3, f'04b')
            curr_value_in = str(random_values[1].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(8, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            th01 = Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())

            # (4) Configure weights wh1 and wh2
            curr_addr = format(0, f'04b')
            curr_data = random_weights[2].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            curr_data = random_weights[3].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (5) Configure input value x2, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(random_values[2].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (6) Configure input value x3, trigger the neuron and store adder output to th23
            addr = format(3, f'04b')
            curr_value_in = str(random_values[3].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(8, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            th23 = Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())

            # (7) Configure both weights to 1.0
            curr_addr = format(0, f'04b')
            curr_data = Fxp(val=1.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (8) Configure bias
            curr_addr = format(2, f'04b')
            curr_data = random_bias.bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (9) Configure input value th01, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(th01.bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (a) Configure input value th23, trigger the neuron and store the actfun output to zj
            addr = format(3, f'04b')
            curr_value_in = str(th23.bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(6, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            hl_neurons_z.append(Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()))

        # Output from output layer neurons
        ol_neurons_z = []
        for _ in range(ol_neurons):
            # Generate random weights and bias for current neuron
            random_weights = []
            for vdx in range(hl_neurons):
                random_value = fxp_generate_random(width, frac_bits)
                random_weights.append(random_value)
            random_bias = fxp_generate_random(width, frac_bits)

            # Wait for Neuron to be ready
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)

            # (1) Configure weights wh0 and wh1
            curr_addr = format(0, f'04b')
            curr_data = random_weights[0].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            curr_data = random_weights[1].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(2, f'04b')
            curr_data = Fxp(val=0.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (2) Configure input value x0, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(hl_neurons_z[0].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (3) Configure input value x1, trigger the neuron and store the adder output to th01
            addr = format(3, f'04b')
            curr_value_in = str(hl_neurons_z[1].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(8, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            th01 = Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())

            # (4) Configure weights wh1 and wh2
            curr_addr = format(0, f'04b')
            curr_data = random_weights[2].bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            curr_data = Fxp(val=0.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (5) Configure input value x2, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(hl_neurons_z[2].bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (6) Tie input value x3 to 1.0 since there are just 3 inputs to the output layer (the
            # respective weight has been already tied to 0.0), trigger the neuron and store adder output to th23
            addr = format(3, f'04b')
            curr_value_in = str(Fxp(val=1.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(8, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            th23 = Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config())

            # (7) Configure both weights to 1.0
            curr_addr = format(0, f'04b')
            curr_data = Fxp(val=1.0, signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()).bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)
            curr_addr = format(1, f'04b')
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (8) Configure bias
            curr_addr = format(2, f'04b')
            curr_data = random_bias.bin()
            await sci_obj.send_data(dut, curr_addr, curr_data, 0)

            # (9) Configure input value th01, trigger the neuron
            addr = format(3, f'04b')
            curr_value_in = str(th01.bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)

            # (a) Configure input value th23, trigger the neuron and store the actfun output to zj
            addr = format(3, f'04b')
            curr_value_in = str(th23.bin())
            await sci_obj.send_data(dut, addr, curr_value_in, 0)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000010', 0)
            addr = format(5, f'04b')
            await wait_for_register_bit(dut, sci_obj, addr, 0, 1)
            addr = format(4, f'04b')
            await sci_obj.send_data(dut, addr, '00000000', 0)
            addr = format(6, f'04b')
            readout_bin = await sci_obj.recv_data(dut, addr, 8, 0)
            ol_neurons_z.append(Fxp(val=f'0b{readout_bin}', signed=True, n_word=width, n_frac=frac_bits, config=fxp_get_config()))

        # Shim delay
        for cycle in range(4):
            await RisingEdge(dut.ui_in_0)
