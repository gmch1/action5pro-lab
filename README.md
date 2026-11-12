# Action5 Pro Lab

**Action5 Pro Lab**（建议仓库名：`action5pro-lab`）是专门面向
**DJI Osmo Action 5 Pro（AC204）** 的工程化扩展项目。它从 Qualcomm
9008/EDL 备份、A/B 槽判断和 FACTORY 启动验证开始，后续将继续实现家庭 Wi-Fi、
NAS 自动同步、充电时本地转码，以及相机设置界面扩展。

本项目只支持 Action 5 Pro，不是 DJI Action 系列或 QCS8550 设备的通用项目。
Action 4、其他 Action 型号、Pocket 系列以及其他厂商设备均不在支持范围内。

仓库的目标是记录**方法和证据链**，不是分发刷机包。仓库不包含：

- 原厂或修改后的固件、ABL、boot、devinfo、GPT 镜像；
- Firehose programmer/loader 本体；
- 设备序列号、USB 唯一标识和设备绑定哈希；
- Wi-Fi、NAS、局域网地址、密钥或个人文件；
- 本机使用的设备绑定写入工具。

## 已验证结论

- 设备基于 QCS8550/SM8550 平台，运行定制嵌入式 Linux，而非 Android 用户空间。
- 存储采用 A/B 槽；槽位必须从当前设备读取，不能按教程或分区名猜测。
- 实验机启动时活动槽为 B；A 槽保持原样作为恢复路径。这只是一次实机结论，不能套用到其他设备。
- FACTORY ABL 与工程状态组合可启动 FACTORY 模式并提供 root ADB。
- 系统包含 `wpa_supplicant`、`hostapd` 和 DHCP 客户端，硬件支持 STA/AP。
- 设备的 Linux 可见内存少于物理内存，主要原因是相机流水线等预留内存。

## 文档导航

1. [范围、安全边界与脱敏规则](docs/01-scope-and-safety.md)
2. [进入 9008 与只读备份](docs/02-edl-backup.md)
3. [A/B 槽的判断方法](docs/03-ab-slots.md)
4. [FACTORY 模式实验与恢复顺序](docs/04-factory-mode.md)
5. [CPU、内存、闪存等硬件信息采集](docs/05-hardware-inventory.md)
6. [Wi-Fi 与无线 ADB 调研](docs/06-network-and-adb.md)
7. [故障恢复清单](docs/07-recovery-runbook.md)
8. [项目边界、架构与路线图](docs/08-project-roadmap.md)
9. [解锁改动的字节级记录](docs/09-unlock-diff.md)
10. [参考资料与来源说明](REFERENCES.md)
11. [第三方工具与二进制说明](THIRD_PARTY.md)

## 仓库中的工具

`action5_edl.py` 是只读包装器，只允许以下 EDL 操作：

- `printgpt`：显示 GPT；
- `gpt`：导出 GPT 元数据；
- `rl`：按分区读取；
- `rs`：按明确扇区范围读取。

它拒绝写入、擦除、切槽和复位命令。所有输出默认进入已被 Git 忽略的本地目录。
EDL 客户端、Firehose programmer 和 FACTORY ABL 均为仓库外部输入，详见
`THIRD_PARTY.md`。

```bash
python3 action5_edl.py doctor \
  --edl-script <EDL_REPO>/edl.py \
  --loader <LOCAL_FIREHOSE_PROGRAMMER> \
  --python <VENV_PYTHON>

python3 action5_edl.py scan \
  --edl-script <EDL_REPO>/edl.py \
  --loader <LOCAL_FIREHOSE_PROGRAMMER> \
  --python <VENV_PYTHON>

python3 action5_edl.py backup \
  --edl-script <EDL_REPO>/edl.py \
  --loader <LOCAL_FIREHOSE_PROGRAMMER> \
  --python <VENV_PYTHON>
```

## 测试

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile action5_edl.py
```

## 重要提醒

9008 能绕过正常系统读取底层存储，也能在使用错误命令时破坏启动链。本文档不是通用刷机包：不同固件版本、硬件批次和活动槽可能不同。执行任何写入前，必须重新读取当前设备 GPT、完整备份目标分区、计算哈希并准备经过验证的恢复路径。
