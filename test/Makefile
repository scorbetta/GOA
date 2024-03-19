.PHONY: clean

VERILOG_SOURCES = 
SRC_DIR = $(PWD)/../src
IVERILOG_ARGS =

ifneq ($(GATES),yes)

VERILOG_SOURCES += $(shell ls $(SRC_DIR)/*.v | tr '\n' ' ' )
VERILOG_SOURCES += tb.v
IVERILOG_ARGS += -DCOCOTB_SIM=1 -s tb -I$(SRC_DIR) -g2012

else

VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
IVERILOG_ARGS += -DFUNCTIONAL -DSIM -DUSE_POWER_PINS -DUNIT_DELAY=\#1

endif

default:
	pip3 install fxpmath
	rm -fR sim_build
	mkdir sim_build
	`which iverilog` -o sim_build/sim.vvp $(IVERILOG_ARGS) -g2012 $(VERILOG_SOURCES)
	MODULE=test TESTCASE= TOPLEVEL=tb TOPLEVEL_LANG=verilog `which vvp` -M `python3 -m site --user-site`/cocotb/libs -m libcocotbvpi_icarus sim_build/sim.vvp

clean:
	find . -name __pycache__ -exec rm -fR {} +
	rm -f results.xml
	rm -fR sim_build
