`default_nettype none

module NEURON_CONTROL_ENGINE
#(
    parameter WIDTH         = 8,
    parameter NUM_INPUTS    = 2
)
(
    input wire                          CLK,
    input wire                          RSTN,
    // New input to neuron
    input wire [WIDTH-1:0]              VALUE_IN,
    input wire                          VALID_IN,
    // Weights and bias
    input wire [NUM_INPUTS*WIDTH-1:0]   WEIGHTS,
    // ALU control interface
    output wire                         MUL_START,
    output wire [WIDTH-1:0]             MUL_VALUE_A_IN,
    output wire [WIDTH-1:0]             MUL_VALUE_B_IN,
    output wire                         ACC_MUX,
    input wire                          ADD_DONE,
    output wire                         BIAS_ADD_START,
    input wire                          ACT_DONE,
    output wire                         BUSY
);

    wire [$clog2(NUM_INPUTS)-1:0]   counter;
    reg [1:0]                       valid_in_edges;
    wire                            new_value;
    reg                             pipe_en;
    reg                             bias_add_start;
    reg                             busy;
    reg [3:0]                       delayed_rstn;

    // Detect new value
    always @(posedge CLK) begin
        if(!RSTN) begin
            valid_in_edges <= 2'b00;
        end
        else begin
            valid_in_edges <= { VALID_IN, valid_in_edges[1] };
        end
    end

    assign new_value = (valid_in_edges == 2'b10) ? 1'b1 : 1'b0;

    // Current pipeline counter
    COUNTER #(
        .WIDTH  ($clog2(NUM_INPUTS))
    )
    DATA_COUNTER (
        .CLK        (CLK),
        .RSTN       (RSTN | new_value),
        .EN         (ADD_DONE),
        .VALUE      (counter),
        .OVERFLOW   () // Unused
    );

    // Begin using ALU as soon as possible
    always @(posedge CLK) begin
        if(!RSTN) begin
            pipe_en <= 1'b0;
            bias_add_start <= 1'b0;
        end
        else begin
            pipe_en <= 1'b0;
            bias_add_start <= 1'b0;
            
            if(new_value && !pipe_en) begin
                pipe_en <= 1'b1;
            end
            else if(ADD_DONE && counter == NUM_INPUTS-1) begin
                bias_add_start <= 1'b1;
            end
        end
    end

    // Out-of-reset busy: release the  busy  signal after a while, so that edge-triggered client
    // modules can see the first edge
    always @(posedge CLK) begin
        if(!RSTN) begin
            delayed_rstn <= 4'b0000;
        end
        else begin
            delayed_rstn <= { delayed_rstn[2:0], RSTN };
        end
    end

    // Busy signal gets asserted/cleared multiple times
    always @(posedge CLK) begin
        if(!RSTN) begin
            busy <= 1'b1;
        end
        else begin
            if(busy && delayed_rstn == 4'b0111) begin
                busy <= 1'b0;
            end
            else if(!busy && new_value) begin
                busy <= 1'b1;
            end
            else if(busy && ADD_DONE) begin
                busy <= 1'b0;
            end
            else if(!busy && bias_add_start) begin
                busy <= 1'b1;
            end
            else if(busy && ACT_DONE) begin
                busy <= 1'b0;
            end
        end
    end

    // Pinout
    assign ACC_MUX          = (counter == 0) ? 1'b0 : 1'b1;
    assign MUL_START        = pipe_en;
    assign MUL_VALUE_A_IN   = VALUE_IN;
    assign MUL_VALUE_B_IN   = WEIGHTS[counter*WIDTH +: WIDTH];
    assign BIAS_ADD_START   = bias_add_start;
    assign BUSY             = busy;
endmodule

`default_nettype wire
