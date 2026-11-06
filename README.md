# GMAIR 果麦新风 · Home Assistant 集成

把果麦（GMAIR）新风机接入 Home Assistant。走果麦官方云端接口，支持账号密码与手机验证码两种登录方式，登录后自动添加账号下的所有新风机。

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## 功能

**传感器**

| 实体 | 说明 |
|---|---|
| 室内 PM2.5 | 机器内置探头读数 |
| CO2 | 室内二氧化碳浓度 |
| 温度 / 湿度 | 室内环境 |
| 风量 | 当前风量档位值（60–420） |
| 所在城市 | 设备绑定的城市 |
| 室外 AQI / 室外 PM2.5 | 该城市的实时空气质量 |
| 初滤网 / 主滤网 | 滤网状态：正常 / 即将到期 / 立即更换 |

**控制**

| 实体 | 说明 |
|---|---|
| 新风机（fan） | 开关机、调速 |
| 模式（select） | 自动 / 睡眠 / 手动 |
| 辅热（select） | 关闭 / 500W / 1000W |
| 灯光亮度（number） | 0–8 |
| 童锁（switch） | 开关 |

数据每 30 秒轮询一次。

## 安装

### 通过 Marketplace（HACS）添加

1. 打开 **设置 → 应用市场**（旧版本为 HACS）
2. 右上角菜单 → **自定义仓库**
3. 填入 `https://github.com/TinkeringHa/ha-gmair`，类型选 **集成**
4. 搜索「果麦」并安装
5. 重启 Home Assistant

### 手动安装

把 `custom_components/gmair` 整个目录复制到 Home Assistant 配置目录下的 `custom_components/`，重启即可。

```
<config>/custom_components/gmair/
├── __init__.py
├── api.py
├── config_flow.py
├── const.py
├── coordinator.py
├── entity.py
├── fan.py
├── manifest.json
├── number.py
├── select.py
├── sensor.py
├── strings.json
├── switch.py
├── brand/
│   ├── icon.png
│   └── logo.png
└── translations/
    ├── en.json
    └── zh-Hans.json
```

## 配置

**设置 → 设备与服务 → 添加集成 → 搜索 GMAIR / 果麦**

支持两种登录方式：

1. **账号密码登录** —— 输入手机号和密码
2. **手机验证码登录** —— 输入手机号，收到短信后填入验证码（5 分钟内有效）

登录成功后会自动发现账号下的所有新风机，不需要手动选择设备。

### 城市设置

室外 AQI 和室外 PM2.5 需要知道城市。集成会优先读取设备在果麦云端绑定的城市；如果读不到，可以在 **集成 → 配置** 里手动从 493 个城市中选一个（默认北京 / 东城）。

## 已知限制

- 完全依赖果麦云端，断网或厂商接口变更会导致实体不可用
- 未实现本地化控制（局域网直连）
- 登录凭证失效时会在界面上提示重新认证

## 免责声明

本项目为非官方集成，与果麦（GMAIR）官方无关。接口来自对官方小程序正常使用流量的分析，可能随厂商升级而失效。使用风险自负。

## 许可

未附带开源许可证。如需在其他项目中复用，请先联系仓库所有者。
