# Đối chiếu vân tay — Pha B ghép nhiệt

Báo cáo lịch sử so sánh 65 kịch bản ở Pha B, khi ST-101 mặc định 35 t. Phép đối chiếu khi đó dùng `time_s`, `equipment`, `balance` và `events`. Khi bật ghép nhiệt, cả 65 vân tay đổi do có thêm trường nội bộ. Khi tắt cờ, 65/65 vân tay khớp fixture Pha A. Bộ hồi quy hiện hành tách vân tay vật liệu và nhiệt/chất lượng cho 68 ca, với tồn đầu ghim 35 t. Mô phỏng mặc định hiện khởi tạo 48 t. [Giới hạn hiện hành](Specification.md#giới-hạn-đã-biết)

Trong 65 kịch bản, **14** đổi lưu lượng/tồn kho/độ ẩm hoặc đại lượng cân bằng theo thiết bị, **26** từng có chuyển damper bypass ở bản Pha B ban đầu, và **8** đổi ít nhất một trạng thái chạy hoặc lý do trip. Các nhóm có thể trùng. So sánh trường vật lý cũ dùng sai số tuyệt đối 1e-8 cho danh sách này. Kiểm thử baseline dùng sai số riêng theo đơn vị trong plant.

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

### Các kịch bản làm thay đổi vật liệu ở Pha B

`fan_derate`, `downstream_feed_stop`, `fan_impeller_degradation`, `fan_damper_stuck`, `raw_silo_outlet_blockage`, `kiln_feeder_jam`, `preheater_cyclone_blockage`, `calciner_fuel_loss`, `kiln_drive_trip`, `kiln_burner_fuel_loss`, `cooler_airflow_loss`, `cooler_grate_jam`, `kiln_id_fan_trip`, `kiln_id_fan_derate`.

## Rà soát trước Bước 3 — Bypass và nguyên nhân gốc

Bảng dưới xác nhận nguyên nhân RM-201 dừng ở cả 26 ca từ báo cáo ban đầu. Mốc là frame đầu tiên thấy damper bắt đầu chuyển ở phiên bản Pha B trước sửa. Sau khi thêm điều kiện lò còn cấp liệu, **19 ca còn chuyển khi lò đang chạy**; **7 ca bị chặn hoàn toàn**. Trong 19 ca còn chuyển, lệnh được bỏ khi lò hết liệu. Kiểm thử quét tất cả frame của 65 kịch bản.

| Kịch bản | Mốc cũ (s) | Nguyên nhân RM-201 dừng | Bypass sau sửa |
|---|---:|---|---|
| `crusher_stop` | 2460 | Crusher dừng, BN-101 cạn nên RM-201 hết liệu | Còn |
| `crusher_rotor_jam` | 2460 | Rotor crusher kẹt, BN-101 cạn sau khi hết đệm | Còn |
| `crusher_motor_cooling_loss` | 2880 | Mất làm mát crusher dẫn đến thiếu nguyên liệu và BN-101 cạn | Còn |
| `crusher_bearing_friction` | 2820 | Ma sát ổ trục làm crusher suy giảm/dừng. BN-101 cạn | Còn |
| `crusher_oil_pressure_loss` | 2520 | Mất áp suất dầu chặn cấp từ crusher. BN-101 cạn | Còn |
| `conveyor_belt_misalignment` | 2460 | Lệch băng dừng cấp lên kho. BN-101 cạn sau khi dùng tồn | Còn |
| `conveyor_chute_blockage` | 2400 | Tắc máng làm ngừng dòng bổ sung. BN-101 cạn | Còn |
| `stockpile_level_false_high` | 2400 | Mức cao giả chặn nhận liệu vào kho. Tuyến dùng hết đệm BN-101 | Còn |
| `stockpile_stacker_failure` | 2400 | Máy rải hỏng, kho thiếu bổ sung. BN-101 cạn | Còn |
| `reclaimer_mechanism_jam` | 1140 | Reclaimer kẹt. BN-101 cạn dù phía kho còn liệu | Còn |
| `reclaimer_bridge_stall` | 1140 | Cầu reclaimer đứng. BN-101 cạn | Còn |
| `feed_bin_outlet_bridging` | 780 | BN-101 còn tồn nhưng vòm liệu chặn cửa xả | Còn |
| `feeder_drive_jam` | 780 | WF-201 kẹt, liệu trong BN-101 không tới mill | Còn |
| `feeder_scale_loss` | 780 | Mất cân WF-201 kích hoạt liên động dừng cấp dù BN-101 còn tồn | Còn |
| `mill_roller_imbalance` | 720 | RM-201 trip bảo vệ rung cao | Còn |
| `mill_hydraulic_loss` | 660 | RM-201 trip áp lực thủy lực thấp | Còn |
| `separator_drive_trip` | 660 | SP-201 trip làm tuyến nghiền bị chặn | Còn |
| `fan_bearing_overheat` | 780 | FN-201 trip nhiệt ổ trục, RM-201 mất điều kiện gió | Còn |
| `downstream_feed_stop` | 1620 | KF-301 ngừng, lò dừng cấp. SL-301 đầy rồi chặn RM-201 | Chặn |
| `raw_silo_outlet_blockage` | 1620 | SL-301 nghẽn xả, lò mất liệu. Silo đầy rồi chặn RM-201 | Chặn |
| `kiln_feeder_jam` | 1620 | KF-301 kẹt, lò mất liệu. SL-301 đầy rồi chặn RM-201 | Chặn |
| `calciner_fuel_loss` | 1620 | PC-301 mất nhiên liệu làm tuyến nung ngừng nhận liệu. SL-301 đầy rồi chặn RM-201 | Chặn |
| `kiln_drive_trip` | 1620 | KL-301 trip ngừng nhận liệu. SL-301 đầy rồi chặn RM-201 | Chặn |
| `kiln_burner_fuel_loss` | 1620 | KL-301 mất nhiên liệu và ngừng nhận liệu. SL-301 đầy rồi chặn RM-201 | Chặn |
| `cooler_grate_jam` | 1620 | CL-301 kẹt ghi, tuyến nung bị chặn. SL-301 đầy rồi chặn RM-201 | Chặn |
| `kiln_id_fan_trip` | 1860 | CF-301 trip làm hệ nung mất draft. SL-301 đầy rồi chặn RM-201 | Chặn |

## Lý do vật lý cho 14 ca đổi vật liệu và 8 ca đổi trạng thái

So sánh Pha B đã sửa với cờ ghép nhiệt tắt. Cột trạng thái là những chuyển đổi xuất hiện ở ít nhất một frame trong so sánh, không nhất thiết là trạng thái cuối.

| Kịch bản | Nguyên nhân đổi vật liệu | Nguyên nhân đổi trạng thái |
|---|---|---|
| `fan_derate` | FN-201 giảm gió do giảm đặt lưu lượng. Năng lực bốc hơi giảm và mill chạy ở sàn tải khi thiếu sâu, làm bột ra ẩm hơn. | — |
| `downstream_feed_stop` | KF-301 ngừng nhận. Nhiệt sấy giảm dần và tồn SL-301 chạm đầy theo quỹ đạo mới. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi hết chỗ nhận. |
| `fan_impeller_degradation` | Cánh FN-201 suy giảm làm giảm gió vận chuyển/sấy. Sàn tải và giới hạn bốc hơi làm đổi lượng và độ ẩm bột liệu. | — |
| `fan_damper_stuck` | Damper FN-201 kẹt thấp làm giảm gió. Năng lực bốc hơi giảm và lượng cấp chịu giới hạn sấy mới. | — |
| `raw_silo_outlet_blockage` | Cửa xả SL-301 bị nghẽn. Lò thiếu liệu và mất nhiệt hồi theo quán tính trong khi tồn phía sản xuất tích lại. | WF-201/RM-201 RUNNING → STOPPED khi hết chỗ nhận. SL-301 vẫn báo OUTLET_BLOCKED. |
| `kiln_feeder_jam` | KF-301 kẹt. Lò mất cấp làm nhiệt hồi giảm dần. Dòng bột liệu vào kho khác Pha A trước khi chạm đầy. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi đầy. |
| `preheater_cyclone_blockage` | Tắc cyclone giảm năng lực tuyến nung. Nhiệt hồi và giới hạn cấp sấy đổi theo tải mới, kéo theo lưu lượng và tồn kho khác. | — |
| `calciner_fuel_loss` | PC-301 mất nhiên liệu, tuyến nung ngừng nhận liệu. Nhiệt hồi mất dần, đổi tốc độ nạp bột vào SL-301. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi đầy. |
| `kiln_drive_trip` | Truyền động KL-301 trip, tuyến nung ngừng. Nhiệt còn lại tiếp tục hỗ trợ sấy trong thời gian ngắn trước khi SL-301 đầy. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi đầy. |
| `kiln_burner_fuel_loss` | Mất nhiên liệu vòi đốt chính làm ngừng cấp nung. Nhiệt vùng nung/khí thải suy giảm theo thời gian và đổi tốc độ tích bột. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi đầy. |
| `cooler_airflow_loss` | CL-301 thiếu gió làm giảm dòng clinker và nhiệt thu hồi. Suất nhiên liệu, tải lò và nhiệt hồi đổi, sau đó tác động sấy. | — |
| `cooler_grate_jam` | Ghi CL-301 kẹt chặn cả tuyến nung. Mất clinker qua ghi làm giảm nhiệt thu hồi và thay đổi tốc độ lấp SL-301. | SL-301 AVAILABLE → FULL; WF-201/RM-201 RUNNING → STOPPED khi đầy. |
| `kiln_id_fan_trip` | CF-301 mất draft tức thời. Nhiệt tích trong đường khí/mill giảm chậm, duy trì bốc hơi và cấp liệu lâu hơn Pha A. | SL-301 AVAILABLE → FULL sớm hơn do RM-201 còn nhận nhiệt dư. |
| `kiln_id_fan_derate` | CF-301 giảm gió và draft. Load lò giảm, đồng thời nhiệt thu hồi có quán tính làm dòng RM-201 khác Pha A. | — |

## Vân tay hồi quy tách riêng

Fixture `tests/phase_b_solver_fingerprints.json` chốt sau sửa bypass, trước khi chiếu số đo Bước 3. Vân tay **vật liệu** gồm lưu lượng vật liệu, tồn kho, cân bằng, sự kiện và trạng thái/liên động. Vân tay **nhiệt/chất lượng** gồm nhiệt độ, áp suất, lưu lượng khí, trạng thái tuyến khí, độ ẩm, free lime và mẫu lab. Kiểm thử hồi quy kiểm riêng hai vân tay. Vân tay đầy đủ Pha A vẫn dùng để kiểm cờ ghép nhiệt tắt.
