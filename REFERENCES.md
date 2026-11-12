# 参考资料与来源说明

本页区分三种证据：Action 5 Pro 社区教程、通用 Qualcomm/Android 技术资料，
以及本项目自己的实机观察。社区教程用于发现路径，不自动视为权威结论；所有
关键写入都必须由当前设备的 GPT、备份和读回校验重新确认。

## Action 5 Pro 社区资料

### 主要过程参考

- [DJI Action 5 Pro 解 BL、刷机、开启 ADB 视频教程](https://www.bilibili.com/video/BV1qr3t6MEGV/)
  - 本次实验最初参考的操作路线。
  - 视频简介列出了酷安原帖、刷机匣、管理后台和 DashBox 等上游资料。
  - 本项目没有照搬其整合工具，而是把流程拆成只读备份、离线准备、受限写入和
    写后校验。

- [酷安：如何解锁你的大疆 Action 5 Pro（QCS8550）](https://www.coolapk.com/feed/72416034)
  - 上述视频注明的参考来源之一。
  - 页面可能要求使用酷安 App 或登录。

- [全球首个大疆 Action 5 Pro 管理后台](https://www.bilibili.com/video/BV129TQ6kE3L)
  - 上述视频注明的后续功能参考。
  - 与 bootloader 解锁字段本身无直接证据关系。

### 社区工具与后续功能参考

- [刷机匣 GeekFlashTool 资源仓库](https://gitee.com/geekflashtool)
  - 教程中使用的图形化 Qualcomm 工具来源。
  - 本项目没有把刷机匣或其资源包加入仓库。

- [DJIAc5PDashBox（AtomGit）](https://atomgit.com/lqsxy/DJIAc5PDashBox)
- [DJIAc5PDashBox 可访问镜像](https://gitcode.com/lqsxy/DJIAc5PDashBox)
  - Action 5 Pro 管理后台、Wi-Fi 脚本和设备端部署方式的参考。
  - 本项目尚未复制其代码；未来若复用代码，必须先核对许可证并明确标注来源。

教程简介还包含若干网盘整合包。因为其中可能包含来源或授权不清晰的 loader、
FACTORY ABL 和厂商二进制，本仓库不复录这些直接下载地址，也不重新分发文件。

## Qualcomm EDL 与 `devinfo`

- [bkerler/edl](https://github.com/bkerler/edl)
  - Sahara/Firehose、GPT 和分区读取所使用的工具系列，GPL-3.0。

- [bkerler/edl `generic.py` 的 OEM unlock 实现](https://github.com/bkerler/edl/blob/master/edlclient/Library/Modules/generic.py)
  - 代码明确对 `devinfo` 的 `0x10` 和 `0x18` 写入 `1`。
  - 代码注释分别称其为 `is_unlocked` 和 `is_critical_unlocked`，但同文件列出的
    结构变体对 `0x18` 有不同解释，因此 AC204 字段名仍需保留限定。

- [Aleph Security：Exploiting Qualcomm EDL Programmers (2)](https://alephsecurity.com/2018/01/22/qualcomm-edl-2/)
  - 展示 `ANDROID-BOOT!` 格式的 `devinfo`，并记录将 `0x10`、`0x18` 置为 `1`
    的通用 Qualcomm bootloader 解锁案例。
  - 文章研究的是其他 Qualcomm 设备，不是 Action 5 Pro；这里只用来交叉验证
    偏移传统，不能替代 AC204 实机验证。

## A/B 槽与启动判断

- [AOSP：A/B seamless system updates](https://source.android.com/docs/core/ota/ab)
  - 解释 A/B 槽、active/bootable/successful 属性和回退机制。
  - 本项目对 B 槽的判断还结合了 AC204 自身 GPT、内核命令行和根文件系统，
    不是仅凭 AOSP 文档推断。

## 硬件资料

- [Qualcomm QCS8550 产品页](https://www.qualcomm.com/internet-of-things/products/q8-series/qcs8550)
- [Qualcomm QCS8550/QCM8550 Product Brief](https://docs.qualcomm.com/doc/87-61717-1/87-61717-1_REV_D_Qualcomm_Dragonwing_QCS8550_QCM8550_Processors_Product_Brief.pdf)
  - 用于核对 CPU、GPU、内存控制器和视频编解码能力。

- [YMTC UC114 UFS 2.2 Product Brief](https://www.ymtc.com/en/resources/file/20211206/d1dcb33354659b1f7787eafd8b721224.pdf)
  - 用于核对 UC114 系列采用 3D TLC NAND 及容量档位。

- [Rockchip UFS AVL 镜像资料](https://blog.armsom.org/de/articles/030-rockchip-ufs-avl/)
  - 列出样机读取到的精确 YMTC 料号、64 GB、单颗 512 Gb TLC 和 UFS 2.2。
  - 这是交叉资料，不是 YMTC 针对该精确料号的官方 datasheet。

- [Linux Device Tree reserved-memory binding](https://www.kernel.org/doc/Documentation/devicetree/bindings/reserved-memory/reserved-memory.yaml)
  - 用于解释设备树保留内存不会进入普通 Linux 内存分配器。

## 本项目自己的实机证据

以下结论来自设备读数和本地二进制比较，不来自上述网页：

- 当前活动槽为 B，A 槽未写入；
- `devinfo` 只有 `0x10`、`0x18` 两个字节从 `00` 变为 `01`；
- stock `abl_b` 与 FACTORY ABL 是两个完整构建，而非简单字段补丁；
- 配对写入后能启动 FACTORY 模式并取得 root ADB；
- Wi-Fi STA 关联和 DHCP 获取地址成功；
- 无线 ADB TCP 端口存在，但协议握手尚未验证成功。

原始日志、镜像、设备绑定哈希和网络凭据只保存在本地，不作为公开引用附件。
