`default_nettype none

module NEURON_WRAPPER
(
    // Clock and reset
    input wire  CLK,
    input wire  RSTN,
    // Configuration interface
    input wire  SCI_CSN,
    input wire  SCI_REQ,
    output wire SCI_RESP,
    output wire SCI_ACK,
    // Debug signals
    output wire DBUG_NI_RREQ,
    output wire DBUG_NI_WREQ,
    output wire DBUG_DATA_COUNT_EN,
    output wire DBUG_ADDR_COUNT_EN,
    output wire DBUG_OPEN_REQ,
    output wire DBUG_SOFT_RESET,
    output wire DBUG_RDATA_SHIFT,
    output wire DBUG_RSTN_I,
    output wire DBUG_RVALID,
    output wire DBUG_RREQ,
    output wire DBUG_WACK,
    output wire DBUG_WREQ,
    output wire DBUG_READY,
    output wire DBUG_ACT_DONE,
    output wire DBUG_BIAS_ADD_DONE,
    output wire DBUG_ADD_DONE,
    output wire DBUG_MUL_DONE,
    output wire DBUG_MUL_START,
    output wire DBUG_VALID_OUT_LATCH,
    output wire DBUG_VALID_OUT,
    output wire DBUG_START,
    output wire DBUG_ACT_OVERFLOW,
    output wire DBUG_BIAS_ADD_OVERFLOW,
    output wire DBUG_ADD_OVERFLOW,
    output wire DBUG_MUL_OVERFLOW
);

    wire                regpool_wreq;
    wire [3:0]          regpool_waddr;
    wire [7:0]          regpool_wdata;
    wire                regpool_wack;
    wire                regpool_rreq;
    wire [3:0]          regpool_raddr;
    wire [7:0]          regpool_rdata;
    wire                regpool_rvalid;
    wire [2*8-1:0]      weights;
    wire [7:0]          bias;
    wire signed [7:0]   value_in;
    wire signed [7:0]   value_out;
    wire                valid_out;
    wire                valid_out_latch;
    wire [7:0]          ctrl;
    wire [7:0]          status;
    wire                ready;
    wire                start;
    wire                soft_reset;
    wire                rstn_i;
    wire signed [7:0]   mult_result;
    wire signed [7:0]   add_result;
    wire signed [7:0]   add_bias_result;

    SCI_SLAVE #(
        .ADDR_WIDTH (4),
        .DATA_WIDTH (8)
    )
    SCI_SLAVE (
        .CLK                (CLK),
        .RSTN               (RSTN),
        .SCI_CSN            (SCI_CSN),
        .SCI_REQ            (SCI_REQ),
        .SCI_RESP           (SCI_RESP),
        .SCI_ACK            (SCI_ACK),
        .NI_WREQ            (regpool_wreq),
        .NI_WADDR           (regpool_waddr),
        .NI_WDATA           (regpool_wdata),
        .NI_WACK            (regpool_wack),
        .NI_RREQ            (regpool_rreq),
        .NI_RADDR           (regpool_raddr),
        .NI_RDATA           (regpool_rdata),
        .NI_RVALID          (regpool_rvalid),
        .DBUG_NI_RREQ       (DBUG_NI_RREQ),
        .DBUG_NI_WREQ       (DBUG_NI_WREQ),
        .DBUG_DATA_COUNT_EN (DBUG_DATA_COUNT_EN),
        .DBUG_ADDR_COUNT_EN (DBUG_ADDR_COUNT_EN),
        .DBUG_OPEN_REQ      (DBUG_OPEN_REQ),
        .DBUG_RDATA_SHIFT   (DBUG_RDATA_SHIFT)
    );

    REGPOOL REGPOOL (
        .CLK                        (CLK),
        .RSTN                       (RSTN),
        .WREQ                       (regpool_wreq),
        .WADDR                      (regpool_waddr),
        .WDATA                      (regpool_wdata),
        .WACK                       (regpool_wack),
        .RREQ                       (regpool_rreq),
        .RADDR                      (regpool_raddr),
        .RDATA                      (regpool_rdata),
        .RVALID                     (regpool_rvalid),
        .HWIF_OUT_WEIGHT_0          (weights[0*8+:8]),
        .HWIF_OUT_WEIGHT_1          (weights[1*8+:8]),
        .HWIF_OUT_BIAS              (bias),
        .HWIF_OUT_VALUE_IN          (value_in),
        .HWIF_OUT_CTRL              (ctrl),
        .HWIF_IN_STATUS             (status),
        .HWIF_IN_RESULT             (value_out),
        .HWIF_IN_MULT_RESULT        (mult_result),
        .HWIF_IN_ADD_RESULT         (add_result),
        .HWIF_IN_BIAS_ADD_RESULT    (add_bias_result)
    );

    // Software controlled reset is active high, while hardware reset is active low. Internal resets
    // are all active-low signals
    assign soft_reset   = ctrl[0];
    assign rstn_i       = RSTN & ~soft_reset;

    EDGE_DETECTOR START_EDGE (
        .CLK            (CLK),
        .SAMPLE_IN      (ctrl[1]),
        .RISE_EDGE_OUT  (start),
        .FALL_EDGE_OUT  () // Unused
    );

    NEURON #(
        .NUM_INPUTS (2),
        .WIDTH      (8),
        .FRAC_BITS  (5)
    )
    NEURON (
        .CLK                    (CLK),
        .RSTN                   (rstn_i),
        .WEIGHTS                (weights),
        .BIAS                   (bias),
        .READY                  (ready),
        .VALUE_IN               (value_in),
        .VALID_IN               (start),
        .VALUE_OUT              (value_out),
        .VALID_OUT              (valid_out),
        .OVERFLOW               (), // Unused
        .MULT_RESULT            (mult_result),
        .ADD_RESULT             (add_result),
        .ADD_BIAS_RESULT        (add_bias_result),
        .DBUG_ACT_DONE          (DBUG_ACT_DONE),
        .DBUG_BIAS_ADD_DONE     (DBUG_BIAS_ADD_DONE),
        .DBUG_ADD_DONE          (DBUG_ADD_DONE),
        .DBUG_MUL_DONE          (DBUG_MUL_DONE),
        .DBUG_MUL_START         (DBUG_MUL_START),
        .DBUG_ACT_OVERFLOW      (DBUG_ACT_OVERFLOW),
        .DBUG_BIAS_ADD_OVERFLOW (DBUG_BIAS_ADD_OVERFLOW),
        .DBUG_ADD_OVERFLOW      (DBUG_ADD_OVERFLOW),
        .DBUG_MUL_OVERFLOW      (DBUG_MUL_OVERFLOW)
    );

    // Latches valid solution
    DELTA_REG #(
        .DATA_WIDTH (1),
        .HAS_RESET  (1)
    )
    VALID_SOLUTION_LATCH (
        .CLK            (CLK),
        .RSTN           (rstn_i),
        .READ_EVENT     (start),
        .VALUE_IN       (valid_out),
        .VALUE_CHANGE   (valid_out_latch),
        .VALUE_OUT      () // Unused
    );

    assign status = {
        6'd0,               // [7:2]
        valid_out_latch,    // [1:1]
        ready               // [0:0]
    };

    // Debug signals
    assign DBUG_SOFT_RESET      = soft_reset;
    assign DBUG_RSTN_I          = rstn_i;
    assign DBUG_VALID_OUT_LATCH = valid_out_latch;
    assign DBUG_VALID_OUT       = valid_out;
    assign DBUG_START           = start;
    assign DBUG_RVALID          = regpool_rvalid;
    assign DBUG_RREQ            = regpool_rreq;
    assign DBUG_WACK            = regpool_wack;
    assign DBUG_WREQ            = regpool_wreq;
    assign DBUG_READY           = ready;
endmodule

`default_nettype wire
