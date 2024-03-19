// Fixed point representation:
//      Word width: 8
//      Integral bits: 3
//      Fractional bits: 5

// Points of interest are in quadrant #1
//      FO = (0.0, 0.0)
//      Z3 = (arctanh(sqrt(1/3)), 0.0) the point where third derivative is 0, meaning the point
//                                     in which first derivative changes convexity direction
//      Z4 = (arctanh(sqrt(2/3)), 0.0) the point where fourth derivative is 0, meaning the point
//                                     in which second derivative changes convexity direction
//      FP = (2.0, 1.0) the approximation poinf of the plateau
localparam F0_X             = 8'h00; // Equals 0.0, 0.0 before approximation
localparam Z3_X             = 8'h15; // Equals 0.65625, 0.6584789484624083 before approximation
localparam Z4_X             = 8'h24; // Equals 1.125, 1.1462158347805889 before approximation
localparam FP_X             = 8'h40; // Equals 2.0, 2.0 before approximation

// Line parameters for quadrant #1
localparam LINE_M_F0_Z3     = 8'h1C; // Equals 0.875, 0.8768 before approximation
localparam LINE_QP_F0_Z3    = 8'h00; // Equals 0.0, 0.0 before approximation
localparam LINE_M_Z3_Z4     = 8'h0F; // Equals 0.4903, 0.4903 before approximation
localparam LINE_QP_Z3_Z4    = 8'h08; // Equals 0.2545, 0.2545 before approximation
localparam LINE_M_Z4_FP     = 8'h06; // Equals 0.2149, 0.2149 before approximation
localparam LINE_QP_Z4_FP    = 8'h12; // Equals 0.5702, 0.5702 before approximation
localparam LINE_M_FP_INF    = 8'h00; // Equals 0.0, 0.0 before approximation
localparam LINE_QP_FP_INF   = 8'h20; // Equals 1.0, 1.0 before approximation

// Line parameters for quadrant #3
localparam LINE_QN_F0_Z3    = -LINE_QP_F0_Z3;
localparam LINE_QN_Z3_Z4    = -LINE_QP_Z3_Z4;
localparam LINE_QN_Z4_FP    = -LINE_QP_Z4_FP;
localparam LINE_QN_FP_INF   = -LINE_QP_FP_INF;
