ECP5_VARIANT?=25k
PACKAGE?=CABGA256
OPENOCD_CONFIG?=../lfe5u12.cfg
TAP?=lfe5u12.tap
IDCODE?=--idcode 0x21111043
SPEED?=8
LPF_FILE?=../pergola.lpf
ACM_DEVICE?=/dev/ttyACM0
TOP_MODULE?=top

all: $(PROJ).bit

%.json: %.v
	yosys \
	-p "hierarchy -top $(TOP_MODULE)" \
	-p "synth_ecp5 -noccu2 -nobram -nomux -json $@" $<

%_out.config: %.json
	nextpnr-ecp5 --json $< --textcfg $@ --$(ECP5_VARIANT) --package $(PACKAGE) --lpf $(LPF_FILE) --speed $(SPEED)

%.bit: %_out.config
	ecppack $(IDCODE) --svf $(PROJ).svf $< $@

$(PROJ).svf : $(PROJ).bit

prog_openocd: $(PROJ).svf
	openocd -f $(OPENOCD_INTERFACE) -f $(OPENOCD_CONFIG) -c "transport select jtag; adapter_khz 10000; init; svf  -tap $(TAP) -quiet -progress $<; exit"

prog: $(PROJ).bit
	stty -F $(ACM_DEVICE) 300 raw -clocal -echo icrnl
	sleep 0.1
	echo "$(shell stat -c%s $^)" > $(ACM_DEVICE)
	cat $^ > $(ACM_DEVICE)
	sync


clean:
	rm -f *.svf *.bit *.config *.json

.PHONY: prog clean
