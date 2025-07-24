import sys
from typing import List, Dict, TypedDict, Union
from langgraph.graph import StateGraph, END

# エージェントの関数をインポート
from agents.github_monitor import fetch_recent_merged_pull_requests
from agents.summarizer import generate_summary_and_tags
from agents.tweet_generator import generate_tweets
from agents.evaluator import evaluate_tweets
from agents.publisher import post_tweets

# --- 1. 状態 (State) の定義 ---
# エージェント間で共有される情報
class AppState(TypedDict):
    pull_requests: List[Dict]  # GitHub監視エージェントからのPR情報
    summaries: List[Dict]     # 要約・タグ付けエージェントからの要約とタグ
    generated_tweets: List[str] # ツイート生成エージェントからのツイート文案
    evaluation_result: Dict   # 評価エージェントからの評価結果
    target_date: str          # 取得対象の日付 (YYYY-MM-DD)
    # フェーズ2で追加される項目:
    # db_save_result:
    # trend_comment: str

# --- 2. エージェント (Node) のラッパー関数定義 ---
# 各エージェントの関数をLangGraphのノードとして機能させるためのラッパー

def github_monitor_node(state: AppState) -> AppState:
    print("\n--- Node: GitHub監視エージェント ---")
    pull_requests = fetch_recent_merged_pull_requests(target_date_str=state.get("target_date"))
    return {"pull_requests": pull_requests}

def summarizer_node(state: AppState) -> AppState:
    print("\n--- Node: 要約・タグ付けエージェント ---")
    all_summaries = []
    for pr in state["pull_requests"]:
        # PRのbodyが空の場合があるため、titleとbodyを結合して渡す
        text_to_summarize = f"タイトル: {pr['title']}\n\n{pr['body']}"
        summary_data = generate_summary_and_tags(text_to_summarize)
        if summary_data:
            all_summaries.append(summary_data)
    return {"summaries": all_summaries}

def tweet_generator_node(state: AppState) -> AppState:
    print("\n--- Node: ツイート生成エージェント ---")
    # フェーズ1ではトレンド分析コメントは空文字列として渡す
    generated_tweets = generate_tweets(state["summaries"])
    return {"generated_tweets": generated_tweets}

def evaluator_node(state: AppState) -> AppState:
    print("\n--- Node: 評価エージェント ---")
    evaluation_result = evaluate_tweets(state["generated_tweets"])
    return {"evaluation_result": evaluation_result}

def publisher_node(state: AppState) -> AppState:
    print("\n--- Node: 投稿エージェント ---")
    success = post_tweets(state["generated_tweets"])
    # 投稿結果を状態に含めることも可能だが、今回は最終ノードなので不要
    return {}

# --- 3. 条件分岐のロジック ---
# 評価結果に基づいて次のノードを決定する
def route_evaluation(state: AppState) -> str:
    print("\n--- Routing: 評価結果のルーティング ---")
    if not state.get("evaluation_result"):
        print("評価結果が取得できませんでした。処理を終了します。")
        return "end"

    evaluation = state["evaluation_result"].get("evaluation")
    reason = state["evaluation_result"].get("reason", "理由なし")

    if evaluation == "Approved":
        print(f"評価結果: Approved. 理由: {reason} -> 投稿エージェントへ")
        return "publisher"
    else:
        print(f"評価結果: Needs Review. 理由: {reason} -> 再度ツイートを生成します。")
        # ここで人間への通知などの処理を追加することも可能
        return "tweet_generator"

# --- 4. LangGraphの構築 ---

def build_graph():
    workflow = StateGraph(AppState)

    # ノードの追加
    workflow.add_node("github_monitor", github_monitor_node)
    workflow.add_node("summarizer", summarizer_node)
    workflow.add_node("tweet_generator", tweet_generator_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("publisher", publisher_node)

    # エッジ（処理の流れ）の定義
    workflow.set_entry_point("github_monitor")
    workflow.add_edge("github_monitor", "summarizer")
    workflow.add_edge("summarizer", "tweet_generator")
    workflow.add_edge("tweet_generator", "evaluator")

    # 条件付きエッジの追加
    workflow.add_conditional_edges(
        "evaluator",
        route_evaluation,
        {
            "publisher": "publisher",
            "tweet_generator": "tweet_generator", # 評価がNGなら再生成
            "end": END,
        },
    )

    # 最終ノードからのエッジ
    workflow.add_edge("publisher", END)

    return workflow.compile()

# --- メイン処理 ---
if __name__ == "__main__":
    print("--- LangGraphベースのツイート生成システムを開始します ---")
    
    # コマンドライン引数から日付を取得
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        print(f"指定された日付: {target_date}")

    app = build_graph()

    # グラフを実行
    # 環境変数にAPIキーが設定されていないとエラーになるため注意
    initial_state = {"target_date": target_date} if target_date else {}
    final_state = app.invoke(initial_state)

    print("\n--- システム処理完了 ---")
    # 最終的な状態を表示（デバッグ用）
    # print(final_state)