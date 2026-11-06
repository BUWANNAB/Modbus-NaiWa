# 奶蛙 Modbus

Windows 桌面 Modbus 调试工具，提供主站轮询和 Modbus TCP 从站模拟两种模式。收到有效数据后可播放内置奶蛙风格齁笑提示音。

## 功能

- Modbus TCP 与 Modbus RTU（RS-485/串口）主站读取
- 功能码 01、02、03、04，单次读取与周期轮询
- 16 位和 32 位数值解释、字顺序切换、收发日志与 CSV 导出
- 手动写单线圈/保持寄存器；写入默认关闭，每次写入前再次确认
- Modbus TCP 从站模拟，可编辑线圈、离散输入、保持寄存器和输入寄存器
- 抖音奶蛙待机、大笑、挥手、睡觉、打拳、八卦六种动画；连接、读数和写入成功会触发相应动作，右键可预览
- 收到有效数据时播放奶蛙笑声提示音，可关闭或载入本地 WAV

角色图片素材的上游来源与权利说明见 [assets/mascot/ASSETS_NOTICE.md](assets/mascot/ASSETS_NOTICE.md)。

所有地址按协议的 **0 起始地址**填写。部分设备手册使用 1 起始编号，例如手册中的 40001 通常对应软件地址 0；请以设备手册为准。

## 直接运行源码

需要 Windows、Python 3.11 和网络连接以安装依赖：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_app.py
```

## 打包成单文件 EXE

```powershell
.uild_exe.ps1
```

输出位置：`dist\NaiWaModbus.exe`。仓库内也提供已打包的 Windows 64 位版本：`release\NaiWaModbus.exe`。首次启动时单文件程序会解包运行时依赖，启动可能比源码运行慢几秒。

## 使用提示

- 轮询间隔默认 1000 ms；RS-485 总线建议从较慢的间隔开始。
- 写操作默认关闭。请先核对设备、从站地址、寄存器地址和数据范围，再启用写入。
- 从站模拟默认仅监听 `127.0.0.1:1502`，仅本机可连接。要让局域网内的 PLC 连接，可将监听地址改为 `0.0.0.0`，并按现场网络策略开放对应端口。
- 该工具用于 Modbus 通信调试；软件断开连接不能代替设备的物理急停或硬件保护。
- 内置提示音为本项目生成的短促原创合成音效。若要使用指定的抖音原声，可在设置中载入本地 WAV 文件；仓库不附带未授权的网络音频素材。

## 技术

- Python 3.11
- PySide6 Essentials（仅使用 Qt Core/Gui/Widgets）
- PyModbus 3.13
- PyInstaller
