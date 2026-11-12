# Wi-Fi 与无线 ADB 调研

## 已确认组件

系统存在：

- `wlan0` 与对应的 802.11 PHY；
- `wpa_supplicant`：STA 客户端模式；
- `hostapd`：AP/热点模式；
- DHCP 客户端；
- DJI 自有的 `dji_network` 服务。

这证明硬件和基础用户空间支持连接家庭 Wi-Fi。实际产品功能还需要处理
`dji_network` 与自定义服务之间的状态协调，避免双方抢占 `wlan0`。

## 临时 STA 验证流程

凭据只写入设备 `/tmp`，不写入仓库或命令记录：

1. 使用 `wpa_passphrase` 在设备上生成权限为 `0600` 的临时配置。
2. 启用 `wlan0`。
3. 用 `wpa_supplicant` 关联测试网络。
4. 通过驱动状态或 `wpa_cli status` 确认关联。
5. 运行 DHCP 客户端获取地址。
6. 验证网关、NAS 和 DNS 可达性。
7. 测试完成后停止临时进程并删除配置；或直接重启使 `/tmp` 清空。

不要把真实 SSID/PSK 写进 shell 脚本、Git 历史或截图。

## 本次结果

设备成功以 STA 模式关联 5 GHz WPA2 网络并取得 IPv4/IPv6 地址，说明家庭 Wi-Fi
和后续 NAS 同步路线可行。

## 无线 ADB 的现状

FACTORY 模式下观察到 `adbd` 监听 TCP 5555，普通 TCP 探测可以访问该端口。
但标准 ADB 协议握手会导致当前 `adbd` 重启；执行临时 `adb tcpip 5555` 后也未完成
无线 transport 建立。因此目前结论是：

- TCP 监听能力存在；
- 无线 ADB 尚未验证成功；
- 不能仅凭端口开放就宣称无线调试可用。

后续应在保留 USB 恢复路径的前提下检查 `adbd` 启动参数、认证配置和日志。TCP
5555 提供 root shell 时风险很高，只能在可信家庭网络使用，并应通过防火墙限制
来源地址。
