# Kiểm kê tín hiệu equipment — Bước 0

Mốc khảo sát là `f1bc06b`. Bảng bao phủ 33 equipment, 4 zone và 7 line. Đã quét các frame của 65 kịch bản đăng ký tại mốc đó, gồm baseline và 64 kịch bản lỗi, rồi đối chiếu với backend, cấu hình plant, Explorer, đặc tả và test. Các nhóm A/B/C/D lưu đề xuất ban đầu. Các mục theo từng bước ghi những thay đổi đã triển khai sau khảo sát. [Số tag và kịch bản hiện hành](README.md#hiện-trạng-mô-phỏng)

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

Tại mốc Bước 1, catalog công bố 147 tag (Z01: 52, Z02: 33, Z03: 34, Z04: 28). Trong 181 cặp thiết bị/trường đo cũ, 92 tên trường không còn công bố theo dạng cũ, gồm các trường đã loại và trường đã đổi điểm đo. Ngoài số này, toàn bộ bản sao trạng thái vật lý từng thiết bị đã rời payload mặc định. [Số tag hiện hành](README.md#hiện-trạng-mô-phỏng)

## Bước 2 — Z02, Pha A

Z02 tăng từ **33 lên 47 tag**. Bổ sung 14 tag và bổ sung metadata hoặc hành vi cho 8 tag có sẵn. Các zone khác giữ nguyên. Mọi tag trong bảng này có `assumed: true`. Giá trị bình thường, dải và ngưỡng dành cho mô phỏng. `null` đánh dấu ngưỡng không áp dụng. Ngưỡng chỉ là metadata, chưa phát lệnh trip và không đi vào liên động.

| Thiết bị | Tag mới | Kênh có sẵn được cập nhật hoặc giữ | Cơ sở suy ra |
|---|---|---|---|
| PH-301 | 8 tag nhiệt khí và áp suất gauge của tầng 1–4, đánh số từ dưới lên | Nhiệt đầu ra có quán tính 180 s | Giả định bốn tầng. Nhiệt mục tiêu qua từng tầng là 800/670/510/340 °C ở tải nhiệt tham chiếu. Độ lớn áp suất âm tăng về phía đầu hút ở trên, tỷ lệ bình phương lưu lượng khí CF-301. |
| PC-301 | Nhiệt gió ba | Dùng nhiệt đầu ra solver làm đại diện nhiệt khí đầu ra. Hằng số thời gian 210 s cho đầu ra và 150 s cho gió ba. | Gió ba suy từ công suất nhiệt thu hồi của CL-301 với hệ số cấu hình. Chưa có cân bằng năng lượng riêng cho ống gió ba. |
| KL-301 | Dòng truyền động và nhiệt khí tại cửa vào liệu lò | — | Dòng có thành phần không tải khi quay và tăng theo lưu lượng liệu. Nhiệt khí là biến đại diện theo tải và gió, với hằng số thời gian 240 s. |
| CL-301 | Áp suất dưới ghi | Tốc độ ghi giữ theo phản hồi hiện có. Nhiệt clinker đầu ra thêm hiệu chỉnh theo tải và quán tính 120 s. | Áp suất dưới ghi có thành phần do dòng gió và thành phần trở lực lớp clinker. Nhiệt clinker kết hợp biến cooler hiện có với tải liệu. |
| CF-301 | Dòng truyền động quạt | Gauge cửa hút giữ dấu âm. Nhiệt ổ trục dùng biến đã có, thêm bộ lọc chỉ thị 20 s. | Dòng theo xấp xỉ bậc ba lưu lượng, về 0 khi quạt dừng. |
| KF-301 | Dòng điện truyền động cân định lượng | Lưu lượng cân và RUN giữ các tag hiện hữu. | Dòng điện theo tải cân, về 0 khi truyền động ngừng. |

Tín hiệu nhiệt khởi tạo theo giá trị mục tiêu của frame đầu tiên. Sau đó dùng bộ lọc bậc một theo thời gian bước thực. Các tín hiệu điện, áp suất và RUN/TRIP phản ứng ngay trong bước solver. Khi kẹt ghi hoặc dừng cân mà CF-301 vẫn chạy, áp suất các tầng vẫn còn và nhiệt cyclone có thể giảm từ bước kế tiếp do tín hiệu nhiệt lò dùng tải bước trước. Khi không còn clinker ra, kênh nhiệt CL-301 biểu diễn nhiệt dư của điểm đo đang nguội dần.

Điểm cần duyệt trước Pha B gồm số tầng/vị trí lắp đầu đo, hệ số và hằng số thời gian theo dữ liệu vận hành, phương pháp gắn nhiệt với chất lượng clinker và mức giảm khả năng sấy, cùng điều kiện chuyển tuyến khí thải trực tiếp khi RM-201 dừng. Cần chốt cả trường hợp khởi động lại và điều kiện quay về tuyến sấy.

## Bước 2 — Z02 và RM-201, Pha B

Trước khi ghép nhiệt đã xác nhận đủ năm tag từ Pha A: `PC-301.calciner_outlet.temperature_c`, `CL-301.grate_drive.speed_m_s`, `CL-301.cooler_outlet.temperature_c`, `KF-301.feeder_drive.current_a` và `PH-301.cyclone_4.gas_temperature_c`.

| Tag / kênh | Thay đổi khi bật ghép nhiệt |
|---|---|
| `RM-201.gas_inlet_temperature_c`, `RM-201.gas_outlet_temperature_c` | Hai điểm đo °C mô phỏng theo nhiệt dự phòng, phần nhiệt khí thu hồi và lượng nước bốc hơi. Khi mill không chạy, trả `null`. Công suất nhiệt khả dụng giữ nội bộ. |
| `CL-301.lab.free_lime_pct` | Kênh lab riêng. Chỉ phát tại thời điểm trả kết quả, kèm thời gian lấy mẫu. Không lấy mẫu nếu không có clinker mới tại đầu ra cooler. |
| Nhiệt khí các tầng PH-301 | Dùng trạng thái nhiệt khí thải tầng trên cùng làm cơ sở, với hệ số theo tầng. Tầng trên cùng chính là nguồn nhiệt của mô hình sấy. |
| Áp suất gauge PH-301 / CF-301 | Trở lực thay đổi theo vị trí damper ở giữa hai chế độ. Dấu âm giữ nguyên khi hút. |

Mặc định `thermal_coupling.enabled: true` trong plant. Khi tắt cờ, hai tag nhiệt RM-201 và kênh lab không xuất hiện. Các tag PH-301 trở lại phép suy ra thụ động của Pha A. Có 163 tag liên tục và 1 tag lab khi bật cờ, gồm 54 tag liên tục Z01 và 47 tag liên tục Z02. Z03 và Z04 giữ nguyên danh mục.

Các giả định chính gồm hệ số nhiệt theo suất nhiên liệu, phân bổ nhiệt cooler 72% gió thứ cấp và 28% gió ba, thời gian lưu tham chiếu 1.800 s và đường cong free lime theo nhiệt/thời gian lưu. Ngưỡng, dải và tham số vẫn là giả định mô phỏng. Điều kiện duyệt Bước 3 gồm hiệu chuẩn từ dữ liệu ca vận hành, tách quán tính của quá trình khỏi quán tính đầu đo, chọn nhiễu theo seed, dải bão hòa, debounce và ngưỡng cảnh báo theo chế độ. [Đối chiếu 65 kịch bản](Thermal-Coupling-Report.md)

## Rà soát trước Bước 3 và cấu hình đo lường

- Không có tag liên tục đại diện độ ẩm bột liệu hoặc free lime. Nhiệt độ khí ra RM-201 là tín hiệu gián tiếp để theo dõi sấy, không chuyển đổi thành giá trị độ ẩm. Free lime chỉ có ở `CL-301.lab.free_lime_pct`. Lịch lab mặc định giả định nhà máy dùng phân tích tự động (lấy mẫu 10 phút, trả sau 5 phút). Đổi `thermal_coupling.lab.analysis_type` sang `manual_hourly` để lấy mẫu 60 phút và trả sau 30 phút.
- Đã rà 26 ca bypass trước đây. Sau khi ràng buộc lò còn cấp liệu, 19 ca được phép bypass khi RM-201 dừng và lò vẫn chạy. Bảy ca còn lại bị chặn hoàn toàn. Các ca thay đổi vật liệu và trạng thái có giải thích riêng. [Báo cáo đối chiếu](Thermal-Coupling-Report.md)
- Bước 3 công bố 87 tag analog, 74 tag nhị phân (RUN/TRIP, mức H/L, giới hạn damper), 20 tag trạng thái/metadata và 2 bộ đếm. Có thêm 84 tag cảnh báo rời rạc ở kênh `alarms`. Một tag lab dùng lịch phân tích riêng. H/L và giới hạn damper là tiếp điểm mô phỏng suy từ nguồn mức/vị trí đã có.
- Mỗi tag đo có cấu hình `conditioning` ngay trong danh mục. Cờ `signal_conditioning.enabled` bật mặc định và tắt được để nhận lại số đo Pha B đã sửa bypass. `noise_enabled` và `seed` chỉ đổi nhiễu thiết bị đo. Vân tay vật liệu và nhiệt/chất lượng được lưu và đối chiếu riêng.
- Các thông số đo là giả định. Nhiệt độ có hằng số đầu đo mặc định 20 s và lấy mẫu 5 s. Dòng điện có hằng số 0,15 s, áp suất 0,25 s, mức 8 s. Thời gian RUN nhả 3 s, cảnh báo thông thường tác động sau 5 s và nhả sau 8 s. Cần hiệu chỉnh theo thiết bị hoặc historian thật trước khi dùng để đánh giá vận hành một nhà máy cụ thể.

## Z01 — Mở rộng tín hiệu và cảnh báo

Z01 tăng từ **60 lên 69 tag vận hành** và từ **12 lên 47 tag cảnh báo**. Chín tag mới đều đánh dấu `assumed: true`.

| Thiết bị | Tag mới | Nguồn và giả định |
|---|---|---|
| BC-101 | Dòng motor băng tải | Suy từ khối lượng liệu trên băng và phản hồi tốc độ. Khi motor có dấu hiệu quay nhưng bị chặn xả, liệu trên băng vẫn tạo tải. |
| RC-101 | Lưu lượng cân băng thu hồi | Dùng kênh lưu lượng ra đã lấy mẫu, giả định có cân băng trên tuyến thu hồi. |
| WF-201 | Dòng motor cân định lượng | Dùng lưu lượng vật lý của solver và phản hồi tốc độ, không dùng số cân đã bị bias. |
| RM-201 | ΔP mill và nhiệt độ ổ trục | ΔP gồm thành phần bình phương lưu lượng khí và thành phần tương tác gió × tải liệu. Nhiệt ổ trục suy từ tải motor với hằng số quá trình 180 s trước quán tính đầu đo. |
| SP-201 | Dòng motor phân ly | Phản hồi tốc độ phân biệt quay và dừng. Khi quay, lưu lượng liệu làm tăng dòng trên mức không tải. |
| FN-201 | Dòng motor, áp suất gauge cửa hút, rung RMS | Dòng tăng theo tải khí. Draft cửa hút gồm lực hút cục bộ và phần ảnh hưởng có trọng số từ áp suất top PH-301 và draft CF-301, giảm theo vị trí bypass. Rung suy theo tải khí và mức suy giảm impeller. |

Ngưỡng **240 °C cũ** gắn vào `RM-201.gas_outlet_temperature_c`. Giữ L 75 °C và sửa H thành 120 °C. Khí vào có L 195 °C và H riêng 400 °C. Tag khí ra quy chiếu nguồn nhiệt ra trong solver về mốc chỉ thị giả định 95 °C, với hệ số 0,6 quanh mốc nguồn 170 °C. Solver, cân bằng sấy và các vân tay không dùng giá trị chỉ thị này. Một nghiên cứu hiện trường ghi nhận nhiệt khí ra mill 88 °C ở ca được khảo sát. [Nghiên cứu năng lượng nhà máy xi măng](https://dyuthi.cusat.ac.in/jspui/bitstream/purl/4727/1/Dyuthi-T1833.pdf)

- **Cảnh báo nhiệt độ cuộn dây và ổ trục H/HH** vẫn hoạt động khi dừng hoặc khởi động. CR-101 giữ cuộn dây 95/105 °C và ổ trục 78/88 °C. RM-201 và FN-201 dùng 75/85 °C. Debounce nhiệt 15/25 s.
- **Cảnh báo phụ thuộc vận hành** chỉ áp dụng ở RUNNING sau thời gian khởi động 120 s. Dòng motor H ở 110% định mức. Dầu CR-101 L/LL ở 2,5/2,0 bar. Thủy lực con lăn RM-201 L/H ở 85/125 bar. ΔP mill L/H ở 2.000/6.000 Pa. Cảnh báo ΔP và nhiệt khí RM-201 yêu cầu còn gió. Debounce dòng, áp và rung là 5/8 s.
- **Rung RMS** dùng ba đường nền giả định riêng. CR-101 là 2,8 mm/s với hệ số H/HH 1,60/2,35. RM-201 là 2,5 mm/s với 1,70/2,60. FN-201 là 2,0 mm/s với 1,80/2,90.
- Có **6 cảnh báo lỗi đầu đo BAD** cho chất lượng rung CR-101 và RM-201, cân băng BC-101, encoder RC-101, mức BN-101 và load cell WF-201. Một chỉ thị BAD che cảnh báo quá trình của đúng phép đo liên kết. Cảnh báo lỗi đầu đo vẫn hoạt động khi thiết bị dừng.

Hiệu chỉnh sau gồm đường nền rung, ngưỡng cuộn dây CR-101, quan hệ chiều cao radar–thể tích của BN-101 và các ô SL-401 (phần trụ và phần côn), mốc nhiệt ra RM-201 và hệ số ghép draft qua damper. Chưa mô tả elevator trong RM-201. Hoãn vị trí ST-101 và ngưỡng cảnh báo áp suất cửa hút FN-201.

## Z03 — Lượt 1

Z03 có **62 tag vận hành, 60 cảnh báo và 2 tag lab**. Thêm 24 tag vận hành cho WF, CM, SP và FN của hai tuyến A/B. Các giá trị suy ra, dải đo và ngưỡng đánh dấu `assumed`. Các zone khác không đổi danh mục. Dòng định mức SP-401A/B giả định **40 A**, normal 30 A và H 44 A, tương ứng 110% định mức.

| Nhóm | Nguồn / giả định |
|---|---|
| Dòng và công suất | Dòng lấy từ tải vật lý và phản hồi truyền động. CM tính thêm ảnh hưởng hồi lưu trong chỉ thị tải. Công suất điện ước tính theo `sqrt(3) × V_kV × I_A × cosφ`. `cosφ = cosφ_idle + clamp(I/I_định_mức, 0, 1) × (cosφ_rated − cosφ_idle)`. CM dùng 3,3 kV, 165 A và cosφ 0,62–0,88. FN dùng 0,69 kV, 175 A và 0,58–0,92. Công thức dùng dòng trước nhiễu đầu đo. Tag A và kW có RNG riêng theo mã tag. |
| Khí ra CM | Khi đang nghiền, nhiệt mục tiêu `95 + 12(P/760 − 1) + 80(1 − G/G_ref) + 34w` °C với P là kW, G là gió thực, G_ref là 55/53 m³/s cho A/B và w là mức mòn 0–1. Lượng liệu tác động qua công suất. Mục tiêu về 25 °C khi dừng, quán tính mô hình 180 s và quán tính đầu đo 20 s. |
| Dầu CM | Mục tiêu khi chạy là `3 − 0,003(T_ổ − 62)` bar, khi dừng là 0 bar. Hằng số lên áp 12 s và xuống áp 20 s. Đây là giả định chỉ thị, không có thêm kịch bản lỗi dầu. |
| Blaine lab | `B = clamp(B_mác + 120(n/880 − 1) + ε, 200, 600)` m²/kg. B_mác là 350 cho A và 380 cho B. ε là nhiễu Gaussian σ = 2 m²/kg, có seed riêng theo tag và thời điểm lấy mẫu. Công thức là proxy của simulator. Mặc định tự động lấy mẫu/trả sau 10/5 phút, tùy chọn thủ công 60/30 phút qua `blaine_lab.analysis_type`. Lấy mẫu khi sản phẩm mịn có lưu lượng. |

| Kịch bản | Hướng Blaine theo công thức |
|---|---|
| Baseline | Quanh mốc của từng mác. |
| `underspeed` | Rotor 880 → 660 rpm làm kết quả giảm khoảng 30 m²/kg so với mẫu cùng thời điểm và seed. |
| `efficiency_loss` | `fines_fraction` giảm, hồi lưu tăng và tốc độ rotor giữ nguyên. Kỳ vọng Blaine gần như giữ nguyên ở cùng mác. |
| Trip | Bỏ kỳ lấy mẫu nếu không có sản phẩm mịn. Mẫu đã lấy vẫn trả đúng lịch. |

Nhiệt cao H/HH vẫn được đánh giá khi dừng. Dòng, kW, rung, tốc độ phân ly, áp dầu và cảnh báo thấp nhiệt hoặc áp quá trình dùng chế độ RUNNING qua giai đoạn khởi động. Nhiệt debounce 15/25 s, các phép đo khác 5/8 s. BAD che cảnh báo quá trình của phép đo cùng đầu đo theo cơ chế chung. Z03 có hai cảnh báo BAD riêng của load cell WF, không che dòng motor WF vì khác nguồn.

WFA-F02 và WFB-F02 mới được mô tả trong đặc tả. Solver đang dùng tỷ lệ thạch cao/phụ gia cố định theo recipe, chưa có sai lệch dòng thạch cao độc lập. Chưa thêm tag thành phần. Phương án chờ duyệt là tạo sai lệch định lượng có khối lượng truy vết cho từng dòng và kiểm chứng rồi mới công bố ba tag cân thành phần mỗi tuyến.

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

### Điểm nhận đề xuất cho độ trễ đo lường

| Tuyến | Tag nhận `transport_delay_s` | Trạng thái và trễ |
|---|---|---|
| KL-301 → đầu ghi CL-301 | — | Đã bỏ đề xuất 3 s |
| Qua ghi cooler | `CL-301.cooler_outlet.temperature_c` | Đã có, giữ 0 s trễ truyền. Cần chiều dài ghi hữu hiệu trước khi đề xuất giá trị, đồng thời tránh chồng lên quán tính nhiệt |
| CL-301 → SL-302 | `SL-302.inlet_conveyor.measured_flow_tph` | Cần thêm, đề xuất 30 s nếu lấy nguồn từ dòng ra cooler |
| BC-101 → ST-101 | `ST-101.inlet_conveyor.measured_flow_tph` | Cần thêm nếu có điểm cân. Buffer solver đã giữ 1 bước, đề xuất 0 s bổ sung nếu lấy nguồn ngay đầu nhận |
| RC-101 → BN-101 | `BN-101.inlet_conveyor.measured_flow_tph` | Cần thêm, đề xuất 10 s nếu lấy nguồn từ RC-101 |
| SP-401A/B → SL-401 A/B | `SL-401.cell_A.inlet_flow_tph`, `SL-401.cell_B.inlet_flow_tph` | Cần thêm, đề xuất 20 s mỗi tuyến nếu lấy nguồn tại điểm phát |
| PK-501 → BC-501 | `BC-501.discharge.bags_count` | Thêm ở Z04, 20 s giả định từ 15 m / 0,75 m/s. Dịch luồng xung một lần |
| Nhiệt khí ra RM-201 | `RM-201.gas_outlet_temperature_c` | Đã có 4 s giả định, chưa có dữ liệu hình học hoặc hiệu chuẩn |

Các tag đề xuất ngoài phạm vi Z04 chờ duyệt, các giá trị trễ có số đều là giả định. Test cân bằng mức dùng tồn và lưu lượng solver chưa trễ để tính tồn kỳ vọng. Chỉ khi đối chiếu PV mới áp bộ lọc và chu kỳ mẫu của đầu đo mức. Mức radar không nhận trễ từ đường vận chuyển.

### Rà soát mức kho trong baseline 2 giờ

[Chuỗi mức lịch sử 120 mẫu](Silo-Level-Baseline.csv) dùng tồn đầu ST-101 **35 t**, bước 60 s, có conditioning và tắt nhiễu đầu đo. Trong 30 phút cuối, ST-101 dao động 13,6–14,0%, trung vị 13,7%. L 15% bật ở cả 120 mẫu của lần chạy đó. Trung vị các tag còn lại là BN-101 24,4%, SL-301 62,3%, SL-302 15,4%, SL-401 A 31,65% và B 33,9%.

Lượt khảo sát riêng dài 48 giờ với cùng tồn đầu 35 t cho trung vị mức vật lý ST-101 ở giờ 8 là 11,02%, giờ 24 là 3,39% và giờ 48 là 0,69% (0,67–0,74%).

Catalog hiện đặt `normal_kind: state_dependent` cho cả sáu tag mức và tham chiếu khởi động ST-101 là 20% (48 t). Ngưỡng ST-101 giữ L/LL 15%/8%. Các fixture phát hành vẫn ghim 35 t. Cảnh báo L gió ba PC-301 dùng nguồn nhiên liệu PC-301. [Giới hạn hiện hành](Specification.md#giới-hạn-đã-biết)

### Công suất điện ước tính Z01/Z02

`P_kW = √3 × V_kV × I_A × cosφ(x)`, với `x = clamp(I/I_rated, 0, 1)` và cosφ nội suy giữa hệ số không tải và định mức. Dùng dòng vật lý trước nhiễu đầu đo, lấy từ `equipment` cho các dòng hiện đọc qua `measurements`, và RNG riêng cho kW. Công thức giả định hệ ba pha cân bằng và điện áp hiệu dụng dây cố định. Dải đo giả định, τ 0,25 s, mẫu mỗi bước, độ phân giải 0,1 kW. Cảnh báo tiếp tục dùng ngưỡng dòng hiện có.

| Tag đề xuất | Tag dòng nguồn | kV / A định mức | cosφ không tải → định mức | Normal gần đúng / dải kW |
|---|---|---:|---:|---:|
| `CR-101.main_motor.power_kw` | `CR-101.main_motor.current_a` | 0,69 / 145 | 0,58 → 0,88 | 152,5 / 0–250 |
| `RM-201.main_motor.power_kw` | `RM-201.main_motor.current_a` | 3,30 / 320 | 0,62 → 0,88 | 1.418,3 / 0–2.200 |
| `KL-301.kiln_drive.power_kw` | `KL-301.kiln_drive.current_a` | 0,69 / 240 | 0,60 → 0,88 | 205,6 / 0–400 |
| `CF-301.fan_drive.power_kw` | `CF-301.fan_drive.current_a` | 3,30 / 350 | 0,58 → 0,92 | 1.561,3 / 0–2.800 |
| `FN-201.fan_drive.power_kw` | `FN-201.fan_drive.current_a` | 0,69 / 115 | 0,58 → 0,92 | 104,7 / 0–220 |
| `RC-101.scraper_chain.power_kw` | `RC-101.scraper_chain.current_a` | 0,40 / 75 | 0,55 → 0,86 | 44,4 / 0–60 |

CR-101 tính normal từ tag dòng 145 A. Dòng vật lý baseline bước 60 s có trung vị 143,70 A sau 10 phút, gần mốc này. RC-101 dùng normal dòng 74,6 A theo trung vị baseline 74,62 A, tương ứng 44,4 kW, dưới công suất điện 44,7 kW tại định mức. Điểm 85% dòng định mức tương ứng khoảng 35,9 kW. Điện áp, tải và công suất truyền động KL-301 đánh dấu `assumed`. CF-301 giữ H 390 A đã có, cao hơn 385 A là 110% của định mức giả định 350 A. Việc thêm chỉ thị kW giữ hành vi cảnh báo đã duyệt, chờ hiệu chỉnh bằng dữ liệu nhà máy. Quạt cooler CL-301 chờ nguồn dòng theo từng motor.

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
