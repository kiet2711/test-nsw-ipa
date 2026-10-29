# Hướng Dẫn Cập Nhật & Bảo Trì (Upstream Sync & Maintenance Guide)

> **Dành cho Người Dùng & AI Agents:** Tài liệu này ghi lại toàn bộ kiến trúc CI/CD, các điểm khác biệt (delta) so với repository gốc của tác giả (`seedds/nxnative`), và quy trình chuẩn để cập nhật (sync) code khi tác giả ra mắt game hoặc bản sửa lỗi mới mà không làm hỏng tính năng tự động build IPA trên GitHub Actions.

---

## 1. Cấu Trúc Git Remotes Chuẩn

Quy ước chuẩn đặt tên remote:
- **`origin`**: Repository của bạn (`https://github.com/kiet2711/test-nsw-ipa.git`)
- **`upstream`**: Repository gốc của tác giả (`https://github.com/seedds/nxnative.git`)
- **Nhánh hoạt động chính:** `main`

Kiểm tra remote bằng lệnh:
```bash
git remote -v
```
Nếu chưa có remote `upstream`, thêm lại bằng:
```bash
git remote add upstream https://github.com/seedds/nxnative.git
```

---

## 2. Danh Sách Các Thành Phần Tùy Biến (Repository Delta)

Toàn bộ mã nguồn giả lập cốt lõi (`dm/host/`, Metal 4, Swift Launcher, NVN, Vulkan, .NET rewriter) được đồng bộ từ tác giả. Các thành phần tùy biến thêm gồm:

1. **`.github/workflows/build_ipa.yml` (TẠO MỚI):**
   * Tự động hóa build trên GitHub Actions runner `macos-26` Apple Silicon.
   * Tự động tải từ link **Gofile** (thư mục hoặc file lẻ) và **Google Drive** (file lẻ hoặc trọn gói cả folder).
   * Tự động giải nén file nén nhiều phần (`.part1.rar`, `.001`) và gộp Base Game + Update + DLC.
   * Tự động quét và tích hợp Mod / Việt hóa LayeredFS (`romfs/`).
   * Bổ sung cờ `--allow-other-metal --allow-shader-regressions` và `DM_ALLOW_OTHER_METAL=1` để tương thích môi trường máy ảo.
   * Ghi nhận toàn bộ console log vào `build_console.log` và đính kèm vào artifact `build-failure-logs` khi có lỗi.
2. **`dm/tools/download_gofile.py` (TẠO MỚI):**
   * Công cụ tải tự động toàn bộ thư mục từ Gofile.io.
   * Cơ chế xác thực dynamic `X-Website-Token` (SHA-256 rotating 4h) và thiết lập session cookies để vượt qua lỗi `error-notPremium`.
3. **`scripts/build_ipa_from_nsp.py` (CHỈNH SỬA):**
   * Hỗ trợ cờ `--mod` và biến `MOD_DIR` để áp dụng mod LayeredFS.
   * Tự động đóng gói thư mục mod thành định dạng `RomFS.img` mới bằng `dm/tools/romfs_image.py`.
   * Đặt mặc định `ALLOW_OTHER_METAL = True` và `ALLOW_SHADER_REGRESSIONS = True` để tránh dừng build do khác biệt phiên bản Metal của runner.
4. **`.github/workflows/tests.yml` (ĐÃ XÓA):**
   * Bộ unit test nội bộ của tác giả. Phải luôn **xóa bỏ** file này để tránh tiêu tốn hàng trăm phút quota GitHub Actions vô ích khi push code.
5. **`game/prod.keys` (TẠO MỚI):**
   * Nintendo Switch keys để giải mã và trích xuất RomFS/ExeFS.

---

## 3. Các Yêu Cầu Kỹ Thuật Bắt Buộc (Critical Gotchas)

| Thành phần | Yêu cầu bắt buộc | Lý do kỹ thuật |
|---|---|---|
| **GitHub Runner** | `runs-on: macos-26` | Cần Metal 4 compiler, flag `-mcpu=apple-a18` và iOS 26 SDK. Runner thấp hơn sẽ lỗi biên dịch 100%. |
| **Python** | `3.14` | Cài đặt `zstandard`, `lz4`, `capstone`, `fonttools`, `gdown`, `requests`. **Không** cài `backports.zstd` vì lỗi trên Python 3.14. |
| **Metal Compiler Lock** | `--allow-other-metal` & `DM_ALLOW_OTHER_METAL=1` | Upstream khóa cứng phiên bản Metal theo file `dmsh_chain.lock` trên máy tác giả. Máy ảo GitHub Actions có phiên bản Metal khác nên bắt buộc phải bật cờ này để không bị `BuildError`. |
| **Shader Regressions** | `--allow-shader-regressions` | Ngăn chặn việc dừng build khi một số shader cũ của game dịch khác biệt nhỏ so với bản dịch trước. |
| **.NET Runtime** | .NET 10 ARM64 | Công cụ trích xuất `nx_extract` cần `DOTNET_ROOT_ARM64` và `/etc/dotnet/install_location_arm64`. |
| **Git Author** | `seedds <seedds@gmail.com>` | Khi commit phải dùng: `git -c user.name=seedds -c user.email=seedds@gmail.com commit`. |

---

## 4. Quy Trình Cập Nhật Chuẩn (Step-by-Step Upstream Sync)

Khi tác giả `seedds/nxnative` ra mắt bản cập nhật mới, thực hiện theo các bước sau:

### Bước 1: Kéo code mới nhất từ upstream
```bash
git fetch upstream
```

### Bước 2: Bắt đầu hợp nhất (Merge) vào nhánh main
```bash
git checkout main
git merge upstream/main --no-commit --no-ff
```

### Bước 3: Xử lý các xung đột (Conflict Resolution)

Khi merge, Git thường sẽ báo conflict ở 2 file sau:

#### 1. Xung đột file `.github/workflows/tests.yml` (modify/delete):
File này tác giả sửa ở upstream nhưng ta đã xóa trên repo của mình. Chỉ cần chạy lệnh xóa:
```bash
git rm .github/workflows/tests.yml
```

#### 2. Xung đột trong `scripts/build_ipa_from_nsp.py`:
Mở file `scripts/build_ipa_from_nsp.py` và giải quyết:
* **Tại đầu file (dòng ~70):** Giữ cả `MOD_DIR` và các cài đặt mới của upstream:
  ```python
  MOD_DIR = ''                            # optional folder holding LayeredFS mod / translated RomFS files (empty = auto-detect romfs/ or mod/ in NSP folder)
  REGION_CHECK_NNMAIN_SECS = 15           # the address region check: the regions a game takes in nninitStartup and its first seconds in nnMain
  SWITCH_ALIAS = 0x1000000000             # the Switch's alias region (64 GB), which holds what a game reserves unchanged
  ```
* **Tại `ALLOW_OTHER_METAL` và `ALLOW_SHADER_REGRESSIONS`:** Luôn đặt thành `True`:
  ```python
  ALLOW_SHADER_REGRESSIONS = True
  ALLOW_OTHER_METAL = True
  ```
* **Tại `parse_args` (dòng ~2080):** Giữ cả tham số `--mod` và các tham số mới của upstream:
  ```python
      ap.add_argument('--no-heap-check', action='store_true', help='a provisional profile: skip the heap check and the address region check on the Mac (the alias / heap split stays a guess); a derived profile: skip the address region check')
      ap.add_argument('--mod', help='folder holding LayeredFS mod / translated RomFS files to apply over extracted RomFS (default: MOD_DIR setting or romfs/ in NSP folder)')
  ```
* **Tại vòng lặp trích xuất và áp dụng Mod (trong hàm `main`):**
  Tuyệt đối **KHÔNG** làm mất vòng lặp `dirs = {}` và `game = dirs[pkg_ver]`. Đoạn code chuẩn:
  ```python
      mod_arg = getattr(args, 'mod', None) or MOD_DIR
      mod_path = Path(os.path.expanduser(mod_arg)).resolve() if mod_arg else (
          Path(os.environ['DM_MOD_DIR']).resolve() if 'DM_MOD_DIR' in os.environ else (
              (nsp_dir / 'romfs') if (nsp_dir / 'romfs').is_dir() else (
                  (nsp_dir / 'mod') if (nsp_dir / 'mod').is_dir() else None
              )
          )
      )
      dirs = {}
      for ver in versions:   # each merged version streams directly into its own image
          b, u = picks[ver]
          dirs[ver] = extract(nx, keys, ex, ver, b, u, None, logs, g, romfs_image=(mod_path is None))
      bad = [] if derived else [f'{v}: {x}' for v in versions for x in build_mismatch(dirs[v], v, g)]
      if bad and provisional: raise BuildError(f'not the builds provisional game profile {g.id} registers: {"; ".join(bad)}')
      if bad:
          derived = f'not the builds game profile {g.id} registers: {"; ".join(bad)}'
          say(f'{derived}: packing {pkg_ver} from a profile derived from it')
          versions, dirs = [pkg_ver], {pkg_ver: dirs[pkg_ver]}
      reg = g
      if derived:
          pdir = Path(os.path.expanduser(args.profile_out or PROFILE_OUT)).resolve() if (args.profile_out or PROFILE_OUT) else nsp_dir / f'{app:016X}_build' / 'profile'
          disp = derive_profile(g, pdir / g.id, pkg_ver, dirs[pkg_ver], g.words('modules'), app)
          os.environ['DM_GAMES_DIR'] = env['DM_GAMES_DIR'] = os.pathsep.join([str(pdir)] + [d for d in os.environ.get('DM_GAMES_DIR', '').split(os.pathsep) if d and d != str(pdir)])
          os.environ['DM_GAMES_FIRST'] = env['DM_GAMES_FIRST'] = '1'
          g = gamemod.load(g.id)
          say(f'derived game profile for {pkg_ver} ({disp}): {g.dir}')
      sv = versions if derived else need
      game = dirs[pkg_ver]
      if mod_path and mod_path.is_dir():
          romfs_subs = [p for p in mod_path.rglob('*') if p.is_dir() and p.name.lower() == 'romfs']
          mod_src = romfs_subs[0] if romfs_subs else mod_path
          say(f'applying LayeredFS mod: {mod_src} → {game / "RomFS"}')
          shutil.copytree(mod_src, game / 'RomFS', dirs_exist_ok=True)
          say(f'packing modified RomFS into image: {game / "RomFS.img"}')
          run([sys.executable, str(repo / 'dm/tools/romfs_image.py'), str(game / 'RomFS'), str(game / 'RomFS.img')], logs / 'romfs_image.log')
          rmtree(game / 'RomFS')
  ```

Sau khi sửa xong, kiểm tra cú pháp Python:
```bash
python -m py_compile scripts/build_ipa_from_nsp.py
```
Và đánh dấu đã giải quyết:
```bash
git add scripts/build_ipa_from_nsp.py
```

### Bước 4: Commit và đẩy lên GitHub
```bash
git -c user.name=seedds -c user.email=seedds@gmail.com commit -m "Merge upstream updates from seedds/nxnative"
git push origin main
```

### Bước 5: Đồng bộ nhánh phụ (nếu có dùng nhánh `update-dlc`)
```bash
git checkout update-dlc
git merge main --ff-only
git push origin update-dlc
git checkout main
```

---

## 5. Hướng Dẫn Đóng Gói Game (Cách Sử Dụng)

1. Gom toàn bộ file game cần thiết (Game gốc `.xci` / `.nsp`, Update `.nsp`, DLC `.nsp`, Mod `.zip`) vào một thư mục trên **[Gofile.io](https://gofile.io/)** (hoặc Google Drive).
2. Vào GitHub Actions -> chọn **Build Nintendo Switch IPA** -> bấm **Run workflow**:
   * **Use workflow from:** Chọn nhánh **`main`**.
   * **`game_download_url`:** Dán liên kết thư mục Gofile (ví dụ `https://gofile.io/d/XXXXXX`).
   * Các ô còn lại để trống.
3. Bấm **Run workflow** màu xanh để hệ thống tự động tải, giải nén, tối ưu hóa và xuất file `.ipa`.
