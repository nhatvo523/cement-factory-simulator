# Cement Factory Simulator V1

- `UI/Explorer.html` mở trực tiếp trong trình duyệt để tra cứu sơ đồ và đặc tả.
- `src/factory_sim/` chứa backend Python và các model dùng chung.
- `configs/model_types/` đăng ký model, cổng, đơn vị và phạm vi tham số.
- `configs/plants/` khai báo thiết bị cụ thể, kết nối và tồn kho ban đầu.
- `configs/scenarios/` khai báo thay đổi tham số theo thời gian.
- `tests/` kiểm tra cân bằng, tín hiệu SCADA, API và hồi quy kịch bản xuyên zone.

## Chạy dự án trên máy mới

1. Cài Python 3.10 trở lên. Backend chỉ dùng thư viện chuẩn nên không cần cài thêm gói bằng `pip`.
2. Clone repo bằng Git.

   ```bash
   git clone https://github.com/nhatvo523/cement-factory-simulator.git
   cd cement-factory-simulator
   ```

   Nếu tải ZIP, giải nén và mở terminal tại thư mục chứa `README.md`, `src/`, `configs/` và `UI/`. Trong VS Code, mở chính thư mục đó rồi chọn **Terminal → New Terminal**.
3. Chạy lệnh tương ứng với hệ điều hành và giữ terminal mở.

### Windows (PowerShell)

```powershell
py -3 --version
$env:PYTHONPATH = "src"
py -3 -m factory_sim.server
```

Nếu máy dùng lệnh `python` thay cho `py`, chạy `python --version` và `python -m factory_sim.server` sau khi đặt `PYTHONPATH`.

### macOS và Linux

```bash
python3 --version
export PYTHONPATH=src
python3 -m factory_sim.server
```

### Mở và dừng Explorer

Mở [Explorer tại localhost](http://127.0.0.1:8000/) và chọn một thiết bị để mở cửa sổ **Thông số vận hành**. Cột phải hiển thị hồ sơ kỹ thuật. Chế độ live chạy liên tục theo thời gian thực, một bước mô hình mỗi giây. Ngay dưới thông số, chọn một hoặc nhiều lỗi rồi bấm **Áp dụng lỗi đã chọn**. Máy chủ bắt đầu lịch lỗi từ bước kế tiếp. Các ca ramp có sự kiện tiếp theo theo `offset_s`. **Đặt lại mô phỏng** khởi tạo phiên mới. Phiên live nằm trong bộ nhớ máy chủ. Muốn lưu kết quả chạy, dùng lệnh export JSON ở dưới. Tệp HTML mở trực tiếp vẫn dùng được để tra cứu sơ đồ và đặc tả.

Nhấn **Ctrl+C** trong terminal để dừng. Nếu cổng 8000 đang được sử dụng, thêm `--port 8001` vào lệnh khởi động và mở [Explorer ở cổng 8001](http://127.0.0.1:8001/). Nếu gặp `No module named 'factory_sim'`, kiểm tra terminal đang ở thư mục gốc và chạy lại lệnh đặt `PYTHONPATH` trong terminal đó.

### Xuất dữ liệu mẫu và chạy kiểm thử

Chạy trong terminal đã đặt `PYTHONPATH`. Các lệnh dưới đây dùng Windows PowerShell. Thay `py -3` bằng `python3` trên macOS hoặc Linux.

```powershell
py -3 -m factory_sim configs/scenarios/baseline.json --output runs/baseline.json
py -3 -m unittest discover -s tests -v
```

Đổi tên kịch bản thành `crusher_stop`, `fan_derate` hoặc `downstream_feed_stop` để sinh dữ liệu tương ứng. Các tệp JSON trong `runs/` có ID plant, ID kịch bản, đơn vị, danh mục tag và chuỗi số đo. Mốc thời gian của frame là cuối bước tính. Sự kiện được áp dụng từ đầu bước.

## Hiện trạng mô phỏng

Dự án mô phỏng **4 zone, 7 line và 33 cụm thiết bị**. Có **68 ca đăng ký**, gồm baseline, 64 ca lỗi ban đầu, hai ca suy giảm phân ly và một ca trượt băng đóng bao. Baseline khi export chạy 90 phút với bước 60 s. Mặc định ST-101 bắt đầu ở **48 t (20%)**. Các test phát lại fixture phát hành của 68 ca ghim **35 t** để so hai vân tay vật liệu và nhiệt/chất lượng. [Phạm vi và giới hạn](Specification.md#4-trạng-thái-triển-khai)

Các kịch bản dùng chung `configs/operating_profiles/zone1_operation.json` cho dao động quá trình và sai số đo. Danh mục công bố ở `configs/operating_profiles/equipment_tags.json` quy định mã tag, thiết bị, nhãn, đơn vị, dải, nguồn và cờ hiển thị. API live, API kịch bản, Explorer và CLI dùng cùng danh mục. Payload mặc định có số đo theo `measurements[device_id][tag_id]`, với metadata trong `tags`.

| Zone | Tag vận hành | Cảnh báo | Lab |
|---|---:|---:|---:|
| Z01 | 73 | 47 | 0 |
| Z02 | 58 | 70 | 1 |
| Z03 | 62 | 60 | 2 |
| Z04, gồm SL-401 | 45 | 30 | 0 |
| **Tổng** | **238** | **207** | **3** |

Free lime và Blaine xuất qua các kênh lab có thời điểm lấy mẫu và trả kết quả. Chỉ thị kW là giá trị mô phỏng ước tính từ dòng và cosφ theo tải. Thời gian truyền cấu hình tại điểm đo hiện áp dụng cho nhiệt khí ra RM-201 (4 s) và bộ đếm cuối băng BC-501 (20 s).

Chẩn đoán có thể bật bằng `?ground_truth=true` trên API GET, `"ground_truth": true` trong body API live, hoặc `--ground-truth` khi export bằng CLI. Kênh này chứa trạng thái vật lý, cân bằng và sự kiện. Giá trị mặc định nằm trong danh mục tag và được đặt là `false`.

Ở Z01–L02, WF-201 điều khiển một dòng phối liệu tổng dựa trên số đo load cell. Lỗi con lăn thay đổi năng lực nghiền; lỗi tốc độ rotor SP-201 thay đổi tỷ lệ phân ly và hồi lưu. Mô hình chưa dự báo phân bố kích thước hạt. Mất tín hiệu rung RM-201 chỉ ảnh hưởng kênh giám sát vì kịch bản sử dụng một kênh bảo vệ rung độc lập. Khi khí sấy giảm, mô hình giới hạn cấp liệu để giữ mục tiêu độ ẩm. SL-301 tiếp tục cấp cho KF-301 theo lượng tồn khả dụng.

Z02 mô phỏng tuyến SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302. CF-301 hút khí qua tháp tiền gia nhiệt. Lực hút thấp giới hạn hoặc ngừng cấp liệu. Mô hình hạch toán nước bay hơi và CO₂ tách từ bột liệu, đồng thời ước tính nhiệt giàn nguội thu hồi cho lò. Nhiệt lò truyền tới PH-301 theo tải lò của bước trước. PH-301 cấp một phần nhiệt sấy cho RM-201 tùy tải nhiệt và lực hút. Nguồn nhiệt dự phòng có thể cấp tới 65% năng lực sấy danh định. Đây là mô hình nhiệt rút gọn với hệ số quy ước.

Zone 3–4 khai báo thiết bị, cổng và kết nối trong `configs/plants/bulk_material_line.json`. Model thiết bị và lỗi component dùng chung cơ chế nạp cấu hình, chèn lỗi và lấy mẫu cảm biến của Zone 1–2.

- Zone 3. SL-302 chia clinker theo nhu cầu hai tuyến. Bộ định lượng bổ sung riêng thạch cao và phụ gia theo công thức từng mác. Bột mịn đi vào ngăn tương ứng của SL-401. Hạt thô quay về mill và chiếm năng lực nghiền. Lưu lượng khí, năng lực mill, tải separator và chỗ trống trong silo giới hạn lượng cấp.
- Zone 4. Đóng bao và xuất rời rút từ tồn đầu bước của từng ngăn. Thiết bị có năng lực thấp nhất giới hạn lưu lượng của tuyến. Xe rời đạt tải đặt thì ngừng cấp và chờ đổi xe. Khi một nhánh ngừng, ngăn tương ứng đầy dần, rồi giới hạn mill và có thể làm clinker dồn về SL-302.
- Mác A/B và tỷ lệ phối liệu là cấu hình giả định. Mô hình giải hồi lưu trong một bước. Z03 trả mẫu lab Blaine ước tính. Z04 công bố số bao, bao/phút và khối lượng bao gần nhất theo mô hình cân. Buffer vật lý và loại bao theo kết quả cân vẫn đang chờ triển khai.

Trình tự công nghệ tham khảo [EPA AP-42, mục 11.6 Portland Cement Manufacturing](https://www.epa.gov/sites/default/files/2020-10/documents/c11s06.pdf).

## Phạm vi mô hình

Tuyến mẫu `bulk_material_line.json` dùng bước tính 60 s và thông số giả định. Khi `downstream_feeder` ngừng nhận, `product_silo` tích lũy và giới hạn dòng từ công đoạn trước khi đầy. Khi công đoạn trước giảm sản lượng, silo tiếp tục cấp liệu trong phạm vi tồn kho khả dụng. `transfer_conveyor` biểu diễn vật liệu đang vận chuyển với độ trễ một bước.

Để dùng lại model cho dự án khác, tạo cấu hình plant với ID, thông số và kết nối riêng, rồi truyền `--plant` khi chạy. `model_type` tham chiếu đến khai báo dùng chung trong `configs/model_types/`. Mục `target` trong kịch bản dùng ID của thiết bị trong plant đã chọn.

Các dòng được phân bổ theo tồn kho đầu bước, rồi cam kết đồng thời. Sấy bảo toàn chất rắn khô và hạch toán hơi nước. Phân ly dùng tỷ lệ hạt mịn và vòng hồi lưu cục bộ trong mỗi bước. Lò dùng thời gian lưu ước tính theo tải để tính free lime. Các vòng PID đầy đủ, phân bố thời gian lưu trong lò, động học cháy và CO₂ từ nhiên liệu nằm ngoài phạm vi hiện tại.
