# Bambu Studio 启动问题修复记录

2026-09-12，当前 MacBook Pro。已安装并成功打开官方 **2.7.1.62**，最终 MicroDuck 工程在主界面正常显示，Bambu 命令行切片返回 Success。

2.8.2.61 的官方安装包完整性和应用签名检查通过，但本机完整重装后仍无法正常启动。现有证据不能确定其具体根因；“damaged”提示本身并不证明安装包真的被修改。此次通过换用前一稳定版本恢复工作。

- [官方 2.7.1.62 发布页](https://github.com/bambulab/BambuStudio/releases/tag/v02.07.01.62)。安装包 SHA-256 为 `1e54c25aefc5249d56b63711cf773bed56f14430aafcc34340cd4894aef15896`，与官方发布记录一致。
- 2.8.2.61 包 SHA-256 为 `cf648a95858fb630e1353c4987038df60d6caab693f18411fb95fb809f2d6926`，与官方发布记录一致。
- 已验证代码签名和 Apple 公证；没有关闭 Gatekeeper、移除隔离属性或自行重签名。
- 安装路径：`/Applications/BambuStudio.app`。失败版本的副本留在临时目录，未覆盖用户打印工程。
- 图形界面已回读到 `MicroDuck-addons-X1C-CoolPlate`，10 个模型、0.4mm 喷嘴、Cool Plate、MicroDuck PLA 和 0.20mm 工艺预设均显示正常。

两盘最终切片记录保存在上级 `slicing/slice-result.json` 与 `slicing/head/slice-result.json`。没有连接真实打印机或发送打印任务。
