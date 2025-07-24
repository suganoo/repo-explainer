
import os
import json
import google.generativeai as genai

# --- 定数 ---
# 環境変数からGemini APIキーを取得
# このキーは、GitHub ActionsのSecretsに設定することを想定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- プロンプトテンプレート ---
# 要件定義で合意した、高品質な要約を生成するためのプロンプト
PROMPT_TEMPLATE = """
# 役割 (Role):
あなたは、政策の動向を市民に分かりやすく伝える、経験豊富な政治ジャーナリストです。

# 目的 (Objective):
以下の政策更新のテキストについて、政策に関心のあるTwitterフォロワーが「何が変わり、なぜそれが重要なのか」を瞬時に理解できるような、100文字程度の要約を作成してください。

# ルール (Rules):
- 必ず「変更点」と「その変更がもたらす影響や目的」の両方を含めてください。
- 専門用語は避け、中学生でも理解できる平易な言葉で表現してください。
- 客観的な事実に徹し、あなたの意見や憶測は含めないでください。
- 出力は、必ず指定されたJSON形式に従ってください。

# 入力テキスト (Input):
```
{pull_request_body}
```

# 出力形式 (Output Format):
"summary"（文字列）と"tags"（文字列の配列、#は不要）の2つのキーを持つJSONオブジェクトで出力してください。
{{
  "summary": "...",
  "tags": ["...", "..."]
}}
"""

def generate_summary_and_tags(pull_request_body: str) -> dict:
    """
    指定されたテキストから、LLMを使って要約とタグを生成する。

    Args:
        pull_request_body (str): 要約対象のテキスト（PRの本文など）。

    Returns:
        dict: "summary"と"tags"のキーを持つ辞書。失敗時は空の辞書を返す。
    """
    if not GEMINI_API_KEY:
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        return {}

    try:
        # モデルの初期化
        genai.configure(api_key=GEMINI_API_KEY)
        #model = genai.GenerativeModel('gemini-pro')
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # プロンプトの生成
        prompt = PROMPT_TEMPLATE.format(pull_request_body=pull_request_body)

        print("LLMに要約とタグの生成をリクエストしています...")
        response = model.generate_content(prompt)

        # LLMの出力からJSON部分を抽出
        # "```json\n{...}\n```" のような形式で返ってくることがあるため
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        
        result = json.loads(cleaned_response)

        # 簡単なバリデーション
        if "summary" in result and "tags" in result:
            print("  - 生成成功")
            print(f"要約: {result['summary']}")
            print(f"タグ: {result['tags']}")
            return result
        else:
            print("エラー: LLMのレスポンスに必要なキーが含まれていません。")
            return {}

    except Exception as e:
        print(f"LLMとの通信中にエラーが発生しました: {e}")
        return {}

if __name__ == '__main__':
    # このファイルを直接実行した際のテスト用コード
    print("--- 要約・タグ付けエージェント テスト実行 ---")
    
    # サンプルテキスト（博士課程学生の支援拡充）
    sample_body = """
    ### 現状認識・課題分析
    * 日本の博士課程進学率はOECD諸国の中でも最低レベルです。
    * 若手が研究者のキャリアを選びづらくなっており、次世代の科学技術を担う高度人材の供給基盤が急速に弱体化しています。
    * 博士課程の学生は、学生としての身分ゆえに、知の対価を受け取れていません。
    * このような経済的な不安定さが、研究への集中を妨げる大きな要因となっています。
    ### 政策概要
    * 博士課程に通う方を「学生」ではなく、「研究を遂行するプロフェッショナルな仕事」を遂行する「研究者」として位置づけます。
    * そうすることで、知の価値に対する対価を保証し、リサーチ・アシスタント（RA）経費等の支援水準を、生活費を十分に賄えるレベルへと大幅に引き上げます。
    """
    
    summary_data = generate_summary_and_tags(sample_body)
    
    if summary_data:
        print("\n--- 生成結果 ---")
        print(f"要約: {summary_data['summary']}")
        print(f"タグ: {summary_data['tags']}")
    else:
        print("処理に失敗しました。")

