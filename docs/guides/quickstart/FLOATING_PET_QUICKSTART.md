# FloatingPet 快速开始指南

## 5 分钟快速测试

### 1. 启动测试 (二选一)

#### 方式 A: 使用测试脚本 (推荐)
```bash
cd /Users/pangge/PycharmProjects/AgentOS
./test_floating_pet.sh
```

#### 方式 B: 手动启动
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app
# 然后打开浏览器访问 http://localhost:8080
```

### 2. 基础测试 (2 分钟)

1. **看到 FAB**: 右下角应该显示一个蓝色圆形按钮 (🤖)
2. **拖拽测试**: 长按并拖动按钮,松手后自动吸边
3. **面板测试**: 轻点按钮,面板弹出,宠物在跳舞
4. **关闭测试**: 点击背景或按 Esc 关闭面板

### 3. 功能测试 (3 分钟)

在面板中测试三个快捷按钮:

- **💬 Chat**: 应跳转到 Chat 页面
- **✅ New Task**: 弹出输入框,输入任务描述并创建
- **📚 Knowledge**: 跳转到 Knowledge Playground

### 4. 高级测试 (可选)

- **位置记忆**: 拖动 FAB 后刷新页面,位置应保持
- **响应式**: 缩小浏览器窗口 (< 768px),面板布局变为垂直
- **键盘**: 按 `Alt+P` 打开面板,按 `Esc` 关闭

---

## 常见问题

### Q: FAB 按钮没有显示?
**A**: 检查控制台是否有错误:
```javascript
// 在浏览器控制台中
console.log(window.floatingPet);
```

### Q: 拖拽不流畅?
**A**: 确保浏览器支持 Pointer Events API (Chrome 90+, Safari 14+)

### Q: 任务创建失败?
**A**: 检查后端 `/api/tasks` 端点是否正常:
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"description":"Test task","status":"pending"}'
```

### Q: 如何自定义配置?
**A**: 修改 `index.html` 中的初始化参数:
```javascript
window.floatingPet = new FloatingPet({
    petType: 'cat',              // 改为猫咪 🐱
    initialPosition: 'top-right', // 改为右上角
    dragThreshold: 10,            // 增大拖拽阈值
});
```

### Q: 如何禁用 FloatingPet?
**A**: 注释掉 `index.html` 中的初始化脚本即可

---

## 快速命令

```bash
# 启动测试
./test_floating_pet.sh

# 查看组件状态 (在浏览器控制台)
window.floatingPet.state

# 手动打开面板
window.floatingPet.openPanel()

# 清除保存的位置
localStorage.removeItem('agentos_floating_pet_position')
location.reload()
```

---

## 下一步

- 📖 阅读完整文档: `FLOATING_PET_DELIVERY.md`
- 🎨 自定义样式: 编辑 `static/css/floating-pet.css`
- 🔧 修改逻辑: 编辑 `static/js/components/FloatingPet.js`
- 🐛 报告问题: 提交 Issue

**享受 FloatingPet! 🤖**
