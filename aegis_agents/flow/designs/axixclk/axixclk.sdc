create_clock -name M_AXI_ACLK -period 0.5700 [get_ports M_AXI_ACLK]
create_clock -name S_AXI_ACLK -period 0.4200 [get_ports S_AXI_ACLK]
set_clock_groups -asynchronous -group {S_AXI_ACLK} -group {M_AXI_ACLK}
