# 复现范围与入口

打印盘可以直接用 Bambu Studio 打开。它们已经包含打印网格、预设和摆放，不需要先安装 Python。配置与界面回读见 `printing/ui-readback.json`；现场实际使用的打印板和材料需要匹配工程。

参数化 CAD 与动力学是另外两条复现路径。设计包不包含完整上游 Git 仓库或全部早期试验日志；工作区的 `microduck-sim/` 保留了它们。若换机器，先按 `dynamics/source-lock.json` 获取固定提交，并保持目录关系：

```text
microduck-sim/
  microduck_rl/
  microduck-simulator/
  Microduck-build-tutorial/
  hardware-design-20260912/
    camera/
    slicing/
    whole-robot-20260912/
```

## 动力学

本次使用 Python 3.12.11，MuJoCo 3.7.0，依赖固定在 `dynamics/requirements.txt`。建立环境后，在同一目录结构下依次运行：

```sh
python relocate_paths.py
python dynamics/prepare_full_model.py
python dynamics/run_final_suite.py
python dynamics/render_trace.py dynamics/final-batteryremove60-headremove15.json
```

命令的工作目录是 `whole-robot-20260912/`。`prepare_full_model.py` 依据冻结头部和躯干清单重新组合质量，并运行9组基础完整模型；`run_final_suite.py` 复现本轮修复前的45组基线，原结果43/45。不能把较早的54组附加质量扫描合并计数。

生成配置中使用绝对路径，来自本次本地工作区。换路径后先运行 `relocate_paths.py`，它只更新三个可执行输入清单并保留备份，不改写历史实验记录。随后重新生成最终配置。不得把找不到文件的报错计为仿真失败或通过。

完成上述基线生成后，运行 `python delay-repair-20260912/run_validation.py`，复现补偿后的45组和附加36组延迟检查；纯补偿接口检查为 `python delay-repair-20260912/test_compensation.py`。修复程序从刚生成的基线配置读取路径，因此换目录时不能跳过前述重定位与基线生成。当前判断以 `delay-repair-20260912/repaired-original45-summary.json` 为准，额外失败和评分范围见该目录 README。此包不包含自动安装上游依赖的部署流程。

结果中的旧电池与旧头内电子减重是明示的假设，不能当作已称重值。电机电流是代理量，实际控制循环时延、坐标和供电仍须测量。

## CAD 与干涉

本次 CAD 环境为 Python 3.11、CadQuery 2.8.0、trimesh 5.1.0、manifold3d 3.5.3；具体零件脚本和说明分别在 `assembly/`、`electrical/head-layout/`、上级 `camera/`。完整布尔结果是最终 STL；头盖的 `construction.step` 包含可编辑构造几何，不冒充完整布尔后的光滑曲面实体。

整机轨迹检查入口：

```sh
python assembly/verify_full_assembly.py
```

它重放最终代表轨迹，按刚体坐标检查真实网格。输出中的同刚体接触另查静态报告；OpenRB 加厚预留模型覆盖 PCB 螺孔，需结合恢复螺孔的专门检查，不把空间预留当成实心零件。

## Bambu 重新切片

已安装官方 Bambu Studio 2.7.1.62。切片脚本调用它的本地命令行：

```sh
python slice_compact.py
python slice_head_and_imu.py
```

第一条还依赖 trimesh/numpy。上级 `slicing/embed_presets.py` 会保留 `different_settings_to_system`，确保重新打开时仍使用4道墙、30%填充及支撑；不能只检查命令行返回成功。修改零件后应重新打开工程，检查预览和支撑，再核对保存的配置。本次没有提交打印任务。
