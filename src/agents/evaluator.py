
import os
import json
import google.generativeai as genai
from typing import List

# --- 定数 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- プロンプトテンプレート ---
PROMPT_TEMPLATE = """
# 役割 (Role):
あなたは、経験豊富なコンテンツレビュアーです。
あなたの任務は、公開されるツイート案が、品質と分かりやすさの基準を満たしているかを確認することです。

# 目的 (Objective):
以下のツイート文案セットをレビューし、公開しても問題ないか、あるいは人間の再確認が必要かを判断してください。

# 評価基準 (Criteria):
1.  **明確さと分かりやすさ:** ツイートの内容は、専門知識がない人にも理解しやすく、明確に書かれていますか？複数の更新情報を含む場合は、箇条書きなどを用いて、内容が整理され、分かりやすく提示されていますか？
2.  **正確性:** ツイートに含まれる情報は、事実に基づいており、誤解を招くような表現はありませんか？
3.  **一貫性:** 複数のツイートがある場合、内容に一貫性があり、自然な流れになっていますか？
4.  **適切なトーン:** 攻撃的、差別的、または不必要に扇動的な言葉遣いを避け、中立的で客観的なトーンを保っていますか？
5. 複数の更新内容がある場合は特に問題ありません。

# 入力ツイート案 (Input):
```
{tweets_text}
```

# 出力形式 (Output Format):
評価結果を、必ず以下のキーを持つJSON形式で出力してください。
- `"evaluation"`: 評価結果。問題なければ `"Approved"`、人間の再確認が必要であれば `"Needs Review"` のいずれか。
- `"reason"`: 判断理由を簡潔に記述してください。

{{
  "evaluation": "...",
  "reason": "..."
}}
"""

def evaluate_tweets(tweets: List[str]) -> dict:
    """
    生成されたツイートのリストをLLMが評価する。

    Args:
        tweets (List[str]): 評価対象のツイート文字列のリスト。

    Returns:
        dict: "evaluation"と"reason"のキーを持つ辞書。失敗時は空の辞書を返す。
    """
    if not GEMINI_API_KEY:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        return {}
    
    if not tweets:
        print("情報: 評価対象のツイートがありません。")
        return {}

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        #model = genai.GenerativeModel('gemini-pro')
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # ツイートリストを整形してプロンプトに埋め込む
        tweets_text = "\n".join([f"--- ツイート{i+1} ---\n{t}" for i, t in enumerate(tweets)])
        prompt = PROMPT_TEMPLATE.format(tweets_text=tweets_text)

        print("LLMにツイート内容の評価をリクエストしています...")
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned_response)

        if "evaluation" in result and "reason" in result:
            print(f"  - 評価成功: {result['evaluation']}")
            print(f"評価: {result['evaluation']}")
            return result
        else:
            print("エラー: LLMのレスポンスに必要なキーが含まれていません。")
            return {}

    except Exception as e:
        print(f"LLMとの通信中にエラーが発生しました: {e}")
        return {}

if __name__ == '__main__':
    print("--- 評価エージェント テスト実行 ---")

    # サンプルデータ（tweet_generatorが生成したツイート案）
    sample_tweets = [
        "【本日の政策更新】\n本日は2件の重要な政策更新がありました。\n\n・博士課程学生の処遇を「研究者」として位置づけ、経済支援を大幅に拡充\n・不登校の児童生徒も念頭においた在宅・フリースクールでの学習支援を明確化\n\n特に博士課程学生の支援については、続けて詳しく解説します。(1/2)\n#チームみらい #政策",
        "【主要な更新】\n博士課程の学生支援の拡充は、日本の科学技術の未来を担う人材への重要な投資です。経済的な不安から研究者の道を諦める若者を減らし、知の創造に専念できる環境を整えることで、国際的な研究競争力の向上を目指します。(2/2)\n#科学技術 #研究者支援"
    ]

    evaluation_result = evaluate_tweets(sample_tweets)

    if evaluation_result:
        print("\n--- 評価結果 ---")
        print(f"評価: {evaluation_result['evaluation']}")
        print(f"理由: {evaluation_result['reason']}")
    else:
        print("処理に失敗しました。")
