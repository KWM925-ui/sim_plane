# Activation Instruction For A Child Session

Send the following message to the child session when enabling supervisor mode:

```text
从这一轮开始进入外部 supervisor 模式，直到我明确解除为止。

每轮开始前，先按这个顺序完整读取并遵守：
1. `/home/coco/sim_plane/.supervisor/supervisor_ledger.md`
2. `/home/coco/sim_plane/.supervisor/state_machine.md`
3. `/home/coco/sim_plane/.supervisor/child_execution_protocol.md`
4. `/home/coco/sim_plane/.supervisor/round_self_checklist.md`

要求：
- 把 `supervisor_ledger.md` 当成当前 live source of truth
- 不准跳过 ledger 直接按记忆工作
- 不准回退到 ledger 已排除的候选集合
- 每轮结束前必须先按 checklist 自检，再更新 ledger，再输出本轮结果
- 在 ledger 没显式放行前，不准开新正式 run，不准写新补丁

现在先只做一件事：
先读取上述 4 个文件，然后用 4 行话复述：
1. 当前 locked facts
2. 当前 frontier
3. 当前 forbidden actions
4. 本轮 output shape

在这 4 行复述完成前，不要做别的。
```
