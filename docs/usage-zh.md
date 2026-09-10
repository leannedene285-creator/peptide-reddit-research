# 使用说明

## 一、环境准备（Windows 10/11）

1. 安装 Python 3.10 以上，安装时勾选 "Add Python to PATH"。
2. 下载本仓库（Code → Download ZIP）并解压，或 `git clone`。
3. 在项目目录打开 PowerShell，执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. 把 `.env.example` 复制一份改名为 `.env`，填入 Reddit 凭证和 Anthropic API key。`.env` 已被 `.gitignore` 排除，不会上传。

## 二、运行顺序

```powershell
python fetch-reddit.py        # 拉取，生成 data/raw-posts.csv
python label-with-claude.py   # 打标，生成 data/labeled-posts.csv（可中断后续跑）
python summarize.py           # 汇总，生成 data/report.md
```

打标完成后请删除 `data/raw-posts.csv`，以符合 Reddit 48 小时内删除原始内容的要求。

## 三、可调参数

| 位置 | 参数 | 说明 |
|---|---|---|
| common.py | `SUBREDDITS` | 目标社区 |
| common.py | `KEYWORDS` | 搜索与过滤关键词 |
| common.py | `LOOKBACK_DAYS` | 回溯天数，默认 365 |
| fetch-reddit.py | `COMMENTS_PER_POST` | 每帖最多取多少评论 |
| label-with-claude.py | `MOTIVATIONS` / `PRE_SALE` / `POST_SALE` | 标签体系 |
| .env | `LABEL_MODEL` | 打标模型，默认 claude-sonnet-5 |

## 四、成本估算

以 3,000 条内容、每批 15 条计算，约 200 次调用，Sonnet 级模型费用通常在几美元以内。想再省可在 `.env` 里设置 `LABEL_MODEL=claude-haiku-4-5-20251001`。

## 五、常见问题

- **401 / invalid_grant**：凭证填错，或账号开了两步验证（PRAW 密码模式不支持 2FA，需关闭或改用 refresh token）。
- **403**：该 sub 限制低 karma 账号，或访问申请尚未通过。
- **搜索结果很少**：Reddit 站内搜索单次上限约 250 条，需要更多历史数据时改用 Arctic Shift 存档。
