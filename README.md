# electron-update-safety

用于 Windows Electron 更新维护的实验性安全工具：在修改前核对来源摘要和版本消费者，始终从新的原始副本开始，并跟踪隔离测试主进程与后端的真实身份。

## 安装与最短示例

```powershell
py -3 -m pip install -e .
electron-update-safety check --source C:\candidate --manifest manifest.json --consumer-root C:\adapter
electron-update-safety stage --source C:\candidate --manifest manifest.json --consumer-root C:\adapter --work-root C:\staging
```

生命周期命令为 `start`、`status`、`wait`、`stop`。`stop` 只向身份一致的可见测试窗口发送正常关闭请求；请让测试应用自行正常退出，再用 `wait` 验证主进程和所有已登记后端均已消失。

清单格式见 `examples/manifest.json`。失败返回非零退出码并输出 JSON。支持 Python 3.10+；真实进程检查仅支持 Windows。

English overview: [README.en.md](README.en.md)。相关项目：[codex-history-compat](https://github.com/catterhu1207-ux/codex-history-compat)、[desktop-adaptation-lab](https://github.com/catterhu1207-ux/desktop-adaptation-lab)。

## 限制

这是实验性源码发布。它不下载、安装或修改任何厂商应用，也不判断第三方包是否获得授权。进程识别依赖 Windows CIM。
