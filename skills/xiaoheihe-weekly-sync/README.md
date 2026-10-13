# xiaoheihe-weekly-sync

定位指定期号或最新的 B 站周报，保留图文，按文章类型去重，核对小黑盒账号及社区后发布并回读。

Agent 执行说明见 [SKILL.md](SKILL.md)。

## 测试

回归测试在本 skill 的 `tests/` 下，改 `scripts/` 后建议跑一遍：

```bash
python3 tests/test_fetch_weekly.py   # 期号定位、作者校验、manifest 不可变
node tests/test_dedup.cjs            # 文章/视频去重判定
```
