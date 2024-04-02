`default_nettype none

// A neuron consists of a configurable number of inputs and a single output
module NEURON #(
    // Number of inputs
    parameter NUM_INPUTS    = 2,
    // Input data width
    parameter WIDTH         = 8,
    // Number of fractional bits
    parameter FRAC_BITS     = 5
)
(
    input wire                                  CLK,
    input wire                                  RSTN,
    // Configuration
    input wire signed [NUM_INPUTS*WIDTH-1:0]    WEIGHTS,
    input wire signed [WIDTH-1:0]               BIAS,
    // Inputs are all asserted at the same time
    output wire                                 READY,
    input wire signed [WIDTH-1:0]               VALUE_IN,
    input wire                                  VALID_IN,
    // Output path
    output wire signed [WIDTH-1:0]              VALUE_OUT,
    output wire                                 VALID_OUT,
    output wire                                 OVERFLOW,
    output wire signed [WIDTH-1:0]              MULT_RESULT,
    output wire signed [WIDTH-1:0]              ADD_RESULT,
    output wire signed [WIDTH-1:0]              ADD_BIAS_RESULT,
    // Debug signals
    output wire                                 DBUG_ACT_DONE,
    output wire                                 DBUG_BIAS_ADD_DONE,
    output wire                                 DBUG_ADD_DONE,
    output wire                                 DBUG_MUL_DONE,
    output wire                                 DBUG_MUL_START,
    output wire                                 DBUG_ACT_OVERFLOW,
    output wire                                 DBUG_BIAS_ADD_OVERFLOW,
    output wire                                 DBUG_ADD_OVERFLOW,
    output wire                                 DBUG_MUL_OVERFLOW
);

    wire                    mul_overflow;
    wire                    add_overflow;
    wire                    act_overflow;
    wire                    bias_add_overflow;
    reg                     overflow;
    genvar                  gdx;
    wire                    mul_start;
    wire signed [WIDTH-1:0] mul_value_a_in;
    wire signed [WIDTH-1:0] mul_value_b_in;
    wire signed [WIDTH-1:0] mul_value_out;
    wire                    mul_done;
    wire signed [WIDTH-1:0] acc_in;
    wire signed [WIDTH-1:0] acc_out;
    wire                    acc_mux;
    wire                    add_done;
    wire                    act_done;
    wire                    bias_add_start;
    wire                    bias_add_done;
    wire signed [WIDTH-1:0] biased_acc_out;
    wire                    busy;
    wire signed [WIDTH-1:0] act_fun_out;

    // Multiplier
    FIXED_POINT_MUL #(
        .WIDTH      (WIDTH),
        .FRAC_BITS  (FRAC_BITS)
    )
    FP_MUL (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_A_IN (mul_value_a_in),
        .VALUE_B_IN (mul_value_b_in),
        .VALID_IN   (mul_start),
        .VALUE_OUT  (mul_value_out),
        .VALID_OUT  (mul_done),
        .OVERFLOW   (mul_overflow)
    );

    // Accumulator (adder engine)
    assign acc_in = ( acc_mux ? acc_out : {WIDTH{1'b0}} );

    FIXED_POINT_ADD #(
        .WIDTH  (WIDTH)
    )
    FP_ADD (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_A_IN (acc_in),
        .VALUE_B_IN (mul_value_out),
        .VALID_IN   (mul_done),
        .VALUE_OUT  (acc_out),
        .VALID_OUT  (add_done),
        .OVERFLOW   (add_overflow)
    );

    // Bias
    FIXED_POINT_ADD #(
        .WIDTH  (WIDTH)
    )
    FP_BIAS (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_A_IN (acc_out),
        .VALUE_B_IN (BIAS),
        .VALID_IN   (bias_add_start),
        .VALUE_OUT  (biased_acc_out),
        .VALID_OUT  (bias_add_done),
        .OVERFLOW   (bias_add_overflow)
    );

    // Non-linear activation function
    FIXED_POINT_ACT_FUN #(
        .WIDTH      (WIDTH),
        .FRAC_BITS  (FRAC_BITS)
    )
    FP_ACT (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_IN   (biased_acc_out),
        .VALID_IN   (bias_add_done),
        .VALUE_OUT  (act_fun_out),
        .VALID_OUT  (act_done),
        .OVERFLOW   (act_overflow)
    );

    // Control engine
    NEURON_CONTROL_ENGINE #(
        .WIDTH      (WIDTH),
        .NUM_INPUTS (NUM_INPUTS)
    )
    NCE (
        .CLK            (CLK),
        .RSTN           (RSTN),
        .VALUE_IN       (VALUE_IN),
        .VALID_IN       (VALID_IN),
        .WEIGHTS        (WEIGHTS),
        .MUL_START      (mul_start),
        .MUL_VALUE_A_IN (mul_value_a_in),
        .MUL_VALUE_B_IN (mul_value_b_in),
        .ACC_MUX        (acc_mux),
        .ADD_DONE       (add_done),
        .BIAS_ADD_START (bias_add_start),
        .ACT_DONE       (act_done),
        .BUSY           (busy)
    );

    // Overflow is sticky
    always @(posedge CLK) begin
        if(!RSTN || VALID_IN) begin
            overflow <= 1'b0;
        end
        else begin
            overflow <= mul_overflow | add_overflow | act_overflow | bias_add_overflow;
        end
    end

    // Pinout
    assign READY            = ~busy;
    assign OVERFLOW         = overflow;
    assign VALID_OUT        = act_done;
    assign VALUE_OUT        = act_fun_out;
    assign MULT_RESULT      = mul_value_out;
    assign ADD_RESULT       = acc_out;
    assign ADD_BIAS_RESULT  = biased_acc_out;

    // Debug signals
    assign DBUG_ACT_DONE            = act_done;
    assign DBUG_BIAS_ADD_DONE       = bias_add_done;
    assign DBUG_ADD_DONE            = add_done;
    assign DBUG_MUL_DONE            = mul_done;
    assign DBUG_MUL_START           = mul_start;
    assign DBUG_ACT_OVERFLOW        = act_overflow;
    assign DBUG_BIAS_ADD_OVERFLOW   = bias_add_overflow;
    assign DBUG_ADD_OVERFLOW        = add_overflow;
    assign DBUG_MUL_OVERFLOW        = mul_overflow;
endmodule

`default_nettype wire
