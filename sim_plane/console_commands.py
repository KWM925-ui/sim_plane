import json
import os
import shlex
import subprocess
import threading
import time
import glob
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONSOLE_RUN_ROOT = REPO_ROOT / "runs" / "console_commands"
CONSOLE_RUN_LOG_OUTPUTS = [
    "runs/console_commands/<run_id>/output.log",
    "runs/console_commands/<run_id>/record.json",
]

REPORT_ROOT_SUFFIX_BY_CLI = {
    "platform-health": "platform_health",
    "live-smoke": "live_smoke",
    "run-suite": "suites",
    "quadrotor-exam": "suites",
    "platform-acceptance": "platform_acceptance",
    "quadrotor-exam-acceptance": "quadrotor_exam_acceptance",
    "px4-failure-acceptance": "px4_failure_injection_acceptance",
    "autotest-pack": "autotest",
    "check-algorithm-ingress": "algorithm_ingress",
    "scenario-fuzz": "scenario_fuzz",
}


def utc_timestamp_for_path():
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def utc_timestamp_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def command_display(argv):
    return shlex.join([str(item) for item in argv])


def sim_plane_subcommand(command):
    argv = list(command)
    if len(argv) >= 4 and argv[:3] == ["python3", "-m", "sim_plane"]:
        return argv[3]
    if len(argv) >= 2 and argv[0] == "sim-plane":
        return argv[1]
    return ""


WORKFLOW_META = {
    "orientation": {
        "workflow": "1 基础确认",
        "workflow_goal": "先确认这台机器、当前仓库和已有证据是否可信。",
        "workflow_order": 10,
    },
    "fresh_run": {
        "workflow": "2 Fresh 运行",
        "workflow_goal": "重新启动一条真实运行链，证明当前代码还能跑起来。",
        "workflow_order": 20,
    },
    "kpi_evaluation": {
        "workflow": "3 KPI 评测",
        "workflow_goal": "批量跑固定任务或扰动，输出可比较的指标和最差 case。",
        "workflow_order": 30,
    },
    "regression": {
        "workflow": "4 回归验收",
        "workflow_goal": "读取已有 artifact/report，对照冻结 reference 判断是否退化。",
        "workflow_order": 40,
    },
    "algorithm_ingress": {
        "workflow": "5 算法接入",
        "workflow_goal": "查看或运行标准算法入口，先验证接口再接复杂算法。",
        "workflow_order": 50,
    },
}


EVIDENCE_META = {
    "read_only": {
        "evidence_type": "只读检查",
        "freshness": "CLI 本体不启动仿真，不新建正式 artifact；从前端运行时仍会写 console 日志。",
        "concurrency_policy": "可与普通阅读并行；不要和正在写 runs/ 的卫生扫描结论混用。",
    },
    "fresh_artifact": {
        "evidence_type": "Fresh 运行证据",
        "freshness": "会重新跑场景并新建 artifact/report。",
        "concurrency_policy": "建议单独运行；运行中不要同时点 hygiene、health、acceptance。",
    },
    "latest_artifact_check": {
        "evidence_type": "历史证据回归",
        "freshness": "读取已有 latest artifact/report，不重新跑仿真。",
        "concurrency_policy": "不要和正在写 runs/ 的长任务并行，否则 latest 选择可能读到中间状态。",
    },
    "artifact_scan": {
        "evidence_type": "artifact 卫生扫描",
        "freshness": "扫描已有 runs/ 目录，不启动仿真，不删除 artifact。",
        "concurrency_policy": "不要和正在写 runs/ 的长任务并行，否则可能把正在生成的 artifact 误判为不完整。",
    },
    "mixed_autotest": {
        "evidence_type": "混合一键复验",
        "freshness": "既会新建 artifact/report，也会读取已有证据做回归检查。",
        "concurrency_policy": "必须单独运行；它本身包含 hygiene/acceptance，不能和其它写 runs/ 任务并发。",
    },
}


CONSOLE_COMMANDS = [
    {
        "id": "platform_health",
        "workflow_id": "orientation",
        "evidence_id": "latest_artifact_check",
        "category": "健康/总览",
        "title": "平台总健康检查",
        "risk": "读取现有证据并写健康报告",
        "duration_hint": "通常几十秒内",
        "command": ["python3", "-m", "sim_plane", "platform-health", "--artifact-root", "runs"],
        "description": "聚合 git 状态、doctor、artifact 卫生、latest acceptance、suite/fuzz/flight-log/autotest 摘要。",
        "value": "用来判断当前平台是否干净、哪些证据最新、有没有非功能性风险。",
        "when_to_use": "每次长时间优化前后、关机前、或者你觉得平台状态混乱时先点它。",
        "outputs": ["runs/platform_health/"],
    },
    {
        "id": "doctor",
        "workflow_id": "orientation",
        "evidence_id": "read_only",
        "category": "健康/总览",
        "title": "本机能力探测",
        "risk": "CLI 只读，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "doctor"],
        "description": "检查当前机器可用的 backend、adapter，并给出推荐运行路径。",
        "value": "把“这台机器现在能跑什么”说清楚，避免盲目点重仿真。",
        "when_to_use": "换机器、重启后、依赖不确定、PX4/ROS/Gazebo 不知道是否可用时。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
    {
        "id": "artifact_hygiene_scan",
        "workflow_id": "orientation",
        "evidence_id": "artifact_scan",
        "category": "健康/总览",
        "title": "artifact 卫生扫描",
        "risk": "只扫描 runs/，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "artifact-hygiene", "--artifact-root", "runs"],
        "description": "只扫描 runs/ 是否存在不完整、过期、未归档的目录，不执行删除。",
        "value": "保证实验结果目录不被垃圾文件污染，后续报告和 latest 选择更可靠。",
        "when_to_use": "跑完一批实验后，或者 dashboard 里看到奇怪 artifact 时。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
    {
        "id": "manual_probe_hygiene_scan",
        "workflow_id": "orientation",
        "evidence_id": "artifact_scan",
        "category": "健康/总览",
        "title": "manual probe 卫生扫描",
        "risk": "只扫描 runs/manual_probes/，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "manual-probe-hygiene", "--artifact-root", "runs"],
        "description": "只扫描 runs/manual_probes/ 中保留的人工探针证据，不执行删除。",
        "value": "把正式验收证据和人工探针证据区分清楚，避免互相污染。",
        "when_to_use": "做过手动可视化、前沿算法探针或临时验证后。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
    {
        "id": "demo_takeoff",
        "workflow_id": "fresh_run",
        "evidence_id": "fresh_artifact",
        "category": "运行/轻量",
        "title": "轻量 demo 起飞",
        "risk": "会新建 artifact",
        "duration_hint": "很快",
        "command": [
            "python3",
            "-m",
            "sim_plane",
            "run",
            "scenarios/basic_takeoff.json",
            "--artifact-root",
            "runs",
            "--no-hold-open",
        ],
        "description": "运行内置 demo backend 的 basic_takeoff 场景，不启动第二个 dashboard。",
        "value": "最快验证 runner、artifact、KPI、dashboard 回放链路是否通。",
        "when_to_use": "第一次试平台、改了通用 runner/evaluation/dashboard 后先点它。",
        "outputs": ["runs/basic_takeoff_*"],
    },
    {
        "id": "live_smoke_fast",
        "workflow_id": "fresh_run",
        "evidence_id": "fresh_artifact",
        "category": "运行/轻量",
        "title": "一键 live smoke fast",
        "risk": "会新建 artifact/report",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "live-smoke", "--profile", "fast", "--artifact-root", "runs"],
        "description": "运行最快的 fresh smoke suite，证明重启后真实运行链还能起。",
        "value": "比只看历史 acceptance 更可靠，因为它会重新跑一条 fresh 链。",
        "when_to_use": "开机后、代码变更后、正式跑重任务前。",
        "outputs": ["runs/live_smoke/", "runs/basic_takeoff_*"],
    },
    {
        "id": "run_suite_basic",
        "workflow_id": "kpi_evaluation",
        "evidence_id": "fresh_artifact",
        "category": "评测/KPI",
        "title": "基础扰动 suite",
        "risk": "会新建多个 artifact/report",
        "duration_hint": "中等",
        "command": [
            "python3",
            "-m",
            "sim_plane",
            "run-suite",
            "scenarios/basic_takeoff.json",
            "--suite",
            "configs/demo_degradation_suite.json",
            "--artifact-root",
            "runs",
        ],
        "description": "对 basic_takeoff 跑一组确定性扰动变体，并输出 KPI、因子影响和最差项。",
        "value": "从“能不能跑”升级到“扰动后表现变差多少”。",
        "when_to_use": "比较算法鲁棒性、检查噪声/dropout/限速等退化影响时。",
        "outputs": ["runs/suites/", "runs/basic_takeoff_*"],
    },
    {
        "id": "quadrotor_exam",
        "workflow_id": "kpi_evaluation",
        "evidence_id": "fresh_artifact",
        "category": "评测/KPI",
        "title": "四旋翼标准考试",
        "risk": "会新建多个 artifact/report",
        "duration_hint": "中等到较久",
        "command": ["python3", "-m", "sim_plane", "quadrotor-exam", "--artifact-root", "runs"],
        "description": "运行论文/项目式四旋翼标准场景集，输出成功率、耗时、轨迹、速度、加速度、平滑性等 KPI。",
        "value": "形成可以反复复现实验结果的标准考试卷。",
        "when_to_use": "算法阶段性完成、需要拿一套完整指标评估时。",
        "outputs": ["runs/suites/", "runs/basic_takeoff_*"],
    },
    {
        "id": "scenario_fuzz_basic",
        "workflow_id": "kpi_evaluation",
        "evidence_id": "fresh_artifact",
        "category": "评测/KPI",
        "title": "基础场景 fuzz",
        "risk": "会新建多个 artifact/report",
        "duration_hint": "中等",
        "command": [
            "python3",
            "-m",
            "sim_plane",
            "scenario-fuzz",
            "scenarios/basic_takeoff.json",
            "--profile",
            "demo_fast",
            "--seed",
            "20260528",
            "--variants",
            "6",
            "--artifact-root",
            "runs",
        ],
        "description": "确定性扫一组场景参数，自动找 KPI 最差 case。",
        "value": "帮助发现人工挑场景时看不到的脆弱组合。",
        "when_to_use": "算法看起来能跑，但你想知道它在哪些参数下最容易变差时。",
        "outputs": ["runs/scenario_fuzz/", "runs/basic_takeoff_*"],
    },
    {
        "id": "platform_acceptance_latest",
        "workflow_id": "regression",
        "evidence_id": "latest_artifact_check",
        "category": "验收/回归",
        "title": "平台 latest 回归验收",
        "risk": "读取现有 artifact，写 report",
        "duration_hint": "较快",
        "command": ["python3", "-m", "sim_plane", "platform-acceptance", "--latest", "--artifact-root", "runs"],
        "description": "用现有 latest artifact 对照冻结 reference 检查平台主基线是否退化。",
        "value": "回答“平台主线有没有退化”。它不重新跑仿真。",
        "when_to_use": "清理、重构、改 backend/adapter 后确认没破坏主基线。",
        "outputs": ["runs/platform_acceptance/"],
    },
    {
        "id": "quadrotor_exam_acceptance_latest",
        "workflow_id": "regression",
        "evidence_id": "latest_artifact_check",
        "category": "验收/回归",
        "title": "四旋翼考试 latest 验收",
        "risk": "读取现有 report，写 report",
        "duration_hint": "较快",
        "command": ["python3", "-m", "sim_plane", "quadrotor-exam-acceptance", "--latest", "--artifact-root", "runs"],
        "description": "检查最新四旋翼考试报告是否相对冻结 reference 退化。",
        "value": "回答“标准考试成绩是否变差”。它不重新跑考试。",
        "when_to_use": "跑完 quadrotor-exam 后，或者比较新旧版本考试成绩时。",
        "outputs": ["runs/quadrotor_exam_acceptance/"],
    },
    {
        "id": "px4_failure_acceptance_latest",
        "workflow_id": "regression",
        "evidence_id": "latest_artifact_check",
        "category": "验收/回归",
        "title": "PX4 原生故障验收",
        "risk": "读取现有 artifact，写 report",
        "duration_hint": "较快",
        "command": ["python3", "-m", "sim_plane", "px4-failure-acceptance", "--latest", "--artifact-root", "runs"],
        "description": "验证 PX4-native failure injection acceptance surface 的 latest 证据。",
        "value": "只证明平台中已正式接入的 PX4 原生故障面，不冒充传感器物理高保真故障。",
        "when_to_use": "改 PX4 failure adapter、failure matrix 或相关报告后。",
        "outputs": ["runs/px4_failure_injection_acceptance/"],
    },
    {
        "id": "autotest_fast",
        "workflow_id": "regression",
        "evidence_id": "mixed_autotest",
        "category": "验收/回归",
        "title": "本机 autotest fast",
        "risk": "会新建 artifact/report",
        "duration_hint": "中等到较久",
        "command": ["python3", "-m", "sim_plane", "autotest-pack", "--profile", "fast", "--artifact-root", "runs"],
        "description": "运行本机 CI/autotest-like 快速包，组合 doctor、hygiene、live smoke、suite、fuzz、acceptance 等。",
        "value": "用一条命令覆盖平台最常用的自动复验链。",
        "when_to_use": "准备提交、长期优化收尾、或者需要一份综合复验证据时。",
        "outputs": [
            "runs/autotest/",
            "runs/live_smoke/",
            "runs/basic_takeoff_*",
            "runs/suites/",
            "runs/scenario_fuzz/",
            "runs/flight_log_analysis/",
            "runs/px4_failure_injection_acceptance/",
            "runs/platform_acceptance/",
        ],
    },
    {
        "id": "list_baselines",
        "workflow_id": "algorithm_ingress",
        "evidence_id": "read_only",
        "category": "算法接入",
        "title": "查看内置 baseline",
        "risk": "CLI 只读，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-baselines"],
        "description": "列出当前平台内置、已标记 ready 的 baseline 算法入口。",
        "value": "让使用者知道不是空平台，可以先跑哪些标准算法/模板。",
        "when_to_use": "不知道先跑哪个算法、或准备接入自己的算法前。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
    {
        "id": "run_baseline_pid_demo",
        "workflow_id": "algorithm_ingress",
        "evidence_id": "fresh_artifact",
        "category": "算法接入",
        "title": "运行 demo PID baseline",
        "risk": "会新建 artifact",
        "duration_hint": "很快",
        "command": [
            "python3",
            "-m",
            "sim_plane",
            "run-baseline",
            "pid_position_demo",
            "--artifact-root",
            "runs",
            "--no-hold-open",
        ],
        "description": "运行 baseline 目录中已标记 ready 的 pid_position_demo。它只代表这个最轻 baseline，不代表所有 planned baseline 都能跑。",
        "value": "给自定义算法提供一个最轻的同场景参照物，先看平台指标和报告长什么样。",
        "when_to_use": "准备比较自己的控制算法前，先跑一条确定性 baseline。",
        "outputs": ["runs/basic_takeoff_*"],
    },
    {
        "id": "check_ingress_px4_external_template",
        "workflow_id": "algorithm_ingress",
        "evidence_id": "fresh_artifact",
        "category": "算法接入",
        "title": "PX4 external_command 体检",
        "risk": "会启动 PX4 SIH 并新建 artifact；控制台打印体检报告",
        "duration_hint": "中等到较久",
        "command": [
            "python3",
            "-m",
            "sim_plane",
            "check-algorithm-ingress",
            "--scenario",
            "scenarios/px4_sih_quadx_external_command_template.json",
            "--artifact-root",
            "runs",
        ],
        "description": "按现有 PX4 SIH external_command 模板跑一次接入体检，检查进程、telemetry、控制输出、adapter 状态和 KPI。",
        "value": "把“算法有没有真正接进平台”变成可复查报告，而不是只看屏幕有没有动。",
        "when_to_use": "接 MAVSDK/MAVROS/MAVLink/普通控制程序前，先用模板确认平台侧入口没问题。",
        "outputs": ["runs/algorithm_ingress/latest_ingress_check_scenario.json", "runs/px4_sih_quadx_external_command_template_*"],
    },
    {
        "id": "list_backends",
        "workflow_id": "algorithm_ingress",
        "evidence_id": "read_only",
        "category": "算法接入",
        "title": "查看 backend",
        "risk": "CLI 只读，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-backends"],
        "description": "列出当前注册的仿真 backend 及 readiness。",
        "value": "明确后端能力面，避免把不可用 backend 当可用。",
        "when_to_use": "选择 PX4 SIH、JSBSim、Gazebo Classic、MARSIM、EGO 等路径前。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
    {
        "id": "list_adapters",
        "workflow_id": "algorithm_ingress",
        "evidence_id": "read_only",
        "category": "算法接入",
        "title": "查看 adapter",
        "risk": "CLI 只读，会写 console 日志",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-adapters"],
        "description": "列出当前注册的算法 adapter 及 readiness。",
        "value": "明确控制类、ROS 类、MAVSDK 等通用算法接入面。",
        "when_to_use": "准备接自己的控制或规划/感知算法前。",
        "outputs": CONSOLE_RUN_LOG_OUTPUTS,
    },
]


HIDDEN_CLI_COMMANDS = {
    "serve": "当前页面本身就是 serve 的结果，不需要在页面里再启动一个 serve。",
    "show-scenario": "需要一个场景路径参数，适合做成后续场景浏览/详情页，而不是固定按钮。",
    "generate-scenario": "需要用户填写 adapter、命令、后端、输出路径等参数，后续应做成算法接入向导。",
    "check-algorithm-ingress": "需要用户填写自己的算法命令或场景，后续应做成算法接入体检向导。",
    "run-baseline": "需要选择 baseline 名称，后续应和 baseline 列表合成一个可选运行入口。",
    "flight-log-analyze": "需要选择 artifact 或 .ulg 文件，后续应从 artifact 详情页触发。",
    "planner-acceptance": "低层 planner baseline 验收，当前由 platform-health/platform-acceptance 间接覆盖，默认不露出。",
}


def list_console_commands(artifact_root=None, repo_root=None):
    rows = []
    for command in CONSOLE_COMMANDS:
        rows.append(enrich_console_command(command, artifact_root=artifact_root, repo_root=repo_root))
    return rows


def get_console_command(command_id, artifact_root=None, repo_root=None):
    for command in CONSOLE_COMMANDS:
        if command["id"] == command_id:
            return enrich_console_command(command, artifact_root=artifact_root, repo_root=repo_root)
    raise KeyError(command_id)


def enrich_console_command(command, artifact_root=None, repo_root=None):
    row = dict(command)
    if artifact_root is not None:
        root_text = artifact_root_for_command(artifact_root, repo_root or REPO_ROOT)
        row["command"] = rewrite_artifact_root_args(row["command"], root_text)
        row["command"] = rewrite_report_root_args(row["command"], root_text)
        row["outputs"] = rewrite_artifact_root_outputs(row.get("outputs", []), root_text)
    workflow = WORKFLOW_META.get(row.get("workflow_id"), WORKFLOW_META["orientation"])
    evidence = EVIDENCE_META.get(row.get("evidence_id"), EVIDENCE_META["read_only"])
    row["workflow_id"] = row.get("workflow_id", "orientation")
    row["evidence_id"] = row.get("evidence_id", "read_only")
    row.update(workflow)
    row.update(evidence)
    row["command_display"] = command_display(row["command"])
    row["cli_command"] = sim_plane_subcommand(row["command"])
    row["executable"] = True
    return row


def artifact_root_for_command(artifact_root, repo_root):
    root = Path(artifact_root).resolve()
    repo = Path(repo_root).resolve()
    try:
        relative = root.relative_to(repo)
    except ValueError:
        return str(root)
    return str(relative) if str(relative) != "." else "."


def rewrite_artifact_root_args(argv, root_text):
    rewritten = []
    index = 0
    while index < len(argv):
        value = argv[index]
        rewritten.append(value)
        if value == "--artifact-root" and index + 1 < len(argv):
            rewritten.append(root_text)
            index += 2
            continue
        index += 1
    return rewritten


def rewrite_report_root_args(argv, root_text):
    rewritten = []
    cli_command = sim_plane_subcommand(argv)
    report_root = report_root_for_command(cli_command, root_text)
    if report_root is None:
        return list(argv)
    index = 0
    replaced = False
    while index < len(argv):
        value = argv[index]
        rewritten.append(value)
        if value == "--report-root" and index + 1 < len(argv):
            rewritten.append(report_root)
            index += 2
            replaced = True
            continue
        index += 1
    if not replaced:
        rewritten.extend(["--report-root", report_root])
    return rewritten


def report_root_for_command(cli_command, root_text):
    suffix = REPORT_ROOT_SUFFIX_BY_CLI.get(cli_command)
    if suffix is None:
        return None
    root = Path(root_text)
    return str(root / suffix)


def rewrite_artifact_root_outputs(outputs, root_text):
    rewritten = []
    for output in outputs or []:
        text = str(output)
        if text == "runs":
            rewritten.append(root_text)
        elif text.startswith("runs/"):
            rewritten.append(root_text.rstrip("/") + "/" + text[len("runs/") :])
        else:
            rewritten.append(output)
    return rewritten


class ConsoleCommandRunner:
    def __init__(self, run_root=None, repo_root=None, commands=None):
        self.run_root = Path(run_root) if run_root is not None else DEFAULT_CONSOLE_RUN_ROOT
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self.commands = commands
        self.lock = threading.Lock()
        self.runs = {}

    def list_commands(self):
        artifact_root = infer_console_artifact_root(self.run_root, self.repo_root)
        if self.commands is None:
            return list_console_commands(artifact_root=artifact_root, repo_root=self.repo_root)
        rows = []
        for command in self.commands:
            rows.append(enrich_console_command(command, artifact_root=artifact_root, repo_root=self.repo_root))
        return rows

    def get_command(self, command_id):
        artifact_root = infer_console_artifact_root(self.run_root, self.repo_root)
        if self.commands is None:
            return get_console_command(command_id, artifact_root=artifact_root, repo_root=self.repo_root)
        for command in self.commands:
            if command["id"] == command_id:
                return enrich_console_command(command, artifact_root=artifact_root, repo_root=self.repo_root)
        raise KeyError(command_id)

    def start(self, command_id):
        command = self.get_command(command_id)
        with self.lock:
            active = [run for run in self.runs.values() if run["status"] == "running"]
            if active:
                raise RuntimeError("another console command is already running: {0}".format(active[0]["run_id"]))
            self.run_root.mkdir(parents=True, exist_ok=True)
            run_id = "{0}_{1}".format(command_id, utc_timestamp_for_path())
            run_dir = self.run_root / run_id
            suffix = 1
            while run_dir.exists():
                suffix += 1
                run_id = "{0}_{1}_{2}".format(command_id, utc_timestamp_for_path(), suffix)
                run_dir = self.run_root / run_id
            run_dir.mkdir(parents=True)
            record = {
                "run_id": run_id,
                "command_id": command_id,
                "title": command["title"],
                "category": command["category"],
                "workflow": command.get("workflow"),
                "workflow_id": command.get("workflow_id"),
                "evidence_type": command.get("evidence_type"),
                "evidence_id": command.get("evidence_id"),
                "freshness": command.get("freshness"),
                "concurrency_policy": command.get("concurrency_policy"),
                "risk": command["risk"],
                "cli_command": command.get("cli_command") or sim_plane_subcommand(command["command"]),
                "command": command["command"],
                "command_display": command["command_display"],
                "cwd": str(self.repo_root),
                "run_dir": str(run_dir),
                "log_path": str(run_dir / "output.log"),
                "record_path": str(run_dir / "record.json"),
                "status": "running",
                "return_code": None,
                "started_at_utc": utc_timestamp_iso(),
                "finished_at_utc": None,
                "outputs": command.get("outputs", []),
                "detected_outputs": [],
            }
            self.runs[run_id] = record
            self._write_record(record)
            thread = threading.Thread(target=self._run_command, args=(run_id,), daemon=True)
            thread.start()
            return dict(record)

    def list_runs(self, limit=20):
        rows = []
        with self.lock:
            rows.extend(dict(run) for run in self.runs.values())
        for path in sorted(self.run_root.glob("*/record.json"), key=lambda item: item.parent.name, reverse=True):
            if len(rows) >= limit:
                break
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if record["run_id"] not in {row["run_id"] for row in rows}:
                rows.append(record)
        rows.sort(key=lambda row: row.get("started_at_utc") or "", reverse=True)
        return rows[: max(int(limit), 0)]

    def get_run(self, run_id):
        with self.lock:
            if run_id in self.runs:
                return dict(self.runs[run_id])
        record_path = self.run_root / str(run_id) / "record.json"
        if not record_path.exists():
            raise KeyError(run_id)
        return json.loads(record_path.read_text(encoding="utf-8"))

    def get_log(self, run_id, tail_bytes=20000):
        record = self.get_run(run_id)
        path = Path(record["log_path"])
        if not path.exists():
            return ""
        with path.open("rb") as handle:
            if tail_bytes > 0:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(size - int(tail_bytes), 0), os.SEEK_SET)
            raw = handle.read()
        return raw.decode("utf-8", errors="replace")

    def _run_command(self, run_id):
        with self.lock:
            record = dict(self.runs[run_id])
        log_path = Path(record["log_path"])
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        output_snapshot = snapshot_console_outputs(record["outputs"], self.repo_root)
        with log_path.open("w", encoding="utf-8") as log:
            log.write("$ {0}\n\n".format(record["command_display"]))
            log.flush()
            try:
                process = subprocess.Popen(
                    record["command"],
                    cwd=str(self.repo_root),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                )
                return_code = process.wait()
                record["return_code"] = return_code
                record["status"] = "passed" if return_code == 0 else "failed"
            except Exception as exc:  # broad by design: preserve command record/log for UI diagnostics
                log.write("\nconsole command failed before completion: {0}\n".format(exc))
                record["return_code"] = None
                record["status"] = "failed"
                record["error"] = str(exc)
            finally:
                record["finished_at_utc"] = utc_timestamp_iso()
                record["detected_outputs"] = detect_console_outputs(record["outputs"], self.repo_root, output_snapshot)
                log.flush()
        with self.lock:
            self.runs[run_id] = record
            self._write_record(record)

    def _write_record(self, record):
        path = Path(record["record_path"])
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_cli_coverage(cli_commands):
    button_by_cli = {}
    for command in list_console_commands():
        cli_command = command.get("cli_command")
        if cli_command:
            button_by_cli.setdefault(cli_command, []).append(command)
    rows = []
    for cli_command in sorted(cli_commands):
        buttons = button_by_cli.get(cli_command, [])
        if buttons:
            rows.append(
                {
                    "cli_command": cli_command,
                    "frontend_status": "fixed_preset",
                    "reason": "已有固定前端入口，但不是完整参数面: {0}".format(", ".join(button["title"] for button in buttons)),
                    "button_ids": [button["id"] for button in buttons],
                }
            )
        else:
            rows.append(
                {
                    "cli_command": cli_command,
                    "frontend_status": "hidden",
                    "reason": HIDDEN_CLI_COMMANDS.get(cli_command, "后端已有能力，但当前前端没有固定入口。"),
                    "button_ids": [],
                }
            )
    return {
        "summary": {
            "cli_command_count": len(cli_commands),
            "covered_count": len([row for row in rows if row["frontend_status"] == "covered"]),
            "fixed_preset_count": len([row for row in rows if row["frontend_status"] == "fixed_preset"]),
            "hidden_count": len([row for row in rows if row["frontend_status"] == "hidden"]),
            "scope": "CLI subcommand-level fixed-entry coverage, not full parameter coverage",
        },
        "rows": rows,
    }


def infer_console_artifact_root(run_root, repo_root):
    root = Path(run_root)
    if root.name == "console_commands":
        return root.parent
    return Path(repo_root) / "runs"


def snapshot_console_outputs(output_patterns, repo_root):
    snapshot = {}
    for output in output_patterns or []:
        if is_console_run_log_output(output):
            continue
        for match in iter_console_output_matches(output, repo_root):
            try:
                snapshot[str(match)] = console_output_signature(match)
            except OSError:
                continue
    return snapshot


def detect_console_outputs(output_patterns, repo_root, previous_snapshot=None):
    detected = []
    previous_snapshot = previous_snapshot or {}
    for output in output_patterns or []:
        if is_console_run_log_output(output):
            continue
        matches = []
        for match in iter_console_output_matches(output, repo_root):
            try:
                signature = console_output_signature(match)
            except OSError:
                continue
            previous_signature = previous_snapshot.get(str(match))
            if previous_signature is None or signature != previous_signature:
                matches.append((match, signature[0]))
        matches.sort(key=lambda item: item[1], reverse=True)
        for match in matches[:3]:
            detected.append(str(match[0]))
    return detected


def is_console_run_log_output(output):
    text = str(output)
    return output == "控制台日志" or "/console_commands/<run_id>/" in text or text.startswith("runs/console_commands/<run_id>/")


def iter_console_output_matches(output, repo_root):
    pattern = str(output).rstrip("/")
    if not pattern:
        return []
    if Path(pattern).is_absolute():
        return [Path(match) for match in glob.glob(pattern)]
    return list(Path(repo_root).glob(pattern))


def console_output_signature(path):
    stat = Path(path).stat()
    return (stat.st_mtime_ns, stat.st_size, "dir" if Path(path).is_dir() else "file")
