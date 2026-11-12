# 第三方工具与二进制说明

本仓库不包含刷机固件或第三方二进制，但实际研究流程使用了以下外部内容。
“本地使用”不代表拥有再分发权。

## EDL 客户端

- 名称：[bkerler/edl](https://github.com/bkerler/edl) 衍生代码
- 用途：Qualcomm Sahara/Firehose 通信、GPT 读取与分区读写
- 许可证标记：GPL-3.0
- 分发状态：未纳入本仓库，安装目录由 `.gitignore` 排除

当前实验环境中的 `edl-tool/` 标记版本为 3.62，并包含 Sahara V3 相关修改，
但该本地目录没有独立 Git 元数据，无法从现有文件证明准确上游仓库和 commit。
因此它只能视为一次实验使用的本地副本，不能作为可复现的固定来源。后续应从
明确的上游地址重新获取，记录 commit，并按照 GPL-3.0 履行相应义务。

EDL 客户端安装的 Python 包是其传递依赖，不复制进本仓库；各依赖继续受各自
许可证约束。

## Firehose programmer

- 本地文件名：`RedMagicCommon_8Gen2_devprg`
- 用途：让 EDL 客户端访问 QCS8550/SM8550 设备的 UFS
- 类型：Qualcomm Firehose programmer ELF
- 分发状态：仅在本地使用，由 `.gitignore` 排除
- 授权状态：未确认公开再分发授权

仓库代码只保留用于拒绝错误 loader 的 SHA-256 指纹，不包含二进制内容。除非
以后获得清晰来源和授权，否则不得上传、打包或随 release 分发该文件。

## FACTORY ABL

- 本地文件名：`abl-factory.img`
- 用途：在已验证的 Action 5 Pro 活动槽上测试 FACTORY 启动路径
- 类型：ARM EFI/ABL 二进制
- 分发状态：仅在本地使用，由 `.gitignore` 排除
- 授权状态：来源和公开再分发授权未形成可验证记录

该文件应按第三方专有固件处理。仓库只能记录兼容性检查方法、写入顺序和恢复
流程，不能发布镜像本体或从镜像中提取的较大代码/数据片段。

## 设备导出和派生文件

原始 ABL、boot、devinfo、GPT、分区备份以及从设备内容生成的修改文件都包含
厂商固件或设备特定数据。即使文件由用户自己的相机读取，也不进入本仓库，
不随 release 分发。

## 本仓库实际提交的内容

公开 Git 树只包含项目自行编写的文档、只读安全包装器和测试。包装器通过子进程
调用外部 EDL 客户端，没有复制或 vendoring 上述第三方源码和二进制。
