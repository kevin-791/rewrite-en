# rewrite-en

Bôi đen text trong bất kỳ app nào (Teams, Outlook, Slack, trình duyệt, editor), bấm một hotkey, text được thay tại chỗ bằng bản tiếng Anh tự nhiên do Claude viết lại. Input có thể là tiếng Việt, tiếng Anh lủng củng hoặc trộn cả hai. Chạy trên Windows 10/11 và macOS.

## Cài đặt

Cần Python 3.11 trở lên và [uv](https://docs.astral.sh/uv/) (hoặc pipx).

```bash
uv tool install .        # hoặc: pipx install .
rewrite-en set-key       # nhập API key một lần, lưu vào keychain của hệ điều hành
rewrite-en test "xin chào, mình cần dời cuộc họp sang chiều mai"
rewrite-en install-autostart
```

Nếu không muốn dùng keychain, đặt biến môi trường `ANTHROPIC_API_KEY` (dùng khi keychain không có key).

## Sử dụng

| Lệnh | Việc |
|---|---|
| `rewrite-en run` | Chạy và lắng nghe hotkey (thêm `-v` để in log ra terminal) |
| `rewrite-en set-key` | Lưu API key vào Credential Manager / Keychain |
| `rewrite-en test "text"` | Gọi API một lần không qua hotkey, để kiểm tra key và prompt |
| `rewrite-en config` | Tạo (nếu chưa có) và in đường dẫn + giá trị config |
| `rewrite-en install-autostart` / `uninstall-autostart` | Bật / tắt tự chạy khi đăng nhập |

Hotkey mặc định: **Ctrl+Alt+E** trên Windows, **Ctrl+Shift+E** trên macOS. Bấm hotkey sẽ nghe một tiếng "tick", sau đó một âm thành công hoặc âm lỗi. Ctrl+Z / Cmd+Z ngay sau đó để quay lại text gốc.

## Cấu hình

`config.toml` nằm trong thư mục cấu hình của OS (`rewrite-en config` in ra đường dẫn chính xác):

- Windows: `%LOCALAPPDATA%\rewrite-en\config.toml`
- macOS: `~/Library/Application Support/rewrite-en/config.toml`

```toml
hotkey = "<ctrl>+<alt>+e"      # cú pháp pynput: <ctrl>, <alt>, <shift>, <cmd> + một phím
model = "claude-haiku-5-5"     # hoặc "claude-sonnet-5-5" nếu cần văn phong tốt hơn
max_chars = 6000               # vượt giới hạn thì không gọi API
timeout_seconds = 20
effort = "low"                 # low | medium | high
sounds = true
```

Khởi động lại `rewrite-en` sau khi sửa config.

## Quyền trên macOS

macOS cần hai quyền trong **System Settings → Privacy & Security**, nếu thiếu thì hotkey **im lặng không hoạt động**:

- **Accessibility** (để giả lập Cmd+C / Cmd+V)
- **Input Monitoring** (để nghe hotkey)

Cấp cho:

- **Terminal** (hoặc iTerm, VS Code...) khi chạy tay bằng `rewrite-en run`.
- File **python** thật mà LaunchAgent chạy, khi dùng autostart. `rewrite-en install-autostart` in ra đường dẫn này. Trong hộp thoại thêm app, bấm Cmd+Shift+G và dán đường dẫn.

Nâng cấp Python hoặc cài lại tool có thể đổi đường dẫn python và làm mất quyền; khi đó cấp lại.

Windows không cần quyền gì, nhưng không gửi phím được vào cửa sổ đang chạy quyền Administrator trừ khi rewrite-en cũng chạy admin.

## Khắc phục sự cố

**Bấm hotkey không có phản ứng gì (macOS)**: kiểm tra hai quyền ở trên. Chạy `rewrite-en run` trong terminal: nếu thiếu quyền, nó in cảnh báo ngay khi khởi động.

**Nghe âm lỗi**: xem log để biết mã lỗi (`auth`, `network`, `rate_limited`, `too_long`, `no selection`...):

- Windows: `%LOCALAPPDATA%\rewrite-en\Logs\rewrite-en.log`
- macOS: `~/Library/Logs/rewrite-en/rewrite-en.log`

Log chỉ ghi độ dài text, thời gian và mã lỗi, không bao giờ ghi nội dung text hay API key.

**Hotkey kích hoạt cả phím tắt của app đang dùng**: rewrite-en không chặn phím, nên app vẫn nhận tổ hợp đó. Đổi `hotkey` sang tổ hợp khác trong config.

## Giới hạn đã biết (MVP)

- Chỉ xử lý **plain text**: định dạng, @mention, link trong Teams thành text thường sau khi thay.
- Nếu clipboard đang chứa **ảnh hoặc file** trước khi bấm hotkey, nội dung đó không khôi phục được (chỉ text được khôi phục).
- Khi không bôi đen gì, một số app (ví dụ VS Code) copy cả dòng hiện tại khi bấm Ctrl+C; rewrite-en khi đó sẽ viết lại cả dòng đó.
- Chỉ gửi đúng đoạn bôi đen lên API. Hãy xác nhận chính sách dữ liệu của công ty trước khi dùng với nội dung thật.

## Phát triển

```bash
uv venv && uv pip install -e '.[dev]'
.venv/bin/pytest                 # unit test, mock clipboard và Claude client
python scripts/spike.py          # Phase 0: thử hotkey + copy/paste, không gọi API
```

Cấu trúc:

```
src/rewrite_en/
├── cli.py            # run, set-key, test, config, install-autostart, uninstall-autostart
├── app.py            # hotkey listener, worker thread, kiểm tra quyền macOS
├── pipeline.py       # chụp selection → gọi Claude → paste → khôi phục clipboard
├── clipboard_io.py   # clipboard, giả lập copy/paste, theo dõi phím modifier
├── claude_client.py  # gọi API và hậu xử lý kết quả
├── prompts.py        # SYSTEM_PROMPT
├── config.py         # đọc TOML, giá trị mặc định theo OS
├── keystore.py       # keyring + ANTHROPIC_API_KEY
├── feedback.py       # âm thanh theo OS
└── autostart.py      # Windows: Startup folder; macOS: LaunchAgent
```
