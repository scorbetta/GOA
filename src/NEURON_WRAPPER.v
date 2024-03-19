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
    // Load data buffer
    input wire  LOAD_IN,
    input wire  LOAD_VALUE_IN,
    // Result data buffer
    input wire  SHIFT_OUT,
    output wire SHIFT_VALUE_OUT,
    // Trigger interface
    output wire READY,
    input wire  START,
    output wire DONE
);

    wire                regpool_wreq;
    wire [1:0]          regpool_waddr;
    wire [7:0]          regpool_wdata;
    wire                regpool_wack;
    wire                regpool_rreq;
    wire [1:0]          regpool_raddr;
    wire [7:0]          regpool_rdata;
    wire                regpool_rvalid;
    wire [2*8-1:0]      weights;
    wire [7:0]          bias;
    wire signed [7:0]   value_in;
    wire signed [7:0]   value_out;
    wire                valid_out;

    SIPO_BUFFER #(
        .DEPTH  (8)
    )
    VALUE_IN_BUFFER (
        .CLK    (CLK),
        .SIN    (LOAD_VALUE_IN),
        .EN     (LOAD_IN),
        .POUT   (value_in)
    );

    SCI_SLAVE #(
        .ADDR_WIDTH (2),
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
        .HWIF_IN_RESULT     (value_out)
    );

    NEURON #(
        .NUM_INPUTS (2),
        .WIDTH      (8),
        .FRAC_BITS  (5)
    )
    NEURON (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .WEIGHTS    (weights),
        .BIAS       (bias),
        .READY      (READY),
        .VALUE_IN   (value_in),
        .VALID_IN   (START),
        .VALUE_OUT  (value_out),
        .VALID_OUT  (valid_out),
        .OVERFLOW   () // Unused
    );

    PISO_BUFFER #(
        .DEPTH  (8)
    )
    VALUE_OUT_BUFFER (
        .CLK        (CLK),
        .PIN        (value_out),
        .LOAD_IN    (valid_out),
        .SHIFT_OUT  (SHIFT_OUT),
        .SOUT       (SHIFT_VALUE_OUT)
    );


    // Pinout
    assign DONE = valid_out;
endmodule

`default_nettype wire
