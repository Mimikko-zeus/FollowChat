# 开源准备清单

在将项目发布到 GitHub 之前，请完成以下检查：

## ✅ 已完成的准备工作

- [x] 创建 LICENSE 文件（MIT 许可证）
- [x] 创建 CONTRIBUTING.md 贡献指南
- [x] 更新 README.md 添加许可证和贡献说明
- [x] 完善 .gitignore 文件
- [x] 创建 Issue 模板（Bug 报告和功能建议）

## 📝 需要您手动完成的事项

### 1. 更新 README.md 中的仓库地址

在 README.md 中，将以下内容：
```bash
git clone https://github.com/your-username/FollowChat.git
```

替换为您的实际 GitHub 仓库地址，例如：
```bash
git clone https://github.com/Mimikko-zeus/FollowChat.git
```

### 2. 更新 CONTRIBUTING.md 中的仓库地址

在 CONTRIBUTING.md 中，将：
- `https://github.com/your-username/FollowChat` 替换为您的实际仓库地址

### 3. 检查敏感信息

确保以下文件不会被提交到仓库：
- `.env` 文件（已在 .gitignore 中）
- 包含 API 密钥的配置文件
- 个人数据库文件（`*.db`, `*.sqlite` 已在 .gitignore 中）

运行以下命令检查是否有敏感信息：
```bash
# 检查是否有 .env 文件被跟踪
git ls-files | grep -E "\.env$"

# 检查是否有数据库文件被跟踪
git ls-files | grep -E "\.(db|sqlite|sqlite3)$"
```

### 4. 初始化 Git 仓库（如果还没有）

```bash
git init
git add .
git commit -m "Initial commit: Open source FollowChat project"
```

### 5. 在 GitHub 上创建仓库

1. 登录 GitHub
2. 点击右上角的 "+" 按钮，选择 "New repository"
3. 填写仓库信息：
   - Repository name: `FollowChat`
   - Description: `一个支持对话树形结构的智能聊天应用`
   - Visibility: 选择 Public（公开）或 Private（私有）
   - **不要**勾选 "Add a README file"（因为我们已经有了）
   - **不要**勾选 "Add .gitignore"（因为我们已经有了）
   - **不要**勾选 "Choose a license"（因为我们已经有了）
4. 点击 "Create repository"

### 6. 推送代码到 GitHub

```bash
# 添加远程仓库（替换为您的实际仓库地址）
git remote add origin https://github.com/your-username/FollowChat.git

# 推送代码
git branch -M main
git push -u origin main
```

### 7. 设置 GitHub 仓库

在 GitHub 仓库页面：

1. **添加仓库描述和主题标签**
   - 点击仓库名称下方的 "⚙️" 图标
   - 添加描述和主题标签（如：`chat`, `ai`, `conversation-tree`, `vue`, `fastapi`）

2. **启用 Issues**
   - 进入 Settings → General → Features
   - 确保 "Issues" 已启用

3. **设置默认分支保护**（可选）
   - Settings → Branches
   - 可以设置 main 分支的保护规则

4. **添加仓库徽章**（可选）
   - 可以在 README.md 中添加更多徽章，如构建状态、代码覆盖率等

### 8. 创建第一个 Release（可选）

1. 在仓库页面，点击 "Releases" → "Create a new release"
2. 填写版本号：`v0.1.0`
3. 添加发布说明
4. 发布

## 🎉 完成！

完成以上步骤后，您的项目就已经成功开源了！

## 📚 后续建议

- 定期更新 README.md 和文档
- 及时回复 Issues 和 Pull Requests
- 保持代码质量和测试覆盖
- 考虑添加 CI/CD 自动化流程
- 添加代码贡献者列表

祝您的开源项目成功！🚀

