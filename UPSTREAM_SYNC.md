# Hướng Dẫn Cập Nhật & Bảo Trì (Upstream Sync & Maintenance Guide)

> **Dành cho Người Dùng & AI Agents:** Tài liệu này ghi lại toàn bộ kiến trúc CI/CD, các điểm khác biệt so với repository gốc của tác giả (`seedds/nxnative`), và quy trình chuẩn để cập nhật (sync) code khi tác giả ra mắt tính năng/bản sửa lỗi mới mà không làm hỏng tính năng tự động build IPA trên GitHub Actions.

---

## 1. Thông Tin Repositories & Cấu Trúc Remote

- **Repo Gốc (Upstream):** `https://github.com/seedds/nxnative.git` (Remote name: `origin`)
- **Repo Build Của Bạn (Target / Custom):** `https://github.com/kiet2711/test-nsw-ipa.git` (Remote name: `test`)
- **Nhánh hoạt động:** `main`

Kiểm tra cấu hình remote bằng lệnh:
```bash
git remote -v
```
Nếu thiếu remote `origin`, thêm lại bằng:
```bash
git remote add origin https://github.com/seedds/nxnative.git
```

---

## 2. Danh Sách Các Thay Đổi So Với Bản Gốc (Repository Delta)

Toàn bộ mã nguồn cốt lõi (`dm/`, `scripts/`, Metal 4, Swift Launcher, NVN, Vulkan, .NET rewriter) được giữ **100% nguyên bản của tác giả**. Chỉ có **4 thành phần** cấu hình sau được tạo mới hoặc chỉnh sửa:

1. **`.github/workflows/build_ipa.yml` (TẠO MỚI):**
   - Workflow GitHub Actions tự động hóa toàn bộ quy trình: tải ROM game từ Google Drive, chuẩn bị runner macOS Apple Silicon, thiết lập .NET 10 ARM64 và Python 3.14, chạy script `build_ipa_from_nsp.py` và xuất artifact file `.ipa`.
2. **`.github/workflows/tests.yml` (ĐÃ XÓA):**
   - Bộ unit test nội bộ của tác giả. Đã xóa bỏ để tránh tiêu tốn hàng trăm phút quota GitHub Actions và không bị spam lỗi/chạy chậm khi push code.
3. **`.gitignore` (BỔ SUNG):**
   - Đã thêm các dòng bỏ qua file ROM và thư mục tạm:
     ```gitignore
     *.xci
     *.nsp
     *.nsz
     *.xcz
     *_build/
     *_survey/
     ```
   - Ngăn chặn việc vô tình `git push` các file game nặng hàng GB lên GitHub (GitHub chặn file > 100MB).
4. **`game/prod.keys` (TẠO MỚI):**
   - Chứa Nintendo Switch keys để giải mã và trích xuất game.

---

## 3. Các Yêu Cầu Kỹ Thuật Bắt Buộc (Critical Technical Gotchas)

Bất kỳ AI Agent hoặc lập trình viên nào bảo trì file `.github/workflows/build_ipa.yml` cần tuyệt đối ghi nhớ:

| Thành phần | Yêu cầu bắt buộc | Lý do kỹ thuật |
|---|---|---|
| **GitHub Runner** | `runs-on: macos-26` | Mã nguồn `nxnative` dùng Metal 4 (`MTL4ComputeCommandEncoder`, `MTL4ArgumentTable`), compiler flag `-mcpu=apple-a18` và SwiftUI `.glassProminent` (iOS 26 SDK). Các runner `macos-14` hoặc `macos-15` sẽ thất bại 100% khi compile. |
| **Python** | `3.14` | Repo yêu cầu Python 3.14. **Không** được cài `backports.zstd` vì gói này lỗi trên 3.14. Phải cài `zstandard` cùng với `lz4`, `capstone`, `fonttools`, `gdown`. |
| **.NET Runtime** | .NET 10 ARM64 | Công cụ giải mã `nx_extract` là binary độc lập ARM64. Phải trỏ biến `DOTNET_ROOT_ARM64` và ghi đường dẫn vào `/etc/dotnet/install_location_arm64` để tránh crash với `exit code 131`. |
| **Tải file lớn** | `python3 -m gdown` | File game ROM lớn (>100MB) trên Google Drive có trang cảnh báo quét virus. Không dùng cờ `--fuzzy` (bị gdown mới loại bỏ). Dùng format: `python3 -m gdown "$URL" -O "$OUT"`. |
| **Lệnh đóng gói** | `scripts/build_ipa_from_nsp.py` | Lệnh chuẩn: `python3 scripts/build_ipa_from_nsp.py game -k game/prod.keys --no-keep-extracted`. |

---

## 4. Quy Trình Cập Nhật Chuẩn (Step-by-Step Upstream Sync)

Khi tác giả `seedds/nxnative` ra mắt bản cập nhật (sửa lỗi đồ họa, hỗ trợ thêm game mới, tối ưu hiệu năng), thực hiện theo các bước sau:

### Bước 1: Kiểm tra trạng thái Git
Đảm bảo thư mục làm việc sạch sẽ, không có thay đổi chưa commit:
```bash
git status
```

### Bước 2: Kéo thông tin mới nhất từ repo gốc
```bash
git fetch origin
```

### Bước 3: Hợp nhất cập nhật

#### Cách 1 (Khuyên dùng): Dùng Git Rebase
Cách này giữ lịch sử commit thẳng hàng và đẹp mắt:
```bash
git rebase origin/main
```
* **Xử lý xung đột (nếu có):**
  * Do ta đã xóa `.github/workflows/tests.yml`, nếu tác giả có sửa file này, Git có thể dừng lại thông báo conflict.
  * Chỉ cần chạy:
    ```bash
    git rm .github/workflows/tests.yml
    git rebase --continue
    ```
  * Các file `.github/workflows/build_ipa.yml`, `.gitignore`, `game/prod.keys` không có trong repo gốc nên sẽ không bao giờ bị conflict.

#### Cách 2: Dùng Git Merge (Đơn giản, một lệnh duy nhất)
Nếu không muốn rebase từng commit:
```bash
git merge origin/main -m "Merge upstream updates from author"
```
*(Nếu Git hỏi về `tests.yml`, chỉ cần xóa nó đi: `git rm .github/workflows/tests.yml` rồi `git commit`)*

### Bước 4: Đẩy lên GitHub để tự động build bản IPA mới
```bash
git push test main
```
*(Nếu dùng `rebase`, có thể cần thêm cờ `--force-with-lease`: `git push test main --force-with-lease`)*

Ngay lập tức, GitHub Actions trên repo của bạn sẽ tự động chạy và build ra bản `.ipa` mới nhất tích hợp tất cả các bản vá của tác giả!

---

## 5. Hướng Dẫn Đổi Game Hoặc Cập Nhật DLC

Để đóng gói một game khác hoặc cập nhật bản update/DLC:
1. Upload file ROM (`.xci` hoặc `.nsp`) lên Google Drive và lấy link chia sẻ công khai.
2. Vào GitHub Repository -> tab **Actions** -> Chọn workflow **Build Nintendo Switch IPA**.
3. Bấm **Run workflow**:
   - Dán URL Google Drive mới vào ô `game_download_url`.
   - Bấm nút **Run workflow** màu xanh để bắt đầu build mà không cần sửa code.
