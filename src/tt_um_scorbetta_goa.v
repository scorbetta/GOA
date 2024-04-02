`default_nettype none
`define default_netname none

module tt_um_scorbetta_goa
(
    input wire [7:0]    ui_in, // Dedicated inputs
    output wire [7:0]   uo_out, // Dedicated outputs
    input wire [7:0]    uio_in, // IOs: Input path
    output wire [7:0]   uio_out, // IOs: Output path
    output wire [7:0]   uio_oe, // IOs: Enable path (active high: 0=input, 1=output)
    input wire          ena, // will go high when the design is enabled
    input wire          clk, // clock
    input wire          rst_n // reset_n - low to reset
);

    wire [1:0]  dbug_select;
    reg [7:0]   dbug_out;
    wire        sci_csn;
    wire        sci_req;
    wire        sci_resp;
    wire        sci_ack;
    wire        loopback;
    wire [3:0]  chip_id;
    wire        dbug_ni_rreq;
    wire        dbug_ni_wreq;
    wire        dbug_data_count_en;
    wire        dbug_addr_count_en;
    wire        dbug_open_req;
    wire        dbug_soft_reset;
    wire        dbug_rdata_shift;
    wire        dbug_rstn_i;
    wire        dbug_rvalid;
    wire        dbug_rreq;
    wire        dbug_wack;
    wire        dbug_wreq;
    wire        dbug_ready;
    wire        dbug_act_done;
    wire        dbug_bias_add_done;
    wire        dbug_add_done;
    wire        dbug_mul_done;
    wire        dbug_mul_start;
    wire        dbug_valid_out_latch;
    wire        dbug_valid_out;
    wire        dbug_start;
    wire        dbug_act_overflow;
    wire        dbug_bias_add_overflow;
    wire        dbug_add_overflow;
    wire        dbug_mul_overflow;

    // Chip identifier
    //                 Version TinyTapeout#
    assign chip_id = { 1'b1,   3'b110 };

    // User design uses a custom clock, generated by remote FPGA
    NEURON_WRAPPER NEURON_WRAPPER (
        .CLK                    (ui_in[0]),
        .RSTN                   (ui_in[1]),
        .SCI_CSN                (sci_csn),
        .SCI_REQ                (sci_req),
        .SCI_RESP               (sci_resp),
        .SCI_ACK                (sci_ack),
        .DBUG_NI_RREQ           (dbug_ni_rreq),
        .DBUG_NI_WREQ           (dbug_ni_wreq),
        .DBUG_DATA_COUNT_EN     (dbug_data_count_en),
        .DBUG_ADDR_COUNT_EN     (dbug_addr_count_en),
        .DBUG_OPEN_REQ          (dbug_open_req),
        .DBUG_SOFT_RESET        (dbug_soft_reset),
        .DBUG_RDATA_SHIFT       (dbug_rdata_shift),
        .DBUG_RSTN_I            (dbug_rstn_i),
        .DBUG_RVALID            (dbug_rvalid),
        .DBUG_RREQ              (dbug_rreq),
        .DBUG_WACK              (dbug_wack),
        .DBUG_WREQ              (dbug_wreq),
        .DBUG_READY             (dbug_ready),
        .DBUG_ACT_DONE          (dbug_act_done),
        .DBUG_BIAS_ADD_DONE     (dbug_bias_add_done),
        .DBUG_ADD_DONE          (dbug_add_done),
        .DBUG_MUL_DONE          (dbug_mul_done),
        .DBUG_MUL_START         (dbug_mul_start),
        .DBUG_VALID_OUT_LATCH   (dbug_valid_out_latch),
        .DBUG_VALID_OUT         (dbug_valid_out),
        .DBUG_START             (dbug_start),
        .DBUG_ACT_OVERFLOW      (dbug_act_overflow),
        .DBUG_BIAS_ADD_OVERFLOW (dbug_bias_add_overflow),
        .DBUG_ADD_OVERFLOW      (dbug_add_overflow),
        .DBUG_MUL_OVERFLOW      (dbug_mul_overflow)
    );

    // I->O loopback
    assign loopback = ui_in[2];

    // Muxed debug signals. All signals are synchronized to the FPGA clock
    assign dbug_select = ui_in[7:6];

    always @(*) begin
        case(dbug_select)
            2'b00 : begin
                dbug_out = {
                    dbug_ni_rreq,
                    dbug_ni_wreq,
                    dbug_data_count_en,
                    dbug_addr_count_en,
                    dbug_open_req,
                    dbug_soft_reset,
                    clk,
                    ena
                };
            end

            2'b01 : begin
                dbug_out = { 
                    dbug_rdata_shift,
                    dbug_rstn_i,
                    dbug_rvalid,
                    dbug_rreq,
                    dbug_wack,
                    dbug_wreq,
                    dbug_ready,
                    loopback
                };
            end

            2'b10 : begin
                dbug_out = {
                    dbug_act_done,
                    dbug_bias_add_done,
                    dbug_add_done,
                    dbug_mul_done,
                    dbug_mul_start,
                    dbug_valid_out_latch,
                    dbug_valid_out,
                    dbug_start
                };
            end

            2'b11 : begin
                dbug_out = {
                    dbug_act_overflow,
                    dbug_bias_add_overflow,
                    dbug_add_overflow,
                    dbug_mul_overflow,
                    chip_id[0],
                    chip_id[1],
                    chip_id[2],
                    chip_id[3]
                };
            end
        endcase
    end

    assign uo_out = dbug_out;

    // I/Os pins as inputs
    assign uio_oe[0]    = 1'b0; // SCI_CSN
    assign sci_csn      = uio_in[0];
    assign uio_oe[1]    = 1'b0;
    assign sci_req      = uio_in[1]; // SCI_REQ

    // I/Os pins as outputs
    assign uio_oe[2]    = 1'b1; // SCI_RESP
    assign uio_out[2]   = sci_resp;
    assign uio_oe[3]    = 1'b1; // SCI_ACK
    assign uio_out[3]   = sci_ack;

    // Unused I/Os
    assign uio_oe[7:4]  = 4'b0000;
    assign uio_out[7:4] = 4'b0000;
    assign uio_out[1:0] = 2'b00;
endmodule

`default_nettype wire
