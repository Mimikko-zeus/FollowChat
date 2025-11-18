# 贡献指南

感谢您对 FollowChat 项目的关注！我们欢迎所有形式的贡献。

## 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/Mimikko-zeus/FollowChat/issues) 中是否已有相关问题
2. 如果没有，请创建新的 Issue，并包含：
   - 清晰的问题描述
   - 复现步骤（如果是 bug）
   - 预期行为和实际行为
   - 环境信息（操作系统、Python 版本、Node.js 版本等）

### 提交代码

1. **Fork 项目**
   ```bash
   # 在 GitHub 上 Fork 项目
   ```

2. **克隆您的 Fork**
   ```bash
   git clone https://github.com/your-username/FollowChat.git
   cd FollowChat
   ```
   
   注意：将 `your-username` 替换为您自己的 GitHub 用户名。

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

4. **进行开发**
   - 遵循项目的代码风格
   - 添加必要的注释和文档
   - 确保代码可以正常运行

5. **提交更改**
   ```bash
   git add .
   git commit -m "描述您的更改"
   ```
   
   提交信息应清晰描述更改内容，例如：
   - `feat: 添加对话导出功能`
   - `fix: 修复树形图显示问题`
   - `docs: 更新 README 安装说明`

6. **推送并创建 Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   然后在 GitHub 上创建 Pull Request。

## 代码规范

### Python 代码

- 遵循 PEP 8 代码风格
- 使用类型提示（Type Hints）
- 添加必要的文档字符串（docstring）

### TypeScript/JavaScript 代码

- 使用 TypeScript 进行类型检查
- 遵循 ESLint 规则
- 使用有意义的变量和函数名

### 提交信息规范

我们使用约定式提交（Conventional Commits）：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更改
- `style:` 代码格式（不影响代码运行）
- `refactor:` 重构代码
- `test:` 添加或修改测试
- `chore:` 构建过程或辅助工具的变动

## 开发环境设置

请参考 [README.md](README.md) 中的安装说明设置开发环境。

### 开发模式

**后端开发**：
```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端开发**：
```bash
cd frontend/followchat
npm run dev
```

## Pull Request 检查清单

在提交 Pull Request 之前，请确保：

- [ ] 代码可以正常运行
- [ ] 遵循了项目的代码风格
- [ ] 添加了必要的注释和文档
- [ ] 更新了相关的文档（如 README.md）
- [ ] 提交信息清晰明确
- [ ] 没有引入新的警告或错误

## 行为准则

- 尊重所有贡献者
- 接受建设性的批评
- 专注于对项目最有利的事情
- 对其他社区成员表示同理心

## 问题？

如果您有任何问题，请随时：

- 创建 Issue 询问
- 联系项目维护者

感谢您的贡献！🎉

