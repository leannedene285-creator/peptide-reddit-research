"""第一步：从 Reddit 拉取近 12 个月的多肽相关帖子与评论，存为 data/raw-posts.csv。

只读操作，不发帖、不评论、不投票。作者信息不落盘，只保留内容与元数据。
"""

import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import praw

import common

logger = common.setup_logger("fetch")

# 每个关键词在单个 sub 内最多取多少帖子；Reddit 搜索单次上限约 250
POSTS_PER_QUERY = 250
# 每条帖子最多取多少评论，避免热帖把请求额度吃光
COMMENTS_PER_POST = 60
# 两次搜索之间的间隔秒数，保证远低于 100 次/分钟
SEARCH_PAUSE_SECONDS = 1.0


def build_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=common.require_env("REDDIT_CLIENT_ID"),
        client_secret=common.require_env("REDDIT_CLIENT_SECRET"),
        username=common.require_env("REDDIT_USERNAME"),
        password=common.require_env("REDDIT_PASSWORD"),
        user_agent=common.require_env("REDDIT_USER_AGENT"),
    )


def to_row(kind: str, subreddit: str, item_id: str, parent_id: str,
           title: str, body: str, score: int, created_utc: float) -> dict:
    return {
        "kind": kind,
        "subreddit": subreddit,
        "id": item_id,
        "parent_id": parent_id,
        "title": title,
        "body": body,
        "score": score,
        "created_at": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
    }


def collect_comments(submission, subreddit: str) -> list[dict]:
    # replace_more(limit=0) 只展开已加载的评论，不额外请求折叠区，节省额度
    submission.comments.replace_more(limit=0)
    rows = []
    for comment in submission.comments.list()[:COMMENTS_PER_POST]:
        body = comment.body or ""
        if len(body) < common.MIN_TEXT_LENGTH:
            continue
        if body.strip() in ("[deleted]", "[removed]"):
            continue
        rows.append(to_row("comment", subreddit, comment.id, submission.id,
                           "", body, comment.score, comment.created_utc))
    return rows


def collect_subreddit(reddit: praw.Reddit, name: str, cutoff: datetime) -> list[dict]:
    subreddit = reddit.subreddit(name)
    seen_ids: set[str] = set()
    rows: list[dict] = []
    for keyword in common.KEYWORDS:
        try:
            results = subreddit.search(keyword, sort="new", time_filter="year",
                                       limit=POSTS_PER_QUERY)
            for submission in results:
                created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if created < cutoff or submission.id in seen_ids:
                    continue
                seen_ids.add(submission.id)
                full_text = f"{submission.title}\n{submission.selftext or ''}"
                if not common.contains_keyword(full_text):
                    continue
                rows.append(to_row("post", name, submission.id, "", submission.title,
                                   submission.selftext or "", submission.score,
                                   submission.created_utc))
                rows.extend(collect_comments(submission, name))
        except Exception as error:  # 单个关键词失败不影响整体，记录后继续
            logger.warning("r/%s 关键词 %s 拉取失败: %s", name, keyword, error)
        time.sleep(SEARCH_PAUSE_SECONDS)
        logger.info("r/%s 关键词 %s 完成，累计 %d 条", name, keyword, len(rows))
    return rows


def main() -> None:
    common.load_config()
    reddit = build_reddit_client()
    reddit.read_only = True
    cutoff = datetime.now(timezone.utc) - timedelta(days=common.LOOKBACK_DAYS)

    all_rows: list[dict] = []
    for name in common.SUBREDDITS:
        all_rows.extend(collect_subreddit(reddit, name, cutoff))

    frame = pd.DataFrame(all_rows).drop_duplicates(subset=["id"])
    frame.to_csv(common.RAW_CSV, index=False, encoding="utf-8-sig")
    logger.info("已写入 %s，共 %d 条（帖子 %d，评论 %d）",
                common.RAW_CSV, len(frame),
                (frame["kind"] == "post").sum(), (frame["kind"] == "comment").sum())
    logger.info("提醒：原始数据请在 48 小时内完成打标并删除，以符合 Reddit 数据政策")


if __name__ == "__main__":
    main()
