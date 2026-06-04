import json
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONSOLE_RUN_ROOT = REPO_ROOT / "runs" / "console_commands"


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


CONSOLE_COMMANDS = [
    {
        "id": "platform_health",
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
        "category": "健康/总览",
        "title": "本机能力探测",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "doctor"],
        "description": "检查当前机器可用的 backend、adapter，并给出推荐运行路径。",
        "value": "把“这台机器现在能跑什么”说清楚，避免盲目点重仿真。",
        "when_to_use": "换机器、重启后、依赖不确定、PX4/ROS/Gazebo 不知道是否可用时。",
        "outputs": ["控制台日志"],
    },
    {
        "id": "artifact_hygiene_scan",
        "category": "健康/总览",
        "title": "artifact 卫生扫描",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "artifact-hygiene", "--artifact-root", "runs"],
        "description": "只扫描 runs/ 是否存在不完整、过期、未归档的目录，不执行删除。",
        "value": "保证实验结果目录不被垃圾文件污染，后续报告和 latest 选择更可靠。",
        "when_to_use": "跑完一批实验后，或者 dashboard 里看到奇怪 artifact 时。",
        "outputs": ["控制台日志"],
    },
    {
        "id": "manual_probe_hygiene_scan",
        "category": "健康/总览",
        "title": "manual probe 卫生扫描",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "manual-probe-hygiene", "--artifact-root", "runs"],
        "description": "只扫描 runs/manual_probes/ 中保留的人工探针证据，不执行删除。",
        "value": "把正式验收证据和人工探针证据区分清楚，避免互相污染。",
        "when_to_use": "做过手动可视化、前沿算法探针或临时验证后。",
        "outputs": ["控制台日志"],
    },
    {
        "id": "demo_takeoff",
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
        "category": "评测/KPI",
        "title": "基础扰动 suite",
        "risk": "会新建多个 artifact/report",
        "duration_hint": "中等",
        "command": ["python3", "-m", "sim_plane", "run-suite", "scenarios/basic_takeoff.json", "--artifact-root", "runs"],
        "description": "对 basic_takeoff 跑一组确定性扰动变体，并输出 KPI、因子影响和最差项。",
        "value": "从“能不能跑”升级到“扰动后表现变差多少”。",
        "when_to_use": "比较算法鲁棒性、检查噪声/dropout/限速等退化影响时。",
        "outputs": ["runs/suites/", "runs/basic_takeoff_*"],
    },
    {
        "id": "quadrotor_exam",
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
            "7",
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
        "category": "验收/回归",
        "title": "本机 autotest fast",
        "risk": "会新建 artifact/report",
        "duration_hint": "中等到较久",
        "command": ["python3", "-m", "sim_plane", "autotest-pack", "--profile", "fast", "--artifact-root", "runs"],
        "description": "运行本机 CI/autotest-like 快速包，组合 doctor、hygiene、live smoke、suite、fuzz、acceptance 等。",
        "value": "用一条命令覆盖平台最常用的自动复验链。",
        "when_to_use": "准备提交、长期优化收尾、或者需要一份综合复验证据时。",
        "outputs": ["runs/autotest/"],
    },
    {
        "id": "list_baselines",
        "category": "算法接入",
        "title": "查看内置 baseline",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-baselines"],
        "description": "列出当前平台内置、已标记 ready 的 baseline 算法入口。",
        "value": "让使用者知道不是空平台，可以先跑哪些标准算法/模板。",
        "when_to_use": "不知道先跑哪个算法、或准备接入自己的算法前。",
        "outputs": ["控制台日志"],
    },
    {
        "id": "list_backends",
        "category": "算法接入",
        "title": "查看 backend",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-backends"],
        "description": "列出当前注册的仿真 backend 及 readiness。",
        "value": "明确后端能力面，避免把不可用 backend 当可用。",
        "when_to_use": "选择 PX4 SIH、JSBSim、Gazebo Classic、MARSIM、EGO 等路径前。",
        "outputs": ["控制台日志"],
    },
    {
        "id": "list_adapters",
        "category": "算法接入",
        "title": "查看 adapter",
        "risk": "只读",
        "duration_hint": "很快",
        "command": ["python3", "-m", "sim_plane", "list-adapters"],
        "description": "列出当前注册的算法 adapter 及 readiness。",
        "value": "明确控制类、ROS 类、MAVSDK 等通用算法接入面。",
        "when_to_use": "准备接自己的控制或规划/感知算法前。",
        "outputs": ["控制台日志"],
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


def list_console_commands():
    rows = []
    for command in CONSOLE_COMMANDS:
        row = dict(command)
        row["command_display"] = command_display(row["command"])
        row["cli_command"] = sim_plane_subcommand(row["command"])
        row["executable"] = True
        rows.append(row)
    return rows


def get_console_command(command_id):
    for command in CONSOLE_COMMANDS:
        if command["id"] == command_id:
            row = dict(command)
            row["command_display"] = command_display(row["command"])
            row["cli_command"] = sim_plane_subcommand(row["command"])
            row["executable"] = True
            return row
    raise KeyError(command_id)


class ConsoleCommandRunner:
    def __init__(self, run_root=None, repo_root=None, commands=None):
        self.run_root = Path(run_root) if run_root is not None else DEFAULT_CONSOLE_RUN_ROOT
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self.commands = commands
        self.lock = threading.Lock()
        self.runs = {}

    def list_commands(self):
        if self.commands is None:
            return list_console_commands()
        rows = []
        for command in self.commands:
            row = dict(command)
            row["command_display"] = command_display(row["command"])
            row["cli_command"] = sim_plane_subcommand(row["command"])
            row["executable"] = True
            rows.append(row)
        return rows

    def get_command(self, command_id):
        if self.commands is None:
            return get_console_command(command_id)
        for command in self.commands:
            if command["id"] == command_id:
                row = dict(command)
                row["command_display"] = command_display(row["command"])
                row["cli_command"] = sim_plane_subcommand(row["command"])
                row["executable"] = True
                return row
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
                record["detected_outputs"] = detect_console_outputs(record["outputs"], self.repo_root)
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
                    "frontend_status": "covered",
                    "reason": "已有前端按钮: {0}".format(", ".join(button["title"] for button in buttons)),
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
            "hidden_count": len([row for row in rows if row["frontend_status"] == "hidden"]),
        },
        "rows": rows,
    }


def detect_console_outputs(output_patterns, repo_root):
    detected = []
    root = Path(repo_root)
    for output in output_patterns or []:
        if output == "控制台日志":
            continue
        pattern = str(output).rstrip("/")
        matches = sorted(root.glob(pattern), key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)
        for match in matches[:3]:
            detected.append(str(match))
    return detected
