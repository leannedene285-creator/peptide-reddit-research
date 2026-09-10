"""第二步：读取 data/raw-posts.csv，用 Claude 批量打标签，输出 data/labeled-posts.csv。

输出只保留标签、简短摘录和元数据，不保留全文，便于满足 48 小时删除原始数据的要求。
支持断点续跑：已打标的 id 会被跳过。
"""

import json
import os
import time

import anthropic
import pandas as pd

import common

logger = common.setup_logger("label")

MODEL = os.getenv("LABEL_MODEL", "claude-sonnet-5")
BATCH_SIZE = 15
MAX_TEXT_CHARS = 1500
RETRY_LIMIT = 3

MOTIVATIONS = ["减脂减重", "伤病恢复", "抗衰老", "增肌健身", "皮肤/毛发", "睡眠/情绪",
               "认知/精力", "好奇尝试", "无/不适用"]
PRE_SALE = ["供应商是否靠谱", "纯度/第三方检测", "价格对比", "物流/海关", "支付方式",
            "合法性/合规", "如何选品/剂量", "无"]
POST_SALE = ["到货状态/包装", "复溶/保存", "批次差异/效果不符", "副作用", "客服响应",
             "退换货", "无"]

SYSTEM_PROMPT = f"""你是市场研究分析师。下面是若干条来自 Reddit 多肽相关社区的公开帖子或评论。
请对每一条做结构化标注，只输出 JSON 数组，不要任何解释、不要 Markdown 代码块。

每个元素字段：
- "id": 原样返回
- "relevant": 是否与购买/使用多肽产品相关（true/false）
- "motivations": 购买动机，从 {json.dumps(MOTIVATIONS, ensure_ascii=False)} 中选 0-3 个
- "pre_sale_concerns": 售前顾虑，从 {json.dumps(PRE_SALE, ensure_ascii=False)} 中选 0-3 个
- "post_sale_concerns": 售后顾虑，从 {json.dumps(POST_SALE, ensure_ascii=False)} 中选 0-3 个
- "sentiment": "positive" / "neutral" / "negative"
- "mentions_vendor": 是否点名了具体商家（true/false）
- "key_quote": 最能代表该条观点的一句原文，不超过 12 个英文单词，没有则为空字符串
- "summary_zh": 一句话中文概括，不超过 30 字

不相关的条目 relevant 设为 false，其余字段填空列表/空字符串。"""


def load_pending(frame: pd.DataFrame) -> pd.DataFrame:
    if not common.LABELED_CSV.exists():
        return frame
    done_ids = set(pd.read_csv(common.LABELED_CSV)["id"].astype(str))
    pending = frame[~frame["id"].astype(str).isin(done_ids)]
    logger.info("已完成 %d 条，剩余 %d 条", len(done_ids), len(pending))
    return pending


def build_batch_prompt(batch: pd.DataFrame) -> str:
    items = []
    for _, row in batch.iterrows():
        text = f"{row['title']}\n{row['body']}".strip()[:MAX_TEXT_CHARS]
        items.append({"id": str(row["id"]), "subreddit": row["subreddit"], "text": text})
    return json.dumps(items, ensure_ascii=False)


def parse_response(raw_text: str) -> list[dict]:
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def label_batch(client: anthropic.Anthropic, batch: pd.DataFrame) -> list[dict]:
    prompt = build_batch_prompt(batch)
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return parse_response(response.content[0].text)
        except (json.JSONDecodeError, anthropic.APIError) as error:
            logger.warning("第 %d 次尝试失败: %s", attempt, error)
            time.sleep(2 * attempt)
    logger.error("批次放弃，起始 id=%s", batch.iloc[0]["id"])
    return []


def merge_labels(batch: pd.DataFrame, labels: list[dict]) -> pd.DataFrame:
    label_frame = pd.DataFrame(labels)
    if label_frame.empty:
        return label_frame
    label_frame["id"] = label_frame["id"].astype(str)
    meta_columns = ["id", "kind", "subreddit", "score", "created_at"]
    meta = batch[meta_columns].copy()
    meta["id"] = meta["id"].astype(str)
    merged = meta.merge(label_frame, on="id", how="inner")
    for column in ("motivations", "pre_sale_concerns", "post_sale_concerns"):
        merged[column] = merged[column].apply(lambda value: "|".join(value or []))
    return merged


def append_to_csv(frame: pd.DataFrame) -> None:
    write_header = not common.LABELED_CSV.exists()
    frame.to_csv(common.LABELED_CSV, mode="a", header=write_header,
                 index=False, encoding="utf-8-sig")


def main() -> None:
    common.load_config()
    client = anthropic.Anthropic(api_key=common.require_env("ANTHROPIC_API_KEY"))
    raw = pd.read_csv(common.RAW_CSV).fillna("")
    pending = load_pending(raw)

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending.iloc[start:start + BATCH_SIZE]
        labels = label_batch(client, batch)
        merged = merge_labels(batch, labels)
        if not merged.empty:
            append_to_csv(merged)
        logger.info("进度 %d/%d", min(start + BATCH_SIZE, len(pending)), len(pending))

    logger.info("打标完成，结果在 %s", common.LABELED_CSV)


if __name__ == "__main__":
    main()
