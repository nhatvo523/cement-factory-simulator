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

- **4 zone, 7 dây chuyền, 33 cụm thiết bị, 68 kịch bản và 448 tag.**
- Explorer hiển thị số đo và cảnh báo mô phỏng theo thời gian thực, hỗ trợ chèn lỗi và quan sát sự cố lan giữa các thiết bị.
- Có thể xuất kết quả kịch bản dưới dạng JSON để phân tích hoặc thử tích hợp.

## Phạm vi mô hình

- Mô phỏng dây chuyền xi măng Portland **phương pháp khô**, từ tiếp nhận nguyên liệu, nghiền sấy và nung clinker đến nghiền xi măng, đóng bao và xuất rời.
- Mô hình tính lưu lượng, tồn kho, hồi lưu và tương tác nhiệt ở mức giản lược. Các tham số vận hành là giả định kỹ thuật và cần hiệu chỉnh bằng dữ liệu nhà máy.

[Đặc tả kỹ thuật và giới hạn mô hình](Specification.md#4-trạng-thái-triển-khai)
