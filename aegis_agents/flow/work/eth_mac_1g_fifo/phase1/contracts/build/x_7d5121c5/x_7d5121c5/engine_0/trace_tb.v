`ifndef VERILATOR
module testbench;
  reg [4095:0] vcdfile;
  reg clock;
`else
module testbench(input clock, output reg genclock);
  initial genclock = 1;
`endif
  reg genclock = 1;
  reg [31:0] cycle = 0;
  reg [0:0] PI_tx_clk_enable;
  reg [0:0] PI_gmii_rx_er;
  reg [0:0] PI_rx_rst;
  reg [0:0] PI_logic_clk;
  reg [0:0] PI_tx_axis_tvalid;
  reg [0:0] PI_tx_axis_tlast;
  reg [0:0] PI_tx_mii_select;
  reg [7:0] PI_cfg_ifg;
  reg [0:0] PI_rx_clk_enable;
  reg [0:0] PI_tx_rst;
  reg [0:0] PI_logic_rst;
  reg [0:0] PI_rx_mii_select;
  reg [7:0] PI_tx_axis_tdata;
  reg [0:0] PI_tx_axis_tkeep;
  reg [0:0] PI_rx_clk;
  reg [7:0] PI_gmii_rxd;
  reg [0:0] PI_cfg_tx_enable;
  reg [0:0] PI_gmii_rx_dv;
  reg [0:0] PI_cfg_rx_enable;
  reg [0:0] PI_tx_clk;
  reg [0:0] PI_tx_axis_tuser;
  reg [0:0] PI_rx_axis_tready;
  aegis_formal_top UUT (
    .tx_clk_enable(PI_tx_clk_enable),
    .gmii_rx_er(PI_gmii_rx_er),
    .rx_rst(PI_rx_rst),
    .logic_clk(PI_logic_clk),
    .tx_axis_tvalid(PI_tx_axis_tvalid),
    .tx_axis_tlast(PI_tx_axis_tlast),
    .tx_mii_select(PI_tx_mii_select),
    .cfg_ifg(PI_cfg_ifg),
    .rx_clk_enable(PI_rx_clk_enable),
    .tx_rst(PI_tx_rst),
    .logic_rst(PI_logic_rst),
    .rx_mii_select(PI_rx_mii_select),
    .tx_axis_tdata(PI_tx_axis_tdata),
    .tx_axis_tkeep(PI_tx_axis_tkeep),
    .rx_clk(PI_rx_clk),
    .gmii_rxd(PI_gmii_rxd),
    .cfg_tx_enable(PI_cfg_tx_enable),
    .gmii_rx_dv(PI_gmii_rx_dv),
    .cfg_rx_enable(PI_cfg_rx_enable),
    .tx_clk(PI_tx_clk),
    .tx_axis_tuser(PI_tx_axis_tuser),
    .rx_axis_tready(PI_rx_axis_tready)
  );
`ifndef VERILATOR
  initial begin
    if ($value$plusargs("vcd=%s", vcdfile)) begin
      $dumpfile(vcdfile);
      $dumpvars(0, testbench);
    end
    #5 clock = 0;
    while (genclock) begin
      #5 clock = 0;
      #5 clock = 1;
    end
  end
`endif
  initial begin
`ifndef VERILATOR
    #1;
`endif
    UUT.aegis_init = 1'b1;
    UUT.chk.f_ok = 8'b00000000;
    UUT.chk.past_ptr = 2'b00;
    // UUT.dut.$auto$async2sync.\cc:253:execute$1741  = 2'b00;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.crc_state = 32'b11111111111111111111111111111111;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.error_bad_fcs_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.error_bad_frame_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_dv_d0 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_dv_d1 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_dv_d2 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_dv_d3 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_dv_d4 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_er_d0 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_er_d1 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_er_d2 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_er_d3 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rx_er_d4 = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rxd_d0 = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rxd_d1 = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rxd_d2 = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rxd_d3 = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.gmii_rxd_d4 = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.in_frame = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.m_axis_tdata_reg = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.m_axis_tlast_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.m_axis_tuser_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.m_axis_tvalid_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.mii_odd = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.start_packet_int_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.start_packet_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_rx_inst.state_reg = 3'b000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.crc_state = 32'b11111111111111111111111111111111;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.error_underflow_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.frame_error_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.frame_min_count_reg = 6'b000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.frame_ptr_reg = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.frame_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.gmii_tx_en_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.gmii_tx_er_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.gmii_txd_reg = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.mii_msn_reg = 4'b0000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.mii_odd_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.s_axis_tready_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.s_tdata_reg = 8'b00000000;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.start_packet_int_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.start_packet_reg = 1'b0;
    UUT.dut.eth_mac_1g_inst.axis_gmii_tx_inst.state_reg = 3'b000;
    // UUT.dut.tx_fifo.fifo_inst.$auto$async2sync.\cc:253:execute$1737  = 1'b1;
    // UUT.dut.tx_fifo.fifo_inst.$auto$async2sync.\cc:253:execute$1739  = 1'b1;
    UUT.dut.tx_fifo.fifo_inst.bad_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.bad_frame_sync1_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.bad_frame_sync2_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.bad_frame_sync3_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.bad_frame_sync4_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.drop_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.good_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.good_frame_sync1_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.good_frame_sync2_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.good_frame_sync3_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.good_frame_sync4_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.\m_axis_pipe_reg[0]  = 10'b0000000000;
    UUT.dut.tx_fifo.fifo_inst.\m_axis_pipe_reg[1]  = 10'b0000000000;
    UUT.dut.tx_fifo.fifo_inst.m_axis_tvalid_pipe_reg = 2'b00;
    UUT.dut.tx_fifo.fifo_inst.m_depth_commit_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.m_depth_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.m_drop_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.m_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.m_rst_sync2_reg = 1'b1;
    UUT.dut.tx_fifo.fifo_inst.m_rst_sync3_reg = 1'b1;
    UUT.dut.tx_fifo.fifo_inst.m_terminate_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.mark_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.overflow_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.overflow_sync1_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.overflow_sync2_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.overflow_sync3_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.overflow_sync4_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.rd_ptr_conv_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.rd_ptr_gray_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.rd_ptr_gray_sync1_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.rd_ptr_gray_sync2_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.rd_ptr_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.s_depth_commit_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.s_depth_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.s_frame_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.s_rst_sync2_reg = 1'b1;
    UUT.dut.tx_fifo.fifo_inst.s_rst_sync3_reg = 1'b1;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_commit_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_commit_sync_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_conv_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_gray_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_gray_sync1_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_gray_sync2_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_sync_commit_reg = 7'b0000000;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_ack_sync1_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_ack_sync2_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_sync1_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_sync2_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_sync3_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.wr_ptr_update_valid_reg = 1'b0;
    UUT.dut.tx_fifo.fifo_inst.mem[6'b000000] = 10'b0010001000;

    // state 0
    PI_tx_clk_enable = 1'b0;
    PI_gmii_rx_er = 1'b0;
    PI_rx_rst = 1'b1;
    PI_logic_clk = 1'b0;
    PI_tx_axis_tvalid = 1'b0;
    PI_tx_axis_tlast = 1'b0;
    PI_tx_mii_select = 1'b0;
    PI_cfg_ifg = 8'b00000000;
    PI_rx_clk_enable = 1'b0;
    PI_tx_rst = 1'b0;
    PI_logic_rst = 1'b0;
    PI_rx_mii_select = 1'b1;
    PI_tx_axis_tdata = 8'b00000000;
    PI_tx_axis_tkeep = 1'b0;
    PI_rx_clk = 1'b0;
    PI_gmii_rxd = 8'b00000010;
    PI_cfg_tx_enable = 1'b0;
    PI_gmii_rx_dv = 1'b1;
    PI_cfg_rx_enable = 1'b0;
    PI_tx_clk = 1'b0;
    PI_tx_axis_tuser = 1'b1;
    PI_rx_axis_tready = 1'b0;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b1;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b0;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b11010101;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b1;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 2
    if (cycle == 1) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b1;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b0;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b00000000;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b1;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 3
    if (cycle == 2) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b1;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b01000000;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b1;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 4
    if (cycle == 3) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b1;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b1;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b00001111;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b0;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 5
    if (cycle == 4) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b1;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b1;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b10000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b00000001;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b0;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 6
    if (cycle == 5) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b1;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b1;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b10001000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b00010000;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b0;
      PI_cfg_rx_enable <= 1'b1;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b0;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 7
    if (cycle == 6) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b1;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b01111000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b01011101;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b0;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b1;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 8
    if (cycle == 7) begin
      PI_tx_clk_enable <= 1'b1;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b1;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b1;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b0;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00010000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b01011101;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b1;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b0;
      PI_rx_axis_tready <= 1'b0;
    end

    // state 9
    if (cycle == 8) begin
      PI_tx_clk_enable <= 1'b0;
      PI_gmii_rx_er <= 1'b0;
      PI_rx_rst <= 1'b0;
      PI_logic_clk <= 1'b0;
      PI_tx_axis_tvalid <= 1'b0;
      PI_tx_axis_tlast <= 1'b0;
      PI_tx_mii_select <= 1'b0;
      PI_cfg_ifg <= 8'b00000000;
      PI_rx_clk_enable <= 1'b0;
      PI_tx_rst <= 1'b0;
      PI_logic_rst <= 1'b0;
      PI_rx_mii_select <= 1'b0;
      PI_tx_axis_tdata <= 8'b00000000;
      PI_tx_axis_tkeep <= 1'b0;
      PI_rx_clk <= 1'b0;
      PI_gmii_rxd <= 8'b00000000;
      PI_cfg_tx_enable <= 1'b0;
      PI_gmii_rx_dv <= 1'b0;
      PI_cfg_rx_enable <= 1'b0;
      PI_tx_clk <= 1'b0;
      PI_tx_axis_tuser <= 1'b0;
      PI_rx_axis_tready <= 1'b0;
    end

    genclock <= cycle < 9;
    cycle <= cycle + 1;
  end
endmodule
