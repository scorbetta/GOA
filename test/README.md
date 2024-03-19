# Sample testbench for a Tiny Tapeout project
This is a sample testbench for a Tiny Tapeout project. It uses
[cocotb](https://docs.cocotb.org/en/stable/) to drive the DUT and check the outputs.

## Notes
This is a very basic test for the `SCORBETTA_GOA` design. It creates two clocks, configures the
neuron via the serial interface, and triggers its operation. Result is then awaited for.

## How-to
To run the RTL simulation:

```sh
make
```
To run gatelevel simulation, first harden your project and copy
`../runs/wokwi/results/final/verilog/gl/{your_module_name}.v` to `gate_level_netlist.v`. Then run:
```sh
make GATES=yes
```

To view the VCD file
```sh
gtkwave dump.vcd
```
