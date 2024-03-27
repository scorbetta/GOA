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
    output wire SCI_ACK
);

    wire                regpool_wreq;
    wire [2:0]          regpool_waddr;
    wire [7:0]          regpool_wdata;
    wire                regpool_wack;
    wire                regpool_rreq;
    wire [2:0]          regpool_raddr;
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

    SCI_SLAVE #(
        .ADDR_WIDTH (3),
        .DATA_WIDTH (8)
    )
    SCI_SLAVE (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .SCI_CSN    (SCI_CSN),
        .SCI_REQ    (SCI_REQ),
        .SCI_RESP   (SCI_RESP),
        .SCI_ACK    (SCI_ACK),
        .NI_WREQ    (regpool_wreq),
        .NI_WADDR   (regpool_waddr),
        .NI_WDATA   (regpool_wdata),
        .NI_WACK    (regpool_wack),
        .NI_RREQ    (regpool_rreq),
        .NI_RADDR   (regpool_raddr),
        .NI_RDATA   (regpool_rdata),
        .NI_RVALID  (regpool_rvalid)
    );

    REGPOOL REGPOOL (
        .CLK                (CLK),
        .RSTN               (RSTN),
        .WREQ               (regpool_wreq),
        .WADDR              (regpool_waddr),
        .WDATA              (regpool_wdata),
        .WACK               (regpool_wack),
        .RREQ               (regpool_rreq),
        .RADDR              (regpool_raddr),
        .RDATA              (regpool_rdata),
        .RVALID             (regpool_rvalid),
        .HWIF_OUT_WEIGHT_0  (weights[0*8+:8]),
        .HWIF_OUT_WEIGHT_1  (weights[1*8+:8]),
        .HWIF_OUT_BIAS      (bias),
        .HWIF_OUT_VALUE_IN  (value_in),
        .HWIF_OUT_CTRL      (ctrl),
        .HWIF_IN_STATUS     (status),
        .HWIF_IN_RESULT     (value_out)
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
        .CLK        (CLK),
        .RSTN       (rstn_i),
        .WEIGHTS    (weights),
        .BIAS       (bias),
        .READY      (ready),
        .VALUE_IN   (value_in),
        .VALID_IN   (start),
        .VALUE_OUT  (value_out),
        .VALID_OUT  (valid_out),
        .OVERFLOW   () // Unused
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
endmodule

`default_nettype wire
