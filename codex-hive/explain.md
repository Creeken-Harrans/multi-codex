# codex-hive 使用说明

这份文档按实际使用顺序介绍 `codex-hive`：先准备环境，再初始化仓库，然后执行一次任务，并说明每一步会生成什么文件、这些文件分别有什么意义。

## 1. 项目是做什么的

`codex-hive` 是一个面向代码仓库的多代理编排工具。你给它一句任务描述，例如：

```bash
codex-hive run "Implement feature with tests and docs" --repo-root .
```

它会做这些事：

- 把自然语言任务解析成 mission
- 生成任务 DAG 和执行策略
- 为可写任务创建独立 Git worktree
- 把任务分发给不同角色的 agent
- 汇总 reviewer 的 finding，做基础共识
- 把 worktree 里的改动提交后串行合并回主仓库
- 自动跑验证命令
- 产出一套可回看的 run artifacts

## 2. 使用前提

在使用 `run` 之前，需要满足这些条件：

- Python 版本至少是 3.11
- 系统里有 `git`
- 当前项目目录本身是一个 Git 仓库
- 这个 Git 仓库至少已经有一个 commit
- 如果要用真实 Codex 执行器，需要系统里有 `codex`

为什么必须先有 Git 仓库和初始 commit：

- `codex-hive` 对可写任务使用原生 `git worktree`
- 没有 commit 就没有稳定的基线可供 `worktree add`
- 合并阶段使用真实 Git commit 和 cherry-pick

## 3. 安装

进入项目目录：

```bash
cd /home/Creeken/Paper/codex-test/codex-hive
```

安装：

```bash
python3 -m pip install -e ".[dev]"
```

安装后可以验证 CLI：

```bash
codex-hive --help
```

这一步不会生成仓库内文件。它只会把 `codex-hive` 命令安装到当前 Python 环境。

## 4. 初始化仓库

在目标仓库里执行：

```bash
codex-hive init --repo-root .
```

如果你想看结构化输出：

```bash
codex-hive init --repo-root . --json
```

这一步会生成：

```text
.codex-hive/
  runs/
  worktrees/
codex-hive.toml
```

说明如下：

- `.codex-hive/runs/`
  用来存放每一次 run 的独立产物目录
- `.codex-hive/worktrees/`
  用来放写任务对应的 Git worktree
- `codex-hive.toml`
  仓库级配置文件

这一步还不会生成：

- `state.db`
- `events.jsonl`
- 任何具体 run 目录

这些要等真正执行 `run` 才会写入。

## 5. 先只看计划，不执行

如果你想先看 `codex-hive` 会怎么拆任务，可以执行：

```bash
codex-hive plan "Implement feature with tests and docs" --repo-root . --json
```

这一步不会创建 run 目录，也不会创建 worktree。它只是把计划打印出来。

你能看到的核心内容包括：

- `mission`
- `tasks`
- `strategy`
- `ownership`
- `notes`

其中：

- `mission` 是解析后的任务定义
- `tasks` 是具体任务列表
- `strategy` 是最终采用的策略
- `ownership` 表示路径所有权和并行风险

## 6. 执行一次完整 run

### 6.1 使用 fake adapter

如果你只是想验证编排链路是否工作，用 fake adapter：

```bash
codex-hive run "Implement feature with tests and docs" --repo-root . --adapter fake
```

这个模式适合：

- 本地冒烟
- 测试
- 演示 artifact 结构
- 不想真的调用 `codex` 的场景

### 6.2 使用真实 codex adapter

如果你希望真正调用 `codex exec`：

```bash
codex-hive run "Implement feature with tests and docs" --repo-root . --adapter codex
```

此时要求系统里能找到 `codex` 命令。

## 7. 一次 run 内部到底发生了什么

假设命令是：

```bash
codex-hive run "Implement feature with tests and docs" --repo-root . --adapter fake
```

执行流程可以理解为下面几个阶段。

### 阶段 1：解析任务

程序先把输入任务转成 `MissionSpec`。

这一阶段确定：

- mission 文本
- scope
- out_of_scope
- constraints
- deliverables
- acceptance_criteria
- risk_level

此时还没有 worker 开始执行。

### 阶段 2：生成计划

程序根据 mission 生成 `PlannerOutput`，其中包括：

- 任务列表 `tasks`
- 策略 `strategy`
- 所有权分析 `ownership`

默认情况下，任务通常会包含这些角色：

- planner
- scout
- architect
- implementer
- tester
- reviewer
- security_reviewer
- performance_reviewer
- maintainability_reviewer

如果是 bug/fix 类型任务，还可能生成竞争式实现分支。

### 阶段 3：建立 run 状态

程序会创建一个新的 run id，例如：

```text
run-1e228047ee
```

然后开始写入状态文件。

这一步通常会生成：

```text
.codex-hive/state.db
.codex-hive/events.jsonl
.codex-hive/runs/<run-id>/
```

其中：

- `.codex-hive/state.db`
  用 SQLite 记录 runs、tasks、executions
- `.codex-hive/events.jsonl`
  记录全局事件流
- `.codex-hive/runs/<run-id>/`
  当前 run 的专属产物目录

在 run 早期，run 目录里会先出现：

```text
.codex-hive/runs/<run-id>/
  run.json
  mission.json
  plan.json
```

说明如下：

- `run.json`
  当前 run 的总体状态快照
- `mission.json`
  解析后的 mission
- `plan.json`
  规划结果，包含 task DAG 和 strategy

### 阶段 4：创建 worktree

对于 `write_enabled=True` 的任务，程序会创建原生 Git worktree。

典型位置：

```text
.codex-hive/worktrees/<run-id>/<task-id>-<role>/
```

例如：

```text
.codex-hive/worktrees/run-abc123/impl-core-implementer/
```

这些 worktree 的作用是：

- 避免多个写任务直接改主工作区
- 给不同任务各自独立的 Git 上下文
- 让后续集成可以走真实 Git 流程

### 阶段 5：执行 worker

每个 task 会被封装成 `WorkerPromptEnvelope`，再交给 adapter 执行。

如果是 fake adapter：

- 它会在 worktree 里写入模拟文件
- 返回结构化 `WorkerResult`

如果是 codex adapter：

- 它会调用 `codex exec --json`
- 再把返回结果规整成 `WorkerResult`

这一阶段不会立刻生成所有最终文档，但会不断更新：

- `state.db` 中的 task 状态
- `events.jsonl` 中的事件流

同时在 run 结束时，每个 task 的结果会写成：

```text
.codex-hive/runs/<run-id>/tasks/<task-id>.json
```

例如：

```text
.codex-hive/runs/<run-id>/tasks/impl-core.json
.codex-hive/runs/<run-id>/tasks/test.json
```

这些文件记录单个任务的：

- role
- status
- summary
- files_changed
- commands_run
- tests_run
- findings
- confidence

### 阶段 6：共识与评审结果

当 reviewer 类任务完成后，程序会收集 finding 并做去重、评分和共识判断。

这一阶段会生成：

```text
.codex-hive/runs/<run-id>/consensus.json
```

里面通常包括：

- `findings`
- `debate_rounds`
- `blind_judge_summary`
- `overall_score`

这不是简单日志，而是汇总后的结构化评审结果。

### 阶段 7：集成与合并计划

当前实现里，集成不是“直接复制文件回主目录”，而是：

1. 在每个 worktree 内对变更做 Git commit
2. 在主仓库中按顺序 cherry-pick 这些 commit
3. 整个集成动作放在串行 Git lock 里执行

这一阶段会生成：

```text
.codex-hive/runs/<run-id>/merge-plan.json
```

里面记录：

- `branch_order`
- `merge_actions`
- `conflicts`
- `verification_required`

同时，主仓库自己的 Git 历史会新增集成 commit，例如：

```text
codex-hive: impl-core (implementer)
codex-hive: impl-docs (implementer)
codex-hive: test (tester)
```

注意，这些 commit 不在 artifact 目录里，而是在仓库本身的 Git 历史中。

### 阶段 8：验证

集成结束后，程序会自动探测当前仓库可运行的验证命令，例如：

- `pytest`
- `make test`
- `ruff check .`
- `mypy .`

它只会在仓库看起来支持这些工具时才尝试运行，不是只因为系统里装了命令就盲跑。

验证结果不会单独写成一个 JSON 文件，但会被写进最终报告。

### 阶段 9：Mission Keeper 检查

程序会检查：

- 有没有改到 scope 外路径
- 必选 acceptance item 是否被覆盖
- 有没有不合理的额外修改

这一阶段会生成：

```text
.codex-hive/runs/<run-id>/mission-check.json
```

里面主要有：

- `goal_alignment_score`
- `scope_violations`
- `missing_acceptance_items`
- `unjustified_extra_changes`
- `passed`

### 阶段 10：写最终报告

run 结束后，会补齐最终产物：

```text
.codex-hive/runs/<run-id>/
  run.json
  mission.json
  plan.json
  consensus.json
  merge-plan.json
  mission-check.json
  summary.md
  final-report.md
  events.jsonl
  tasks/
```

这些文件各自的作用：

- `run.json`
  最完整的机器可读总报告
- `mission.json`
  mission 定义
- `plan.json`
  任务拆分和策略
- `consensus.json`
  reviewer finding 的共识结果
- `merge-plan.json`
  集成顺序和操作说明
- `mission-check.json`
  目标一致性检查结果
- `summary.md`
  简短的人类可读摘要
- `final-report.md`
  更完整的人类可读报告
- `events.jsonl`
  当前 run 的专属事件流
- `tasks/*.json`
  每个 task 的执行结果

## 8. 如何查看结果

### 查看所有 run

```bash
codex-hive status --repo-root . --json
```

你会看到：

- `run_id`
- `status`
- `strategy`
- `mission`
- `artifacts_dir`

### 查看单个 run

```bash
codex-hive inspect <run-id> --repo-root . --json
```

它本质上读取的是：

```text
.codex-hive/runs/<run-id>/run.json
```

### 查看环境状态

```bash
codex-hive doctor --repo-root . --json
```

输出主要包含：

- `git_available`
- `codex_available`
- `config_found`
- `writable_state_dir`

## 9. resume / cancel / clean 是怎么工作的

### resume

```bash
codex-hive resume <run-id> --repo-root . --adapter fake
```

当前语义是：

- 已成功的 task 会从已有状态中恢复
- 未完成、失败、取消类 task 会重新进入待执行
- 然后重新继续整条编排链

它不是操作系统级别的“从上次子进程中断点恢复”，而是基于已落盘状态重新推进。

### cancel

```bash
codex-hive cancel <run-id> --repo-root .
```

这一步会做两件事：

- 把 SQLite 里的 run 状态标为 `cancelled`
- 在 run 目录里写入一个取消标记文件：

```text
.codex-hive/runs/<run-id>/cancelled
```

后续编排检测到这个标记后会停止继续推进。

### clean

```bash
codex-hive clean --repo-root .
```

这会删除整个：

```text
.codex-hive/
```

也就是：

- state.db
- 全局 events.jsonl
- 所有 runs
- 所有 worktrees

注意，这不会回滚已经合并进 Git 历史的 commit。

## 10. 常见命令组合

### 最常见的一套

```bash
codex-hive init --repo-root .
codex-hive run "Implement feature with tests and docs" --repo-root . --adapter fake
codex-hive status --repo-root . --json
codex-hive inspect <run-id> --repo-root . --json
```

### 只先看计划

```bash
codex-hive plan "Implement feature with tests and docs" --repo-root . --json
```

### 直接走 review 快捷入口

```bash
codex-hive review "Review branch for correctness and security" --repo-root .
```

### 竞争式修 bug

```bash
codex-hive run "Fix flaky bug" --repo-root . --strategy competitive-generation --adapter fake
```

## 11. 你最应该关心的几个目录

### `.codex-hive/runs/`

存放每一次任务执行的最终结果，是你排查 run 的第一入口。

### `.codex-hive/worktrees/`

存放写任务的独立工作树，是你排查写任务隔离、分支状态和中间文件的入口。

### `.codex-hive/state.db`

存放结构化状态，是 `status`、`resume` 等命令读取的核心状态源。

### `.codex-hive/events.jsonl`

存放所有 run 的全局事件流。适合做调试、追踪和后期分析。

## 12. 当前版本边界

当前项目已经能真实跑起来，但仍有这些边界：

- 任务规划仍然是启发式生成，不是复杂的智能规划器
- `resume` 已经能恢复已成功 task，但还不是“外部进程级精确断点续跑”
- 共识、judge、debate 已可用，但仍是轻量实现

如果你需要更深度开发，可以沿着下面几条继续扩展：

- 更强的 planner
- 更细的 merge/conflict 处理
- 更完整的 verifier artifact 输出
- 更强的 resume/checkpoint 机制
