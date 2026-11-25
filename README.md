# Cement Factory Simulator V1

- `UI/Explorer.html` mở trực tiếp trong trình duyệt để tra cứu sơ đồ và đặc tả.
- `src/factory_sim/` chứa backend Python và các model dùng chung.
- `configs/model_types/` đăng ký model, cổng, đơn vị và phạm vi tham số.
- `configs/plants/` khai báo thiết bị cụ thể, kết nối và tồn kho ban đầu.
- `configs/scenarios/` khai báo thay đổi tham số theo thời gian.
- `tests/` kiểm tra cân bằng và tác động giữa hai Zone.

## Chạy backend

Chạy từ thư mục gốc bằng Python 3.10 trở lên. Backend chỉ dùng thư viện chuẩn.

```powershell
$env:PYTHONPATH = "src"
python -m factory_sim configs/scenarios/baseline.json --output runs/baseline.json
python -m unittest discover -s tests -v
```

### Mở Explorer với dữ liệu Python

```powershell
$env:PYTHONPATH = "src"
python -m factory_sim.server
```

Mở [Explorer tại localhost](http://127.0.0.1:8000/) và chọn một thiết bị để mở cửa sổ **Thông số vận hành**. Cột phải hiển thị hồ sơ kỹ thuật. Chế độ vận hành chạy liên tục theo thời gian thực, với một bước mô hình mỗi giây. Ngay dưới thông số, chọn một hoặc nhiều lỗi rồi bấm **Áp dụng lỗi đã chọn**. Lỗi bắt đầu ở bước kế tiếp và có hiệu lực đến khi **Đặt lại mô phỏng**. Có thể đóng cửa sổ hoặc mở thiết bị khác trong cùng phiên. Tệp HTML mở trực tiếp vẫn dùng được để tra cứu, còn dữ liệu Python cần mở qua máy chủ. Ánh xạ mã kỹ thuật sang ID mô phỏng nằm trong `simulationAssets` của `UI/Explorer.html`.

Đổi tên kịch bản thành `crusher_stop`, `fan_derate` hoặc `downstream_feed_stop` để sinh dữ liệu tương ứng. Các tệp JSON trong `runs/` có ID plant, ID kịch bản, đơn vị, sự kiện và chuỗi kết quả. Mốc thời gian của frame là cuối bước tính. Sự kiện được áp dụng từ đầu bước.

Các kịch bản dùng chung `configs/operating_profiles/zone1_operation.json` để cấu hình dao động quá trình và sai số đo. Explorer đọc số đo giả lập từ `measurements`, gồm cả các kênh component, cùng các trạng thái và cảnh báo của bộ điều khiển. API vận hành trực tiếp chỉ gửi các trường này và thời điểm lấy mẫu. Kết quả mô phỏng theo kịch bản vẫn chứa giá trị vật lý trong `equipment` để kiểm tra mô hình. Nếu bỏ `operating_profile`, simulator dùng tham số quá trình danh định.

Ở Z01–L02, WF-201 điều khiển một dòng phối liệu tổng dựa trên số đo load cell. Lỗi con lăn thay đổi năng lực nghiền; lỗi tốc độ rotor SP-201 thay đổi tỷ lệ phân ly và hồi lưu. Mô hình chưa dự báo phân bố kích thước hạt. Mất tín hiệu rung RM-201 chỉ ảnh hưởng kênh giám sát vì kịch bản sử dụng một kênh bảo vệ rung độc lập. Khi khí sấy giảm, mô hình giới hạn cấp liệu để giữ mục tiêu độ ẩm. SL-301 tiếp tục cấp cho KF-301 theo lượng tồn khả dụng.

Z02 mô phỏng tuyến SL-301 → KF-301 → PH-301 → PC-301 → KL-301 → CL-301 → SL-302. CF-301 hút khí qua tháp tiền gia nhiệt. Lực hút thấp giới hạn hoặc ngừng cấp liệu. Mô hình hạch toán nước bay hơi và CO₂ tách từ bột liệu, đồng thời ước tính nhiệt giàn nguội thu hồi cho lò. Mô hình dùng hệ số phản ứng và nhiệt độ quy ước. Thời gian lưu, động học cháy và CO₂ từ nhiên liệu nằm ngoài phạm vi bản này. Cửa xả SL-302 cấp cho một nhu cầu hạ nguồn giả định 60 t/h ở ranh giới Zone 3.

## Phạm vi mô hình

Tuyến mẫu `bulk_material_line.json` dùng bước tính 60 s và thông số giả định. Khi `downstream_feeder` ngừng nhận, `product_silo` tích lũy và giới hạn dòng từ công đoạn trước khi đầy. Khi công đoạn trước giảm sản lượng, silo tiếp tục cấp liệu trong phạm vi tồn kho khả dụng. `transfer_conveyor` biểu diễn vật liệu đang vận chuyển với độ trễ một bước.

Để dùng lại model cho dự án khác, tạo cấu hình plant với ID, thông số và kết nối riêng, rồi truyền `--plant` khi chạy. `model_type` tham chiếu đến khai báo dùng chung trong `configs/model_types/`. Mục `target` trong kịch bản dùng ID của thiết bị trong plant đã chọn.

Các dòng được phân bổ theo tồn kho đầu bước, rồi cam kết đồng thời. Sấy bảo toàn chất rắn khô và hạch toán hơi nước. Phân ly dùng tỷ lệ hạt mịn và vòng hồi lưu cục bộ ở trạng thái ổn định trong mỗi bước. Nhiệt khả dụng là tham số riêng của drying_mill. Solver hiện hỗ trợ các tuyến vật liệu một đầu vào, một đầu ra có bộ đệm, cùng nhánh khí và vòng hồi lưu máy nghiền/phân ly. Dữ liệu xuất là giá trị vật lý mô phỏng. Đo lường, PID và động học lò thuộc các bước triển khai sau.
