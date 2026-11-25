# CEMENT FACTORY SIMULATOR V1
## Đặc tả dự án mô phỏng nhà máy xi măng

**Phiên bản tổng hợp:** 2026-11-23  
**Phạm vi:** Nhà máy xi măng giả định, từ tiếp nhận nguyên liệu đến xi măng bao và xi măng rời. Không phải tài liệu hoàn công (as-built) của một nhà máy cụ thể.  
**Mục đích:** Tài liệu nguồn Markdown để thiết kế Process Graph, mô hình thiết bị, mô hình vật lý, fault propagation, telemetry và giao diện Engineering Explorer.

> **Lưu ý về nguồn:** Nội dung chi tiết phía dưới được chuyển từ các tài liệu DOCX đã soạn trong dự án. Có thể có phần trùng lặp giữa các phiên bản. Các trị số, ngưỡng, công thức rút gọn và cấu hình component phải được kiểm chứng/hiệu chỉnh trước khi sử dụng như thông số thực tế.

## 1. Kiến trúc và phạm vi cố định

**Factory → Zone → Line → Process → Equipment → Component.**  
*Process* là hoạt động biến đổi/vận chuyển/lưu trữ vật chất; *Equipment* là thiết bị/cụm thực hiện một hoặc nhiều Process; *Component* là bộ phận cấu thành Equipment. Quan hệ Process–Equipment có thể nhiều-nhiều. Không mặc định thiết bị nào cũng có động cơ.

| Zone | Line | Thiết bị/cụm logic | Đầu ra chính |
|---|---|---:|---|
| Z01 Raw Material Preparation | L01 Crushing & Storage | 5 | Nguyên liệu đã chuẩn bị |
| Z01 Raw Material Preparation | L02 Raw Milling | 4 | Raw meal |
| Z02 Clinker Production | L01 Kiln Line | 8 | Clinker |
| Z03 Cement Grinding | L01 Cement Mill A | 4 | Xi măng bột |
| Z03 Cement Grinding | L02 Cement Mill B | 4 | Xi măng bột |
| Z04 Packing & Dispatch | L01 Bag Packing | 4 | Xi măng bao |
| Z04 Packing & Dispatch | L02 Bulk Loading | 3 | Xi măng rời |
| Shared asset Z03/Z04 | SL-401 Cement Silo | 1 | Tồn kho xi măng theo grade |
| **Tổng** | **7 Line** | **33** | |

### Luồng sản xuất

```text
Raw materials
   ↓
Z01-L01 Crushing & Storage
   ↓
Z01-L02 Raw Milling ────────────────┐
   ↓                               │ coarse recycle tại separator
SL-301 Raw Meal Silo                ┘
   ↓
Z02-L01 Kiln Line
   ↓
SL-302 Clinker Silo
   ├──→ Z03-L01 Cement Mill A ──┐
   └──→ Z03-L02 Cement Mill B ──┤
                                ↓
                        SL-401 Cement Silo
                           ├──→ Z04-L01 Bag Packing → Bagged cement
                           └──→ Z04-L02 Bulk Loading → Bulk cement
```

**Các dòng bổ sung:** nhiên liệu, khí nóng/không khí, thạch cao, phụ gia, hơi nước, CO₂, khí thải và các vòng hồi lưu. Không được hiểu sơ đồ chính là thứ tự tuần tự tuyệt đối: nghiền/sấy có thể đồng thời; quạt và dòng khí hỗ trợ xuyên suốt; các silo tạo độ trễ và bộ đệm.

## 2. Quy tắc đặc tả một đối tượng

Mỗi Factory/Zone/Line/Process/Equipment/Component nên có: `id`, `name`, `function`, `inputs`, `outputs`, `connections`. Với Process bổ sung `transformations`, `participating_equipment`, `physical_models`; với Equipment bổ sung `components`, `operating_parameters`, `states`, `faults`; với Component bổ sung `type`, `input_output`, `sensor_or_actuator`, `failure_modes`. Phân loại input/output theo `material`, `energy`, `control`, `information`, `event`.

**Nhóm mô hình:** M01 Mass Balance; M02 Capacity; M03 Electrical Power; M04 Mechanical Dynamics; M05 Heat & Energy; M06 Particle Size Reduction; M07 Moisture & Drying; M08 Separation & Recirculation; M09 Chemical Reaction; M10 Gas Flow & Pressure; M11 Storage & Inventory; M12 Material Transport; M13 Quality & Composition; M14 Control & Interlock; M15 Fault & Degradation; M16 Discrete Event.

## 3. Nội dung đặc tả chi tiết từ tài liệu dự án


---

## 3.1. Quy trình sản xuất (Process-first)

ĐẶC TẢ QUY TRÌNH SẢN XUẤT • THIẾT BỊ • MÔ HÌNH VẬT LÝ • SỰ CỐ

Bản biên soạn lại theo luồng vận hành \| 23/11/2026

Phạm vi: Nhà máy xi măng tích hợp giả định, từ nguyên liệu nhận vào đến xi măng bao/rời. Không mô tả khai thác mỏ, utilities độc lập, môi trường hoặc hành chính. Không phải thông số được xác nhận của một nhà máy cụ thể.

### Hướng dẫn đọc tài liệu

Đi từ Factory → Zone → Line → Process → Equipment. Mỗi Line trình bày mục đích, chuỗi công đoạn, từng quy trình (đầu vào → biến đổi → đầu ra), thiết bị thực hiện, tag/trạng thái, phương trình và lỗi tác động. Cuối tài liệu là liên kết liên Line, điều khiển và quy tắc kiểm chứng.

### 1. Khái niệm và quy mô

| Khái niệm | Định nghĩa trong simulator                                                                          |
|-----------|-----------------------------------------------------------------------------------------------------|
| Zone      | Nhóm công đoạn theo chức năng sản xuất                                                              |
| Line      | Tuyến sản xuất có đầu vào, đầu ra và trạng thái vận hành                                            |
| Process   | Hoạt động vật lý/hóa học/vận chuyển như định lượng, nghiền, sấy, phân ly, nung, làm nguội, đóng bao |
| Equipment | Thiết bị/cụm thiết bị thực hiện một hoặc nhiều process                                              |
| Stream    | Dòng vật chất/nhiệt nối các process, có lưu lượng, thành phần, nhiệt độ                             |
| Fault     | Sự kiện làm thay đổi điều kiện đầu vào, tham số thiết bị, điều khiển hoặc trạng thái bảo vệ         |

| Zone               | Line                   | Thiết bị logic |
|--------------------|------------------------|----------------|
| Z01 Nguyên liệu    | L01 Crushing & Storage | 5              |
| Z01 Nguyên liệu    | L02 Raw Milling        | 4              |
| Z02 Clinker        | L01 Kiln Line          | 8              |
| Z03 Nghiền xi măng | L01 Mill A             | 4              |
| Z03 Nghiền xi măng | L02 Mill B             | 4              |
| Z04 Xuất hàng      | L01 Bag Packing        | 4              |
| Z04 Xuất hàng      | L02 Bulk Loading       | 3              |
| Dùng chung         | SL-401 Cement Silo     | 1              |
| Tổng               | 7 Line                 | 33             |

Quy ước: 33 là số cụm logic, không phải số máy/cảm biến vật lý. ST-101 đại diện khu lưu trữ; PH-301 đại diện cụm cyclone; mỗi hệ feeder có thể chứa nhiều nhánh. SL-401 được sở hữu một lần, không nhân đôi trong hai Mill.

### 2. Liên kết quy trình toàn nhà máy

Nguyên liệu → Z01-L01 (đập/vận chuyển/lưu trữ/thu hồi) → Z01-L02 (định lượng/nghiền/sấy/phân ly) → SL-301 → Z02-L01 (tiền gia nhiệt/tiền nung/nung/làm nguội) → SL-302 → Z03-L01 hoặc L02 (phối liệu/nghiền/phân ly) → SL-401 → Z04-L01 (đóng bao) hoặc L02 (xuất rời).

Dòng phụ cần mô phỏng tối thiểu: thạch cao và phụ gia vào hai Mill; nhiên liệu và khí vào calciner/kiln; khí nóng và khí thải trong preheater–kiln–cooler; hơi nước thoát khi sấy; CO₂ sinh ra khi phân hủy carbonate. Không cần thêm Zone phụ trợ.

### 3. Mô tả chi tiết theo Zone / Line / Process

#### Z01 – L01: Crushing & Storage

Chức năng: Nhận nguyên liệu, giảm kích thước, vận chuyển và tạo tồn kho đệm trước nghiền liệu.

Chuỗi quy trình: Nguyên liệu rời → CR-101 → BC-101 → ST-101 → RC-101 → BN-101

### P01 Tiếp nhận và đập

| Mục                            | Mô tả                                                                                                        |
|--------------------------------|--------------------------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Đá vôi/đất sét hoặc dòng phù hợp → giảm cỡ hạt → vật liệu đạt cỡ vận chuyển                                  |
| Thiết bị tham gia              | CR-101                                                                                                       |
| Thông số vận hành / trạng thái | Feed rate t/h; F80/P80 mm; motor A/kW; shaft rpm; vibration mm/s; bearing °C; lubrication pressure; RUN/TRIP |
| Mô hình và phép tính           | M02 giới hạn công suất; M06 năng lượng/cỡ hạt; M03 điện; M15 suy giảm                                        |
| Fault → tác động               | Overload, choke, mòn búa/hàm, thiếu bôi trơn → tăng điện/rung, giảm lưu lượng hoặc trip                      |

### P02 Vận chuyển

| Mục                            | Mô tả                                                                            |
|--------------------------------|----------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Vật liệu từ crusher → băng tải → kho                                             |
| Thiết bị tham gia              | BC-101                                                                           |
| Thông số vận hành / trạng thái | Belt speed m/s; belt load kg/m; flow t/h; motor A; slip; misalignment; pull-cord |
| Mô hình và phép tính           | M12 vận chuyển và trễ; M02 giới hạn; M03 công suất                               |
| Fault → tác động               | Trượt băng, lệch băng, kẹt chute → lưu lượng giảm, upstream phải giảm cấp        |

### P03 Lưu trữ và phối trộn sơ bộ

| Mục                            | Mô tả                                                                 |
|--------------------------------|-----------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Vật liệu vào kho → tồn kho/độ ẩm/thành phần hỗn hợp                   |
| Thiết bị tham gia              | ST-101                                                                |
| Thông số vận hành / trạng thái | Inventory t; fill %; moisture %; composition estimate; high/low level |
| Mô hình và phép tính           | M11 cân bằng tồn kho; M13 phối trộn                                   |
| Fault → tác động               | Kho cạn, ẩm cao, sai thành phần → ảnh hưởng phối liệu Raw Mill        |

### P04 Thu hồi và cấp phễu

| Mục                            | Mô tả                                                                             |
|--------------------------------|-----------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Kho → reclaimer → bins → feeder tuyến sau                                         |
| Thiết bị tham gia              | RC-101, BN-101                                                                    |
| Thông số vận hành / trạng thái | Reclaim t/h; drive A; travel/position; bin level %; outlet flow; low-level switch |
| Mô hình và phép tính           | M02 năng lực thu hồi; M11 tồn kho; M14 interlock                                  |
| Fault → tác động               | Reclaimer trip, bridging, bin low level → Raw Milling thiếu cấp liệu              |

#### Z01 – L02: Raw Milling

Chức năng: Phối trộn, nghiền và sấy nguyên liệu thành bột liệu đủ độ mịn và độ ẩm để nung.

Chuỗi quy trình: BN-101 → WF-201 → RM-201 → SP-201 → SL-301; dòng thô SP-201 hồi về RM-201; FN-201 cung cấp dòng khí

### P01 Định lượng và phối liệu

| Mục                            | Mô tả                                                                              |
|--------------------------------|------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Đá vôi/đất sét/chất điều chỉnh → tỷ lệ phối trộn mục tiêu                          |
| Thiết bị tham gia              | WF-201                                                                             |
| Thông số vận hành / trạng thái | Per-material flow t/h; SP t/h; belt speed; belt load; totalizer; deviation; status |
| Mô hình và phép tính           | M01 cân bằng khối lượng; M13 thành phần; M14 điều khiển                            |
| Fault → tác động               | Feeder drift/jam, thiếu một thành phần → sai hóa học bột liệu, giảm cấp            |

### P02 Nghiền và sấy đồng thời

| Mục                            | Mô tả                                                                                                                         |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Phối liệu ẩm + khí nóng → hạt nhỏ hơn, nước bay hơi                                                                           |
| Thiết bị tham gia              | RM-201, FN-201                                                                                                                |
| Thông số vận hành / trạng thái | Mill feed/output t/h; power kW; vibration; ΔP Pa; inlet/outlet °C; hydraulic pressure nếu VRM; gas flow; moisture %; fineness |
| Mô hình và phép tính           | M06 nghiền; M07 cân bằng nước; M05 nhiệt; M02 công suất; M10 khí                                                              |
| Fault → tác động               | Ẩm cao, thiếu nhiệt, rung cao, nghẹt mill → giảm năng suất/ẩm sản phẩm tăng                                                   |

### P03 Phân ly và hồi lưu

| Mục                            | Mô tả                                                                          |
|--------------------------------|--------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Dòng bột nghiền → bột mịn ra silo + hạt thô quay về mill                       |
| Thiết bị tham gia              | SP-201                                                                         |
| Thông số vận hành / trạng thái | Rotor rpm; motor A; airflow; return t/h; product residue %; circulating load % |
| Mô hình và phép tính           | M08 phân ly và hồi lưu; M13 độ mịn                                             |
| Fault → tác động               | Separator speed sai, rotor trip → quá thô, tăng hồi lưu hoặc giảm sản lượng    |

### P04 Chuyển bột liệu

| Mục                            | Mô tả                                                                       |
|--------------------------------|-----------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Bột liệu đạt chuẩn → SL-301                                                 |
| Thiết bị tham gia              | RM-201, SP-201, SL-301                                                      |
| Thông số vận hành / trạng thái | Accepted product t/h; moisture; chemistry; transfer status; silo inlet flow |
| Mô hình và phép tính           | M01 dòng ra; M12 trễ; M11 tồn kho silo                                      |
| Fault → tác động               | Tắc tuyến chuyển → mill bị hạn chế bởi downstream                           |

#### Z02 – L01: Kiln Line

Chức năng: Chuyển bột liệu thành clinker qua tiền gia nhiệt, phân hủy carbonate, tạo khoáng và làm nguội.

Chuỗi quy trình: SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302; CF-301 duy trì draft

### P01 Lưu trữ và cấp bột liệu

| Mục                            | Mô tả                                                                       |
|--------------------------------|-----------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Raw meal từ Z01 → cấp ổn định vào preheater                                 |
| Thiết bị tham gia              | SL-301, KF-301                                                              |
| Thông số vận hành / trạng thái | Silo inventory t; level %; feed SP/PV t/h; aeration pressure; feeder status |
| Mô hình và phép tính           | M11 tồn kho; M02 năng lực; M14 feed control                                 |
| Fault → tác động               | Silo low level, bridging, feeder jam → giảm kiln feed                       |

### P02 Tiền gia nhiệt

| Mục                            | Mô tả                                                                       |
|--------------------------------|-----------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Bột liệu tiếp xúc khí nóng ngược chiều → tăng nhiệt, trao đổi nhiệt khí–rắn |
| Thiết bị tham gia              | PH-301, CF-301                                                              |
| Thông số vận hành / trạng thái | Cyclone temperature by stage °C; gas pressure/ΔP Pa; O₂ %; draft; fan flow  |
| Mô hình và phép tính           | M05 trao đổi nhiệt; M10 mạng khí/áp; M12 thời gian lưu                      |
| Fault → tác động               | Cyclone blockage, draft thấp → tăng ΔP, giảm hiệu quả và giới hạn kiln feed |

### P03 Tiền nung/calcination

| Mục                            | Mô tả                                                                      |
|--------------------------------|----------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Bột liệu + nhiên liệu + khí → CaCO₃ phân hủy thành CaO + CO₂               |
| Thiết bị tham gia              | PC-301                                                                     |
| Thông số vận hành / trạng thái | Calciner °C; fuel t/h; air flow; O₂ %; CO ppm; conversion estimate %       |
| Mô hình và phép tính           | M09 phản ứng; M05 nhiệt; M01 cân bằng thành phần và khí                    |
| Fault → tác động               | Fuel shortage, thiếu O₂, nhiệt thấp → conversion giảm, tải nhiệt kiln tăng |

### P04 Nung tạo clinker

| Mục                            | Mô tả                                                                                                         |
|--------------------------------|---------------------------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Vật liệu chuyển động trong lò → phản ứng tạo khoáng clinker                                                   |
| Thiết bị tham gia              | KL-301                                                                                                        |
| Thông số vận hành / trạng thái | Kiln rpm; drive A/torque; burning-zone temp; inlet temp/draft; fuel flow; O₂/CO; shell scan; quality estimate |
| Mô hình và phép tính           | M04 quay và lưu; M05 nhiệt; M09 phản ứng; M13 chất lượng                                                      |
| Fault → tác động               | Nhiên liệu thiếu, feed quá cao, refractory hotspot, drive overload → clinker kém/giảm tải/trip                |

### P05 Làm nguội và thu hồi nhiệt

| Mục                            | Mô tả                                                                                            |
|--------------------------------|--------------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Clinker nóng + khí làm mát → clinker nguội; khí nóng hồi về quá trình                            |
| Thiết bị tham gia              | CL-301                                                                                           |
| Thông số vận hành / trạng thái | Clinker inlet/outlet °C; cooler pressure; grate speed; air flow; fan current; secondary-air temp |
| Mô hình và phép tính           | M05 cân bằng nhiệt; M10 khí; M12 vận chuyển                                                      |
| Fault → tác động               | Cooler fan fail, grate jam → clinker nóng, giới hạn kiln output                                  |

### P06 Lưu trữ clinker

| Mục                            | Mô tả                                                          |
|--------------------------------|----------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Clinker ra cooler → silo → hai Cement Mill                     |
| Thiết bị tham gia              | SL-302                                                         |
| Thông số vận hành / trạng thái | Inventory t; level %; inlet/outlet t/h; discharge gate; alarms |
| Mô hình và phép tính           | M11 tồn kho; M13 chất lượng theo lô                            |
| Fault → tác động               | Silo full/empty, outlet blockage → kiln hoặc mill giảm tải     |

#### Z03 – L01: Cement Mill A

Chức năng: Nghiền clinker cùng thạch cao/phụ gia thành xi măng đạt loại sản phẩm A.

Chuỗi quy trình: SL-302 + gypsum/additives → WF-401A → CM-401A → SP-401A → SL-401; coarse return; FN-401A

### P01 Phối liệu xi măng

| Mục                            | Mô tả                                                        |
|--------------------------------|--------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Clinker + thạch cao + phụ gia → công thức sản phẩm A         |
| Thiết bị tham gia              | WF-401A                                                      |
| Thông số vận hành / trạng thái | Clinker/gypsum/additive t/h; recipe %; feeder SP/PV; motor A |
| Mô hình và phép tính           | M01 và M13 phối liệu; M14 điều khiển                         |
| Fault → tác động               | Sai tỷ lệ, feeder jam → chất lượng sai, giảm feed            |

### P02 Nghiền và điều tiết nhiệt

| Mục                            | Mô tả                                                                                       |
|--------------------------------|---------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Phối liệu → hạt xi măng mịn; sinh nhiệt do nghiền                                           |
| Thiết bị tham gia              | CM-401A, FN-401A                                                                            |
| Thông số vận hành / trạng thái | Mill feed t/h; power kW; vibration; bearing °C; outlet °C; gas flow; fineness/Blaine; kWh/t |
| Mô hình và phép tính           | M06 nghiền; M03 điện; M05 nhiệt; M02 công suất                                              |
| Fault → tác động               | Grinding degradation, bearing hot, ventilation fail → giảm năng suất/độ mịn lệch            |

### P03 Phân ly và hồi lưu

| Mục                            | Mô tả                                                              |
|--------------------------------|--------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Hạt đạt chuẩn → silo; hạt thô → mill                               |
| Thiết bị tham gia              | SP-401A                                                            |
| Thông số vận hành / trạng thái | Separator rpm; reject flow t/h; airflow; product fineness; motor A |
| Mô hình và phép tính           | M08 hồi lưu; M13 độ mịn                                            |
| Fault → tác động               | Rotor fault, phân ly kém → tải hồi lưu tăng, product fineness sai  |

#### Z03 – L02: Cement Mill B

Chức năng: Dây chuyền nghiền song song, độc lập với Mill A; có thể sản xuất loại xi măng B.

Chuỗi quy trình: SL-302 + gypsum/additives → WF-401B → CM-401B → SP-401B → SL-401; coarse return; FN-401B

### P01 Phối liệu xi măng

| Mục                            | Mô tả                                                        |
|--------------------------------|--------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Clinker + thạch cao + phụ gia → công thức sản phẩm B         |
| Thiết bị tham gia              | WF-401B                                                      |
| Thông số vận hành / trạng thái | Clinker/gypsum/additive t/h; recipe %; feeder SP/PV; motor A |
| Mô hình và phép tính           | M01 và M13 phối liệu; M14 điều khiển                         |
| Fault → tác động               | Sai tỷ lệ, thiếu clinker, feeder jam                         |

### P02 Nghiền và điều tiết nhiệt

| Mục                            | Mô tả                                                                                       |
|--------------------------------|---------------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Phối liệu → hạt xi măng mịn                                                                 |
| Thiết bị tham gia              | CM-401B, FN-401B                                                                            |
| Thông số vận hành / trạng thái | Mill feed t/h; power kW; vibration; bearing °C; outlet °C; gas flow; fineness/Blaine; kWh/t |
| Mô hình và phép tính           | M06 nghiền; M03 điện; M05 nhiệt; M02 công suất                                              |
| Fault → tác động               | Mill degradation, fan trip, bearing overheating                                             |

### P03 Phân ly và hồi lưu

| Mục                            | Mô tả                                                                |
|--------------------------------|----------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Hạt mịn đi silo, hạt thô hồi nghiền                                  |
| Thiết bị tham gia              | SP-401B                                                              |
| Thông số vận hành / trạng thái | Rotor rpm; reject t/h; product fineness; motor A                     |
| Mô hình và phép tính           | M08 hồi lưu; M13 chất lượng                                          |
| Fault → tác động               | Separator trip, sai tốc độ → sản phẩm không đạt hoặc giảm throughput |

#### Z04 – L01: Bag Packing

Chức năng: Rút xi măng từ silo, định lượng vào bao, chuyển bao và xếp lên xe.

Chuỗi quy trình: SL-401 → FD-501 → PK-501 → BC-501 → LD-501

### P01 Rút xi măng từ silo

| Mục                            | Mô tả                                                       |
|--------------------------------|-------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Xi măng tồn kho → cấp đều cho packer                        |
| Thiết bị tham gia              | FD-501                                                      |
| Thông số vận hành / trạng thái | Feed t/h; feeder speed; valve position; motor A; silo level |
| Mô hình và phép tính           | M02 capacity; M11 tồn kho; M14 điều khiển                   |
| Fault → tác động               | Silo low, feeder jam → thiếu xi măng cấp máy đóng bao       |

### P02 Định lượng và đóng bao

| Mục                            | Mô tả                                                                                 |
|--------------------------------|---------------------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Xi măng rời + vỏ bao → bao theo khối lượng mục tiêu                                   |
| Thiết bị tham gia              | PK-501                                                                                |
| Thông số vận hành / trạng thái | Rotor rpm; filling pressure; spout status; bag weight kg; bags/min; reject count; jam |
| Mô hình và phép tính           | M16 sự kiện rời rạc; M02 capacity; M15 lỗi                                            |
| Fault → tác động               | Bag shortage, spout jam, under/overweight → giảm bao đạt chuẩn                        |

### P03 Chuyển và xếp bao

| Mục                            | Mô tả                                                                     |
|--------------------------------|---------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Bao thành phẩm → băng tải → xe                                            |
| Thiết bị tham gia              | BC-501, LD-501                                                            |
| Thông số vận hành / trạng thái | Belt speed; photoeye bag count; motor A; jam; truck presence; loaded bags |
| Mô hình và phép tính           | M12 vận chuyển; M16 đếm/xếp; M14 permissive                               |
| Fault → tác động               | Belt jam, truck absent → tắc downstream, packer dừng                      |

#### Z04 – L02: Bulk Loading

Chức năng: Xuất xi măng rời trực tiếp vào xe bồn, kiểm soát khối lượng xuất.

Chuỗi quy trình: SL-401 → FD-502 → SP-502 → WS-502

### P01 Cấp xi măng rời

| Mục                            | Mô tả                                           |
|--------------------------------|-------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Xi măng trong silo → lưu lượng cấp ra ống xuất  |
| Thiết bị tham gia              | FD-502                                          |
| Thông số vận hành / trạng thái | Flow t/h; feeder speed; valve position; motor A |
| Mô hình và phép tính           | M01 dòng vật chất; M02 giới hạn; M14 điều khiển |
| Fault → tác động               | Feeder restriction/blockage → loading rate giảm |

### P02 Kết nối và xuất rời

| Mục                            | Mô tả                                                                   |
|--------------------------------|-------------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Ống xuất hạ đúng vị trí → xi măng vào xe                                |
| Thiết bị tham gia              | SP-502                                                                  |
| Thông số vận hành / trạng thái | Spout position; lowered limit; loading rate; dust extraction permissive |
| Mô hình và phép tính           | M02 capacity; M14 interlock; M10 khí ở mức đơn giản                     |
| Fault → tác động               | Spout not lowered, dust extraction unavailable → không cho xuất         |

### P03 Cân và kết thúc đơn

| Mục                            | Mô tả                                                            |
|--------------------------------|------------------------------------------------------------------|
| Đầu vào → xử lý → đầu ra       | Khối lượng xe tăng đến target → đóng van, hoàn tất               |
| Thiết bị tham gia              | WS-502                                                           |
| Thông số vận hành / trạng thái | Gross/tare/net t; target t; truck present; complete; weigh error |
| Mô hình và phép tính           | M01 tích lũy khối lượng; M16 trạng thái xe; M14 dừng theo target |
| Fault → tác động               | Weighing fault, truck unavailable, overfill risk → ngừng xuất    |

### 4. Silo xi măng dùng chung và ranh giới sản phẩm

SL-401 là một tài sản logic dùng chung sau hai Mill và trước hai tuyến xuất. Với nhiều mác xi măng, cấu hình nhiều ngăn/silo riêng, không trộn chất lượng không tương thích. Mỗi ngăn có inventory, capacity, product_grade, inlet/outlet flow, high/low level và discharge availability. Dòng xi măng chỉ được chuyển vào ngăn phù hợp.

### 5. Danh mục mô hình vật lý: áp dụng ở đâu?

| Mã / Mô hình                | Thiết bị / quy trình điển hình                                   | Phép tính đại diện                                                               |
|-----------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------|
| M01 Cân bằng khối lượng     | Mọi nút dòng/silo; đặc biệt feeder, kiln, cooler, packing        | dM/dt = Σṁin − Σṁout + Σṁreaction (theo cấu tử); tổng khối lượng gồm khí/hơi     |
| M02 Giới hạn năng lực       | Crusher, conveyors, feeders, mills, packer, loading              | Qactual ≤ min(Qfeed available, Qrated·η, Qdownstream available)                  |
| M03 Công suất điện          | Crusher, conveyors, mills, fans, drives                          | P ≈ Qprocessed·Especific + Pidle; hoặc mô hình torque·ω                          |
| M04 Động lực cơ             | Conveyor, drives, kiln rotation, fans                            | J·dω/dt = τmotor − τload; hoặc đáp ứng bậc nhất                                  |
| M05 Cân bằng nhiệt          | Raw mill drying, preheater, calciner, kiln, cooler, cement mill  | dU/dt = Σṁhin − Σṁhout + Qheat − W; có tổn thất                                  |
| M06 Giảm kích thước hạt     | Crusher, Raw Mill, Cement Mill A/B                               | Bond: E=10Wi(1/√P80−1/√F80), F/P µm; hiệu chỉnh theo máy                         |
| M07 Sấy và độ ẩm            | Raw Mill                                                         | ṁdry=ṁwet(1−win); ṁout=ṁdry/(1−wout); ṁevap=ṁwet−ṁout                            |
| M08 Phân ly và hồi lưu      | Raw/Cement separators                                            | D=F+R; P=αD; R=(1−α)D ở steady state không tổn thất                              |
| M09 Phản ứng hóa học        | Precalciner và Rotary Kiln                                       | CaCO3→CaO+CO2; ṁCO2=0.4397·X·ṁCaCO3; clinker quality surrogate                   |
| M10 Dòng khí và áp suất     | Mill fan, preheater, ID fan, cooler, loading spout               | Fan curve + system resistance ΔP≈KQ² (đơn vị/điều kiện xác định)                 |
| M11 Tồn kho                 | Stockpile, bins, raw meal/clinker/cement silo                    | M(t+dt)=M(t)+(Qin−Qout)dt/3600, Q t/h                                            |
| M12 Vận chuyển và trễ       | Belt, material transfer, preheater residence, kiln, bag conveyor | Delay t≈L/v hoặc residence-time/holdup model                                     |
| M13 Chất lượng/thành phần   | Raw blending, kiln, cement blending, silo                        | Mass-weighted composition, moisture, fineness, product grade                     |
| M14 Điều khiển và liên động | Feeder, mills, kiln, silo, packing/loading                       | PID/ramp, permissive, HH/LL trip, anti-windup                                    |
| M15 Suy giảm và lỗi         | Crusher, mills, fan, kiln, packer                                | Fault modifies η, friction, air flow, fuel availability, sensor bias, trip state |
| M16 Sự kiện rời rạc         | Packer, bags, truck arrivals, weighing                           | Bag fill/reject events, truck states, batch completion                           |

### 6. Fault theo Zone và thiết bị: tác động và lan truyền

| Zone | Thiết bị        | Fault                          | Biến đổi trực tiếp               | Lan truyền                            |
|------|-----------------|--------------------------------|----------------------------------|---------------------------------------|
| Z01  | CR-101          | Overload / wear                | η giảm; motor A/rung tăng        | BC flow giảm → raw bins cạn           |
| Z01  | BC-101          | Slip / misalignment            | belt speed/flow giảm, trip       | Stockpile thiếu cấp                   |
| Z01  | ST-101          | Moisture/quality excursion     | moisture/composition thay đổi    | Raw Mill tải sấy tăng, phối liệu lệch |
| Z01  | RC-101 / BN-101 | Reclaim trip / bridging        | outflow giảm, level LL           | WF-201 thiếu liệu                     |
| Z01  | WF-201          | Feeder jam / calibration drift | feed PV khác SP                  | raw meal chemistry sai                |
| Z01  | RM-201          | High vibration / wet feed      | feed giảm; ΔP/ẩm tăng            | SL-301 tồn kho giảm                   |
| Z01  | SP-201 / FN-201 | Rotor/fan failure              | reject/airflow/ΔP đổi            | raw meal fineness sai hoặc mill trip  |
| Z02  | SL-301 / KF-301 | Low level / feed jam           | kiln feed giảm                   | kiln giảm tải sau buffer              |
| Z02  | PH-301          | Cyclone blockage               | ΔP tăng; draft giảm              | kiln feed giảm, nhiệt kém             |
| Z02  | PC-301          | Fuel shortage / low O₂         | T, conversion giảm               | kiln nhiệt tải tăng                   |
| Z02  | KL-301          | Fuel/drive/refractory fault    | T/torque/shell hotspot đổi       | clinker output/quality giảm           |
| Z02  | CL-301          | Cooler fan/grate trip          | airflow giảm, clinker out T tăng | kiln giảm tải                         |
| Z02  | CF-301          | ID fan trip                    | draft mất                        | kiln interlock/trip                   |
| Z02  | SL-302          | Full / discharge blocked       | inventory HH / outlet 0          | kiln hạn chế, mills thiếu clinker     |
| Z03  | WF-401A/B       | Recipe drift / feeder jam      | ratio và feed đổi                | xi măng sai loại/chất lượng           |
| Z03  | CM-401A/B       | Wear / high vibration          | η giảm; power/kWh/t đổi          | sản lượng xi măng giảm                |
| Z03  | SP-401A/B       | Separator malfunction          | recycle/fineness đổi             | output không đạt hoặc giảm            |
| Z03  | FN-401A/B       | Fan trip                       | airflow giảm                     | mill giảm tải/trip                    |
| Z03  | SL-401          | Full / wrong-grade routing     | inventory HH / grade mismatch    | mill giảm tải; nguy cơ lẫn mác        |
| Z04  | FD-501 / PK-501 | Feeder jam / bag jam           | bags/min giảm, rejects tăng      | xuất bao giảm                         |
| Z04  | BC-501 / LD-501 | Conveyor jam / no truck        | bag backlog tăng                 | packer dừng                           |
| Z04  | FD-502 / SP-502 | Restriction / spout not ready  | loading rate giảm hoặc 0         | xuất rời giảm                         |
| Z04  | WS-502          | Scale error / target reached   | weigh discrepancy / stop         | ngừng xuất, kiểm tra cân              |

### 7. Trạng thái và danh mục tag chuẩn

Thiết bị: OFF → STARTING → RUNNING → DEGRADED/WARNING → STOPPING → OFF; TRIPPED cần reset và permissive. Process: IDLE / RAMPING / STABLE / LIMITED / BLOCKED / FAILED. Sensor có quality GOOD/BAD/STALE. Không được đồng nhất alarm với fault: alarm là tín hiệu phát hiện, fault là nguyên nhân.

| Loại    | Ví dụ                                                | Nguồn                        |
|---------|------------------------------------------------------|------------------------------|
| PV (đo) | motor_current_A, temperature_C, belt_speed_mps       | Sensor/PLC hoặc sensor model |
| SP      | feed_setpoint_tph, kiln_speed_sp_rpm                 | Controller                   |
| CALC    | effective_capacity_tph, calcination_pct, inventory_t | Process model                |
| STATE   | RUNNING, TRIPPED, BLOCKED                            | State machine                |
| PARAM   | rated_capacity_tph, silo_capacity_t, heat_capacity   | Equipment configuration      |
| FAULT   | wear_factor, blockage_fraction, fuel_shortage        | Fault injector               |

### 8. Quy tắc tính toán và kiểm chứng

Mỗi timestep: (1) đọc input, lệnh và fault; (2) tính khả năng cấp/nhận; (3) giải phân bổ dòng kể cả recycle; (4) giải vật chất/nhiệt/phản ứng; (5) cập nhật tồn kho và state đồng thời; (6) phát sinh PV/alarms; (7) kiểm tra sai số cân bằng. Với Q t/h, dt giây: ΔM=Q·dt/3600.

Các scenario phải thử: thiếu đầu vào nhưng còn buffer; buffer cạn; downstream silo đầy; lỗi một trong hai Cement Mill; thay đổi độ ẩm; thiếu nhiên liệu; tắc cyclone; mất quạt cooler; kẹt packer; xe rời chưa sẵn sàng. Kiểm chứng rằng output không giảm ngay khi còn buffer, chất lượng có thể xấu đi trước khi throughput giảm, và không có vật chất âm/nhân đôi.

### 9. Các giới hạn của bản V1

Không có OEM datasheet, P&ID, I/O list hoặc lịch sử vận hành thực tế; vì vậy các tag là danh mục tham chiếu, không phải xác nhận tất cả đều được lắp đặt. Chưa chốt rated capacity, chemistry, ngưỡng trip, fan curves, reaction kinetics, specific energy. Cần bộ parameter baseline có đơn vị và basis rõ ràng trước khi chạy số. Các mô hình là reduced-order engineering models, không phải CFD/DEM hay mô hình thiết kế công nghệ chi tiết.

---

## 3.2. Thiết bị, thông số vận hành, mô hình vật lý và fault

ĐẶC TẢ CẤU TRÚC ZONE / LINE / EQUIPMENT, TAG VẬN HÀNH VÀ FAULT LIBRARY

Phiên bản: 2.0 \| Ngày: 23/11/2026 \| Phạm vi: mô phỏng nhà máy xi măng tích hợp (không phải as-built của VICEM Hà Tiên)

Mục đích: tài liệu đầu vào để xây dựng Process Graph, Equipment Models, Telemetry Registry, Fault Injection và SCADA trong Virtual Factory.

### 1. Phạm vi và nguyên tắc

Bao gồm từ nguyên liệu đã được giao đến nhà máy đến sản phẩm xi măng bao/xi măng rời. Không mô hình hóa khai thác mỏ, hệ thống điện/khí nén toàn nhà máy, xử lý môi trường hoặc quản trị doanh nghiệp. Nhiên liệu, khí, nước bay hơi, CO2 và nhiệt vẫn phải xuất hiện trong cân bằng vật chất/năng lượng.

Quy ước: S = cảm biến thực hoặc đo được; C = giá trị tính toán; SP = setpoint; D = trạng thái rời rạc; P = tham số mô hình. Các mục trong bảng là danh mục yêu cầu, KHÔNG khẳng định tất cả đều có sensor lắp đặt trong mọi nhà máy. Cần lập tag dictionary cụ thể cho từng signal khi triển khai.

Quy mô: 4 Zone, 7 Line, 32 thiết bị/cụm trong các Line + 1 cụm silo xi măng dùng chung SL-401 = 33 đối tượng logic. Stockpile/stacker và các weigh feeder nhiều nhánh được gộp ở cấp mô hình; số máy vật lý thực tế có thể lớn hơn.

| Zone                     | Line                      | Số cụm | Sản phẩm ra               |
|--------------------------|---------------------------|--------|---------------------------|
| Raw Material Preparation | Crushing & Storage        | 5      | Raw material              |
| Raw Material Preparation | Raw Milling               | 4      | Raw meal                  |
| Clinker Production       | Kiln Line                 | 8      | Clinker                   |
| Cement Grinding          | Cement Mill A             | 4      | Cement powder             |
| Cement Grinding          | Cement Mill B             | 4      | Cement powder             |
| Packing & Dispatch       | Bag Packing               | 4      | Bagged cement             |
| Packing & Dispatch       | Bulk Loading              | 3      | Bulk cement               |
| Z03/Z04                  | SL-401 Shared Cement Silo | 1      | Cement inventory by grade |

### 2. Process Graph và ranh giới liên kết

Main path: Raw materials → Z01-L01 → Z01-L02 → SL-301 → Z02-L01 → SL-302 → \[Z03-L01 \|\| Z03-L02\] → SL-401 → \[Z04-L01 \|\| Z04-L02\] → dispatch.

Các silo SL-301, SL-302, SL-401 là buffer; mỗi silo chỉ sở hữu một state tồn kho (không nhân đôi trong Line). SL-401 được quản lý như shared asset giữa Z03 và Z04; nếu sản xuất nhiều grade phải tách tồn kho theo silo/compartment và định tuyến grade tương thích. Các tuyến parallel chia sẻ nguyên liệu và có thể tranh chấp giới hạn cấp/xả.

Tương tác xuôi: thiếu feed, hiệu suất nghiền giảm, chất lượng kém hoặc trip gây giảm output downstream sau độ trễ và tồn kho. Tương tác ngược: downstream không tiếp nhận → silo đầy → upstream giảm tải/trip. Đường khí/nhiệt của kiln và vòng hồi lưu separator phải có cạnh riêng trong graph, không chỉ chuỗi một chiều.

### 3. Đặc tả theo Zone → Line → Equipment

### Z01 — Raw Material Preparation

#### Z01-L01 — Crushing & Storage

Chức năng Line: Tiếp nhận nguyên liệu; đập, vận chuyển, lưu trữ và cấp cho phối liệu.

Chuỗi quy trình: Nguồn nguyên liệu → CR-101 → BC-101 → ST-101 → RC-101 → BN-101 → L02. Đất sét/phụ gia có thể đi qua tuyến tiếp nhận riêng; ST-101 là kho vật liệu, không phải một máy đập.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### CR-101 — Crusher

**Quy ước hiển thị SCADA cho Z01–L01.** Bảng vận hành lấy giá trị số từ các kênh đo giả lập trong `measurements`. Các trạng thái chạy, liên động và trip là tín hiệu trạng thái của bộ điều khiển mô phỏng. Giá trị nội bộ phục vụ cân bằng vật chất, giới hạn công suất và mức mòn giả định được dùng trong bộ giải. Sự cố mất tín hiệu đưa giá trị đo liên quan về `null`, hiển thị `—`. Sự cố báo mức cao giả đổi số đo mức và có thể kích hoạt liên động nạp kho, trong khi cân bằng tồn kho vẫn dùng dòng vật liệu thực trong mô hình.

Các phép đo tồn kho giả định dùng kênh độc lập với cảm biến mức: đo tải trên đoạn băng, ước tính khối lượng từ quét thể tích kho, và load cell cân phễu. Màn hình RC-101 dùng lại số đo tồn kho ST-101. Các kênh này là giả định của simulator và có sai số đo riêng.

Chức năng: Giảm kích thước đá vôi; giới hạn dòng liệu theo năng lực đập.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                             |
|-------------------------------------|-----------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Feed t/h; F80 mm; moisture %                                                |
| Vận hành / sức khỏe                 | Motor I A, P kW; speed rpm; bearing T °C; vibration mm/s; lube pressure bar |
| Đầu ra / chất lượng                 | Discharge t/h; P80 mm; oversize fraction                                    |
| Điều khiển / bảo vệ                 | Start/stop; feed setpoint; overload/trip; lube permissive                   |
| Trạng thái                          | STOPPED/STARTING/RUNNING/DERATED/TRIPPED                                    |
| Tham số mô hình (không phải sensor) | rated_tph, size_reduction, work_index, efficiency, trip thresholds          |

Fault theo thiết bị: CR-F01 quá tải/kẹt buồng nghiền → I,P↑, Qout↓/trip; CR-F02 mòn búa/hàm → P80↑, năng suất hiệu dụng↓; CR-F03 thiếu bôi trơn → bearing T↑ → trip

### BC-101 — Belt Conveyor

Chức năng: Chuyển liệu từ crusher tới kho, có trễ vận chuyển.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                |
|-------------------------------------|----------------------------------------------------------------|
| Đầu vào / điều kiện                 | Inlet flow t/h; bulk density                                   |
| Vận hành / sức khỏe                 | Belt speed m/s; belt load kg/m; motor I; pulley T              |
| Đầu ra / chất lượng                 | Outlet flow t/h; accumulated mass                              |
| Điều khiển / bảo vệ                 | Speed SP; slip switch; misalignment; pull-cord; chute blockage |
| Trạng thái                          | RUNNING/SLIPPING/MISALIGNED/JAMMED/TRIPPED                     |
| Tham số mô hình (không phải sensor) | length_m, rated_tph, transport_delay_s, belt_capacity          |

Fault theo thiết bị: BC-F01 trượt băng → speed thực↓, Qout↓; BC-F02 lệch băng → cảnh báo/trip; BC-F03 tắc máng → tích liệu và dừng cấp

### ST-101 — Raw Stockpile / Stacker Area

Chức năng: Đệm vật liệu trước khi thu hồi; lưu trữ theo loại nguyên liệu.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                         |
|-------------------------------------|-------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Inflow t/h; composition; moisture                                       |
| Vận hành / sức khỏe                 | Inventory t; level %; stacker travel/boom position nếu mô phỏng stacker |
| Đầu ra / chất lượng                 | Available material t; reclaim availability                              |
| Điều khiển / bảo vệ                 | Stockpile capacity; high level; stacking permissive                     |
| Trạng thái                          | AVAILABLE/FULL/LOW/UNAVAILABLE                                          |
| Tham số mô hình (không phải sensor) | capacity_t, initial_t, reclaimable_fraction, quality_layers             |

Fault theo thiết bị: ST-F01 kho đầy → hạn chế upstream; ST-F02 ẩm nguyên liệu tăng → tăng tải sấy ở RM-201; ST-F03 phân tầng chất lượng → sai lệch phối liệu

### RC-101 — Reclaimer

Chức năng: Thu hồi nguyên liệu từ kho và cấp đến bins.

| Nhóm                                | Thông số / tín hiệu cần quản lý                         |
|-------------------------------------|---------------------------------------------------------|
| Đầu vào / điều kiện                 | Available stock t; moisture                             |
| Vận hành / sức khỏe                 | Reclaim rate t/h; drive current; travel speed; position |
| Đầu ra / chất lượng                 | Outlet t/h                                              |
| Điều khiển / bảo vệ                 | Reclaim SP; drive interlock; travel limits              |
| Trạng thái                          | RUNNING/DERATED/TRIPPED/STARVED                         |
| Tham số mô hình (không phải sensor) | rated_tph, efficiency, response_time_s                  |

Fault theo thiết bị: RC-F01 cơ cấu thu hồi suy giảm → Qout↓; RC-F02 drive trip → Qout=0; RC-F03 stockpile cạn → thiếu cấp

### BN-101 — Raw Material Bins

Chức năng: Đệm nguyên liệu riêng theo thành phần trước weigh feeders.

| Nhóm                                | Thông số / tín hiệu cần quản lý                           |
|-------------------------------------|-----------------------------------------------------------|
| Đầu vào / điều kiện                 | Inflow by material t/h; composition                       |
| Vận hành / sức khỏe                 | Level %; inventory t; outlet gate position                |
| Đầu ra / chất lượng                 | Available discharge t/h                                   |
| Điều khiển / bảo vệ                 | High-high/low-low; gate command                           |
| Trạng thái                          | NORMAL/LOW/EMPTY/FULL/BLOCKED                             |
| Tham số mô hình (không phải sensor) | capacity_t_by_material, min_usable_t, discharge_limit_tph |

Fault theo thiết bị: BN-F01 hết liệu → feeder starved; BN-F02 bridging → outlet flow↓ dù level còn; BN-F03 đầy → chặn upstream

#### Z01-L02 — Raw Milling

Chức năng Line: Định lượng phối liệu, nghiền và sấy thành bột liệu đạt độ mịn/độ ẩm mục tiêu.

Chuỗi quy trình: BN-101 → WF-201 → RM-201 → SP-201 → bột mịn tới SL-301; phần thô hồi lưu RM-201. FN-201 cấp lưu lượng khí/quạt hút cho tuyến nghiền.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### WF-201 — Raw Weigh Feeder System

Chức năng: Định lượng đá vôi, đất sét và chất điều chỉnh theo recipe.

| Nhóm                                | Thông số / tín hiệu cần quản lý                            |
|-------------------------------------|------------------------------------------------------------|
| Đầu vào / điều kiện                 | Bin availability; composition; moisture                    |
| Vận hành / sức khỏe                 | Actual t/h từng feeder; belt speed; belt load; totalized t |
| Đầu ra / chất lượng                 | Blended feed t/h; blend fractions                          |
| Điều khiển / bảo vệ                 | Individual SP t/h; recipe; deviation alarm                 |
| Trạng thái                          | AUTO/MANUAL/STARVED/JAMMED/TRIPPED                         |
| Tham số mô hình (không phải sensor) | rated_tph_each, recipe, calibration_error, response_time   |

Fault theo thiết bị: WF-F01 kẹt feeder → thiếu một cấu tử; WF-F02 lệch cân → phối liệu sai; WF-F03 thiếu liệu bin → tổng feed↓

### RM-201 — Raw Mill (VRM giả định)

Chức năng: Nghiền, sấy hỗn hợp thành raw meal.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                                                    |
|-------------------------------------|----------------------------------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Feed t/h; F80; moisture; gas inlet T/flow                                                          |
| Vận hành / sức khỏe                 | Mill P kW; motor I; vibration; ΔP Pa; hydraulic grinding pressure; roller/bearing T; lube pressure |
| Đầu ra / chất lượng                 | Product t/h; fineness/residue; moisture; outlet T                                                  |
| Điều khiển / bảo vệ                 | Feed SP; roller pressure SP; mill stop on high vibration/ΔP/T                                      |
| Trạng thái                          | STOPPED/STARTING/RUNNING/DERATED/TRIPPED                                                           |
| Tham số mô hình (không phải sensor) | rated_tph, kWh_per_t, drying_heat_kw, thermal_mass, grind_efficiency                               |

Fault theo thiết bị: RM-F01 độ ẩm cao → năng lực sấy giới hạn Qout; RM-F02 high vibration → controller giảm feed/trip; RM-F03 roller wear → energy/t↑, fineness xấu; RM-F04 gas flow thấp → outlet moisture↑

### SP-201 — Raw Mill Separator

Chức năng: Phân loại hạt, hồi lưu hạt thô về mill.

| Nhóm                                | Thông số / tín hiệu cần quản lý                  |
|-------------------------------------|--------------------------------------------------|
| Đầu vào / điều kiện                 | Mill discharge t/h; PSD; airflow                 |
| Vận hành / sức khỏe                 | Rotor rpm; current; pressure drop; reject ratio  |
| Đầu ra / chất lượng                 | Fine flow t/h; coarse return t/h; fineness       |
| Điều khiển / bảo vệ                 | Rotor speed SP; separator trip                   |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                          |
| Tham số mô hình (không phải sensor) | cut_size, separation_curve, holdup_t, efficiency |

Fault theo thiết bị: SP-F01 rotor trip → phân ly không đạt; SP-F02 tốc độ sai → fineness lệch, circulating load↑

### FN-201 — Raw Mill Fan

Chức năng: Duy trì dòng khí vận chuyển/sấy và áp suất.

| Nhóm                                | Thông số / tín hiệu cần quản lý                         |
|-------------------------------------|---------------------------------------------------------|
| Đầu vào / điều kiện                 | Gas inlet T; resistance                                 |
| Vận hành / sức khỏe                 | Speed rpm; flow m3/h; ΔP Pa; P kW; vibration; bearing T |
| Đầu ra / chất lượng                 | Gas outlet flow/pressure                                |
| Điều khiển / bảo vệ                 | Speed/damper SP; vibration and temperature trips        |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                                 |
| Tham số mô hình (không phải sensor) | fan_curve, efficiency, system_resistance, max_speed     |

Fault theo thiết bị: FN-F01 fan degradation → airflow↓, drying↓; FN-F02 bearing overheating → trip; FN-F03 damper stuck → draft sai

### Z02 — Clinker Production

#### Z02-L01 — Kiln Line

Chức năng Line: Tích trữ raw meal, cấp liệu, tiền gia nhiệt, phân hủy carbonate, nung tạo clinker và làm nguội.

Chuỗi quy trình: SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302. Dòng khí nóng đi ngược chiều vật liệu qua preheater; CF-301 duy trì draft. Khí/nhiên liệu/CO2 cần được tính trong cân bằng dù không mô hình Zone phụ trợ.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### SL-301 — Raw Meal Silo

Chức năng: Đệm bột liệu trước hệ thống nung.

| Nhóm                                | Thông số / tín hiệu cần quản lý                         |
|-------------------------------------|---------------------------------------------------------|
| Đầu vào / điều kiện                 | Raw meal inflow t/h; quality/LOI                        |
| Vận hành / sức khỏe                 | Inventory t; level %; aeration pressure                 |
| Đầu ra / chất lượng                 | Available kiln feed t/h                                 |
| Điều khiển / bảo vệ                 | Low-low/high-high; discharge gates                      |
| Trạng thái                          | NORMAL/LOW/EMPTY/FULL/BLOCKED                           |
| Tham số mô hình (không phải sensor) | capacity_t, initial_t, min_operating_t, discharge_limit |

Fault theo thiết bị: SL301-F01 low level → kiln feed bị giới hạn; SL301-F02 bridging → discharge↓; SL301-F03 full → raw mill bị chặn

### KF-301 — Kiln Feed System

Chức năng: Cấp bột liệu ổn định vào preheater.

| Nhóm                                | Thông số / tín hiệu cần quản lý              |
|-------------------------------------|----------------------------------------------|
| Đầu vào / điều kiện                 | Silo available mass; raw meal quality        |
| Vận hành / sức khỏe                 | Actual feed t/h; feeder speed; motor current |
| Đầu ra / chất lượng                 | Raw meal to PH t/h                           |
| Điều khiển / bảo vệ                 | Feed SP; deviation alarm; kiln permissives   |
| Trạng thái                          | RUNNING/DERATED/JAMMED/TRIPPED               |
| Tham số mô hình (không phải sensor) | rated_tph, response_s, calibration_error     |

Fault theo thiết bị: KF-F01 feeder jam → feed↓; KF-F02 cân lệch → cấp sai; KF-F03 thiếu silo → giảm tải lò

### PH-301 — Preheater Cyclone Train

Chức năng: Trao đổi nhiệt khí nóng–bột liệu, tiền gia nhiệt và tiền phân hủy.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                   |
|-------------------------------------|-------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Raw meal t/h; kiln exhaust gas T/flow                             |
| Vận hành / sức khỏe                 | Stage gas T; pressure; ΔP; selected O2/CO; material T estimate    |
| Đầu ra / chất lượng                 | Heated meal T; gas outlet T; pressure loss                        |
| Điều khiển / bảo vệ                 | Draft constraints; blockage alarms                                |
| Trạng thái                          | NORMAL/FOULING/BLOCKED/TRIPPED                                    |
| Tham số mô hình (không phải sensor) | stage_count, heat_transfer_UA, pressure_loss_curve, solids_holdup |

Fault theo thiết bị: PH-F01 tắc cyclone → ΔP↑, draft↓, kiln feed giảm/trip; PH-F02 heat exchange degradation → meal T↓, fuel demand↑

### PC-301 — Precalciner

Chức năng: Đốt nhiên liệu và phân hủy CaCO3 trước kiln.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                     |
|-------------------------------------|---------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Meal t/h; fuel t/h; combustion air; O2                              |
| Vận hành / sức khỏe                 | Calciner T; draft; gas O2/CO; fuel flow                             |
| Đầu ra / chất lượng                 | Calcination degree estimated; outlet meal T; CO2 flow               |
| Điều khiển / bảo vệ                 | Fuel SP; air-fuel interlock; CO/high T alarms                       |
| Trạng thái                          | RUNNING/LOW_HEAT/COMBUSTION_FAULT/TRIPPED                           |
| Tham số mô hình (không phải sensor) | fuel_LHV, reaction_enthalpy, residence_s, kinetic_or_conversion_map |

Fault theo thiết bị: PC-F01 fuel shortage → conversion↓; PC-F02 thiếu khí → CO↑, cháy kém; PC-F03 temperature low → kiln thermal load↑

### KL-301 — Rotary Kiln

Chức năng: Hoàn thành nung clinker và hình thành khoáng clinker.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                                                                       |
|-------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Precalcined meal; fuel; air; secondary air T                                                                          |
| Vận hành / sức khỏe                 | Kiln rpm; drive torque/current; burning-zone T estimate; inlet T/pressure; O2/CO; shell T; roller/tyre T; lubrication |
| Đầu ra / chất lượng                 | Hot clinker t/h; quality index; exhaust gas; CO2                                                                      |
| Điều khiển / bảo vệ                 | Speed SP; fuel SP; draft; flame and drive interlocks                                                                  |
| Trạng thái                          | HEATING/RUNNING/DERATED/UNSTABLE/TRIPPED                                                                              |
| Tham số mô hình (không phải sensor) | thermal_mass_MJ_K, heat_loss, fuel_LHV, residence_time, clinker_yield, quality_map                                    |

Fault theo thiết bị: KL-F01 fuel shortage → burning T↓, quality↓; KL-F02 drive overload → rpm↓/trip; KL-F03 refractory heat loss↑ → shell T↑; KL-F04 high CO → combustion protection

### CL-301 — Clinker Cooler

Chức năng: Làm nguội clinker và thu hồi nhiệt cho khí thứ cấp.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                           |
|-------------------------------------|---------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Hot clinker t/h/T; cooling air                                            |
| Vận hành / sức khỏe                 | Grate speed; fan airflow/current; bed pressure; outlet T; secondary air T |
| Đầu ra / chất lượng                 | Cooled clinker t/h/T; recovered heat                                      |
| Điều khiển / bảo vệ                 | Grate SP; fan SP; hot clinker alarm                                       |
| Trạng thái                          | RUNNING/DERATED/OVERHEATED/TRIPPED                                        |
| Tham số mô hình (không phải sensor) | rated_tph, air_curve, heat_transfer_UA, grate_capacity                    |

Fault theo thiết bị: CL-F01 cooler fan fail → clinker outlet T↑, heat recovery↓; CL-F02 grate jam → bed depth↑, throughput↓; CL-F03 airflow imbalance → local hot spots

### CF-301 — Kiln ID Fan

Chức năng: Duy trì hút khí và áp suất âm kiln/preheater.

| Nhóm                                | Thông số / tín hiệu cần quản lý                               |
|-------------------------------------|---------------------------------------------------------------|
| Đầu vào / điều kiện                 | Hot gas flow/T; dust load                                     |
| Vận hành / sức khỏe                 | Speed; inlet/outlet P; draft; motor I/P; vibration; bearing T |
| Đầu ra / chất lượng                 | Exhaust flow; available draft                                 |
| Điều khiển / bảo vệ                 | Speed SP; damper; high vibration trip                         |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                                       |
| Tham số mô hình (không phải sensor) | fan_curve, system_resistance, efficiency                      |

Fault theo thiết bị: CF-F01 fan capacity loss → draft↓, preheater ΔP↑; CF-F02 trip → kiln feed/fuel interlock

### SL-302 — Clinker Silo

Chức năng: Đệm clinker cấp hai cement mill.

| Nhóm                                | Thông số / tín hiệu cần quản lý                           |
|-------------------------------------|-----------------------------------------------------------|
| Đầu vào / điều kiện                 | Cooler discharge t/h; clinker quality/T                   |
| Vận hành / sức khỏe                 | Inventory t; level %; discharge status                    |
| Đầu ra / chất lượng                 | Available clinker t/h to A/B                              |
| Điều khiển / bảo vệ                 | High-high/low-low; discharge gates                        |
| Trạng thái                          | NORMAL/LOW/EMPTY/FULL/BLOCKED                             |
| Tham số mô hình (không phải sensor) | capacity_t, initial_t, max_discharge_tph, quality_batches |

Fault theo thiết bị: SL302-F01 low level → mill A/B thiếu clinker; SL302-F02 full → kiln giảm tải; SL302-F03 outlet blocked → mill starved

### Z03 — Cement Grinding

#### Z03-L01 — Cement Mill A

Chức năng Line: Nghiền clinker, thạch cao và phụ gia theo recipe A, chuyển sản phẩm vào silo xi măng đúng grade.

Chuỗi quy trình: SL-302 + gypsum/additive bins → WF-401A → CM-401A → SP-401A → SL-401; coarse return về CM-401A; FN-401A cung cấp khí.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### WF-401A — Weigh Feeders A

Chức năng: Định lượng clinker, gypsum, additives cho Mill A.

| Nhóm                                | Thông số / tín hiệu cần quản lý                   |
|-------------------------------------|---------------------------------------------------|
| Đầu vào / điều kiện                 | Clinker/gypsum/additive availability              |
| Vận hành / sức khỏe                 | Individual actual t/h; belt speed; totalized mass |
| Đầu ra / chất lượng                 | Blended feed t/h; composition                     |
| Điều khiển / bảo vệ                 | Recipe SP; ratio control; deviation alarms        |
| Trạng thái                          | AUTO/STARVED/JAMMED/TRIPPED                       |
| Tham số mô hình (không phải sensor) | rated_each, recipe_A, accuracy                    |

Fault theo thiết bị: WFA-F01 clinker shortage → feed↓; WFA-F02 gypsum ratio drift → chất lượng cement sai; WFA-F03 jam → line A giảm

### CM-401A — Cement Mill A

Chức năng: Nghiền phối liệu thành xi măng đạt độ mịn mục tiêu.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                             |
|-------------------------------------|-----------------------------------------------------------------------------|
| Đầu vào / điều kiện                 | Blend t/h; PSD; moisture                                                    |
| Vận hành / sức khỏe                 | Power kW; current; vibration; bearing T; lubrication P; outlet T; mill load |
| Đầu ra / chất lượng                 | Discharge t/h; Blaine estimate; kWh/t                                       |
| Điều khiển / bảo vệ                 | Feed SP; temperature and vibration trips                                    |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                                                     |
| Tham số mô hình (không phải sensor) | rated_tph, energy_curve, thermal_mass, wear_factor                          |

Fault theo thiết bị: CMA-F01 wear → kWh/t↑, capacity↓; CMA-F02 overload → power↑, trip; CMA-F03 overheating → feed giảm

### SP-401A — Cement Separator A

Chức năng: Tách hạt mịn, hồi lưu hạt thô.

| Nhóm                                | Thông số / tín hiệu cần quản lý          |
|-------------------------------------|------------------------------------------|
| Đầu vào / điều kiện                 | Mill discharge; PSD; airflow             |
| Vận hành / sức khỏe                 | Rotor rpm; motor I; ΔP; circulating load |
| Đầu ra / chất lượng                 | Fine cement t/h; return t/h; Blaine      |
| Điều khiển / bảo vệ                 | Speed SP; classifier trip                |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                  |
| Tham số mô hình (không phải sensor) | efficiency_curve, recycle_holdup         |

Fault theo thiết bị: SPA-F01 rotor speed drift → fineness sai; SPA-F02 reject excess → circulating load↑, mill capacity↓

### FN-401A — Mill Fan A

Chức năng: Thông gió/vận chuyển bụi mịn cho circuit A.

| Nhóm                                | Thông số / tín hiệu cần quản lý              |
|-------------------------------------|----------------------------------------------|
| Đầu vào / điều kiện                 | Gas flow demand; system resistance           |
| Vận hành / sức khỏe                 | Fan rpm; airflow; pressure; power; vibration |
| Đầu ra / chất lượng                 | Available transport air                      |
| Điều khiển / bảo vệ                 | Speed/damper SP; trips                       |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                      |
| Tham số mô hình (không phải sensor) | fan_curve, efficiency                        |

Fault theo thiết bị: FNA-F01 airflow↓ → mill T↑, classification↓; FNA-F02 fan trip → mill interlock

#### Z03-L02 — Cement Mill B

Chức năng Line: Dây chuyền nghiền song song độc lập với Mill A; có thể chạy recipe/grade khác.

Chuỗi quy trình: SL-302 + gypsum/additive bins → WF-401B → CM-401B → SP-401B → SL-401 (đúng grade); coarse return về CM-401B; FN-401B cấp khí.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### WF-401B — Weigh Feeders B

Chức năng: Định lượng phối liệu cho Mill B.

| Nhóm                                | Thông số / tín hiệu cần quản lý      |
|-------------------------------------|--------------------------------------|
| Đầu vào / điều kiện                 | Clinker/gypsum/additive availability |
| Vận hành / sức khỏe                 | Individual t/h; speed; totalizer     |
| Đầu ra / chất lượng                 | Blended feed t/h; recipe ratio       |
| Điều khiển / bảo vệ                 | Recipe B; feeder SP; deviation alarm |
| Trạng thái                          | AUTO/STARVED/JAMMED/TRIPPED          |
| Tham số mô hình (không phải sensor) | rated_each, recipe_B, accuracy       |

Fault theo thiết bị: WFB-F01 thiếu clinker; WFB-F02 sai recipe; WFB-F03 jam → output B↓

### CM-401B — Cement Mill B

Chức năng: Nghiền xi măng độc lập với Mill A.

| Nhóm                                | Thông số / tín hiệu cần quản lý                               |
|-------------------------------------|---------------------------------------------------------------|
| Đầu vào / điều kiện                 | Blend t/h; PSD; moisture                                      |
| Vận hành / sức khỏe                 | Power; current; vibration; bearing T; lubrication P; outlet T |
| Đầu ra / chất lượng                 | Discharge t/h; Blaine; specific energy                        |
| Điều khiển / bảo vệ                 | Feed SP; protection                                           |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                                       |
| Tham số mô hình (không phải sensor) | rated_tph, energy_curve, wear_factor                          |

Fault theo thiết bị: CMB-F01 wear → capacity↓; CMB-F02 bearing overheating → trip; CMB-F03 overload → throughput↓

### SP-401B — Cement Separator B

Chức năng: Phân loại xi măng, tạo vòng hồi lưu B.

| Nhóm                                | Thông số / tín hiệu cần quản lý |
|-------------------------------------|---------------------------------|
| Đầu vào / điều kiện                 | Mill discharge; PSD; airflow    |
| Vận hành / sức khỏe                 | Rotor rpm; I; ΔP; return flow   |
| Đầu ra / chất lượng                 | Fine cement t/h; fineness       |
| Điều khiển / bảo vệ                 | Rotor speed SP                  |
| Trạng thái                          | RUNNING/DERATED/TRIPPED         |
| Tham số mô hình (không phải sensor) | efficiency_curve, holdup        |

Fault theo thiết bị: SPB-F01 rotor trip → fineness mất kiểm soát; SPB-F02 efficiency↓ → recycle↑

### FN-401B — Mill Fan B

Chức năng: Duy trì thông gió và khí vận chuyển Mill B.

| Nhóm                                | Thông số / tín hiệu cần quản lý          |
|-------------------------------------|------------------------------------------|
| Đầu vào / điều kiện                 | Gas demand; resistance                   |
| Vận hành / sức khỏe                 | Speed; airflow; pressure; I/P; vibration |
| Đầu ra / chất lượng                 | Available transport air                  |
| Điều khiển / bảo vệ                 | Speed SP; trip                           |
| Trạng thái                          | RUNNING/DERATED/TRIPPED                  |
| Tham số mô hình (không phải sensor) | fan_curve, efficiency                    |

Fault theo thiết bị: FNB-F01 fan degradation → airflow↓; FNB-F02 trip → B giảm/dừng

### Z04 — Packing & Dispatch

#### Z04-L01 — Bag Packing

Chức năng Line: Lấy xi măng từ silo, đóng bao theo khối lượng đặt, vận chuyển và bốc lên xe.

Chuỗi quy trình: SL-401 → FD-501 → PK-501 → BC-501 → LD-501 → xi măng bao. Phân biệt số bao tạo, bao đạt và bao đã xếp lên xe.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### FD-501 — Bag Line Discharge Feeder

Chức năng: Cấp xi măng từ silo vào packer.

| Nhóm                                | Thông số / tín hiệu cần quản lý                 |
|-------------------------------------|-------------------------------------------------|
| Đầu vào / điều kiện                 | Silo inventory; cement grade                    |
| Vận hành / sức khỏe                 | Flow t/h; feeder speed; current; valve position |
| Đầu ra / chất lượng                 | Cement to packer t/h                            |
| Điều khiển / bảo vệ                 | Feed SP; silo low interlock                     |
| Trạng thái                          | RUNNING/STARVED/BLOCKED/TRIPPED                 |
| Tham số mô hình (không phải sensor) | rated_tph, response_s                           |

Fault theo thiết bị: FD501-F01 nghẹt xả → flow↓; FD501-F02 silo cạn → packer starved

### PK-501 — Rotary Packer

Chức năng: Chiết rót xi măng vào bao, kiểm tra trọng lượng và loại bao lỗi.

| Nhóm                                | Thông số / tín hiệu cần quản lý                                |
|-------------------------------------|----------------------------------------------------------------|
| Đầu vào / điều kiện                 | Cement t/h; empty bag availability                             |
| Vận hành / sức khỏe                 | Rotor rpm; filling pressure; spout state; bag weight; bags/min |
| Đầu ra / chất lượng                 | Good bags/min; reject bags/min; total bags                     |
| Điều khiển / bảo vệ                 | Bag target kg; weight tolerance; jam detection                 |
| Trạng thái                          | RUNNING/NO_BAGS/JAMMED/DERATED/TRIPPED                         |
| Tham số mô hình (không phải sensor) | spouts, rpm, fill_time, reject_probability, bag_target_kg      |

Fault theo thiết bị: PK-F01 thiếu bao → good bags↓; PK-F02 vòi đóng bao lỗi → reject↑; PK-F03 jam → line dừng

### BC-501 — Bag Conveyor

Chức năng: Chuyển bao thành phẩm tới trạm bốc.

| Nhóm                                | Thông số / tín hiệu cần quản lý                  |
|-------------------------------------|--------------------------------------------------|
| Đầu vào / điều kiện                 | Good bag rate; bag dimensions                    |
| Vận hành / sức khỏe                 | Belt speed; motor current; bag count; jam sensor |
| Đầu ra / chất lượng                 | Delivered bags/min                               |
| Điều khiển / bảo vệ                 | Speed SP; jam/misalignment interlock             |
| Trạng thái                          | RUNNING/JAMMED/TRIPPED                           |
| Tham số mô hình (không phải sensor) | rated_bags_min, transit_s, buffer_bags           |

Fault theo thiết bị: BC501-F01 kẹt bao → buffer đầy, packer giảm; BC501-F02 drive trip → dispatch=0

### LD-501 — Bag Loading Station

Chức năng: Xếp bao lên xe và xác nhận số bao đã giao.

| Nhóm                                | Thông số / tín hiệu cần quản lý                 |
|-------------------------------------|-------------------------------------------------|
| Đầu vào / điều kiện                 | Delivered bags/min; truck presence              |
| Vận hành / sức khỏe                 | Loaded bag count; loader status; truck capacity |
| Đầu ra / chất lượng                 | Dispatched bag count / mass                     |
| Điều khiển / bảo vệ                 | Truck permissive; order target; stop command    |
| Trạng thái                          | WAIT_TRUCK/LOADING/COMPLETE/TRIPPED             |
| Tham số mô hình (không phải sensor) | loading_bags_min, truck_schedule, order_bags    |

Fault theo thiết bị: LD-F01 không có xe → tồn bao tăng; LD-F02 loader failure → bag dispatch↓

#### Z04-L02 — Bulk Loading

Chức năng Line: Cấp xi măng rời vào xe bồn, cân khối lượng và kết thúc khi đạt mục tiêu.

Chuỗi quy trình: SL-401 → FD-502 → SP-502 → WS-502 → xe bồn. Lưu ý cân có thể đo khối lượng xe theo thời gian, không phải thiết bị nối tiếp trên đường chảy vật liệu.

Line KPIs: input_tph, output_tph, output_quality, energy_kwh_t (nếu phù hợp), availability, throughput_loss_t, upstream_starved, downstream_blocked, active_faults, material_holdup_t.

### FD-502 — Bulk Discharge Feeder

Chức năng: Điều tiết xi măng cấp vào loading spout.

| Nhóm                                | Thông số / tín hiệu cần quản lý                 |
|-------------------------------------|-------------------------------------------------|
| Đầu vào / điều kiện                 | Silo availability; order demand                 |
| Vận hành / sức khỏe                 | Flow t/h; feeder speed; motor I; valve position |
| Đầu ra / chất lượng                 | Flow to spout t/h                               |
| Điều khiển / bảo vệ                 | Flow SP; loading permissive                     |
| Trạng thái                          | RUNNING/BLOCKED/STARVED/TRIPPED                 |
| Tham số mô hình (không phải sensor) | rated_tph, response_s                           |

Fault theo thiết bị: FD502-F01 nghẹt → flow↓; FD502-F02 feeder trip → flow=0

### SP-502 — Bulk Loading Spout

Chức năng: Dẫn xi măng vào miệng xe bồn, kiểm soát vị trí và hút bụi cục bộ.

| Nhóm                                | Thông số / tín hiệu cần quản lý                       |
|-------------------------------------|-------------------------------------------------------|
| Đầu vào / điều kiện                 | Feed t/h; truck position                              |
| Vận hành / sức khỏe                 | Spout position; lower limit; extraction status; flow  |
| Đầu ra / chất lượng                 | Delivered cement t/h                                  |
| Điều khiển / bảo vệ                 | Lower/raise command; truck and extraction permissives |
| Trạng thái                          | RAISED/LOWERING/READY/LOADING/FAULT                   |
| Tham số mô hình (không phải sensor) | rated_tph, position_limits, permissive_logic          |

Fault theo thiết bị: SP502-F01 spout không hạ → không cho cấp; SP502-F02 dust extraction fail → inhibit/stop theo logic; SP502-F03 blockage → flow↓

### WS-502 — Truck Weighing Station

Chức năng: Cân net loaded mass và xác nhận hoàn tất đơn hàng.

| Nhóm                                | Thông số / tín hiệu cần quản lý                       |
|-------------------------------------|-------------------------------------------------------|
| Đầu vào / điều kiện                 | Truck tare; material loading rate                     |
| Vận hành / sức khỏe                 | Gross/tare/net mass; scale status; loading rate       |
| Đầu ra / chất lượng                 | Loaded mass t; completion flag                        |
| Điều khiển / bảo vệ                 | Target mass; cutoff compensation; overfill protection |
| Trạng thái                          | WAIT_TRUCK/TARING/LOADING/COMPLETE/FAULT              |
| Tham số mô hình (không phải sensor) | scale_accuracy, cutoff_delay_s, truck_target_t        |

Fault theo thiết bị: WS-F01 scale fault → inhibit loading; WS-F02 cut-off delay → nguy cơ overfill; WS-F03 truck absent → không cho xuất

### 4. Shared Asset — SL-401 Cement Silo

### SL-401 — Cement Silo Bank

Chức năng: Đệm xi măng thành phẩm từ hai mill và cấp cho hai tuyến xuất hàng; phân tách theo grade nếu có nhiều mác.

| Nhóm                                | Thông số / tín hiệu cần quản lý                              |
|-------------------------------------|--------------------------------------------------------------|
| Đầu vào / điều kiện                 | Inflow Mill A/B t/h, grade, temperature                      |
| Vận hành / sức khỏe                 | Inventory t/grade; level %; aeration; outlet valves          |
| Đầu ra / chất lượng                 | Discharge to FD-501/FD-502 t/h; available capacity           |
| Điều khiển / bảo vệ                 | High-high/low-low; route selection; grade permissive         |
| Trạng thái                          | NORMAL/LOW/FULL/BLOCKED/WRONG_ROUTE                          |
| Tham số mô hình (không phải sensor) | capacity_t_per_grade, initial_t, max_inout_tph, min_usable_t |

Fault theo thiết bị: SL401-F01 silo đầy → Mill A/B phải giảm/dừng; SL401-F02 outlet blockage → Packing/Bulk thiếu cấp; SL401-F03 sai routing grade → quality hold

### 5. Mô hình vật lý và phép tính tối thiểu

#### 5.1 Cân bằng tồn kho

M(t+dt)=M(t)+dt/3600 × (ΣQin−ΣQout), với Q tính t/h, dt tính s. Dòng vật chất phải được phân bổ theo nguồn khả dụng, giới hạn thiết bị, giới hạn silo và tuyến đích trước khi cập nhật state.

#### 5.2 Công suất thiết bị

Qactual ≤ min(Qinput_available, Qrated×ηcondition, Qdownstream_accept). ηcondition bị thay đổi bởi wear/fault; interlock có thể ép Qactual=0. Chỉ giảm η khi nguyên nhân có thật, không sửa trực tiếp output tag.

#### 5.3 Băng tải và feeder

Qbelt(t/h)=3.6×belt_load(kg/m)×belt_speed(m/s). Thêm transport delay, buffer và giới hạn load; feeder có response time và sai số định lượng.

#### 5.4 Nghiền và sấy

Specific energy kWh/t, grinding capacity theo feed hardness, fineness và wear. Water evaporation = wet feed − dry-basis-corrected product; Qdrying ≥ evaporation×latent_heat + sensible_heat. Moisture phải khai báo wet basis.

#### 5.5 Separator

Trong steady state không thất thoát: D=F+R, P=αD, R=(1−α)D, P=F; transient cần holdup. Độ mịn sản phẩm là hàm của rotor speed, air flow, PSD và hiệu suất phân ly.

#### 5.6 Calcination và kiln

CaCO3 → CaO + CO2. Với CaCO3 phản ứng: mCO2 ≈0.4397×mCaCO3×X, mCaO ≈0.5603×mCaCO3×X. Tính cả CO2, hơi nước và nhiên liệu/khí trong mass balance. Heat balance: dU/dt=enthalpy_in−enthalpy_out+Qfuel−Qreaction−Qloss. Fuel energy MW = fuel(t/h)×LHV(MJ/kg)/3.6.

#### 5.7 Cooler

Qcooling ≈ mclinker×cp×(Tin−Tout), trừ/tính phần tích trữ nhiệt. Cooling air và grate capacity giới hạn clinker throughput; secondary-air heat recovery ảnh hưởng ngược kiln.

#### 5.8 Đóng bao / xuất rời

Bag throughput (t/h)=good_bags_per_hour×bag_weight_kg/1000. Bulk net_mass(t+dt)=net_mass(t)+Qload(t/h)×dt/3600; stop khi đạt target với bù độ trễ cutoff.

#### 5.9 Động học và sensor

Các state nhiệt, tốc độ, feed và tồn kho có quán tính. Sensor = physical truth + bias + noise + lag. Fault sensor phải khác fault process; trạng thái thật không được thay đổi chỉ vì sensor sai.

### 6. Fault taxonomy và quy tắc lan truyền

| Loại                   | Thay đổi trong engine                               | Hậu quả có thể quan sát                                  |
|------------------------|-----------------------------------------------------|----------------------------------------------------------|
| Input disturbance      | Nguồn cấp/độ ẩm/độ cứng/thành phần thay đổi         | Qin, moisture, fineness, heat demand, quality            |
| Equipment degradation  | Hiệu suất, ma sát, capacity, UA, fan curve thay đổi | P, vibration, ΔP, temperature, Qout                      |
| Actuator/control fault | Speed, valve, damper, feed SP, response thay đổi    | PV-SP deviation, line derate, trip                       |
| Trip / interlock       | State chuyển TRIPPED; flow về 0 theo ramp           | Buffer depletion/accumulation, downstream loss           |
| Measurement fault      | Bias/stuck/noise/delay tại sensor                   | PV sai, có thể gây control response nếu dùng closed loop |

Fault record tối thiểu: fault_id, equipment_id, trigger_time_s, duration_s, severity, affected_parameters, activation_condition, ramp_in_s, recovery_s, trip_logic, alarm_tags, expected_propagation, acceptance_checks. Tránh lỗi “ép output giảm 30%” nếu không có cơ chế vật lý.

### 7. Scenario kiểm thử end-to-end

| ID    | Kịch bản              | Chuỗi ảnh hưởng kỳ vọng                                                           |
|-------|-----------------------|-----------------------------------------------------------------------------------|
| SC-01 | CR-101 overload       | Crusher capacity↓ → ST/BN thiếu liệu sau buffer → WF-201↓ → raw meal↓             |
| SC-02 | BC-101 trip           | Conveyor outflow=0 → stockpile supply↓ → raw milling starved sau trễ              |
| SC-03 | Raw feed moisture↑    | RM-201 drying load↑ → Qraw meal↓ hoặc moisture product↑ → kiln impact             |
| SC-04 | RM-201 high vibration | Controller giảm feed → SL-301 depletion → kiln feed derate khi chạm low threshold |
| SC-05 | PH-301 blockage       | Cyclone ΔP↑, draft↓ → feed limit/trip → clinker production↓                       |
| SC-06 | PC-301 fuel shortage  | Calcination degree↓ → KL-301 heat demand↑ → quality/throughput giảm               |
| SC-07 | CL-301 fan failure    | Clinker outlet T↑, secondary air T↓ → kiln energy impact/derate                   |
| SC-08 | CM-401A trip          | Mill A output=0; Mill B vẫn chạy trong capacity; cement silo inventory slope↓     |
| SC-09 | SP-401B efficiency↓   | Reject↑, circulating load↑, Blaine shift → Mill B capacity↓                       |
| SC-10 | PK-501 jam            | Bag throughput=0; bulk unaffected nếu nguồn đủ; cement silo fills                 |
| SC-11 | SL-401 full           | Mill A/B discharge constrained → mills derate/trip; clinker inventory may rise    |
| SC-12 | WS-502 scale failure  | Bulk loading inhibited; bag line may continue; no false mass dispatch             |

### 8. Chuẩn trạng thái, alarm và kiểm thử

State machine gợi ý: STOPPED → STARTING → RUNNING → DERATED → STOPPING; TRIPPED có thể phát sinh từ bất kỳ trạng thái hoạt động; RESET/READY trước khi restart. Silo: NORMAL/LOW/EMPTY/FULL/BLOCKED; packing: WAIT_TRUCK/LOADING/COMPLETE. Không đồng nhất WARNING với TRIPPED: alarm có thể xuất hiện khi máy vẫn RUNNING.

Với mỗi tag: tag_id, equipment_id, unit, kind(S/C/SP/D/P), source, scan_interval_s, normal_range, alarm_H/L, trip_HH/LL, deadband, sensor_noise, sensor_lag, formula_ref, fault_links, display_group. Các ngưỡng phải lấy từ OEM/thiết kế hoặc đặt giả định có ghi nhãn; không sao chép ngưỡng giữa các loại máy.

Validation: (1) tổng mass balance theo vật chất/khí; (2) không tồn kho âm hoặc vượt capacity; (3) output không vượt khả năng cấp và nhận; (4) fault có nguyên nhân→PV→alarm→hậu quả; (5) buffer gây trễ hợp lý; (6) khi recover, ramp và control không tạo bước nhảy phi vật lý; (7) 2 mill và 2 tuyến xuất hàng không đếm trùng dòng vật chất.

### 9. Giới hạn và dữ liệu cần hiệu chỉnh

Danh mục trên là engineering reference để thiết kế mô phỏng, không phải P&ID, I/O List, OEM datasheet hoặc thông số đo đã kiểm chứng của một nhà máy cụ thể. Chưa xác định công suất thực, loại crusher, số cyclone, công nghệ mill A/B, số silo/grade, thiết bị đóng bao và ngưỡng trip. Trước khi triển khai sát nhà máy thật cần xác minh các lựa chọn này, sau đó hiệu chỉnh nhiệt, vật liệu, động học và control loops bằng dữ liệu lịch sử.

Khuyến nghị V1: mỗi thiết bị có registry đầu vào, process state, output, control, protection và fault; mỗi stream có flow, temperature, moisture, composition/grade, source/destination và capacity; cập nhật mô phỏng theo hai pha allocate→commit để tránh phụ thuộc thứ tự thực thi.

10\. Ma trận áp dụng mô hình vật lý theo Zone / Line / Equipment

Phần cập nhật này là phụ lục triển khai cho mục 3–8. Mỗi thiết bị được gắn mô hình tính toán, biến đầu vào, đầu ra, công thức lõi và cơ chế fault. Công thức là mô hình rút gọn để triển khai V1, không phải thiết kế OEM hoặc dữ liệu đo của VICEM Hà Tiên.

| Mã  | Mô hình                  | Vai trò                                                                           |
|-----|--------------------------|-----------------------------------------------------------------------------------|
| M01 | Mass/species balance     | Bảo toàn tổng khối lượng và từng cấu tử, tính cả nước bay hơi, CO₂ và khí thải.   |
| M02 | Capacity / throughput    | Giới hạn lưu lượng theo nguồn cấp, tình trạng thiết bị và khả năng nhận phía sau. |
| M03 | Power / energy use       | Tính kW, kWh/t, tải và điện năng theo lưu lượng hoặc đặc tuyến.                   |
| M04 | Drive dynamics           | Tốc độ, quán tính, tải cơ khí và điều kiện truyền động.                           |
| M05 | Thermal balance          | Nhiệt dung, nhiệt vào/ra, trao đổi nhiệt và tổn thất.                             |
| M06 | Comminution              | Giảm kích thước hạt, phân bố hạt và năng lượng nghiền.                            |
| M07 | Drying / moisture        | Cân bằng nước theo wet basis và tải nhiệt bay hơi.                                |
| M08 | Classification / recycle | Tách hạt mịn–thô, hồi lưu và tồn lưu tuần hoàn.                                   |
| M09 | Reaction / conversion    | Phân hủy carbonat và phản ứng tạo clinker rút gọn.                                |
| M10 | Gas / pressure           | Lưu lượng khí, trở lực, chênh áp, draft và quạt.                                  |
| M11 | Inventory / mixing       | Mức chứa, tồn kho, trộn thành phần và giới hạn xả.                                |
| M12 | Transport delay          | Thời gian vận chuyển, lượng vật liệu trên tuyến và độ trễ.                        |
| M13 | Composition / quality    | Phối liệu, độ mịn, độ ẩm, chỉ số chất lượng.                                      |
| M14 | Control / protection     | Setpoint, permissive, interlock, ramp, trip và restart.                           |
| M15 | Fault / degradation      | Fault làm đổi tham số vật lý, hiệu suất hoặc actuator.                            |
| M16 | Discrete events          | Bao, xe, cân, đếm và chu trình vận hành rời rạc.                                  |

#### 10.1 Z01-L01 — Crushing & Storage

Chuỗi vật liệu: CR-101 → BC-101 → ST-101 → RC-101 → BN-101

| Thiết bị | Mô hình                 | Phép tính / đầu ra                                                                        | Fault tác động trực tiếp                                  |
|----------|-------------------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| CR-101   | M01 M02 M03 M06 M15     | Qout=min(Qfeed,Qrated·η); E≈10Wi(1/√P80−1/√F80); P≈Q·E+Pidle. Kích thước F80/P80 dùng µm. | Overload, wear, bearing/lubrication → η↓, P↑, trip.       |
| BC-101   | M01 M02 M03 M04 M12 M15 | Q(t/h)=3.6·v(m/s)·λ(kg/m); τ≈L/v; tính lượng trên băng và giới hạn drive.                 | Slip/misalignment/jam → v thực↓, trip.                    |
| ST-101   | M01 M11 M13             | Mnext=M+Δt(Qin−Qout)/3600; độ ẩm/thành phần là trung bình khối lượng.                     | Overfill, wet feed, segregation → giới hạn xả/chất lượng. |
| RC-101   | M02 M03 M04 M11 M15     | Qreclaim=min(Qcommand,Qrated·η,Mavailable·3600/Δt); tải motor theo Q.                     | Drive fault/wear → năng lực thu hồi↓.                     |
| BN-101   | M01 M11 M14             | Cân bằng từng bin; level=100·M/Mmax; xả phụ thuộc gate và permissive.                     | Bridging/empty/high level → thiếu feed hoặc dừng.         |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.2 Z01-L02 — Raw Milling

Chuỗi vật liệu: WF-201 → RM-201 → SP-201 → raw meal; SP-201 coarse → RM-201; FN-201 là nhánh khí

| Thiết bị | Mô hình                     | Phép tính / đầu ra                                                                                                 | Fault tác động trực tiếp                                      |
|----------|-----------------------------|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| WF-201   | M01 M02 M13 M14             | Qtotal=ΣQi; xi=Qi/ΣQi; sai lệch setpoint và giới hạn feeder.                                                       | Feeder jam, wrong ratio → Q và hóa phối liệu thay đổi.        |
| RM-201   | M01 M02 M03 M05 M06 M07 M15 | mdry=Qwet(1−win); Qproduct=mdry/(1−wout); mevap=Qwet−Qproduct; Qheat≈mevap·λ+ sensible; Qcap=min(grinding,drying). | High moisture, vibration, grinding wear → giảm tải/ẩm tăng.   |
| SP-201   | M01 M08 M13                 | D=F+R; P=αD; R=(1−α)D ở steady state; transient có holdup.                                                         | Rotor degradation → α, fineness và circulating load thay đổi. |
| FN-201   | M03 M04 M10 M15             | Δp=f(Qgas,system resistance); Pfan≈Δp·Qgas/ηfan (Qgas m³/s).                                                       | Fan trip/damper blockage → khí sấy và draft giảm.             |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.3 Z02-L01 — Kiln Line

Chuỗi vật liệu: SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302; CF-301 nối mạng khí

| Thiết bị | Mô hình                         | Phép tính / đầu ra                                                                                      | Fault tác động trực tiếp                                             |
|----------|---------------------------------|---------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| SL-301   | M01 M11 M13                     | dM/dt=Qrawmeal−Qkilnfeed; cập nhật thành phần phối trộn.                                                | Low level/bridging → thiếu cấp lò.                                   |
| KF-301   | M01 M02 M14                     | Qactual theo setpoint, khả năng silo và interlock; tích phân totalizer.                                 | Underfeed/jam → nhiệt và mức tải lò thay đổi.                        |
| PH-301   | M01 M05 M10 M12                 | Khí–rắn trao đổi nhiệt Q≈UAΔT hoặc ε·Cmin·ΔTin; Δp≈K·Qgas²; trễ theo residence.                         | Cyclone blockage → Δp↑, Qgas↓, Tprofile thay đổi.                    |
| PC-301   | M01 M05 M09 M10 M13             | Qfuel=ṁfuel·LHV; Xcalc=1−exp(−k(T)τ) xấp xỉ; CO₂=0.4397·X·mCaCO3.                                       | Fuel/air shortage → T↓, conversion↓, CO/O₂ đổi.                      |
| KL-301   | M01 M03 M04 M05 M09 M12 M13 M15 | Ceff dT/dt=Qfuel−Qreaction−Qexhaust−Qloss−Qmaterial; τ=f(kiln speed); yield clinker từ cân bằng cấu tử. | Fuel loss, refractory, drive overload → T, quality, output biến đổi. |
| CL-301   | M01 M03 M05 M10 M12             | Qclinker·cp(Tin−Tout)=Qair,absorbed+Qloss+accumulation; Qair phụ thuộc fan/grate.                       | Cooler fan failure → Tout↑, secondary air T thay đổi.                |
| CF-301   | M03 M04 M10 M15                 | Đặc tuyến fan Δpfan(Q,n) giao với system resistance; tính draft, power.                                 | ID fan trip/low draft → giảm tải hoặc interlock kiln.                |
| SL-302   | M01 M11 M13                     | dM/dt=Qclinker−QA−QB; giới hạn tồn kho và phân phối cho hai mill.                                       | Silo full/low → backpressure hoặc starvation.                        |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.4 Z03-L01 — Cement Mill A

Chuỗi vật liệu: WF-401A → CM-401A → SP-401A → SL-401; coarse recycle → CM-401A; FN-401A là nhánh khí

| Thiết bị | Mô hình                     | Phép tính / đầu ra                                                                            | Fault tác động trực tiếp                              |
|----------|-----------------------------|-----------------------------------------------------------------------------------------------|-------------------------------------------------------|
| WF-401A  | M01 M02 M13 M14             | Qtotal=Qclinker+Qgypsum+Qadditive; recipe fractions=Qi/Qtotal.                                | Wrong ratio / feeder loss → quality, feed↓.           |
| CM-401A  | M01 M02 M03 M05 M06 M13 M15 | Qout=min(feed,capacity,downstream); P≈Qprocessed·Especific+Pidle; tính fineness và heat rise. | Wear/high vibration → η↓, kWh/t↑, fineness lệch.      |
| SP-401A  | M01 M08 M13                 | D=F+R; P=αD; R=(1−α)D; tính circulating load và fineness.                                     | Separator speed fault → α↓ hoặc cut size thay đổi.    |
| FN-401A  | M03 M04 M10                 | Qgas, Δp, Pfan theo fan/system curve.                                                         | Low airflow → nhiệt/độ mịn/khả năng nghiền ảnh hưởng. |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.5 Z03-L02 — Cement Mill B

Chuỗi vật liệu: WF-401B → CM-401B → SP-401B → SL-401; coarse recycle → CM-401B; FN-401B là nhánh khí

| Thiết bị | Mô hình                     | Phép tính / đầu ra                                      | Fault tác động trực tiếp                               |
|----------|-----------------------------|---------------------------------------------------------|--------------------------------------------------------|
| WF-401B  | M01 M02 M13 M14             | Lưu lượng và recipe riêng cho B; không đồng nhất với A. | Feed deviation → chất lượng hoặc sản lượng B thay đổi. |
| CM-401B  | M01 M02 M03 M05 M06 M13 M15 | Cùng dạng phương trình Mill A, state/parameter độc lập. | Mill B trip → chỉ B mất sản lượng tức thời.            |
| SP-401B  | M01 M08 M13                 | D=F+R, P=αD, R=(1−α)D; holdup độc lập.                  | Separator B fault → recirculation B tăng.              |
| FN-401B  | M03 M04 M10                 | Đặc tuyến fan B và tổn thất áp suất nhánh B.            | Fan B trip → B giảm công suất.                         |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.6 Z04-L01 — Bag Packing

Chuỗi vật liệu: SL-401 → FD-501 → PK-501 → BC-501 → LD-501

| Thiết bị | Mô hình             | Phép tính / đầu ra                                                                | Fault tác động trực tiếp                       |
|----------|---------------------|-----------------------------------------------------------------------------------|------------------------------------------------|
| FD-501   | M01 M02 M14         | Qfeed=min(Qset,Qrated,Qavailable); valve/feeder permissive.                       | Feeder blockage → packer starvation.           |
| PK-501   | M01 M02 M03 M15 M16 | Nbags/min≈nspouts·rpm·ηcycle; Qgood=N_good·mbag/1000 (t/h nếu N/h); reject riêng. | Bag jam/underweight → good bags↓, rejects↑.    |
| BC-501   | M02 M03 M04 M12 M16 | Thời gian vận chuyển τ=L/v; đếm bao theo sự kiện, giới hạn mật độ.                | Conveyor trip → buffer đầy, packer interlock.  |
| LD-501   | M02 M14 M16         | Nloaded tích lũy theo sự kiện, giới hạn xe và loading permissive.                 | Truck absent/loading failure → không xuất bao. |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.7 Z04-L02 — Bulk Loading

Chuỗi vật liệu: SL-401 → FD-502 → SP-502 → WS-502

| Thiết bị | Mô hình         | Phép tính / đầu ra                                                           | Fault tác động trực tiếp                      |
|----------|-----------------|------------------------------------------------------------------------------|-----------------------------------------------|
| FD-502   | M01 M02 M14     | Qfeed=min(Qset,Qrated,Qavailable).                                           | Feeder jam → Qbulk↓.                          |
| SP-502   | M02 M10 M14 M15 | Qloading theo spout lowered, permissive, năng lực và dust extraction.        | Spout misposition/dust fault → restrict/stop. |
| WS-502   | M01 M14 M16     | Mtruck,next=Mtruck+Qloading·Δt/3600; stop khi đạt target (xét cutoff delay). | Scale fault/truck absent → pause hoặc stop.   |

Các mô hình của Line trao đổi dòng vật chất qua Process Graph; dòng hồi lưu và kho đệm được giải đồng thời với giới hạn nguồn cấp/đầu nhận.

#### 10.8 Shared Asset — SL-401 Cement Silo Bank

M01 + M11 + M13 + M14. Với mỗi grade g: M\[g\]next=M\[g\]+Δt·(QA\[g\]+QB\[g\]−Qbag\[g\]−Qbulk\[g\])/3600. Không trộn các grade khác nhau vào cùng một tồn kho trừ khi mô hình hóa chuyển grade. Silo được sở hữu một lần và cấp cho cả hai tuyến Z04.

### 11. Công thức nền tảng, đơn vị và tính nhất quán

#### 11.1 Cân bằng khối lượng

Mnext=M+Δt·(ΣQin−ΣQout)/3600 với Q t/h, Δt s. Khi có phản ứng phải cân bằng từng species; CO₂ và hơi nước là các dòng ra hợp lệ, không được coi là khối lượng biến mất.

#### 11.2 Cân bằng năng lượng

Unew=Uold+Δt·(Σṁin hin−Σṁout hout+Q̇−Ẇ). Định nghĩa ranh giới và dấu nhất quán; nếu dùng MW, MJ và s thì 1 MW=1 MJ/s.

#### 11.3 Capacity / buffer / two-phase update

Qtransfer≤min(source available/Δt, link capacity, destination acceptance/Δt). Giải/allocate tất cả dòng trước khi cập nhật silo để kết quả không phụ thuộc thứ tự duyệt equipment.

#### 11.4 Độ ẩm và chất lượng

Wet-basis w=mwater/(mwater+mdry). Thành phần hóa học phải chỉ rõ dry basis / oxide basis; các tỷ lệ phải tổng 100% theo basis định nghĩa.

#### 11.5 Sensor và fault

Physical truth → sensor lag/noise/bias → alarm. Fault thiết bị đổi η, Kpressure, fuel supply, actuator hoặc logic bảo vệ; fault sensor chỉ đổi measurement và có thể ảnh hưởng controller qua feedback.

#### 11.6 Điều kiện trạng thái

STOPPED, STARTING, RUNNING, DERATED, WARNING, TRIPPED, RECOVERING; trạng thái được quyết định bởi lệnh, permissive, interlock, PV và timer; fault không tự động đồng nghĩa với trip.

#### 11.7 Kiểm thử bắt buộc

Kiểm tra mass residual, energy residual, tồn kho không âm/không vượt max, phân loại sản phẩm, giới hạn actuator, response delay, restart interlock và fault propagation cả xuôi lẫn ngược.

### 12. Ví dụ liên kết fault với mô hình

#### Raw Mill high moisture

Tăng win tại RM-201 → M07 tăng ṁevap và Q̇drying → M02 giảm capacity nếu nhiệt sấy không đủ → M01 giảm raw meal → SL-301 inventory giảm → KF-301 thiếu feed khi xuống ngưỡng → Kiln giảm tải có độ trễ.

#### Preheater cyclone blockage

Tăng hệ số trở lực K ở PH-301 → M10 tăng Δp/giảm Qgas → M05 thay đổi trao đổi nhiệt, M09 conversion tại PC-301 thay đổi → controller giảm kiln feed hoặc trip theo giới hạn.

#### Cement Mill A trip

CM-401A mất drive, Q_A→0 sau ramp; Mill B không tự tăng nếu không có logic phân bổ. SL-401 giảm tốc độ nhập, Packing/Bulk vẫn xuất đến khi silo cạn.

#### Packing jam / downstream blockage

PK-501 jam → bag output=0 → SL-401 tích lũy nếu Mill A/B tiếp tục → khi silo high-high, controller giảm/dừng mill → clinker silo tích lũy và có thể ảnh hưởng Kiln.

### 13. Dữ liệu bắt buộc trước khi triển khai

Với mỗi thiết bị: rated_capacity, operating_limits, initial_state, response_time, control setpoints, alarm/trip thresholds, material properties, calibration curves và fault severity/recovery. Với mỗi stream: source, destination, material, flow, temperature, composition, moisture, delay, capacity. Dữ liệu ví dụ không thay thế P&ID, OEM manual, DCS logic hoặc kết quả commissioning.

---

## 3.3. Kiến trúc thực thi mô phỏng và liên kết dữ liệu (đề xuất mới)

> **Trạng thái:** Phần này là đề xuất thiết kế bổ sung, không phải nội dung được xác nhận từ tài liệu DOCX gốc và chưa được triển khai/kiểm thử. Mục 3.1 xác định *quy trình xảy ra như thế nào*; mục 3.2 xác định *thiết bị, công thức, thông số và fault*; mục 3.3 xác định *cách tổ chức dữ liệu và thực thi các mô hình đó trong simulator*.

### 3.3.1. Hai cấu trúc song song: phân cấp quản lý và đồ thị công nghệ

- **Hierarchy:** `Factory → Zone → Line → Process → Equipment → Component` để duyệt, gán quyền sở hữu, tìm kiếm và hiển thị chi tiết. Một Equipment có thể tham gia nhiều Process; do đó không nên suy ra quan hệ độc quyền từ cây phân cấp.
- **Process Graph:** Các nút Process liên kết bằng luồng vật chất, năng lượng, điều khiển, thông tin và sự kiện. Các cạnh phải có định danh và hướng. Một Process có thể có nhiều thiết bị tham gia; một Equipment có thể được tham chiếu bởi nhiều Process.
- **Equipment/Component Graph:** Mô tả kết nối chức năng bên trong cụm thiết bị (motor → gearbox → rotor; transmitter → controller → actuator), không mặc định tất cả thiết bị đều có motor.
- **Asset ownership:** Mỗi Equipment có một `asset_id` duy nhất, kể cả khi tham gia nhiều Process. `SL-401` là tài sản dùng chung, chỉ tồn tại một lần trong inventory; các Line liên kết đến cùng `asset_id`.

### 3.3.2. Các hợp đồng dữ liệu tối thiểu

| Đối tượng | Trường bắt buộc đề xuất | Quan hệ |
|---|---|---|
| Zone | `id`, `name`, `function`, `inputs`, `outputs`, `line_ids` | Chứa nhiều Line |
| Line | `id`, `zone_id`, `process_ids`, `input_ports`, `output_ports` | Chứa chuỗi/cụm Process |
| Process | `id`, `function`, `input_ports`, `output_ports`, `equipment_ids`, `model_ids` | Nhiều-nhiều với Equipment |
| Equipment | `id`, `type`, `component_ids`, `parameter_set`, `state`, `model_ids`, `fault_ids` | Một asset, nhiều Process |
| Component | `id`, `equipment_id`, `type`, `inputs`, `outputs`, `measurements` | Thuộc một asset |
| Stream | `id`, `source_port`, `target_port`, `kind`, `quantity`, `unit`, `delay` | Cạnh có hướng |
| Model instance | `id`, `model_type`, `target_id`, `parameters`, `state_variables`, `inputs`, `outputs` | Áp dụng cho Process hoặc Equipment |
| Fault scenario | `id`, `target_id`, `onset`, `severity`, `duration`, `parameter_effects`, `recovery` | Tác động qua tham số/trạng thái |

`kind` của port/stream gồm `material`, `energy`, `control`, `information`, `event`. Mọi đại lượng phải ghi đơn vị, cơ sở tính (wet/dry basis khi liên quan), giới hạn hợp lệ và nguồn dữ liệu (measured/calculated/setpoint/internal).

### 3.3.3. Ví dụ liên kết Process – Equipment – Model

Quy ước mã công đoạn cho Z01 – L02 Raw Milling:

| Mã | Process | Thiết bị tham gia |
|---|---|---|
| P01 | Dosing | WF-201 |
| P02 | Grinding & Drying | RM-201; FN-201 hỗ trợ dòng khí |
| P03 | Classification & Recirculation | SP-201; RM-201 nhận dòng hồi lưu |
| P04 | Gas Handling | FN-201 |

Nghiền và sấy diễn ra đồng thời trong P02. Trong mô hình dữ liệu, `grinding` và `drying` là hai phép tính thuộc cùng Process ID `Z01-L02-P02`.

```yaml
process:
  id: Z01-L02-P02
  name: Grinding & Drying
  equipment_ids: [RM-201, FN-201]
  model_ids: [M01, M02, M05, M06, M07, M10]
  input_ports: [wet_raw_mix, hot_gas, coarse_return]
  output_ports: [ground_material_to_separator, humid_exhaust]

equipment:
  id: RM-201
  type: vertical_raw_mill
  participates_in: [Z01-L02-P02, Z01-L02-P03]
  components: [grinding_table, grinding_rollers, main_drive, hydraulic_system]

stream:
  id: RAW_MEAL_TO_SILO
  source_port: Z01-L02.raw_meal_out
  target_port: SL-301.raw_meal_in
  kind: material
  unit: t/h
```

P03 phân ly liệu đã nghiền từ P02 và đưa phần hạt thô trở lại RM-201. Luồng `RAW_MEAL_TO_SILO` mang phần bột liệu đạt yêu cầu từ đầu ra của dây chuyền đến SL-301.

### 3.3.4. Chu kỳ tính toán mô phỏng

1. Đọc thời gian mô phỏng, lệnh vận hành, recipe và kịch bản fault đến hạn.
2. Áp dụng fault vào **tham số vật lý hoặc trạng thái thiết bị** (ví dụ hiệu suất quạt, hệ số nghẹt, khả năng cấp liệu); không ghi đè tùy tiện PV để tạo sự cố giả.
3. Đánh giá permissive, interlock, alarm/trip và các lệnh điều khiển. Xác định setpoint có hiệu lực.
4. Tính giới hạn năng lực và phân bổ lưu lượng theo nguồn cấp, tải máy, tồn kho, đường hồi lưu và khả năng nhận của downstream.
5. Giải các nhóm mô hình liên kết: cân bằng vật chất, nhiệt, khí, phản ứng, chất lượng và công suất; lặp hội tụ khi có vòng recycle hoặc ghép mạnh.
6. Cập nhật trạng thái động học/tồn kho theo bước thời gian và giới hạn vật lý; tránh dùng giá trị mới của một nút và giá trị cũ của nút khác trong cùng một bước tính.
7. Tạo phép đo giả lập từ trạng thái thật của mô hình (sensor lag, noise, quality flag), sau đó publish telemetry/event.
8. Kiểm tra bất biến, ghi nhật ký và lưu snapshot phục vụ tái lập kịch bản.

**Lưu ý kỹ thuật:** Tách `physical_state`, `measured_value`, `setpoint`, `alarm_state`; tách đơn vị t/h với kg/s và bước thời gian giây. Dùng cơ chế tính hai pha hoặc solver đồ thị để giảm sai lệch do thứ tự cập nhật. Chu kỳ solver, tốc độ UI và tần suất telemetry không nhất thiết bằng nhau.

### 3.3.5. Quan hệ nhân quả và lan truyền fault

Mỗi fault cần mô tả `root_cause → parameter_change → physical_response → sensor_response → control_response → downstream_effect`, kèm thời gian trễ và điều kiện tồn kho.

**Ví dụ – FN-201 giảm năng lực:** hiệu suất/tốc độ quạt giảm → lưu lượng khí giảm → khả năng sấy của RM-201 giảm → độ ẩm raw meal tăng hoặc hệ điều khiển giảm feed → chất lượng/lưu lượng vào `SL-301` thay đổi → tác động đến Kiln chỉ khi bộ đệm tồn kho hoặc giới hạn chất lượng bị vượt qua. Không mặc định Kiln dừng ngay.

**Ví dụ – PK-501 kẹt bao:** sản lượng đóng bao giảm về 0 → `SL-401` có thể tăng tồn kho nếu các mill tiếp tục chạy → khi đạt ngưỡng bảo vệ, điều khiển giảm/dừng cấp từ mill → tác động ngược về tồn kho clinker; nhánh Bulk Loading có thể tiếp tục nếu điều kiện riêng vẫn đáp ứng.

### 3.3.6. Trạng thái, điều khiển và telemetry

Biểu diễn trạng thái thiết bị bằng ba trường độc lập. `STOPPED` là giá trị chuẩn cho thiết bị không vận hành.

| Trường | Giá trị | Ý nghĩa |
|---|---|---|
| `operating_state` | `STOPPED` | Thiết bị không vận hành. |
| `operating_state` | `STARTING` | Đang khởi động. |
| `operating_state` | `RUNNING` | Đang vận hành. |
| `operating_state` | `STOPPING` | Đang dừng. |
| `operating_state` | `TRIPPED` | Dừng do bảo vệ. |
| `health_state` | `DEGRADED` | Tình trạng thiết bị suy giảm. |
| `health_state` | `FAULTED` | Có lỗi được xác nhận. Lỗi có thể phát cảnh báo khi thiết bị vẫn chạy hoặc kích hoạt bảo vệ và chuyển thiết bị sang `TRIPPED`. |
| `capacity_limitation` | `DERATED` | Công suất hoặc năng suất khả dụng bị giới hạn. |

Ví dụ: RM-201 vẫn đang chạy, có cảnh báo rung cao và bị giới hạn còn 70% năng suất danh định. Biểu diễn bằng `operating_state: RUNNING`, `health_state: DEGRADED` và `capacity_limitation: DERATED`, kèm mức giới hạn 70%.

- **Thiết bị thụ động:** Theo dõi trạng thái tồn kho và cửa xả đối với silo.
- **Process state:** `IDLE`, `READY`, `ACTIVE`, `STARVED`, `BLOCKED`, `DEGRADED`, `STOPPED`.
- **Control:** ghi rõ `mode`, `setpoint`, `feedback`, `actuator_output`, `permissives`, `interlocks`, `trip_reason`, `reset_condition`.
- **Telemetry:** mỗi tag có `tag_id`, `asset_id`, `value`, `unit`, `timestamp`, `quality`, `source_type` và `sample_period`; không xem tag calculated là cảm biến thực.
- **Event log:** ghi thời điểm, nguồn, severity, trước/sau khi thay đổi và liên kết đến fault hoặc thao tác vận hành.

### 3.3.7. Kiểm thử chấp nhận trước khi kết nối UI

| Nhóm test | Điều kiện đạt đề xuất |
|---|---|
| Topology | 4 Zone, 7 Line, 33 Equipment logic; `SL-401` chỉ có một inventory |
| Referential integrity | Mọi Process, Equipment, Model, Fault và Stream tham chiếu ID hợp lệ |
| Mass conservation | Cân bằng tổng và thành phần trong sai số số học đã định nghĩa; CO₂/hơi nước được tính ở đúng biên |
| Energy consistency | Không tạo nhiệt/công suất vô lý; đơn vị và cơ sở tính nhất quán |
| Capacity/inventory | Không có tồn kho âm hoặc vượt giới hạn mà không phát sinh trạng thái bảo vệ |
| Recycle stability | Vòng separator hội tụ hoặc báo không hội tụ rõ ràng |
| Fault propagation | Tác động theo quan hệ vật lý và thời gian trễ; không nhảy trạng thái vô cớ |
| Reproducibility | Cùng cấu hình, seed và event schedule tạo cùng kết quả trong sai số xác định |
| UI navigation | Click Zone/Line/Process/Equipment/Model/Fault mở đúng chi tiết; có fallback khi JS lỗi |

### 3.3.8. Ranh giới V1 và thứ tự triển khai đề xuất

1. Chuẩn hóa định danh, topology, input/output port và material properties.
2. Cài đặt mô hình cân bằng vật chất, giới hạn công suất, vận chuyển và silo trước.
3. Bổ sung nghiền/sấy/phân ly và recycle; tiếp theo là nhiệt, phản ứng và dòng khí cho Kiln.
4. Bổ sung điều khiển, interlock, fault và sensor/telemetry.
5. Tạo bộ test vật lý, integration test và scenario test; cuối cùng mới kết nối Engineering Explorer/SCADA.

**Ngoài phạm vi đã xác nhận:** mô phỏng khai thác mỏ, toàn bộ utilities, P&ID/OEM chi tiết và mô hình động học cấp cao chưa hiệu chỉnh. Không diễn giải các thông số giả định thành thông số nhà máy thật.
---

## 4. Trạng thái triển khai

Tài liệu là **đặc tả mô phỏng**, chưa phải bằng chứng hệ thống simulation đã chạy. Engineering Explorer HTML là công cụ duyệt kiến trúc; dữ liệu mô phỏng, phương trình đã hiệu chỉnh, điều khiển thời gian thực và kiểm thử end-to-end là các phần cần triển khai/kiểm chứng riêng.
