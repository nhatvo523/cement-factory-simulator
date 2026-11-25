# Đối chiếu vân tay — Pha B ghép nhiệt

So sánh 65 kịch bản đăng ký trên cấu hình plant mặc định. Vân tay bao gồm `time_s`, `equipment`, `balance` và `events`, nên cả 65 vân tay bật cờ đổi vì có thêm trường nội bộ. Khi tắt cờ, 65/65 vân tay khớp fixture đã ghi ở Pha A.

Trong 65 kịch bản, **14** đổi lưu lượng/tồn kho/độ ẩm hoặc đại lượng cân bằng theo thiết bị, **26** có chuyển damper bypass, và **8** đổi ít nhất một trạng thái chạy hoặc lý do trip. Các nhóm có thể trùng. So sánh trường vật lý cũ dùng sai số tuyệt đối 1e-8 cho danh sách này. Kiểm thử baseline dùng sai số riêng theo đơn vị trong plant.

Ở baseline, dòng vật liệu, tồn kho, giới hạn bốc hơi, độ ẩm, lưu lượng khí và trạng thái vận hành đạt dung sai đã khai báo. Vân tay đầy đủ vẫn đổi do trường nhiệt/chất lượng mới. Các ca kiểm chứng tổng hợp reset thủy lực, thiếu nhiệt sâu và thiếu nhiên liệu một phần nằm trong test, ngoài 65 kịch bản đã đăng ký.

| Kịch bản | Vật liệu đổi | Có bypass | Trạng thái đổi | Lý do chính |
|---|---|---|---|---|
| `baseline` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `crusher_stop` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `fan_derate` | Có | — | — | Thay đổi gió điều chỉnh nhiệt sấy khả dụng, giới hạn cấp hoặc độ ẩm. |
| `downstream_feed_stop` | Có | Có | Có | Chặn xả SL-301 làm đổi độ đầy, tải lò và nhu cầu sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `crusher_rotor_jam` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `crusher_tool_wear` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `crusher_motor_cooling_loss` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `crusher_bearing_friction` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `crusher_oil_pressure_loss` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `crusher_vibration_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `conveyor_belt_slip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `conveyor_belt_misalignment` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `conveyor_chute_blockage` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `conveyor_scale_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `stockpile_level_false_high` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `stockpile_stacker_failure` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `reclaimer_mechanism_jam` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `reclaimer_bridge_stall` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `reclaimer_harrow_encoder_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `feed_bin_outlet_bridging` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `feed_bin_level_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `feeder_drive_jam` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `feeder_scale_bias` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `feeder_scale_loss` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `mill_roller_wear` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `mill_roller_imbalance` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `mill_hydraulic_loss` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `mill_vibration_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `separator_underspeed` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `separator_drive_trip` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. Đổi năng lực bốc hơi, lưu lượng vật liệu giữ trong sai số. |
| `fan_impeller_degradation` | Có | — | — | Thay đổi gió điều chỉnh nhiệt sấy khả dụng, giới hạn cấp hoặc độ ẩm. |
| `fan_damper_stuck` | Có | — | — | Thay đổi gió điều chỉnh nhiệt sấy khả dụng, giới hạn cấp hoặc độ ẩm. |
| `fan_bearing_overheat` | — | Có | — | RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `raw_silo_outlet_blockage` | Có | Có | Có | Chặn xả SL-301 làm đổi độ đầy, tải lò và nhu cầu sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `raw_silo_level_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `kiln_feeder_jam` | Có | Có | Có | Giảm hoặc mất cấp/nhiệt lò làm giảm nhiệt khí thải và giới hạn sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `preheater_cyclone_blockage` | Có | — | — | Tắc cyclone làm giảm cấp lò và nhiệt khí về mill. |
| `calciner_fuel_loss` | Có | Có | Có | Giảm hoặc mất cấp/nhiệt lò làm giảm nhiệt khí thải và giới hạn sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `kiln_drive_trip` | Có | Có | Có | Giảm hoặc mất cấp/nhiệt lò làm giảm nhiệt khí thải và giới hạn sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `kiln_burner_fuel_loss` | Có | Có | Có | Giảm hoặc mất cấp/nhiệt lò làm giảm nhiệt khí thải và giới hạn sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `cooler_airflow_loss` | Có | — | — | Giảm làm nguội/thu hồi nhiệt tác động nhiệt vùng nung và sấy. |
| `cooler_grate_jam` | Có | Có | Có | Giảm làm nguội/thu hồi nhiệt tác động nhiệt vùng nung và sấy. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `kiln_id_fan_trip` | Có | Có | Có | Thay đổi gió điều chỉnh nhiệt sấy khả dụng, giới hạn cấp hoặc độ ẩm. RM-201 ngừng chạy, damper chuyển bypass và đổi trở lực. |
| `kiln_id_fan_derate` | Có | — | — | Thay đổi gió điều chỉnh nhiệt sấy khả dụng, giới hạn cấp hoặc độ ẩm. |
| `clinker_silo_outlet_blockage` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `clinker_silo_level_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_mill_a_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_mill_b_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bag_packer_jam` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bulk_loading_stop` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_feeder_a_jam` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_feeder_b_jam` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_mill_a_wear` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_mill_b_wear` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_separator_a_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_separator_b_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_fan_a_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_fan_b_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_silo_gate_blockage` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `cement_silo_level_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bag_feeder_jam` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bag_conveyor_trip` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bag_loader_stop` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `bulk_feeder_jam` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |
| `truck_scale_signal_loss` | — | — | — | Chỉ thêm trạng thái nhiệt/chất lượng hoặc thay giá trị nhiệt nội bộ. |

### Các kịch bản làm thay đổi vật liệu

`fan_derate`, `downstream_feed_stop`, `fan_impeller_degradation`, `fan_damper_stuck`, `raw_silo_outlet_blockage`, `kiln_feeder_jam`, `preheater_cyclone_blockage`, `calciner_fuel_loss`, `kiln_drive_trip`, `kiln_burner_fuel_loss`, `cooler_airflow_loss`, `cooler_grate_jam`, `kiln_id_fan_trip`, `kiln_id_fan_derate`.
