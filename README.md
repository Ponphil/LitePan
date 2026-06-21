# LitePan v0.3.2-Beta

LitePan 是一个多网盘聚合与管理工具，支持 Web 界面、WebDAV、STRM 生成、媒体整理等功能。

官网 / 文档站：[http://www.litepan.top](http://www.litepan.top)

默认服务端口：**5211**

## 许可证

本项目采用 [PolyForm Noncommercial License 1.0.0](./LICENSE)。

- ✅ 允许：个人学习、研究、测试、 hobby 项目等非商业用途
- ✅ 允许：Fork 仓库用于非商业目的
- ❌ 禁止：任何商业用途（收费服务、集成到商业产品、公司内部商用等）

如需商业授权，请通过 [B 站主页](https://space.bilibili.com/1501989416) 联系作者另行协商。

## 贡献与反馈

- 暂不接受公开 Pull Request（目前主要由个人维护，暂时无法持续审核）
- 如有意愿合作、共同维护此项目，或有使用疑问，请通过 [B 站主页](https://space.bilibili.com/1501989416) 联系我

## 快速启动

```bash
docker run -d \
  --name litepan \
  --restart unless-stopped \
  --network host \
  -e TZ=Asia/Shanghai \
  -p 5211:5211 \
  -v ./data:/app/data \
  -v ./log:/app/log \
  -v ./strm:/app/strm \
  -v ./plugins:/app/plugins \
  ponphil/litepan:latest
```

浏览器访问：`http://localhost:5211`

更多说明见 [DOCKER.md](./DOCKER.md)。


## 目录结构

```
├── api/            # HTTP API
├── core/           # 核心逻辑
├── drivers/        # 各网盘驱动
├── web/            # 前端源码与静态资源
├── webdav/         # WebDAV 服务
├── mediaorganize/  # 媒体整理
├── main.py         # 程序入口
├── config.py       # 配置
├── docker-compose.yml
└── Dockerfile
```

## 支持的网盘驱动

项目包含多种网盘驱动（115网盘、123云盘、百度网盘、夸克网盘、光鸭云盘、移动云盘、天翼云盘等），具体以 `drivers/` 目录为准。


## 免责声明

本项目仅供学习与个人非商业使用。使用各网盘 API 时请遵守对应平台的服务条款。作者不对因使用本项目产生的任何损失负责。
