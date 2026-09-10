"""第三步：读取 data/labeled-posts.csv，生成 data/report.md（动机、顾虑排行 + 典型摘录）。"""

import pandas as pd

import common

logger = common.setup_logger("summarize")

TOP_QUOTES_PER_TAG = 3


def explode_tags(frame: pd.DataFrame, column: str) -> pd.Series:
    tags = frame[column].fillna("").astype(str).str.split("|").explode()
    tags = tags[tags.str.strip().ne("") & tags.ne("无") & tags.ne("无/不适用")]
    return tags.value_counts()


def format_table(counts: pd.Series, total: int) -> str:
    lines = ["| 标签 | 条数 | 占比 |", "|---|---|---|"]
    for tag, count in counts.items():
        lines.append(f"| {tag} | {count} | {count / total:.1%} |")
    return "\n".join(lines)


def top_quotes(frame: pd.DataFrame, column: str, tag: str) -> list[str]:
    matched = frame[frame[column].fillna("").astype(str).str.contains(tag, regex=False)]
    matched = matched[matched["key_quote"].fillna("").astype(str).str.len() > 0]
    matched = matched.sort_values("score", ascending=False).head(TOP_QUOTES_PER_TAG)
    return [f"- r/{row['subreddit']}：{row['key_quote']}（{row['summary_zh']}）"
            for _, row in matched.iterrows()]


def build_section(frame: pd.DataFrame, title: str, column: str) -> str:
    counts = explode_tags(frame, column)
    parts = [f"## {title}", "", format_table(counts, len(frame)), ""]
    for tag in counts.index[:5]:
        parts.append(f"### {tag}")
        parts.extend(top_quotes(frame, column, tag) or ["- （无摘录）"])
        parts.append("")
    return "\n".join(parts)


def build_overview(frame: pd.DataFrame, total_all: int) -> str:
    by_sub = frame["subreddit"].value_counts()
    sentiment = frame["sentiment"].value_counts(normalize=True)
    vendor_rate = frame["mentions_vendor"].astype(str).str.lower().eq("true").mean()
    lines = [
        "# 多肽社群讨论分析报告", "",
        f"- 原始条数：{total_all}，相关条数：{len(frame)}",
        f"- 各社区相关条数：" + "，".join(f"r/{sub} {count}" for sub, count in by_sub.items()),
        f"- 情绪分布：" + "，".join(f"{key} {value:.0%}" for key, value in sentiment.items()),
        f"- 点名具体商家比例：{vendor_rate:.0%}", "",
    ]
    return "\n".join(lines)


def main() -> None:
    common.load_config()
    labeled = pd.read_csv(common.LABELED_CSV)
    relevant = labeled[labeled["relevant"].astype(str).str.lower().eq("true")].copy()
    if relevant.empty:
        raise SystemExit("没有相关条目，请先检查打标结果")

    report = "\n".join([
        build_overview(relevant, len(labeled)),
        build_section(relevant, "购买动机", "motivations"),
        build_section(relevant, "售前顾虑", "pre_sale_concerns"),
        build_section(relevant, "售后顾虑", "post_sale_concerns"),
    ])
    common.REPORT_MD.write_text(report, encoding="utf-8")
    logger.info("报告已生成：%s", common.REPORT_MD)


if __name__ == "__main__":
    main()
