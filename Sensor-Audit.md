# Kiểm kê tín hiệu equipment — Bước 0

Mốc khảo sát là `f1bc06b`. Bảng bao phủ 33 equipment, 4 zone và 7 line. Đã quét các frame của 65 kịch bản đăng ký, gồm baseline và 64 kịch bản lỗi, sau đó đối chiếu với backend, cấu hình plant, phần hiển thị Explorer, đặc tả và test. Các nhóm A/B/C/D bên dưới là **đề xuất để duyệt**. Các tag ở cột D chưa được triển khai.

- **A** — Kênh có phép đo hoặc phản hồi thiết bị tương ứng, giữ tên/ý nghĩa hiện tại. Việc thêm metadata và chuẩn hóa hành vi phổ biến sẽ thực hiện ở bước sau.
- **B** — Có thể đo bằng phần cứng thực tế, nhưng cần chốt vị trí, hiệu chỉnh cách mô phỏng hoặc loại kênh trùng. Chỉ đưa vào danh mục SCADA khi xác định được điểm đo.
- **C** — Biến solver, chỉ số ước tính hoặc chẩn đoán tổng hợp. Giữ nội bộ. Trạng thái PLC, mã trip và chất lượng tín hiệu được xem xét riêng, bên dưới.
- **D** — Kênh cần bổ sung trên equipment hiện có. Các hạng mục tùy cấu hình nhà máy được đánh dấu rõ.

## Trạng thái sau Bước 1

| Hạng mục đã duyệt | Kết quả |
|---|---|
| A/B/C · Danh mục công bố | Một danh mục tại `configs/operating_profiles/equipment_tags.json`. API và export mặc định chỉ trả các tag trong danh mục. Explorer dùng nhãn, đơn vị và cờ hiển thị từ danh mục. |
| A/B · CF-301 | Chuyển magnitude draft hiện có sang áp suất gauge có dấu tại cửa hút, đơn vị Pa. Quạt dừng trả 0 theo mô hình hiện tại. |
| B · PK-501 | Công bố bộ đếm nguyên mô phỏng qua các mốc hoàn tất bao, và chênh bộ đếm trong cửa sổ tối đa 60 giây. Mốc hoàn tất được suy từ khối lượng đang đóng và khối lượng danh định mỗi bao. Kết quả không phản hồi về solver. |
| C/D · RM-201 | Giữ hệ số nhiệt khả dụng trong solver. Nhiệt độ khí vào và ra chưa có nguồn đo phù hợp, chuyển sang Bước 2. |
| B/C · SL-401 | Phương án A. Hai ô A/B có tag mức riêng theo % chiều cao quy ước. Mô hình hiện dùng quan hệ tuyến tính với phần khối lượng của từng ô sau lấy mẫu và giới hạn mức trong miền 0–100%. Tồn theo mác và tồn tổng tấn giữ nội bộ. |
| C · Trạng thái và sự kiện | RUN/TRIP là tag riêng từ trạng thái thiết bị. Lý do trip, sự kiện chèn lỗi, tình trạng solver và cân bằng vật chất chỉ có trong `ground_truth` khi bật rõ ràng. |
| D · Hạng mục chuyển tiếp | Giữ toàn bộ đề xuất bổ sung điểm đo ở cột D cho Bước 2. Dải tag Bước 1 là dải cấu hình giả định. Hiệu chuẩn theo OEM, bão hòa, độ trễ và đáp ứng tín hiệu thuộc các bước sau. |

Hiện công bố 147 tag (Z01: 52, Z02: 33, Z03: 34, Z04: 28). Trong 181 cặp thiết bị/trường đo cũ, 92 tên trường không còn công bố theo dạng cũ, gồm các trường đã loại và trường đã đổi điểm đo. Ngoài số này, toàn bộ bản sao trạng thái vật lý từng thiết bị đã rời payload mặc định. Hai bảng và phụ lục bên dưới giữ nguyên mốc Bước 0 để đối chiếu.

## Bề mặt dữ liệu trước Bước 1

| Bề mặt | Dữ liệu hiện có |
|---|---|
| `POST /api/live-operation` | `measurements`, trạng thái thiết bị, lý do chờ/trip, cảnh báo quá trình và lỗi đã chèn. `measurements` vẫn có kênh C. |
| `GET /api/simulation`, `GET /api/operation`, CLI export JSON | Dùng chung `build_result()`. Mỗi frame trả cả `measurements` và toàn bộ trạng thái solver trong `equipment`, cùng cân bằng vật chất và sự kiện. |
| Explorer | Đọc API live. Ngoài số đo, UI hiển thị tình trạng/lỗi, tồn từng mác và lượng đã thu hồi trong phiên. RC-101 lấy thêm tồn kho ST-101. BC-101 đổi nhãn tồn/mức/ẩm mô hình thành các thông số trên băng. |

**Quy ước chung cho bảng.** C áp dụng cho mọi equipment có trường tương ứng trong export: công suất cấu hình/khả dụng `configured_capacity_tph`, `effective_capacity_tph`; lưu lượng khí danh định `nominal_airflow_m3_s`; các cột template của solver như `fresh_inlet_tph`, `recycle_tph`, độ ẩm vào/ra hoặc nước bay hơi được giữ nội bộ khi điểm đo cụ thể chưa được xác nhận. Một tên có trong cả hai nhóm payload (ví dụ `outlet_tph`) có thể là số đo hợp lệ **trong `measurements`**, còn bản giá trị vật lý gốc trong `equipment` vẫn là nội bộ. Phụ lục liệt kê tên trường thực tế.

`signal_quality` là metadata của phép đo. `operating_state` hiện là trạng thái tổng hợp; khi có I/O phản hồi, đề xuất chuyển SCADA sang bit **RUN/TRIP** và giữ `trip_reason` như sự kiện PLC. `active_faults`, `health_state`, `waiting_reason`, `process_notice` và trạng thái tổng hợp `drive.condition` không phải giá trị đo. Lỗi đã chèn vẫn có thể hiển thị trong phần điều khiển kịch bản, tách khỏi bảng sensor. Một giá trị `condition` chỉ giữ ở nhóm B khi ánh xạ được về tiếp điểm hoặc trạng thái phản hồi cụ thể.

## Z02 — Sản xuất clinker

| Equipment | A — Giữ | B — Hiệu chỉnh/định vị | C — Nội bộ | D — Bổ sung |
|---|---|---|---|---|
| SL-301 | — | Mức liên tục: gộp `level_fraction` và tag mức của component thành một điểm radar; lưu lượng vào/ra chỉ khi có cân thật | Tồn tấn từ thể tích/cân bằng; ẩm tồn | Mức radar theo m hoặc % chiều cao đã hiệu chuẩn; công tắc H/L |
| KF-301 | Tốc độ băng; lưu lượng cấp lò từ băng cân | Xác nhận dải đo lưu lượng, vùng lưu lượng thấp và trạng thái mất tín hiệu | Bản sao lưu lượng vào, tải khả dụng | Dòng motor; RUN/TRIP |
| PH-301 | — | ΔP cyclone, nhiệt độ đầu ra và lưu lượng liệu: xác định tầng/vị trí lấy áp, loại nhiệt đo và dùng chung tag cân KF-301 nếu cùng điểm cấp | `heat_fraction`, CO₂ tính toán | Nhiệt độ khí và áp suất gauge từng tầng; ΔP qua từng tầng có đủ hai đầu lấy áp |
| PC-301 | — | Lưu lượng nhiên liệu theo cân cấp hoặc lưu lượng kế; nhiệt đầu ra ghi rõ nhiệt độ khí; lưu lượng liệu ra hiện suy từ phản ứng | Lưu lượng liệu ra và CO₂ làm biến nội bộ nếu thiếu điểm cân | Áp suất gauge, nhiệt gió ba, vị trí damper/khí nếu thuộc tuyến PC-301; phản hồi ngọn lửa nếu có |
| KL-301 | Tốc độ quay lò | Lưu lượng nhiên liệu hiện suy từ tải và nhiệt thu hồi: chỉ giữ nếu gắn điểm đo nhiên liệu; lưu lượng clinker nên lấy tag cân tại điểm chuyển tải đã xác định | Nhiệt độ bulk vùng nung hiện là tham số, clinker ra theo solver và nhiệt thu hồi | Dòng/công suất truyền động, RUN/TRIP, nhiệt khí đầu vào lò và áp suất chụp lò; pyrometer bề mặt là tùy chọn với tag riêng |
| CL-301 | Tốc độ ghi | Nhiệt clinker đầu ra: định nghĩa vị trí/kiểu đo; lưu lượng gió theo điểm đo ống; clinker ra chỉ giữ nếu có cân | `thermal_power_kw`, `recovered_heat_kw`, dòng clinker chưa có cân | Áp dưới ghi theo khoang, dòng motor, RUN/TRIP; nhiệt gió thu hồi tại điểm đo |
| CF-301 | Tốc độ, nhiệt ổ trục | Lưu lượng khí cần xác định điều kiện thể tích; độ mở damper phải là feedback; `draft_suction_pa` hiện là độ lớn suy từ lưu lượng, đề xuất áp suất gauge có dấu tại cửa hút hoặc phép đo ΔP riêng | Lưu lượng khí danh định, trạng thái tổng hợp | Dòng/công suất, rung, áp suất đầu hút/xả, RUN/TRIP |
| SL-302 | — | Mức radar và lưu lượng theo cùng nguyên tắc SL-301; cửa xả cần phản hồi hành trình nếu hiển thị | Tồn tấn, ẩm tồn, trạng thái bridging suy luận | Mức radar và công tắc H/L, feedback cửa xả nếu áp dụng |

## Z01 — Nguyên liệu

| Equipment | A — Giữ | B — Hiệu chỉnh/định vị | C — Nội bộ | D — Bổ sung |
|---|---|---|---|---|
| CR-101 | Dòng motor, nhiệt cuộn dây, nhiệt hai ổ trục, tốc độ rotor, áp suất dầu, rung RMS | Lưu lượng vào/ra chỉ giữ khi có cân tương ứng; độ ẩm đầu vào chỉ giữ khi có thiết bị đo ẩm trên dòng, nếu không chuyển sang nội bộ hoặc lab | Độ mòn búa/rotor, công suất khả dụng | Công suất điện, RUN/TRIP |
| BC-101 | Tốc độ băng; tín hiệu lệch băng | Một tốc độ/lưu lượng chuẩn từ encoder/cân băng. Gộp lưu lượng vào/ra trùng. Máng tắc chỉ công bố khi có công tắc tắc máng | Khối lượng trong đoạn băng, độ đầy băng, ẩm tồn | Tải băng kg/m nếu cân hỗ trợ, dòng motor, RUN/TRIP |
| ST-101 | — | Mức kho phải là chiều cao tại vị trí đo, không suy tuyến tính từ tổng tấn. Tốc độ stacker tương đối cần quy về feedback; lưu lượng chuyển tải chỉ giữ ở điểm thực sự có cân | Tồn toàn đống, ẩm tồn, lưu lượng ước tính | Radar/đo khoảng cách, công tắc H/L tại điểm cấp/rút phù hợp |
| RC-101 | Dòng và tốc độ xích, vị trí/tốc độ bridge và harrow, công tắc cuối hành trình | Chiều di chuyển là feedback. Lưu lượng chỉ giữ khi nối với cân thực. `reclaimed_total_t` chỉ giữ nếu là totalizer của cân đó, cùng quy tắc reset; hiện là tích phân theo phiên | Tồn kho ST-101 gắn sang RC-101, tổng phiên nếu không có totalizer, chẩn đoán liên động tổng hợp | RUN/TRIP, phản hồi contactor/encoder theo cụm |
| BN-101 | — | Radar mức và tag component đang trùng. Cân vào/ra và máng tắc chỉ công bố có điểm I/O tương ứng | Tồn tấn, ẩm tồn, trạng thái bridging suy luận | Radar mức, công tắc H/L |
| WF-201 | Tốc độ băng cân, lưu lượng cân ra | Lưu lượng vào đang là số cùng tuyến, chỉ giữ thêm nếu có cân thứ hai | Lưu lượng vào trùng và biến solver | Dòng/công suất, RUN/TRIP; mẫu lab hóa liệu có timestamp, tách khỏi tín hiệu online |
| RM-201 | Dòng motor, áp lực thủy lực, rung | Cấp mới nên tham chiếu cân WF-201; lưu lượng vào/ra gộp chứa hồi lưu nên chỉ giữ nếu thực sự có cân tại điểm đo. Ẩm đầu ra chỉ giữ nếu có máy đo ẩm đã xác nhận | `mill_hot_gas.heat_fraction`, `recycle_tph` hiện do solver, mục tiêu ẩm, nước bay hơi và giới hạn sấy | Nhiệt khí vào/ra, ΔP mill, áp suất khí, dòng elevator tích hợp, công suất, nhiệt ổ trục, RUN/TRIP |
| SP-201 | Tốc độ rotor | Lưu lượng vào/ra và ẩm hiện là dữ liệu solver được lấy mẫu; chỉ giữ nếu có cân/thiết bị đo riêng | `fines_fraction`, `recycle_tph`, luồng/ẩm chưa có thiết bị đo | ΔP phân ly, dòng motor/đường nâng nếu có, RUN/TRIP; độ mịn lab |
| FN-201 | Tốc độ, nhiệt ổ trục | Lưu lượng khí và độ mở damper cần quy ước điểm đo và phản hồi vị trí | Lưu lượng danh định | Áp suất/ΔP, dòng/công suất, rung, RUN/TRIP |

## Z03 — Nghiền xi măng

| Equipment | A — Giữ | B — Hiệu chỉnh/định vị | C — Nội bộ | D — Bổ sung |
|---|---|---|---|---|
| WF-401A và WF-401B | Tốc độ băng | Lưu lượng clinker/thạch cao/phụ gia hiện tỷ lệ với recipe thay vì đọc riêng. Chỉ giữ từng kênh khi mô phỏng phản hồi từ cân định lượng từng dòng tích hợp. Lưu lượng tổng cần điểm cân chung hoặc giữ nội bộ | Recipe, lưu lượng thành phần chỉ suy từ recipe, tổng không có cân chung | Dòng motor, RUN/TRIP; phản hồi cân thành phần theo cấu hình đã duyệt |
| CM-401A và CM-401B | Dòng motor, rung ổ trục | Cấp mới dùng tag cân feeder nếu là cùng điểm; tổng liệu vào/ra hiện gồm hồi lưu, chỉ giữ nếu có điểm cân riêng | Lưu lượng gross chưa đo, hồi lưu solver, trạng thái truyền động suy luận | Nhiệt đầu ra/khí ra, ΔP, dòng elevator tích hợp, công suất, tốc độ, nhiệt ổ trục, RUN/TRIP |
| SP-401A và SP-401B | Tốc độ rotor | Lưu lượng vào/ra cần xác nhận cân và vị trí | Tỷ lệ hạt mịn, hồi lưu tính toán, lưu lượng chưa đo | ΔP, dòng/công suất, RUN/TRIP; độ mịn lab theo mẫu |
| FN-401A và FN-401B | Tốc độ, nhiệt ổ trục | Lưu lượng và damper theo quy ước của FN-201 | Lưu lượng danh định | Áp suất/ΔP, dòng/công suất, rung, RUN/TRIP |

## Z04 — Đóng bao và xuất hàng

| Equipment | A — Giữ | B — Hiệu chỉnh/định vị | C — Nội bộ | D — Bổ sung |
|---|---|---|---|---|
| SL-401 | — | Mức tổng hiện là khối lượng/tổng sức chứa, chưa tương đương radar. Nếu là silo nhiều ngăn vật lý, một radar chỉ đo một vị trí. Đề xuất dùng mức radar theo vị trí hoặc cảm biến mức tổng theo giả định hình học đã duyệt. Lưu lượng vào/ra chỉ giữ khi có cân | `grades`, tồn tổng tấn, mức suy từ tồn logic, lưu lượng chưa đo | H/L, mức tại vị trí đo thực, feedback cửa xả |
| FD-501 | Tốc độ băng và phản hồi cân cấp nếu giữ cấu hình băng cân | Kiểm tra loại feeder và điểm đo; tránh một giá trị chung cho nhiều thiết bị | Lưu lượng solver gán lặp khi thiếu cân | Dòng motor, RUN/TRIP |
| PK-501 | — | Tình trạng đầu nạp phải ánh xạ sang tín hiệu đầu nạp sẵn sàng/kẹt được xác nhận | `bags_per_min` hiện quy từ t/h và khối lượng đặt; lưu lượng xuất bao chưa có cân trực tiếp | Khối lượng từng bao, xung đếm bao và bộ đếm, tốc độ máy, RUN/TRIP |
| BC-501 | Tốc độ băng | Tình trạng băng lấy từ tiếp điểm; lưu lượng t/h hiện là dòng bao của solver | Lưu lượng bao quy đổi t/h, tình trạng suy luận | Xung đếm bao, công tắc kẹt/lệch, dòng motor, RUN/TRIP |
| LD-501 | Dòng motor, rung ổ trục | `drive.condition` chuyển sang feedback truyền động. Lưu lượng hiện chỉ gán theo tuyến | Lưu lượng t/h chưa có cân riêng | Đếm bao tại điểm xếp nếu có, vị trí/sẵn sàng xe, RUN/TRIP |
| FD-502 | Tốc độ băng và phản hồi cân cấp nếu giữ cấu hình băng cân | Xác nhận cân riêng và cơ cấu cấp liệu | Lưu lượng solver gán lặp khi thiếu cân | Dòng motor, RUN/TRIP |
| SP-502 | — | Tình trạng ống chuyển thành công tắc trên/dưới hoặc encoder vị trí | Lưu lượng ống hiện gán theo tuyến; dùng cân riêng nếu có | Vị trí ống, phản hồi mở/đóng, công tắc xe vào vị trí, ΔP hút bụi nếu áp dụng |
| WS-502 | — | `truck_net_t` là khối lượng tải ròng mô phỏng; triển khai dưới dạng cân tổng và giá trị net theo tare đã chốt, giữ bước đổi xe và không làm nhiễu khi mất tín hiệu | `dispatch_flow_tph` suy ra từ mô hình nạp, lượng tải đích, trạng thái đổi xe | Gross t, tare theo giao dịch, bit cân ổn định và xe trên bàn cân |

## Đề xuất cần duyệt

1. **Một danh mục tag công bố do config xác định.** Mỗi tag ghi equipment, mã, giá trị nguồn nội bộ, vị trí/kiểu đo, đơn vị, dải, giá trị bình thường, ngưỡng và kiểu cập nhật. Giữ giá trị vật lý để solver và test dùng. API live, API kịch bản và CLI export mặc định dùng cùng hợp đồng sensor; các test cần trạng thái vật lý gọi solver trực tiếp. Trường số đo có thể dùng `null` kèm quality khi mất tín hiệu. Alarm/trip hiện hữu giữ logic cũ; ngưỡng tag ban đầu phục vụ hiển thị và nghiệm thu.
2. **Quy ước vị trí và đơn vị.** Áp suất gauge có dấu, ΔP ghi rõ hai đầu lấy áp và chiều hiệu dụng; lưu lượng khí ghi điều kiện thực hoặc chuẩn tại điểm đo. Mức ưu tiên m hoặc % chiều cao, không lấy % khối lượng làm radar. Dùng số chỉ thị cân băng hoặc totalizer của thiết bị đo khi xác nhận được điểm cân. Elevator, damper, bộ cân và công tắc là thuộc tính/bộ phận trên thiết bị hiện có.
3. **Chốt giả định mô phỏng trước khi điền dải và ngưỡng.** Số tầng cyclone, điểm đo khí/nhiệt, vị trí cân, loại đo mức SL-401, dải động cơ, số bao và cấu hình lấy mẫu lab chưa có hồ sơ OEM/P&ID của nhà máy. Đề xuất dùng thông số giả định có nguồn và đánh dấu rõ theo tag. Độ mịn, free lime và hóa liệu xuất dưới dạng mẫu lab có thời điểm lấy mẫu và trả kết quả. Không dùng nhiệt độ bulk vùng nung làm nhiệt độ pyrometer. Lỗi cảm biến nên đổi quality hoặc số đo công bố; mọi liên động hiện hữu đang dùng mất tín hiệu để dừng máy vẫn giữ nguyên.
4. **Thứ tự sau duyệt.** Tách C khỏi payload công bố trước. Bổ sung theo Z02 → Z01 → Z03 → Z04. Sau đó hiệu chỉnh đáp ứng, bão hòa, nhiễu, làm trơn và debounce tại lớp thuộc tính của equipment. Độ trễ vận chuyển hiện hữu giữ trong solver; nếu cần thêm trễ cho tín hiệu ở điểm đo sau, mô phỏng trễ lấy mẫu mà không đổi vật liệu. Giữ các kịch bản cũ và thêm test hợp đồng công bố, tái lập theo seed, thứ tự đáp ứng trip/degrade và invariants vật lý.

### Tài liệu kỹ thuật đối chiếu

- Đo mức radar, nhiệt độ và áp suất từng cyclone, nhiệt/áp dầu ổ trục lò. [Endress+Hauser — Clinker production](https://www.lasc.endress.com/en/endress-hauser-group/Case-studies-application-notes/clinker-production)
- Điểm đo mức và công tắc mức silo xi măng. [VEGA — Level and pressure instrumentation for the cement industry](https://www.vega.com/-/media/pdf-files/industry-brochures/35185-en-level-and-pressure-instrumentation-for-the-cement-industry.pdf)
- Điểm đo fuel, tốc độ lò, áp suất chụp lò, khí và áp suất dưới ghi. [FM — Rotary Kilns and Dryers](https://www.fm.com/FMApi/data/ApprovalStandardsDownload?itemId=%7B150A947E-86F1-4F2B-9CF0-53317E0FE9C3%7D)
- Đo lưu lượng, tải và totalizer bằng cân băng có đo tốc độ. [Siemens — Belt Weighing MSI/MMI](https://cache.industry.siemens.com/dl/files/828/109764828/att_1125554/v1/WT10_en_Milltronics_MSI_MMI_wt10_en.pdf)
- Cân bao trong quá trình nạp. [BEUMER — Tuyến đóng bao xi măng Cruz Azul](https://www.beumergroup.com/reference/cement/cruz-azul/)
- Mô hình dự án chọn kênh lab rời rạc. Các nhà máy có thể dùng máy phân tích hóa online chuyên dụng, nằm ngoài cấu hình hiện tại. [Thermo Fisher Scientific — Cement Production Technologies](https://www.thermofisher.com/us/en/home/industrial/cement-coal-minerals/cement-production-technologies.html)

## Phụ lục — Tên trường quan sát được trong payload

Đã quét 5.850 frame của 65 kịch bản. Có 181 cặp equipment/trường trong `measurements` (Z01: 74, Z02: 38, Z03: 40, Z04: 29), gồm cả chất lượng tín hiệu và trường dạng object. Tag lồng dùng dạng `component.field`. `grades` được đếm là một trường. Số đo và biến vật lý có thể trùng tên.

| Zone | Equipment | Trường trong measurements | Trạng thái API live | Trường solver bổ sung trong API / export |
|---|---|---|---|---|
| Z01 | CR-101 (`crusher`) | `drive_end_bearing.temperature_c`, `inlet_moisture_fraction`, `inlet_tph`, `lubrication.pressure_bar`, `main_motor.current_a`, `main_motor.winding_temperature_c`, `non_drive_end_bearing.temperature_c`, `outlet_tph`, `rotor.speed_rpm`, `vibration_sensor.signal_quality`, `vibration_sensor.vibration_mm_s` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `health_state`, `outlet_moisture_fraction`, `recycle_tph`, `rotor.tool_wear_fraction` |
| Z01 | BC-101 (`transfer_conveyor`) | `belt.speed_m_s`, `belt_scale.measured_flow_tph`, `belt_scale.signal_quality`, `discharge_chute.condition`, `inlet_tph`, `inventory_moisture_fraction`, `inventory_t`, `level_fraction`, `misalignment_switch.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | — |
| Z01 | ST-101 (`stockpile`) | `inlet_tph`, `inventory_moisture_fraction`, `inventory_t`, `level_fraction`, `level_sensor.measured_level_fraction`, `outlet_tph`, `stacker_drive.speed_fraction` | `active_faults`, `operating_state`, `trip_reason` | — |
| Z01 | RC-101 (`reclaimer`) | `bridge_travel.direction`, `bridge_travel.end_limit`, `bridge_travel.position_m`, `bridge_travel.travel_speed_m_min`, `discharge_interlock.condition`, `harrow_encoder.position_m`, `harrow_encoder.signal_quality`, `harrow_encoder.travel_speed_m_min`, `harrow_travel.direction`, `harrow_travel.end_limit`, `inlet_tph`, `outlet_tph`, `reclaimed_total_t`, `scraper_chain.current_a`, `scraper_chain.speed_m_s` | `active_faults`, `operating_state`, `trip_reason`, `waiting_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `outlet_moisture_fraction`, `recycle_tph` |
| Z01 | BN-101 (`feed_bin`) | `inlet_tph`, `inventory_moisture_fraction`, `inventory_t`, `level_fraction`, `level_sensor.measured_level_fraction`, `level_sensor.signal_quality`, `outlet_chute.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | — |
| Z01 | WF-201 (`weigh_feeder`) | `feeder_drive.speed_m_s`, `inlet_tph`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `outlet_moisture_fraction`, `recycle_tph` |
| Z01 | RM-201 (`drying_mill`) | `fresh_inlet_tph`, `hydraulic_unit.pressure_bar`, `inlet_tph`, `main_motor.current_a`, `mill_hot_gas.heat_fraction`, `mill_vibration_sensor.signal_quality`, `mill_vibration_sensor.vibration_mm_s`, `outlet_moisture_fraction`, `outlet_tph`, `recycle_tph` | `active_faults`, `operating_state`, `process_notice`, `trip_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `evaporated_water_tph`, `evaporation_limit_tph`, `inlet_moisture_fraction`, `target_moisture_fraction` |
| Z01 | SP-201 (`separator`) | `inlet_tph`, `outlet_moisture_fraction`, `outlet_tph`, `recycle_tph`, `separator_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fines_fraction`, `inlet_moisture_fraction` |
| Z01 | FN-201 (`process_fan`) | `airflow_m3_s`, `damper.opening_fraction`, `fan_bearing.temperature_c`, `fan_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `nominal_airflow_m3_s` |
| Z02 | SL-301 (`product_silo`) | `inlet_tph`, `inventory_t`, `level_fraction`, `level_sensor.measured_level_fraction`, `level_sensor.signal_quality`, `outlet_chute.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `inventory_moisture_fraction` |
| Z02 | KF-301 (`downstream_feeder`) | `feeder_drive.speed_m_s`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `inlet_tph`, `outlet_moisture_fraction`, `recycle_tph` |
| Z02 | PH-301 (`preheater`) | `cyclone.differential_pressure_pa`, `inlet_tph`, `preheater_exhaust_heat.heat_fraction`, `preheater_outlet.temperature_c` | `active_faults`, `operating_state`, `process_notice`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `outlet_moisture_fraction`, `outlet_tph`, `process_co2_tph`, `recycle_tph` |
| Z02 | PC-301 (`precalciner`) | `calciner_burner.fuel_flow_tph`, `calciner_outlet.temperature_c`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `inlet_tph`, `outlet_moisture_fraction`, `process_co2_tph`, `recycle_tph` |
| Z02 | KL-301 (`rotary_kiln`) | `burning_zone.temperature_c`, `kiln_drive.speed_rpm`, `main_burner.fuel_flow_tph`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `inlet_tph`, `outlet_moisture_fraction`, `process_co2_tph`, `recovered_heat_kw`, `recycle_tph` |
| Z02 | CL-301 (`clinker_cooler`) | `cooler_fan.airflow_m3_s`, `cooler_heat_recovery.thermal_power_kw`, `cooler_outlet.temperature_c`, `grate_drive.speed_m_s`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `evaporated_water_tph`, `fresh_inlet_tph`, `inlet_moisture_fraction`, `inlet_tph`, `outlet_moisture_fraction`, `process_co2_tph`, `recovered_heat_kw`, `recycle_tph` |
| Z02 | CF-301 (`kiln_id_fan`) | `airflow_m3_s`, `damper.opening_fraction`, `draft_sensor.draft_suction_pa`, `fan_bearing.temperature_c`, `fan_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `nominal_airflow_m3_s` |
| Z02 | SL-302 (`clinker_silo`) | `inlet_tph`, `inventory_t`, `level_fraction`, `level_sensor.measured_level_fraction`, `level_sensor.signal_quality`, `outlet_chute.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `inventory_moisture_fraction` |
| Z03 | WF-401A (`WF-401A`) | `additive_tph`, `clinker_tph`, `feeder_drive.speed_m_s`, `gypsum_tph`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `inlet_tph` |
| Z03 | CM-401A (`CM-401A`) | `bearing.vibration_mm_s`, `drive.condition`, `drive.current_a`, `fresh_inlet_tph`, `outlet_tph`, `recycle_tph` | `active_faults`, `operating_state`, `process_notice`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z03 | SP-401A (`SP-401A`) | `inlet_tph`, `outlet_tph`, `recycle_tph`, `separator_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `fines_fraction` |
| Z03 | FN-401A (`FN-401A`) | `airflow_m3_s`, `damper.opening_fraction`, `fan_bearing.temperature_c`, `fan_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `nominal_airflow_m3_s` |
| Z03 | WF-401B (`WF-401B`) | `additive_tph`, `clinker_tph`, `feeder_drive.speed_m_s`, `gypsum_tph`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `inlet_tph` |
| Z03 | CM-401B (`CM-401B`) | `bearing.vibration_mm_s`, `drive.condition`, `drive.current_a`, `fresh_inlet_tph`, `outlet_tph`, `recycle_tph` | `active_faults`, `operating_state`, `process_notice`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z03 | SP-401B (`SP-401B`) | `inlet_tph`, `outlet_tph`, `recycle_tph`, `separator_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `fines_fraction` |
| Z03 | FN-401B (`FN-401B`) | `airflow_m3_s`, `damper.opening_fraction`, `fan_bearing.temperature_c`, `fan_drive.speed_rpm` | `active_faults`, `operating_state`, `trip_reason` | `nominal_airflow_m3_s` |
| Z04 | SL-401 (`SL-401`) | `grades`, `inlet_tph`, `inventory_t`, `level_fraction`, `level_sensor.signal_quality`, `outlet_gate.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | — |
| Z04 | FD-501 (`FD-501`) | `feeder_drive.speed_m_s`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason`, `waiting_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `inlet_tph` |
| Z04 | PK-501 (`PK-501`) | `bags_per_min`, `filling_head.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z04 | BC-501 (`BC-501`) | `belt.condition`, `belt.speed_m_s`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z04 | LD-501 (`LD-501`) | `bearing.vibration_mm_s`, `drive.condition`, `drive.current_a`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z04 | FD-502 (`FD-502`) | `feeder_drive.speed_m_s`, `load_cell.signal_quality`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason`, `waiting_reason` | `configured_capacity_tph`, `effective_capacity_tph`, `inlet_tph` |
| Z04 | SP-502 (`SP-502`) | `loading_spout.condition`, `outlet_tph` | `active_faults`, `operating_state`, `trip_reason` | `configured_capacity_tph`, `inlet_tph` |
| Z04 | WS-502 (`WS-502`) | `dispatch_flow_tph`, `load_cell.condition`, `load_cell.signal_quality`, `truck_net_t` | `active_faults`, `operating_state`, `trip_reason`, `waiting_reason` | `configured_capacity_tph`, `inlet_tph`, `outlet_tph` |

Export còn trả `balance` và `events` ở cấp frame. Đề xuất giữ chẩn đoán cân bằng nội bộ và đưa sự kiện lỗi sang luồng sự kiện riêng nếu được duyệt.
