// Generated by  grogu  starting from JINJA templated  MODULE_TEMPLATE_NATIVE.v  file

`default_nettype none

`include "REGPOOL.vh"

// Native interface based design for large and distributed register files (used in conjunction with
// the SCI configuration ring)
module REGPOOL (
    // Clock and reset
    input wire CLK,
    input wire RSTN,
    // Register interface
    input wire WREQ,
    input wire [1:0] WADDR,
    input wire [7:0] WDATA,
    output wire WACK,
    input wire RREQ,
    input wire [1:0] RADDR,
    output wire [7:0] RDATA,
    output wire RVALID,
    // Register bundles
    output wire [7:0] HWIF_OUT_WEIGHT_0,
    output wire [7:0] HWIF_OUT_WEIGHT_1,
    output wire [7:0] HWIF_OUT_BIAS,
    input wire [7:0] HWIF_IN_RESULT
);

    reg rvalid;
    reg [7:0] rdata;
    reg wack;

    // Instantiate registers and declare their own signals. From a Software perspective, i.e. access
    // via the AXI4 Lite interface, Configuration registers are Write-only while Status and Delta
    // registers are Read-only

    // WEIGHT_0: Input weight 0
    reg weight_0_wreq;
    wire [7:0] weight_0_value_out;
    RW_REG #(
        .DATA_WIDTH (8),
        .HAS_RESET  (0)
    )
    WEIGHT_0_REG (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .WEN        (weight_0_wreq),
        .VALUE_IN   (WDATA),
        .VALUE_OUT  (weight_0_value_out)
    );
        
    // WEIGHT_1: Input weight 1
    reg weight_1_wreq;
    wire [7:0] weight_1_value_out;
    RW_REG #(
        .DATA_WIDTH (8),
        .HAS_RESET  (0)
    )
    WEIGHT_1_REG (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .WEN        (weight_1_wreq),
        .VALUE_IN   (WDATA),
        .VALUE_OUT  (weight_1_value_out)
    );
        
    // BIAS: Input bias
    reg bias_wreq;
    wire [7:0] bias_value_out;
    RW_REG #(
        .DATA_WIDTH (8),
        .HAS_RESET  (0)
    )
    BIAS_REG (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .WEN        (bias_wreq),
        .VALUE_IN   (WDATA),
        .VALUE_OUT  (bias_value_out)
    );
        
    // RESULT: Activation function result
    wire [7:0] result_value_in;
    wire [7:0] result_value_out;
    RO_REG #(
        .DATA_WIDTH (8),
        .HAS_RESET  (0)
    )
    RESULT_REG (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_IN   (result_value_in),
        .VALUE_OUT  (result_value_out)
    );
        
    // Write decoder
    always @(posedge CLK) begin
        wack <= 1'b0;
        weight_0_wreq <= 1'b0;
        weight_1_wreq <= 1'b0;
        bias_wreq <= 1'b0;

        if(WREQ) begin
            wack <= 1'b1;

            case(WADDR)
               `WEIGHT_0_OFFSET : begin weight_0_wreq <= 1'b1; end
               `WEIGHT_1_OFFSET : begin weight_1_wreq <= 1'b1; end
               `BIAS_OFFSET : begin bias_wreq <= 1'b1; end
            endcase
        end
    end

    // Create Read strobe from Read request edge
    always @(posedge CLK) begin
        rvalid <= RREQ;
    end

    // Read decoder
    always @(RADDR) begin
        case(RADDR)
            `WEIGHT_0_OFFSET : begin rdata = weight_0_value_out; end
            `WEIGHT_1_OFFSET : begin rdata = weight_1_value_out; end
            `BIAS_OFFSET : begin rdata = bias_value_out; end
            `RESULT_OFFSET : begin rdata = result_value_out; end
            default : begin rdata = {8{1'b1}}; end
        endcase
    end

    // Pinout
    assign RVALID   = rvalid;
    assign RDATA    = rdata;
    assign WACK     = wack;

    // Compose and decompose CSR bundle data. Control registers (those written by the Software and
    // read by the Hardware) are put over the  HWIF_OUT_*  ports; Status registers (those written by
    // the Hardware and read by the Software) are get over the  HWIF_IN_*  ports
    assign HWIF_OUT_WEIGHT_0 = weight_0_value_out;
    assign HWIF_OUT_WEIGHT_1 = weight_1_value_out;
    assign HWIF_OUT_BIAS = bias_value_out;
    assign result_value_in = HWIF_IN_RESULT;
endmodule

`default_nettype wire