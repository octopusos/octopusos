# Example Vite + React Project

这是一个最小的 Vite + React 示例项目，用于测试 OctopusOS 的扫描功能。

## 结构

- `package.json` - 项目依赖和脚本
- `vite.config.ts` - Vite 配置
- `tsconfig.json` - TypeScript 配置
- `src/App.tsx` - React 组件

## 测试

```bash
# 注册项目
uv run octopusos project add examples/vite-react --id vite-example

# 扫描项目
uv run octopusos scan vite-example

# 查看生成的 FactPack
cat reports/vite-example/*/factpack.json
```
