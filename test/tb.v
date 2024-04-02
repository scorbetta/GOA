`timescale 1ns/100ps
`default_nettype none

// The module wraps project to flatten its ports. This is required to work around some open-source
// tools limitations
module tb
(
    // Dedicated inputs
    input wire  ui_in_7,
    input wire  ui_in_6,
    input wire  ui_in_5,
    input wire  ui_in_4,
    input wire  ui_in_3,
    input wire  ui_in_2,
    input wire  ui_in_1,
    input wire  ui_in_0,
    // Dedicated outputs
    output wire uo_out_7,
    output wire uo_out_6,
    output wire uo_out_5,
    output wire uo_out_4,
    output wire uo_out_3,
    output wire uo_out_2,
    output wire uo_out_1,
    output wire uo_out_0,
    // IOs: Input path
    input wire  uio_in_7,
    input wire  uio_in_6,
    input wire  uio_in_5,
    input wire  uio_in_4,
    input wire  uio_in_3,
    input wire  uio_in_2,
    input wire  uio_in_1,
    input wire  uio_in_0,
    // IOs: Output path
    output wire uio_out_7,
    output wire uio_out_6,
    output wire uio_out_5,
    output wire uio_out_4,
    output wire uio_out_3,
    output wire uio_out_2,
    output wire uio_out_1,
    output wire uio_out_0,
    // IOs: Enable path (active high: 0=input, 1=output)
    output wire uio_oe_7,
    output wire uio_oe_6,
    output wire uio_oe_5,
    output wire uio_oe_4,
    output wire uio_oe_3,
    output wire uio_oe_2,
    output wire uio_oe_1,
    output wire uio_oe_0,
    // will go high when the design is enabled
    input wire  ena,
    // clock
    input wire  clk,
    // reset_n - low to reset
    input wire  rst_n
);

    tt_um_scorbetta_goa DUT (
`ifdef GL_TEST
        .VPWR       (1'b1),
        .VGND       (1'b0),
`endif
        .ui_in      ({ ui_in_7, ui_in_6, ui_in_5, ui_in_4, ui_in_3, ui_in_2, ui_in_1, ui_in_0 }),
        .uo_out     ({ uo_out_7, uo_out_6, uo_out_5, uo_out_4, uo_out_3, uo_out_2, uo_out_1, uo_out_0 }),
        .uio_in     ({ uio_in_7, uio_in_6, uio_in_5, uio_in_4, uio_in_3, uio_in_2, uio_in_1, uio_in_0 }),
        .uio_out    ({ uio_out_7, uio_out_6, uio_out_5, uio_out_4, uio_out_3, uio_out_2, uio_out_1, uio_out_0 }),
        .uio_oe     ({ uio_oe_7, uio_oe_6, uio_oe_5, uio_oe_4, uio_oe_3, uio_oe_2, uio_oe_1, uio_oe_0 }),
        .ena        (ena),
        .clk        (clk),
        .rst_n      (rst_n)
    );

    //@DUMP_VCDinitial begin
    //@DUMP_VCD    $dumpfile("dump.vcd");
    //@DUMP_VCD    $dumpvars(0, tb);
    //@DUMP_VCDend
endmodule

`default_nettype wire
