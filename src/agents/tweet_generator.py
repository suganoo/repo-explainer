
import os
import json
import google.generativeai as genai
from typing import List, Dict

# --- 定数 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- プロンプトテンプレート ---
PROMPT_TEMPLATE = """
# 役割 (Role):
あなたは、政党のSNS広報を担当する、経験豊富な編集長です。

# 目的 (Objective):
以下の「本日の政策更新リスト」を元に、分かりやすい2連投のツイート文案セットを作成してください。

# ルール (Rules):
- **1ツイート目（ヘッドライン）:**
    - 全ての更新の要点を網羅し、箇条書きで簡潔に紹介してください。
    - 末尾に「(1/2)」と付けてください。
    - 最も重要と思われる更新について、次のツイートで詳しく解説することを予告してください。
- **2ツイート目（深掘り解説）:**
    - 【注目】から書き始めてください。
    - 最も重要だと判断した更新を1つだけ選び、その政策が持つ「背景」や「社会的意義」を、より詳しく解説してください。
    - 末尾に「(2/2)」と付けてください。
- 全体を通して、客観的かつ信頼できるトーンを保ってください。
- 1ツイートあたりの文字数は、日本語で280文字以内に厳守してください。
- 出力は、必ず指定されたJSON形式に従ってください。
- アイコンを入れないでください。
- タグも入れないでください。
- 熱意あるトーンにしないでください。そのため!は使わないこと。

# 本日の政策更新リスト (Input):
{summaries_text}

# 出力形式 (Output Format):
"tweets"というキーを持つJSONオブジェクトで出力してください。"tweets"の値は、生成した2つのツイート文（文字列）を格納した配列です。
{{
  "tweets": [
    "ツイート1の本文...",
    "ツイート2の本文..."
  ]
}}
"""

PROMPT_TEMPLATE_SINGLE = """
# 役割 (Role):
あなたは、政党のSNS広報を担当する、経験豊富な編集長です。

# 目的 (Objective):
以下の「本日の政策更新」を元に、分かりやすい単独のツイート文案を作成してください。

# ルール (Rules):
- 政策が持つ「背景」や「社会的意義」まで含めて、1ツイートで完結させてください。
- 客観的かつ信頼できるトーンを保ってください。
- 文字数は、日本語で280文字以内に厳守してください。
- 出力は、必ず指定されたJSON形式に従ってください。
- アイコンを入れないでください。
- タグも入れないでください。
- 熱意あるトーンにしないでください。そのため!は使わないこと。

# 本日の政策更新 (Input):
{summary_text}

# 出力形式 (Output Format):
"tweets"というキーを持つJSONオブジェクトで出力してください。"tweets"の値は、生成した1つのツイート文（文字列）を格納した配列です。
{{
  "tweets": [
    "ツイートの本文..."
  ]
}}
"""

def generate_tweets(summaries: List[Dict]) -> List[str]:
    """
    要約リストから、LLMを使って連投ツイートを生成する。

    Args:
        summaries (List[Dict]): 各更新の要約とタグを含む辞書のリスト。

    Returns:
        List[str]: 生成されたツイート文のリスト。失敗時は空のリストを返す。
    """
    if not GEMINI_API_KEY:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        return []
    
    if not summaries:
        print("情報: 要約リストが空のため、ツイートは生成されません。")
        return []

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        #model = genai.GenerativeModel('gemini-pro')
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # 更新が1件か複数かでプロンプトを切り替える
        if len(summaries) == 1:
            summary_text = f"- {summaries[0]['summary']}"
            prompt = PROMPT_TEMPLATE_SINGLE.format(summary_text=summary_text)
            print("LLMに単独ツイートの生成をリクエストしています...")
        else:
            summaries_text = "\n".join([f"- {s['summary']}" for s in summaries])
            prompt = PROMPT_TEMPLATE.format(summaries_text=summaries_text)
            print("LLMに連投ツイートの生成をリクエストしています...")

        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned_response)

        if "tweets" in result and isinstance(result["tweets"], list):
            print(f"  - {len(result['tweets'])}件のツイートを生成成功")
            for i, tweet in enumerate(result["tweets"], 1):
                print(f"【ツイート {i}】")
                print(tweet)
                print(f"文字数: {len(tweet)}")
                print("-" * 20)
            return result["tweets"]
        else:
            print("エラー: LLMのレスポンスに必要なキーまたは正しい形式が含まれていません。")
            return []

    except Exception as e:
        print(f"LLMとの通信中にエラーが発生しました: {e}")
        return []

if __name__ == '__main__':
    print("--- ツイート生成エージェント テスト実行 ---")

    # サンプルデータ（2件の更新）
    sample_summaries = [
        {
            "summary": "多様な学びの選択肢を確保するため、これまでの在宅学習の記述に「不登校の児童生徒も念頭に」と明確に追記し、フリースクール等での学習継続支援を推進する方針を示しました。",
            "tags": ["教育", "不登校支援", "多様な学び", "在宅学習"]
        },
        {
            "summary": "博士課程の学生を単なる「学生」ではなく対価を得るべき「研究者」と位置づけ、経済的支援を大幅に拡充。これにより、若手が経済的な理由で研究者の道を断念することなく、安心して研究に専念できる環境を目指します。",
            "tags": ["科学技術", "博士課程", "研究者支援", "人材育成", "経済的支援"]
        }
    ]

    generated_tweets = generate_tweets(sample_summaries)

    if generated_tweets:
        print("\n--- 生成結果 ---")
        for i, tweet in enumerate(generated_tweets, 1):
            print(f"【ツイート {i}】")
            print(tweet)
            print(f"文字数: {len(tweet)}")
            print("-" * 20)
    else:
        print("処理に失敗しました。")
