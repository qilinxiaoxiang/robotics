# 再生成和验收

使用 Python 3.11，在独立环境安装 `requirements.txt`。所有尺寸单位为毫米。CAD 不需要连接打印机或登录云服务。

依次运行：

1. `camera/build_camera_mount.py`：生成相机两件及相机占位装配 STEP。
2. `head/build_head.py`：从随附的 `head/source-head-6.npz` 生成改孔头壳、曲面垫座和内压板。
3. `battery/build_battery_backpack.py`：从随附框架网格生成托盘和垫架。
4. `battery/build_electronics_and_audio.py`：生成最终版本硬盖、电子板和音频盒，替换第三步的基础硬盖。
5. `battery/render_and_verify.py`，然后 `battery/verify_full_local_assembly.py`；另运行 `head/render_assembly.py`：复核局部装配几何。电池检查依赖前一步生成的绑带参考。
6. `slicing/prepare_profiles.py`、`slicing/slice_parts.py`、`slicing/slice_head.py`：使用本机已安装的官方 Bambu Studio，生成 X1 Carbon / 0.4 / PLA / 0.20mm 切片。
7. `python slicing/embed_presets.py slicing/fit-parts.3mf slicing/MicroDuck-addons-X1C-CoolPlate.3mf`；再运行 `python slicing/embed_presets.py slicing/head/head-with-camera-mount.3mf slicing/head/MicroDuck-head-X1C-CoolPlate.3mf`，打包可在界面保留参数的工程。

头壳独立切片，使用 `slicing/head-process.json` 的树状支撑配置。STL 是打印方向；命名含 assembly、reference 或 envelope 的文件用于装配或占位，不是打印零件。

验收文件包括 camera/verification.json、head/validation.json、head/assembled-camera-clearance.json、battery/design-metrics.json、battery/full-local-collision-check.json，以及每盘切片的 slice-result.json。每盘必须 return_code=0 且包含 sliced_plates，保留实际耗材和时间；模型更新后需重切，旧切片不能当作新版本证据。Bambu 的 info/render 操作会覆盖 result.json，因此切片结果另存为 slice-result.json。

Bambu Studio 的命令行导出默认不会为新用户配置打包全部预设。最终工程另将预设嵌入工程，避免打开后回退默认参数。CLI 参数中的输出文件名必须为文件名，输出目录另用 outputdir；两者均传绝对路径会错误拼接。
