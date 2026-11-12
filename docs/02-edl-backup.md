# 进入 9008 与只读备份

## 识别 9008

相机进入 Qualcomm EDL 后，主机应看到 `05c6:9008`。macOS 可查看 USB
设备树，Linux 可使用 `lsusb`。不要把普通 ADB、Fastboot 或充电接口误认为
EDL。

```bash
python3 action5_edl.py doctor \
  --edl-script <EDL_REPO>/edl.py \
  --loader <LOCAL_FIREHOSE_PROGRAMMER> \
  --python <VENV_PYTHON>
```

`doctor` 只检查依赖、loader 指纹和 USB 状态，不读写分区。

用于实验的 EDL 客户端和 programmer 是仓库外部依赖。开始新的可复现实验前，
应记录 EDL 上游 URL、准确 commit、许可证和 programmer 指纹；来源不完整的
本地副本不得作为发布包的一部分。

## 推荐备份顺序

1. `printgpt`：观察各 UFS LUN 及分区名称。
2. `gpt`：导出 GPT 和 rawprogram 元数据。
3. 解析 rawprogram，建立“分区名 → LUN/起始扇区/长度”清单。
4. 先备份小型启动关键分区，包括 `devinfo`、`abl_a`、`abl_b`、
   `boot_a`、`boot_b`、`xbl_a` 和 `xbl_b`。
5. 对备份文件计算 SHA-256，并复制到另一块存储介质。
6. 在副本上重新校验 SHA-256，确认恢复材料真正可读。

默认不要读取或公开 `userdata`。其中可能包含网络凭据、相机配置、媒体索引
和个人数据。

## 为什么不能照抄扇区地址

EDL 的 `rs` 直接使用 LUN、起始扇区和数量。任何一个字段错误都会读错位置；
若换成写命令，后果更严重。因此扇区参数只能来自同一设备、同一次维护窗口中
刚导出的 GPT，不能来自截图、教程或另一台相机。

## 备份完整性

备份清单至少记录：

- 逻辑分区名；
- LUN；
- 起始扇区、扇区数和扇区大小；
- 输出文件长度；
- SHA-256；
- 工具版本和采集时间。

公开仓库只记录字段定义，不保存真实清单。
