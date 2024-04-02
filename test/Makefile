.PHONY: clean

VERILOG_SOURCES = tb.v
SRC_DIR = $(PWD)/../src
IVERILOG_ARGS =
COCOTB_PREFIX = $(shell cocotb-config --prefix)

ifneq ($(GATES),yes)

VERILOG_SOURCES += $(shell ls $(SRC_DIR)/*.v | tr '\n' ' ' )
IVERILOG_ARGS += -DCOCOTB_SIM=1 -s tb -I$(SRC_DIR) -g2012

else

VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
IVERILOG_ARGS += -Ttyp -DUSE_POWER_PINS -DGL_TEST -DFUNCTIONAL -DSIM -DUNIT_DELAY=\#1

endif

default: test_top test_dbug_mux test_network_emulation

test_%:
	pip3 install fxpmath
	rm -fR sim_build
	mkdir sim_build
	`which iverilog` -o sim_build/sim.vvp $(IVERILOG_ARGS) $(VERILOG_SOURCES)
	MODULE=test TESTCASE=$@ TOPLEVEL=tb TOPLEVEL_LANG=verilog `which vvp` -M $(COCOTB_PREFIX)/cocotb/libs -m libcocotbvpi_icarus sim_build/sim.vvp

clean:
	find .. -name __pycache__ -exec rm -fR {} +
	rm -f results.xml
	rm -fR sim_build
