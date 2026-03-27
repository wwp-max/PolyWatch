# 浠诲姟娓呭崟锛歁ilestone 2 涓?3 鍙栬瘉瀹炵幇

**杈撳叆鏂囨。**锛?- `/specs/001-milestone2-validation/spec.md`
- `/specs/002-milestone3-investigation/spec.md`
- `/docs/plans/2026-03-27-milestone3-spec.md`

**鍓嶇疆鏉′欢**锛歱lan.md銆乻pec.md

**缁勭粐鏂瑰紡**锛氫换鍔℃寜鐢ㄦ埛鏁呬簨鍒嗙粍锛屼繚璇佹瘡涓晠浜嬪彲鐙珛瀹炵幇涓庢祴璇曘€?
## 鏍煎紡锛歚[ID] [P?] [Story] 鎻忚堪`

- **[P]**锛氬彲骞惰锛堜笉鍚屾枃浠躲€佹棤渚濊禆锛?- **[Story]**锛氭墍灞炵敤鎴锋晠浜嬶紙濡?US1銆乁S2銆乁S3锛?- 鎻忚堪涓渶鍖呭惈绮剧‘鏂囦欢璺緞

---

## 1. 鐜涓庝緷璧?
- [x] `[T1.1]` `[P]` `[US-Setup]` 纭繚鎴愬憳 D 鍙栬瘉渚濊禆锛坄pandas`銆乣graphviz`銆乣psycopg2-binary`锛夊凡鍖呭惈鍦ㄦ牴鐩綍 `requirements.txt` 涓€?- [x] `[T1.2]` `[P]` `[US-Setup]` 鍒涘缓鍗犱綅娴嬭瘯鏂囦欢锛歚tests/forensics/test_export_alerts.py`銆乣tests/forensics/test_generate_fp_report.py`銆乣tests/forensics/test_fund_flow_graph.py`銆?
## 2. Milestone 2锛氬憡璀︽牳楠岋紙M2-US1, M2-US2锛?
**鐢ㄦ埛鏁呬簨**锛氳幏鍙栧憡璀﹀巻鍙插苟杩涜浜哄伐鏍搁獙

- [x] `[T2.1]` `[ ]` `[M2-US1]` 鍦?`tests/forensics/test_export_alerts.py` 涓疄鐜?`test_export_anomalies_to_csv`锛堜娇鐢?`unittest.mock.patch`锛夈€?- [x] `[T2.2]` `[ ]` `[M2-US1]` 鍦?`forensics/export_alerts.py` 涓疄鐜?`export_anomalies_to_csv`锛屼粠鏁版嵁搴撴媺鍙栧苟鏂板 `is_true_positive` 涓?`verification_notes` 瀛楁銆?- [x] `[T2.3]` `[ ]` `[M2-US1]` 纭繚 `python -m pytest tests/forensics/test_export_alerts.py -v` 閫氳繃銆?- [x] `[T2.4]` `[ ]` `[M2-US2]` 鎵ц `export_anomalies_to_csv("forensics/alerts_to_verify.csv")` 鐢熸垚鍒濆绌虹櫧鏍搁獙鏂囦欢銆?
## 3. Milestone 2锛氳鎶ョ巼鎶ュ憡锛圡2-US3锛?
**鐢ㄦ埛鏁呬簨**锛氳鎶ュ弽棣堟姤鍛?
- [x] `[T3.1]` `[P]` `[M2-US3]` 鍦?`tests/forensics/test_generate_fp_report.py` 涓疄鐜?`test_generate_report`锛屼娇鐢ㄥ寘鍚?TP/FP 鏍囩鐨?mock CSV 鏁版嵁銆?- [x] `[T3.2]` `[ ]` `[M2-US3]` 鍦?`forensics/generate_fp_report.py` 涓疄鐜?`generate_report(input_csv, output_md)`锛岃绠?FP rate 骞惰緭鍑?Markdown 鎽樿銆?- [x] `[T3.3]` `[ ]` `[M2-US3]` 纭繚 `python -m pytest tests/forensics/test_generate_fp_report.py -v` 閫氳繃銆?
## 4. Milestone 3锛氭繁搴﹁皟鏌ュ彲瑙嗗寲锛圡3-US2锛?
**鐢ㄦ埛鏁呬簨**锛欸raphViz 閽卞寘鍏宠仈鍙鍖?
- [x] `[T4.1]` `[P]` `[M3-US2]` 鍦?`tests/forensics/test_fund_flow_graph.py` 涓疄鐜?`test_create_wallet_graph`锛岄獙璇?`.dot` 鏂囦欢鐢熸垚銆?- [x] `[T4.2]` `[ ]` `[M3-US2]` 鍦?`forensics/fund_flow_graph.py` 涓疄鐜?`create_wallet_graph(edges, output_prefix)`锛堜娇鐢?`graphviz.Digraph`锛夈€?- [x] `[T4.3]` `[ ]` `[M3-US2]` 澧炲姞 `graphviz.backend.execute.ExecutableNotFound` 缂哄け鍦烘櫙涓嬬殑浼橀泤闄嶇骇銆?- [x] `[T4.4]` `[ ]` `[M3-US2]` 纭繚 `python -m pytest tests/forensics/test_fund_flow_graph.py -v` 閫氳繃銆?
## 5. Milestone 3锛氭姤鍛婃暣鍚堬紙M3-US3锛?
**鐢ㄦ埛鏁呬簨**锛氭渶缁堟渚嬫姤鍛婄敓鎴?
- [x] `[T5.1]` `[ ]` `[M3-US3]` 浣跨敤 `fund_flow_graph.py` 鐢熸垚 1~3 涓祫閲戞祦鍥撅紙`.png` 鎴?`.dot`锛屽彲鐪熷疄鎴栧悎鎴愯竟鏁版嵁锛夈€?- [x] `[T5.2]` `[ ]` `[M3-US3]` 杩愯 `generate_report` 鐢熸垚 `forensics/v0.1_false_positive_report.md`銆?- [x] `[T5.3]` `[ ]` `[M3-US3]` 浜у嚭鏈€缁?`case_study_00X.md`锛屾暣鍚堝浘琛ㄣ€佸紓甯稿憡璀︿笌澶栭儴鏂伴椈鏃堕棿绾裤€?
## 6. Milestone 3锛氫釜浜鸿瘉鎹寘鎻愪氦锛圡3-US4锛?
**鐢ㄦ埛鏁呬簨**锛氫釜浜烘渶缁堟彁浜ゅ寘

- [x] `[T6.1]` `[ ]` `[M3-US4]` 鍒涘缓/濉啓 `forensics/Individual-Evidence-Pack-Milestone3.md`锛岄噰鐢?*浠呯储寮曟眹鎬?*鏂瑰紡锛屾眹鎬?M2 涓?M3 浜х墿閾炬帴銆?- [x] `[T6.2]` `[ ]` `[M3-US4]` 鍦?Evidence Pack 涓姞鍏ュ伐浠剁姸鎬佹槧灏勶紙璺緞銆佺敤閫斻€佸畬鎴愬害锛夛紝**涓嶉噸澶嶆挵鍐欐渚嬪垎鏋愭鏂?*銆?- [x] `[T6.3]` `[ ]` `[M3-US4]` 鍦?Evidence Pack 涓姞鍏ユ渶缁堟彁浜ゆ竻鍗曪紝骞舵牎楠?`forensics/` 涓嬭寮曠敤宸ヤ欢鍧囧瓨鍦ㄣ€?- [x] `[T6.4]` `[ ]` `[M3-US4]` 鎵ц鏈€缁堥獙璇侊細`python -m pytest tests/forensics/test_export_alerts.py tests/forensics/test_generate_fp_report.py tests/forensics/test_fund_flow_graph.py -v`锛屽苟鍦?Evidence Pack 璁板綍閫氳繃鎽樿銆?
