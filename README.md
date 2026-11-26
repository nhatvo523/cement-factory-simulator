# Cement Factory Simulator V1

- `UI/Explorer.html` mở trực tiếp trong trình duyệt để tra cứu sơ đồ và đặc tả.
- `src/factory_sim/` chứa backend Python và các model dùng chung.
- `configs/model_types/` đăng ký model, cổng, đơn vị và phạm vi tham số.
- `configs/plants/` khai báo thiết bị cụ thể, kết nối và tồn kho ban đầu.
- `configs/scenarios/` khai báo thay đổi tham số theo thời gian.
- `tests/` kiểm tra cân bằng và tác động giữa hai Zone.

## Chạy dự án trên máy mới

1. Cài Python 3.10 trở lên. Backend chỉ dùng thư viện chuẩn nên không cần cài thêm gói bằng `pip`.
2. Tải repo bằng Git hoặc giải nén bản ZIP. Mở terminal tại thư mục chứa `README.md`, `src/`, `configs/` và `UI/`. Nếu dùng VS Code, mở chính thư mục này rồi chọn **Terminal → New Terminal**.
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

Mở [Explorer tại localhost](http://127.0.0.1:8000/) và chọn một thiết bị để mở cửa sổ **Thông số vận hành**. Cột phải hiển thị hồ sơ kỹ thuật. Chế độ vận hành chạy liên tục theo thời gian thực, với một bước mô hình mỗi giây. Ngay dưới thông số, chọn một hoặc nhiều lỗi rồi bấm **Áp dụng lỗi đã chọn**. Lỗi bắt đầu ở bước kế tiếp và có hiệu lực đến khi **Đặt lại mô phỏng**. Có thể đóng cửa sổ hoặc mở thiết bị khác trong cùng phiên. Tệp HTML mở trực tiếp vẫn dùng được để tra cứu, còn dữ liệu Python cần mở qua máy chủ. Ánh xạ mã thiết bị tới biến nguồn nằm trong danh mục tag.

Nhấn **Ctrl+C** trong terminal để dừng. Nếu cổng 8000 đang được sử dụng, thêm `--port 8001` vào lệnh khởi động và mở [Explorer ở cổng 8001](http://127.0.0.1:8001/). Nếu gặp `No module named 'factory_sim'`, kiểm tra terminal đang ở thư mục gốc và chạy lại lệnh đặt `PYTHONPATH` trong terminal đó.

### Xuất dữ liệu mẫu và chạy kiểm thử

Chạy trong terminal đã đặt `PYTHONPATH`. Các lệnh dưới đây dùng Windows PowerShell. Thay `py -3` bằng `python3` trên macOS hoặc Linux.

```powershell
py -3 -m factory_sim configs/scenarios/baseline.json --output runs/baseline.json
py -3 -m unittest discover -s tests -v
```

Đổi tên kịch bản thành `crusher_stop`, `fan_derate` hoặc `downstream_feed_stop` để sinh dữ liệu tương ứng. Các tệp JSON trong `runs/` có ID plant, ID kịch bản, đơn vị, danh mục tag và chuỗi số đo. Mốc thời gian của frame là cuối bước tính. Sự kiện được áp dụng từ đầu bước.

Các kịch bản dùng chung `configs/operating_profiles/zone1_operation.json` cho dao động quá trình và sai số đo. Danh mục công bố ở `configs/operating_profiles/equipment_tags.json` quy định mã tag, thiết bị, nhãn, đơn vị, dải, nguồn và cờ hiển thị. API live, API kịch bản, Explorer và CLI dùng cùng danh mục. Payload mặc định có số đo theo `measurements[device_id][tag_id]`, với metadata trong `tags`.

Chẩn đoán có thể bật bằng `?ground_truth=true` trên API GET, `"ground_truth": true` trong body API live, hoặc `--ground-truth` khi export bằng CLI. Kênh này chứa trạng thái vật lý, cân bằng và sự kiện. Giá trị mặc định nằm trong danh mục tag và được đặt là `false`.

Ở Z01–L02, WF-201 điều khiển một dòng phối liệu tổng dựa trên số đo load cell. Lỗi con lăn thay đổi năng lực nghiền; lỗi tốc độ rotor SP-201 thay đổi tỷ lệ phân ly và hồi lưu. Mô hình chưa dự báo phân bố kích thước hạt. Mất tín hiệu rung RM-201 chỉ ảnh hưởng kênh giám sát vì kịch bản sử dụng một kênh bảo vệ rung độc lập. Khi khí sấy giảm, mô hình giới hạn cấp liệu để giữ mục tiêu độ ẩm. SL-301 tiếp tục cấp cho KF-301 theo lượng tồn khả dụng.

Z02 mô phỏng tuyến SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302. CF-301 hút khí qua tháp tiền gia nhiệt. Lực hút thấp giới hạn hoặc ngừng cấp liệu. Mô hình hạch toán nước bay hơi và CO₂ tách từ bột liệu, đồng thời ước tính nhiệt giàn nguội thu hồi cho lò. Nhiệt lò truyền tới PH-301 theo tải lò của bước trước. PH-301 cấp một phần nhiệt sấy cho RM-201 tùy tải nhiệt và lực hút. Nguồn nhiệt dự phòng có thể cấp tới 65% năng lực sấy danh định. Đây là mô hình nhiệt rút gọn với hệ số quy ước.

Zone 3–4 khai báo thiết bị, cổng và kết nối trong `configs/plants/bulk_material_line.json`. Model thiết bị và lỗi component dùng chung cơ chế nạp cấu hình, chèn lỗi và lấy mẫu cảm biến của Zone 1–2.

- Zone 3. SL-302 chia clinker theo nhu cầu hai tuyến. Bộ định lượng bổ sung riêng thạch cao và phụ gia theo công thức từng mác. Bột mịn đi vào ngăn tương ứng của SL-401. Hạt thô quay về mill và chiếm năng lực nghiền. Lưu lượng khí, năng lực mill, tải separator và chỗ trống trong silo giới hạn lượng cấp.
- Zone 4. Đóng bao và xuất rời rút từ tồn đầu bước của từng ngăn. Thiết bị có năng lực thấp nhất giới hạn lưu lượng của tuyến. Xe rời đạt tải đặt thì ngừng cấp và chờ đổi xe. Khi một nhánh ngừng, ngăn tương ứng đầy dần, rồi giới hạn mill và có thể làm clinker dồn về SL-302.
- Mác A/B và tỷ lệ phối liệu là cấu hình giả định. Mô hình giải hồi lưu trong một bước và quy đổi lưu lượng thành số bao mỗi phút. Độ mịn thực nghiệm, chất lượng bao và quá trình vận chuyển từng bao cần mô hình riêng.

Trình tự công nghệ tham khảo [EPA AP-42, mục 11.6 Portland Cement Manufacturing](https://www.epa.gov/sites/default/files/2020-10/documents/c11s06.pdf).

## Phạm vi mô hình

Tuyến mẫu `bulk_material_line.json` dùng bước tính 60 s và thông số giả định. Khi `downstream_feeder` ngừng nhận, `product_silo` tích lũy và giới hạn dòng từ công đoạn trước khi đầy. Khi công đoạn trước giảm sản lượng, silo tiếp tục cấp liệu trong phạm vi tồn kho khả dụng. `transfer_conveyor` biểu diễn vật liệu đang vận chuyển với độ trễ một bước.

Để dùng lại model cho dự án khác, tạo cấu hình plant với ID, thông số và kết nối riêng, rồi truyền `--plant` khi chạy. `model_type` tham chiếu đến khai báo dùng chung trong `configs/model_types/`. Mục `target` trong kịch bản dùng ID của thiết bị trong plant đã chọn.

Các dòng được phân bổ theo tồn kho đầu bước, rồi cam kết đồng thời. Sấy bảo toàn chất rắn khô và hạch toán hơi nước. Phân ly dùng tỷ lệ hạt mịn và vòng hồi lưu cục bộ trong mỗi bước. Export mặc định lưu số đo giả lập. Có thể bật chẩn đoán khi cần giá trị vật lý. Các vòng PID đầy đủ, thời gian lưu trong lò, động học cháy, và CO₂ từ nhiên liệu nằm ngoài phạm vi mô hình hiện tại.
