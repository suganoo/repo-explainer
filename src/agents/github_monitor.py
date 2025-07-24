import os
from datetime import datetime, timedelta, timezone
from github import Github, GithubException

# --- 定数 ---
GITHUB_TOKEN = os.environ.get("GITHUB_API_TOKEN")
TARGET_REPO = "team-mirai/policy"

def fetch_recent_merged_pull_requests(repo_name: str = TARGET_REPO, target_date_str: str = None) -> list[dict]:
    """
    指定されたGitHubリポジトリから、過去24時間以内、または指定された日付にマージされたPull Requestを取得する。
    GitHub Search APIを使用して効率的にフィルタリングを行う。

    Args:
        repo_name (str): 対象リポジリ名 (例: "owner/repo")
        target_date_str (str, optional): 取得対象の日付文字列 (例: "2025-07-19").
                                         指定しない場合、過去24時間以内のPRを取得する。

    Returns:
        list[dict]: マージされたPRの情報のリスト。各PRは辞書形式。
                     取得失敗時は空のリストを返す。
    """
    if not GITHUB_TOKEN:
        print("エラー: 環境変数 GITHUB_API_TOKEN が設定されていません。")
        return []

    try:
        g = Github(GITHUB_TOKEN)

        base_query = f"is:pr is:merged repo:{repo_name}"

        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                # 指定日の00:00:00から翌日の00:00:00まで
                query_since = target_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_until = (target_date + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
                date_query = f"merged:{query_since}..{query_until}"
                print(f"  - 指定日付: {target_date_str} のPRを検索します (UTC: {query_since} から {query_until} まで)")
            except ValueError:
                print(f"エラー: 無効な日付形式です。YYYY-MM-DD形式で指定してください: {target_date_str}")
                return []
        else:
            # 過去24時間の時刻を計算
            since_time = datetime.now(timezone.utc) - timedelta(days=1)
            query_since = since_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            date_query = f"merged:>{query_since}" # 24時間前から現在まで
            print(f"  - 過去24時間以内のPRを検索します (UTC: {query_since} から現在まで)")

        full_query = f"{base_query} {date_query}"
        print(f"  - GitHub Search APIでクエリを実行中: {full_query}")

        # Search APIはIssueとPRを返すため、is:prでフィルタリング
        # 検索結果はIssueオブジェクトとして返される
        issues_and_prs = g.search_issues(query=full_query)
        
        print("  - 検索結果のフィルタリングとデータ抽出を開始します...")

        merged_prs = []
        for item in issues_and_prs:
            # 検索結果がPull Requestであることを確認
            if hasattr(item, 'pull_request') and item.pull_request:
                # PullRequestオブジェクトとして扱う
                pr = item.pull_request
                
                # Search APIのmergedクエリは厳密だが、念のため最終確認
                if pr.merged_at:
                    print(f"  - 発見: PR #{item.number} {item.title} (Merged: {pr.merged_at})")
                    merged_prs.append({
                        "number": item.number,
                        "title": item.title,
                        "body": item.body if item.body else "", # bodyがNoneの場合があるため空文字列に
                        "url": item.html_url,
                        "merged_at": pr.merged_at.isoformat(),
                        "author": item.user.login
                    })
        
        print(f"{len(merged_prs)}件のマージ済みPull Requestが見つかりました。")
        print("  - GitHub監視エージェントの処理が完了しました。")
        return merged_prs

    except GithubException as e:
        print(f"GitHub APIエラーが発生しました: {e}")
        if e.status == 403 and 'rate limit exceeded' in str(e).lower():
            print("  - レートリミットに達しました。しばらく待ってから再試行してください。")
            # Search APIのレートリミットはCore APIとは別なので注意
            # g.get_rate_limit().search を参照すべきだが、ここでは簡略化
        return []
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        return []

if __name__ == '__main__':
    print("--- GitHub監視エージェント テスト実行 ---")
    
    print("\n--- 過去24時間のPRを取得 --- ")
    recent_pulls_24h = fetch_recent_merged_pull_requests()
    if recent_pulls_24h:
        for pr_data in recent_pulls_24h:
            print(f"PR #{pr_data['number']}: {pr_data['title']}")
    else:
        print("過去24時間以内にマージされたPRはありませんでした。")

    print("\n--- 特定の日付 (2025-07-19) のPRを取得 --- ")
    recent_pulls_specific_date = fetch_recent_merged_pull_requests(target_date_str="2025-07-19")
    if recent_pulls_specific_date:
        for pr_data in recent_pulls_specific_date:
            print(f"PR #{pr_data['number']}: {pr_data['title']}")
    else:
        print("2025-07-19にマージされたPRはありませんでした。")

    print("\n--- 無効な日付形式の例 --- ")
    fetch_recent_merged_pull_requests(target_date_str="2025/07/19")