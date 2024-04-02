.PHONY: clean

# Optionals to be passed to COCOTB's Makefile
WAVES ?= 0
# Optional args for specific configuration
EXTRA_ARGS ?= ""

all: test_sci_slave test_neuron_wrapper test_regpool

test_%:
	$(MAKE) -C tests -f Makefile.verilator purge
	$(eval top := $(shell echo $@ | cut -d '_' -f 2- | tr '[:lower:]' '[:upper:]'))
	$(MAKE) -C tests -f Makefile.verilator TOPLEVEL=$(top) MODULE=$@ WAVES=$(WAVES)

clean:
	$(MAKE) -C tests -f Makefile.verilator purge
	find . -name __pycache__ -exec rm -fR {} +
