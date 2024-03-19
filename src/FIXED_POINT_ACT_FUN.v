`default_nettype none

// The non-linear activation function. This is a piecewise approximation of the tanh(x) function.
// Piecewise approximation are explained somewhere else (see plots and paper)
module FIXED_POINT_ACT_FUN
#(
    // Input data width
    parameter WIDTH         = 16,
    // Number of fractional bits
    parameter FRAC_BITS     = 13
)
(
    input wire                      CLK,
    input wire                      RSTN,
    input wire signed [WIDTH-1:0]   VALUE_IN,
    input wire                      VALID_IN,
    output wire signed [WIDTH-1:0]  VALUE_OUT,
    output wire                     VALID_OUT,
    output wire                     OVERFLOW
);

    wire                    sign;
    wire                    value_gt_f0;
    wire                    value_eq_f0;
    wire                    value_lt_z3;
    wire                    value_gt_z3;
    wire                    value_eq_z3;
    wire                    value_lt_z4;
    wire                    value_gt_z4;
    wire                    value_eq_z4;
    wire                    value_lt_fp;
    wire                    value_gt_fp;
    wire                    value_eq_fp;
    reg signed [WIDTH-1:0]  m;
    reg signed [WIDTH-1:0]  qp;
    reg signed [WIDTH-1:0]  qn;
    wire signed [WIDTH-1:0] m_times_x;
    wire                    m_times_x_valid;
    wire signed [WIDTH-1:0] value_in_abs;
    wire                    abs_valid;
    wire signed [WIDTH-1:0] line_q1_out;
    wire                    line_q1_valid;
    wire signed [WIDTH-1:0] line_out;
    wire                    line_valid;
    wire                    abs_overflow;
    wire                    mul_overflow;
    wire                    add_overflow;
    wire                    change_sign_overflow;
    reg                     overflow;

    // Load parameters
    `include "PIECEWISE_APPROXIMATION_PARAMETERS.vh"
 
    // Parallel comparators give the segment we are in. Since the tanh(x) function is odd-symmetric,
    // we consider only positive values and change sign later if required. Comparison is made on
    // inclusive-on-the-left intervals
    FIXED_POINT_ABS #(
        .WIDTH  (WIDTH)
    )
    ABS_ENGINE (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_IN   (VALUE_IN),
        .VALID_IN   (VALID_IN),
        .VALUE_OUT  (value_in_abs),
        .VALID_OUT  (abs_valid),
        .OVERFLOW   (abs_overflow)
    );

    // Fall within [0,arctanh(sqrt(1/3)))
    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_F0_Z3_0 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (F0_X),
        .GT         (value_gt_f0),
        .EQ         (value_eq_f0),
        .LT         () // Unused
    );

    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_F0_Z3_1 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (Z3_X),
        .GT         (), // Unused
        .EQ         (), // Unused
        .LT         (value_lt_z3)
    );

    // Fall within [arctanh(sqrt(1/3)),arctanh(sqrt(2/3)))
    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_Z3_Z4_0 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (Z3_X),
        .GT         (value_gt_z3),
        .EQ         (value_eq_z3),
        .LT         () // Unused
    );

    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_Z3_Z4_1 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (Z4_X),
        .GT         (), // Unused
        .EQ         (), // Unused
        .LT         (value_lt_z4)
    );

    // Fall within [arctanh(sqrt(2/3)),2)
    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_Z4_FP_0 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (Z4_X),
        .GT         (value_gt_z4),
        .EQ         (value_eq_z4),
        .LT         () // Unused
    );

    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_Z4_FP_1 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (FP_X),
        .GT         (), // Unused
        .EQ         (), // Unused
        .LT         (value_lt_fp)
    );

    // Fall within [2,+inf)
    FIXED_POINT_COMP #(
        .WIDTH  (WIDTH)
    )
    COMP_FP_INF_0 (
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (FP_X),
        .GT         (value_gt_fp),
        .EQ         (value_eq_fp),
        .LT         () // Unused
    );

    // Sign of incoming value. Since this is an integer value in 2's complement, the MSB gives
    // information about its sign, even though it is not the sign bit
    assign sign = VALUE_IN[WIDTH-1];

    // Retrieve the line's parameters  m  and  q  according to the segment the value belongs to.
    // Checks make use of all boolean values above as a double check. This might be simplified, but
    // we let the synthesizer do its job here!  q  is returned in two values:  qp  and  qn  , the
    // former for quadrant 1 and the latter for quadrant 3, since the non-linear function is
    // odd-symmetric
    always @* begin
        // Fall within [0,arctanh(sqrt(1/3)))
        if((value_gt_f0 || value_eq_f0) && value_lt_z3) begin
            m = LINE_M_F0_Z3;
            qp = LINE_QP_F0_Z3;
            qn = LINE_QN_F0_Z3;
        end

        // Fall within [arctanh(sqrt(1/3)),arctanh(sqrt(2/3)))
        else if((value_gt_z3 || value_eq_z3) && value_lt_z4) begin
            m = LINE_M_Z3_Z4;
            qp = LINE_QP_Z3_Z4;
            qn = LINE_QN_Z3_Z4;
        end

        // Fall within [arctanh(sqrt(2/3)),2)
        else if((value_gt_z4 || value_eq_z4) && value_lt_fp) begin
            m = LINE_M_Z4_FP;
            qp = LINE_QP_Z4_FP;
            qn = LINE_QN_Z4_FP;
        end

        // Fall within [2,+inf)
        else if(value_gt_fp || value_eq_fp) begin
            m = LINE_M_FP_INF;
            qp = LINE_QP_FP_INF;
            qn = LINE_QN_FP_INF;
        end

        // Shall never reach this point, though
        else begin
            m = LINE_M_FP_INF;
            qp = LINE_QP_FP_INF;
            qn =LINE_QN_FP_INF;
        end
    end

    // Multiplier and adder to solve the linear equation for quadrant#1
    FIXED_POINT_MUL #(
        .WIDTH      (WIDTH),
        .FRAC_BITS  (FRAC_BITS)
    )
    LINE_MUL (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_A_IN (value_in_abs),
        .VALUE_B_IN (m),
        .VALID_IN   (abs_valid),
        .VALUE_OUT  (m_times_x),
        .VALID_OUT  (m_times_x_valid),
        .OVERFLOW   (mul_overflow)
    );

    FIXED_POINT_ADD #(
        .WIDTH  (WIDTH)
    )
    LINE_ADD (
        .CLK        (CLK),
        .RSTN       (RSTN),
        .VALUE_A_IN (m_times_x),
        .VALUE_B_IN (qp),
        .VALID_IN   (m_times_x_valid),
        .VALUE_OUT  (line_q1_out),
        .VALID_OUT  (line_q1_valid),
        .OVERFLOW   (add_overflow)
    );

    // Adjust sign if needed
    FIXED_POINT_CHANGE_SIGN #(
        .WIDTH  (WIDTH)
    )
    SIGN_ADJUST (
        .CLK            (CLK),
        .RSTN           (RSTN),
        .TARGET_SIGN    (sign),
        .VALUE_IN       (line_q1_out),
        .VALID_IN       (line_q1_valid),
        .VALUE_OUT      (line_out),
        .VALID_OUT      (line_valid),
        .OVERFLOW       (change_sign_overflow)
    );

    // Overflow is sticky
    always @(posedge CLK) begin
        if(!RSTN || VALID_IN) begin
            overflow <= 1'b0;
        end
        else begin
            if(abs_valid && abs_overflow) begin
                overflow <= 1'b1;
            end

            if(m_times_x_valid && mul_overflow) begin
                overflow <= 1'b1;
            end

            if(line_q1_valid && add_overflow) begin
                overflow <= 1'b1;
            end

            if(line_valid && change_sign_overflow) begin
                overflow <= 1'b1;
            end
        end
    end

    // Pinout
    assign VALUE_OUT    = line_out;
    assign VALID_OUT    = line_valid;
    assign OVERFLOW     = overflow;
endmodule

`default_nettype wire
