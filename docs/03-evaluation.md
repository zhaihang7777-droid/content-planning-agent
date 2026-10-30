# 评估与复现

本地运行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tests/run_examples.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tests/run_deepseek_examples.py
```

当前单元测试15项通过，离线场景11项通过。examples根目录包含正常、缺预算、缺截止时间、无可行预算、超预算调整、工具失败、保存失败、重复、恢复、截止时间和调用上限证据；summary.json列出实际结果。

真实模型为DeepSeek官方接口deepseek-flash，业务工具仍为本地合成工具。examples/deepseek包含normal、budget、failure、time_short的实际输入、注入故障、时钟和Trace。结果以文件中的status及工具结果为准，不将模型口头成功作为证据。真实模型输出具有不确定性，重跑不保证相同路径。

时间案例使用固定时钟隔离模拟工具耗时与模型推理延迟，不证明真实50秒端到端完成。默认CLI采用实时钟，并在每次工具执行前检查剩余时间；推理等待过长会导致未完成。

本地重复与恢复、中断回滚均有单元测试；不保证外部服务恰好一次执行。不使用历史Gemini超时记录作为当前模型通过依据。

## 本次最终核对

15项单元测试、11个离线场景通过。更新保存方案结构后，四个DeepSeek真实场景重新执行并核对通过：normal费用12；budget、failure、time_short费用8。均确认completed、成功保存记录、完整活动方案及费用一致，汇总见examples/deepseek/summary.json。

复测中预算场景曾被模型误判为failed，时间场景曾因检索无结果返回needs_input；随后复测通过。这说明真实模型仍有随机性，不能承诺每次运行成功。工具状态和费用校验提供保守失败边界，不将失败伪装成功。JSON有效性、本地文档链接与交付目录密钥扫描通过。临时数据库和缓存已清理。
