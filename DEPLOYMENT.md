# Triển khai agent Day 14

## Nền tảng và trạng thái

Agent Part 6 đang chạy trên Render tại [https://day14-agent-scfb.onrender.com](https://day14-agent-scfb.onrender.com/health). Blueprint `day14-lab` triển khai commit `72c353d` từ nhánh `main`. Dịch vụ Docker `day14-agent` ở trạng thái **Live** và dịch vụ Key Value `day14-redis` ở trạng thái **Available**. Hai dịch vụ chạy ở vùng Oregon.

- [Dashboard Blueprint](screenshots/dashboard.png)
- [Dịch vụ Live](screenshots/running.png)
- [Kết quả kiểm tra API public](screenshots/test.png)

## Thiết lập trên Render

1. Trong **New → Blueprint**, nhập URL public của repo bài lab và đặt **Blueprint Path** thành `06-lab-complete/render.yaml`.
2. Blueprint tạo web service `day14-agent` từ Dockerfile trong `06-lab-complete/` và dịch vụ Key Value `day14-redis` cùng vùng. Render dùng đường dẫn `/health` để kiểm tra web service.
3. Sau khi web service báo **Live**, sao chép URL HTTPS và chạy bốn lệnh bên dưới. Chụp trang tổng quan, trạng thái **Live** và kết quả kiểm tra vào `screenshots/dashboard.png`, `screenshots/running.png` và `screenshots/test.png`.

[Render Blueprints](https://render.com/docs/infrastructure-as-code) · [Cấu hình đường dẫn Blueprint](https://render.com/changelog/blueprints-now-support-custom-filenames-and-paths)

## Biến môi trường

| Biến | Nguồn |
|---|---|
| `PORT` | Render cấp cho web service. Dockerfile truyền giá trị này cho Uvicorn. |
| `ENVIRONMENT` | Blueprint đặt `production`. |
| `AGENT_API_KEY` | Render sinh ngẫu nhiên, lấy trong tab **Environment** của web service. |
| `REDIS_URL` | Blueprint lấy URL kết nối nội bộ từ `day14-redis`. |
| `RATE_LIMIT_PER_MINUTE` | Mặc định 10. |
| `MONTHLY_BUDGET_USD` | Mặc định 10 USD/tháng UTC. `DAILY_BUDGET_USD` tùy chọn chuyển sang ngân sách ngày UTC. |
| `LOG_LEVEL` | Mặc định `INFO`. |

## Kiểm tra URL public

Bốn request thực tế được chạy ngày 27/11/2026 lúc 18:06 GMT+7.

| Request | Mã HTTP |
|---|---:|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` thiếu API key | 401 |
| `POST /ask` có API key hợp lệ | 200 |

Để kiểm tra lại, chạy trong Bash và nhập URL cùng API key từ dashboard khi được hỏi.

```bash
read -r -p 'URL HTTPS của agent: ' BASE
read -rs -p 'AGENT_API_KEY: ' AGENT_API_KEY
printf '\n'
BASE=${BASE%/}

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'
unset AGENT_API_KEY
```

## Kiểm tra local

Bản Docker Compose đã được xác minh trên cổng 18006 với Redis và API key tạm. `GET /health` và `GET /ready` trả 200. `POST /ask` thiếu key trả 401 và có key hợp lệ trả 200. Câu hỏi chỉ có khoảng trắng trả 422. Kết quả bài chấm đầy đủ nằm trong [MISSION_ANSWERS.md](MISSION_ANSWERS.md#part-6--production-readiness-check).
