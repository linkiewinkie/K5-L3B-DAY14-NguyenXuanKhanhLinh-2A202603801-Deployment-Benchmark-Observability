# Benchmark & Observability Report — Day 14

**Họ tên:** Nguyễn Xuân Khánh Linh  
**Ngày chạy:** 27/11/2026 (GMT+7)  
**Môi trường:** Windows, Ubuntu WSL2 với Python 3.11.18 cho benchmark develop, Docker Desktop Engine 29.9.3 với 12 vCPU và 15,45 GiB RAM cho stack production. Agent dùng mock LLM.

## 1. SLO của agent

| SLI | SLO | Lý do |
| --- | --- | --- |
| p95 latency `/ask` | ≤ 500 ms | Kiểm tra trải nghiệm của phần lớn request, bao gồm nhóm request chậm hơn mức điển hình. |
| Error rate `/ask` | ≤ 2% | Giới hạn tỷ lệ request lỗi, gồm lỗi upstream 503 do mock. |
| Accuracy trên golden dataset | ≥ 85% trên CI, 100% ở bài sửa KB | Chặn giảm chất lượng trước merge và xác nhận sửa đủ 23 câu của bài lab. |

Trong môi trường observability, alert dùng ngưỡng vận hành riêng của đề. Error rate 5xx vượt 5% trong 1 phút và p95 lớn hơn 1 giây trong 2 phút mới firing. Load test bên dưới dùng ngưỡng chặt hơn của `load_test.py`.

## 2. Benchmark hiệu năng (develop)

### Exercise 7.1 — Metrics

- Counter `http_requests_total{method="POST",route="/ask",status="200"}` tăng lên 1 sau một request thành công.
- Gauge `agent_in_flight_requests` bằng 0 sau khi request kết thúc. Giá trị tăng khi nhận thêm request và giảm khi xử lý xong.
- Histogram `agent_question_length_chars` đo độ dài câu hỏi bằng các bucket 20, 50, 100, 200, 500, 1.000 và 2.000 ký tự. Sau câu hỏi thử, `_count` là 1 và `_sum` là 40 ký tự.

Dùng route template và gom URL lạ vào `unmatched` giúp số series ổn định. Nếu dùng nguyên URL làm label, mỗi đường dẫn ngẫu nhiên sinh thêm series mới theo từng method và status, gây tăng bộ nhớ và chi phí truy vấn Prometheus.

### Exercise 7.2 — Concurrency và latency

Mỗi hàng dùng 300 request với v2, `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. RPS tính trên mọi request. Percentile chỉ tính các response 200 theo `load_test.py`.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO | Report |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 4,19 | 200,6 | 234,7 | 1.684,8 | 1,00% | PASS | [JSON](reports/load_v2_c1.json) |
| 10 | 35,04 | 201,6 | 250,9 | 1.719,3 | 1,00% | PASS | [JSON](reports/load_v2_c10.json) |
| 50 | 109,83 | 331,7 | 473,9 | 709,8 | 1,33% | PASS | [JSON](reports/load_v2_c50.json) |
| 100 | 45,96 | 798,7 | 4.601,2 | 4.990,3 | 0,67% | FAIL p95 | [JSON](reports/load_v2_c100.json) |

p50 là trung vị, p95 và p99 lần lượt mô tả ngưỡng của 95% và 99% request thành công. RPS tăng từ 4,19 lên 109,83 rồi giảm ở concurrency 100. Khi số request đồng thời tăng, việc lập lịch và xử lý kết nối trên máy dùng chung cũng có thể tăng thời gian chờ. Lần đo này có hoạt động Docker cùng lúc nên kết quả phản ánh môi trường lab của lần chạy. Cần đo lại ở máy dành riêng cho benchmark để tách nguyên nhân của mức giảm tại concurrency 100.

### Exercise 7.2 — Tail latency

Giữ 300 request, concurrency 20 và `MOCK_ERROR_RATE=0.01`. Khởi động lại agent khi đổi cấu hình.

| `MOCK_SLOW_RATE` | Avg (ms) | p95 (ms) | p99 (ms) | Report |
| ---: | ---: | ---: | ---: | --- |
| 0 | 294,9 | 425,0 | 483,8 | [JSON](reports/load_v2_slow_0.json) |
| 0,03 (mặc định) | 309,9 | 438,8 | 1.806,3 | [JSON](reports/load_v2_slow_0.03.json) |
| 0,1 | 354,8 | 1.699,6 | 1.748,5 | [JSON](reports/load_v2_slow_0.1.json) |

p99 phản ứng rõ khi chuyển từ 0 sang 3% chậm. Ở 10%, lượng request chậm đủ để p95 tăng theo. Average chỉ tăng từ 294,9 lên 354,8 ms vì phần lớn request vẫn nhanh. p99 của hai lần có tail dao động theo jitter và các mẫu hiếm trong 300 request. Dùng p95 làm SLO chính và theo dõi p99 để thấy phần đuôi mà average làm loãng.

## 3. Benchmark chất lượng — Exercise 7.3

Chạy eval với `MOCK_ERROR_RATE=0` để đo chất lượng câu trả lời. Cả ba lần chạy dùng cùng golden dataset 23 câu.

| Chỉ số | [Agent v1](reports/eval_v1.json) | [Agent v2 ban đầu](reports/eval_v2.json) | [Agent v2 đã sửa](reports/eval_v2_fixed.json) |
| --- | ---: | ---: | ---: |
| Accuracy | 4,35% (1/23) | 91,30% (21/23) | 100% (23/23) |
| Avg tokens/câu | 57,3 | 109,1 | 114,1 |
| Tổng cost (USD) | 0,000406 | 0,000762 | 0,000795 |
| Cost/câu đúng (USD) | 0,00040635 | 0,00003627 | 0,00003455 |
| Quality gate khi chạy | FAIL (80%) | PASS (80%, baseline v1) | PASS (100%, baseline v2) |

| Câu thiếu keyword ở v2 | Keyword bị thiếu | Sửa trong `KNOWLEDGE_BASE` |
| --- | --- | --- |
| `security-02` | token, hết hạn, chữ ký | Thêm tài liệu JWT, giải thích chữ ký và hạn dùng của token. |
| `scaling-03` | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA và các tín hiệu dùng để scale pod. |

V2 đã sửa cải thiện 2 câu và có 0 câu bị regression. Retrieval thêm một bước trước LLM và đưa tài liệu vào prompt, nên v2 dùng nhiều token hơn. Tổng chi phí tăng, nhưng chi phí trên mỗi câu đúng giảm mạnh do số câu đúng tăng. p95 của ba lượt eval với 23 câu lần lượt là 1.525,8 ms, 250,7 ms và 1.680,2 ms. Với mẫu nhỏ và tail latency ngẫu nhiên, ba số này chưa đủ để định lượng chi phí độ trễ của retrieval.

Job [Quality gate](.github/workflows/eval.yml) chạy trên pull request, đợi agent v2 healthy rồi chạy `run_eval.py --min-accuracy 0.85`. Script trả mã thoát 1 khi accuracy dưới ngưỡng. Khi có `--baseline`, nó cũng trả mã 1 nếu câu từng đúng chuyển thành sai. Đặt job thành required status check để GitHub chặn merge khi job thất bại.

## 4. Observability stack (production)

### Exercise 7.4 — Grafana và Golden Signals

Chạy stack `k5-day14-observability` với 2 replica và Locust 30 user, ramp-up 5 user/s. Grafana mở qua cổng 13000 vì cổng 3000 đang được dùng trên máy. [Ảnh dashboard Grafana](screenshots/grafana-dashboard.png)

1. Trong cùng lần đo Prometheus, p95 của `/ask` là **293,28 ms** và average **230,71 ms**, lệch khoảng **62,57 ms**. p99 khoảng **1.806,06 ms** cho thấy nhóm nhỏ request chậm. Ảnh Grafana refresh sau đó và hiển thị p95 **293,53 ms**.
2. Hai series `Requests/s theo instance` là **7,82 req/s** và **7,71 req/s**. Lưu lượng được chia gần đều ở thời điểm đo.
3. Input đạt **1.207,23 token/s** và output **636,36 token/s**. V2 đưa system prompt, câu hỏi và tài liệu retrieval vào input, còn output chỉ chứa câu trả lời.
4. `GET http://localhost:8080/metrics` trả **404**. Nginx chặn route này. Prometheus scrape `/metrics` trực tiếp ở cổng 8000 của các container agent trên mạng nội bộ.

### Exercise 7.5 — Tracing

Trong truy vấn Jaeger của service `observable-agent` theo operation `POST /ask`, trace thành công chậm nhất trong cửa sổ lấy mẫu 45 giây có ID `39bc3f7766186035384033ae7843f822` và kéo dài **1.707,89 ms**. Span tác vụ `chat mock-llm-small` chiếm **1.679,57 ms (98,34%)**. Retrieval chiếm **25,42 ms**. [Ảnh trace chậm](screenshots/jaeger-slow-trace.png)

```json
{"ts":"2026-11-27T03:44:48.256804+00:00","level":"INFO","service":"observable-agent","instance":"8872dfdc3f3d","event":"llm_call","trace_id":"39bc3f7766186035384033ae7843f822","span_id":"e142233b0bc38270","request_id":"fe4b15a4d1e1","model":"mock-llm-small","agent_version":"v2","input_tokens":74,"output_tokens":37,"cost_usd":0.000033,"llm_ms":1679.6}
```

Trace lỗi `d59f0922b790b82881071239b4327699` trả 503 trong **116,35 ms**. Span `chat mock-llm-small` có event `exception` với type `utils.mock_llm.LLMError` và message `Upstream LLM error: 503 Service Unavailable (mock)`. ID trong log `llm_error` mở đúng trace này trên Jaeger. [Ảnh trace lỗi](screenshots/jaeger-error-trace.png)

```json
{"ts":"2026-11-27T03:45:18.172879+00:00","level":"INFO","service":"observable-agent","instance":"36fd03b3e81e","event":"llm_error","trace_id":"d59f0922b790b82881071239b4327699","span_id":"87a83c310c43e751","request_id":"003f5fca9649","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

### Exercise 7.6 — Alerts và fault injection

`promtool test rules` báo `SUCCESS`. `promtool check rules` xác nhận 4 rule hợp lệ.

| Thí nghiệm | Thay đổi | Alert firing | Thời gian từ lúc đổi | Panel |
| --- | --- | --- | ---: | --- |
| A | Đặt `MOCK_ERROR_RATE=0.2`, tạo lại hai agent trong lúc Locust đang gửi tải | `AgentHighErrorRate` | 91,28 s | Error rate, Requests/s theo status code |
| D | `docker pause` một replica khi A vẫn đang firing | `AgentInstanceDown` | 44,97 s | Instances up, Requests/s theo instance |

Thời gian lấy từ lúc gọi lệnh thay đổi đến lần poll API báo firing, với khoảng poll 2 giây. A cần tỷ lệ 5xx vượt 5% trong 1 phút. Lần đầu phát hiện firing ghi nhận **18,83%**. D cần mất scrape liên tục 30 giây cho một target. Thời gian thực tế gồm độ trễ scrape, timeout và vòng đánh giá rule. Ảnh chụp khi hai cảnh báo đều firing, sau đó replica được unpause. [Ảnh Prometheus Alerts](screenshots/prometheus-alert-firing.png)

Ở thí nghiệm E, chuyển về v1 vẫn có thể trả HTTP 200 nhanh trong khi câu trả lời sai. Các rule vận hành đo latency, lỗi, availability và cost nên có thể bỏ qua suy giảm chất lượng này. Dùng golden eval như required check trước deploy và chạy synthetic eval định kỳ trên bản đang phục vụ. Theo dõi accuracy theo phiên bản và cảnh báo khi accuracy giảm dưới ngưỡng.

## 5. Benchmark scaling — Exercise 7.7

Mỗi lần chạy Locust headless trong 2 phút với 100 user, ramp-up 10 user/s và cùng cấu hình v2, `mock-llm-small`, `MOCK_SLOW_RATE=0.03`, `MOCK_ERROR_RATE=0.01`. Sau khi đổi số replica, kiểm tra Nginx trả phản hồi từ đủ số địa chỉ upstream rồi mới bắt đầu đo. Số trong bảng lấy từ dòng `POST,/ask` trong CSV.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Report |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 53,71 | 260 | 1.100 | 1.900 | 67/6.389 (1,05%) | [CSV](benchmark-results/scale_1_stats.csv) |
| 3 | 59,38 | 200 | 350 | 1.700 | 73/7.076 (1,03%) | [CSV](benchmark-results/scale_3_stats.csv) |

Tăng từ 1 lên 3 replica giảm p95 từ 1.100 xuống 350 ms (**68,18%**) và tăng throughput khoảng **10,55%**. Kết quả phù hợp với việc chia tải làm giảm phần chờ tại agent khi nhiều user gửi request. Lượt đo này không phân lập được bằng số CPU hay queue depth. Tốc độ còn chịu ảnh hưởng của số user cố định, thời gian nghỉ giữa các request và latency mock LLM. p99 vẫn 1.700 ms do đuôi chậm mô phỏng. Tỷ lệ lỗi khoảng 1% ở cả hai lần.

## 6. Kết luận

1. Tải cao cần theo dõi throughput cùng p95 và p99. Chỉ nhìn RPS sẽ bỏ qua độ trễ ở nhóm request chậm.
2. Golden eval bắt lỗi chất lượng ngay cả khi HTTP và các chỉ số vận hành còn xanh. Chi phí trên mỗi câu đúng cho thấy lợi ích của retrieval trong bài này.
3. Dashboard chỉ ra xu hướng và alert xác định tình trạng kéo dài qua ngưỡng. Trace liên kết với log giúp tìm đúng công đoạn gây chậm hoặc lỗi trong một request.

Với agent thật, bổ sung tỷ lệ upstream timeout theo model, tỷ lệ retrieval rỗng và accuracy của synthetic eval theo phiên bản. Đặt cảnh báo dự toán chi phí so với ngân sách còn lại của kỳ.
