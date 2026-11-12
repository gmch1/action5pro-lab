# 解锁改动的字节级记录

本文只描述本次 Action 5 Pro（AC204）样机上已经实际执行并读回验证的改动。
不包含设备绑定哈希、真实扇区地址或任何镜像文件。

## 改动概览

| 目标 | 实际操作 | 改动范围 |
| --- | --- | --- |
| `devinfo` | 从本机原始备份生成修改副本 | 仅两个字节 |
| 活动槽 `abl_b` | 用外部 FACTORY ABL 完整替换 | 整个 1 MiB 分区镜像 |
| A 槽 | 未写入 | 无 |
| `boot` / `system` / `xbl` / GPT | 未写入 | 无 |

没有执行擦除、批量刷机或 `setactiveslot`。

## `devinfo` 的准确差异

原始与修改后的 `devinfo` 均为 4096 字节，以 `ANDROID-BOOT!` 开头。二进制
逐字节比较只发现以下两处差异：

| 文件偏移 | 原值 | 新值 | 外部资料中的常见解释 | 本项目证据等级 |
| ---: | ---: | ---: | --- | --- |
| `0x10` | `0x00` | `0x01` | `is_unlocked` | 高 |
| `0x18` | `0x00` | `0x01` | bkerler/edl 补丁代码称 `is_critical_unlocked` | 中 |

其余 4094 字节保持不变。偏移是相对于 `devinfo` 文件开头的字节偏移，不是磁盘
绝对扇区地址。

`0x10` 的含义有 bkerler/edl 代码、常见 Qualcomm `device_info` 结构和 EDL
研究文章相互印证。`0x18` 需要保留限定：bkerler 的实际补丁逻辑把它标为
critical unlock，但同一文件列出的某些结构变体又把 `0x18` 标作
`charger_screen_enabled`。这说明不同 bootloader 的结构布局可能不同。

因此，本项目只能确认：AC204 教程采用这两个偏移，本次样机上的二进制确实只改
了这两个字节，并且与 FACTORY ABL 配对后成功进入 FACTORY 模式。没有 DJI 源码
或带符号的 AC204 ABL 可以独立证明 `0x18` 的正式字段名。

可在本地使用以下只读方式复核，不需要把镜像加入 Git：

```bash
cmp -l <DEVINFO_ORIGINAL> <DEVINFO_PATCHED>
xxd -g 1 -l 64 <DEVINFO_ORIGINAL>
xxd -g 1 -l 64 <DEVINFO_PATCHED>
```

`cmp -l` 的位置从 1 开始计数，因此它显示的位置 17 和 25，分别对应零基偏移
`0x10` 和 `0x18`。

## FACTORY ABL 的准确描述

`abl_b` 不是由本项目在 stock ABL 上修改几个字段生成的。实际操作是把活动 B
槽原有的 1 MiB `abl_b` 完整替换为一个外部取得、同样为 1 MiB 的 FACTORY ABL。

stock 与 FACTORY 镜像逐字节比较共有 156,811 个字节位置不同，说明它们是两个
独立构建，不能描述为简单字段补丁。本项目没有 FACTORY ABL 的源码，也没有尝试
重建或重新签名它。

由于该二进制的来源和再分发授权尚未形成可验证记录，它只保存在本地，绝不进入
Git、release 或公开下载包。

## 写入与恢复顺序

配对写入顺序：

1. 写入 FACTORY `abl_b`；
2. 完整读回 `abl_b` 并校验；
3. 写入仅修改两个字节的 `devinfo`；
4. 完整读回 `devinfo` 并校验；
5. 退出 9008 后冷启动。

配对恢复采用相反的安全顺序：

1. 先恢复原始 `devinfo` 并读回校验；
2. 再恢复原始 `abl_b` 并读回校验。

这样可以避免在恢复过程中留下“stock ABL + 已修改 `devinfo`”的中间状态。

## 实际结果

冷启动成功后，设备显示 `FACTORY mode`，ADB shell 为 root。启动参数中观察到
engineering/secure-debug 状态以及 B 槽后缀。该结果证明这组改动在本次样机和
当时固件上可工作，不证明其他 Action 5 Pro 固件版本必然兼容。

参考代码、教程和技术文章见 [参考资料与来源说明](../REFERENCES.md)。
