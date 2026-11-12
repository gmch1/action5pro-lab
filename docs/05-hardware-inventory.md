# 硬件信息采集

以下命令均为已启动系统中的只读采集。公开结果前应删除序列号、MAC 地址、IP、
分区哈希和绝对路径。

## SoC 与内核

```bash
adb shell cat /sys/devices/soc0/machine
adb shell cat /sys/devices/soc0/family
adb shell cat /sys/devices/soc0/soc_id
adb shell cat /sys/devices/soc0/revision
adb shell cat /sys/devices/soc0/chip_id
adb shell uname -a
```

本次设备识别为 Qualcomm QCS8550 系列，8 核 CPU。核是否在线应从
`/sys/devices/system/cpu/online` 和 `offline` 读取，不能把“当前在线核数”误写成
物理核心数。

```bash
adb shell cat /sys/devices/system/cpu/possible
adb shell cat /sys/devices/system/cpu/present
adb shell cat /sys/devices/system/cpu/online
adb shell cat /sys/devices/system/cpu/offline
adb shell cat /proc/cpuinfo
```

## 运行内存

```bash
adb shell cat /proc/meminfo
adb shell dmesg
adb shell cat /proc/swaps
```

要区分三个数字：

- 物理检测容量；
- Linux `MemTotal`；
- 当前 `MemAvailable`。

本次设备物理内存约 6 GB，但 Linux 仅管理约 2.8 GiB。启动日志显示大量内存被
reserved-memory 和 CMA 使用，其中约 2.7 GB 的 `dcam_region` 为不可复用相机
区域，推测用于 RAW 帧、HDR、多帧降噪、增稳/畸变校正、预览及编码流水线。

预留大小不等于每时每刻都已写满，但不可复用区域不会被普通 Linux 进程使用。
评估自定义转码程序时，应以 `MemAvailable` 和实际压力测试为准，而不是按标称
6 GB 预算。

## 内存使用者

```bash
adb shell ps -eo pid,comm,rss --sort=-rss
adb shell cat /sys/kernel/debug/dma_buf/bufinfo
adb shell find /sys/kernel/debug/cma -maxdepth 2 -type f
```

设备可能不支持完整 GNU `ps` 选项；必要时读取 `/proc/<PID>/status`。DMA-BUF、
CMA 和进程 RSS 是不同统计口径，不能直接相加得出物理占用。

## UFS 与容量

```bash
adb shell lsblk -b
adb shell cat /sys/block/sda/device/vendor
adb shell cat /sys/block/sda/device/model
adb shell cat /sys/block/sda/device/rev
adb shell blockdev --getsize64 /dev/sda
```

本次样机识别到 YMTC 64 GB UFS 2.2 TLC 器件。厂商标称 GB 使用十进制，Linux
常以 GiB 显示，因此约 64 GB 显示为约 59.6 GiB 是正常换算，不代表被“开卡”
限制。NAND 类型应以准确料号和厂商资料确认，不能通过可用容量猜测。
