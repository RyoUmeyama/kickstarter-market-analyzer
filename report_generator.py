#!/usr/bin/env python3
"""
レポート生成モジュール
テンプレート + OpenAI API対応
"""

import os
from openai import OpenAI


class ReportGenerator:
    """レポート生成クラス"""

    def __init__(self, api_key=None, model='gpt-4o-mini'):
        """
        Args:
            api_key (str, optional): OpenAI API key
            model (str, optional): モデル名（デフォルト: gpt-4o-mini）
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        # API keyがある場合のみOpenAIクライアントを初期化
        if self.api_key and self.api_key != 'your-openai-api-key-here':
            self.client = OpenAI(api_key=self.api_key)
            self.api_available = True
        else:
            self.client = None
            self.api_available = False

    def generate_report(self, template, kickstarter_url, product_name=''):
        """
        テンプレートに基づいてレポートを生成

        仕様:
        - A1（en_subject）とB1（jp_subject）はGOOGLETRANSLATE関数で連動
        - A2（en_body）とB2（jp_body）もGOOGLETRANSLATE関数で連動
        - A3（プロンプト、日本語）がある場合のみOpenAI APIを使用
          → 英語でレポートを生成 → Google Sheetsで日本語に翻訳

        Args:
            template (dict): テンプレート設定
                {
                    'jp_subject': 日本語件名（GOOGLETRANSLATE関数）,
                    'en_subject': 英語件名,
                    'jp_body': 日本語本文（GOOGLETRANSLATE関数）,
                    'en_body': 英語本文,
                    'jp_prompt': （未使用、B3は空のはず）,
                    'en_prompt': A3のプロンプト（日本語で記載）
                }
            kickstarter_url (str): Kickstarter URL
            product_name (str, optional): 製品名/メーカー名

        Returns:
            dict: 生成されたレポート
                {
                    'jp_subject': 日本語件名（GOOGLETRANSLATE関数の結果）,
                    'en_subject': 英語件名,
                    'jp_body': 日本語本文（GOOGLETRANSLATE関数の結果 or 空文字列）,
                    'en_body': 英語本文
                }
        """
        # 件名のプレースホルダーを置換（GOOGLETRANSLATE関数の結果がそのまま入っている）
        en_subject = self._replace_placeholders(
            template['en_subject'],
            kickstarter_url,
            product_name
        )
        jp_subject = self._replace_placeholders(
            template['jp_subject'],
            kickstarter_url,
            product_name
        )

        # A3（en_prompt）にプロンプトがあるかチェック
        prompt = template.get('en_prompt', '')

        if not prompt or not prompt.strip():
            # プロンプトがない場合: テンプレートの本文をそのまま使用
            en_body = self._replace_placeholders(
                template['en_body'],
                kickstarter_url,
                product_name
            )
            jp_body = self._replace_placeholders(
                template['jp_body'],
                kickstarter_url,
                product_name
            )
        else:
            # プロンプトがある場合: OpenAI APIで英語レポートを生成
            # jp_bodyは空文字列（Google SheetsでGOOGLETRANSLATE関数を使って翻訳してもらう）
            en_body = self._generate_from_prompt(
                prompt,
                kickstarter_url,
                product_name
            )
            # 日本語本文は空文字列（Google SheetsのGOOGLETRANSLATE関数で翻訳）
            jp_body = ''

        return {
            'jp_subject': jp_subject,
            'en_subject': en_subject,
            'jp_body': jp_body,
            'en_body': en_body
        }

    def _generate_from_prompt(self, prompt, kickstarter_url, product_name):
        """
        日本語プロンプトからOpenAI APIで英語レポートを生成

        Args:
            prompt (str): プロンプト（日本語）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            str: 生成された英語レポート
        """
        if not self.api_available:
            print(f"  ⚠️  OpenAI API key not configured. Cannot generate report from prompt.")
            return "Error: OpenAI API key not configured"

        try:
            # プロンプトのプレースホルダーを置換
            processed_prompt = self._replace_placeholders(prompt, kickstarter_url, product_name)

            print(f"  🤖 Calling OpenAI API with Japanese prompt to generate English report...")

            # OpenAI APIを呼び出し（日本語プロンプト → 英語レポート）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional business consultant. The user will provide a prompt in Japanese. Please respond in English with a detailed business report."
                    },
                    {
                        "role": "user",
                        "content": processed_prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7
            )

            generated_report = response.choices[0].message.content.strip()
            print(f"  ✓ English report generated via OpenAI API")

            return generated_report

        except Exception as e:
            print(f"  ❌ Error calling OpenAI API: {e}")
            return f"Error: Failed to generate report from prompt ({str(e)})"

    def _generate_body(self, body_template, prompt_template, kickstarter_url, product_name, language='Japanese'):
        """
        本文を生成

        Args:
            body_template (str): 本文テンプレート
            prompt_template (str): プロンプトテンプレート（空の場合はbody_templateをそのまま使用）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名
            language (str): 言語（Japanese or English）

        Returns:
            str: 生成された本文
        """
        # プロンプトが空の場合は、本文テンプレートのプレースホルダーを置換してそのまま返す
        if not prompt_template or not prompt_template.strip():
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

        # プロンプトがある場合は、OpenAI APIで生成
        if not self.api_available:
            print(f"  ⚠️  OpenAI API key not configured. Using template body as-is.")
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

        try:
            # プロンプトのプレースホルダーを置換
            prompt = self._replace_placeholders(prompt_template, kickstarter_url, product_name)

            print(f"  🤖 Calling OpenAI API for {language} report...")

            # OpenAI APIを呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional business consultant specializing in market analysis for product launches in Japan. Respond in {language}."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7
            )

            generated_body = response.choices[0].message.content.strip()
            print(f"  ✓ {language} report generated via OpenAI API")

            return generated_body

        except Exception as e:
            print(f"  ❌ Error calling OpenAI API: {e}")
            print(f"  ⚠️  Falling back to template body")
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

    def _replace_placeholders(self, text, kickstarter_url, product_name):
        """
        プレースホルダーを置換

        Args:
            text (str): テキスト
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            str: 置換後のテキスト
        """
        if not text:
            return ''

        # {{URL}}を置換
        text = text.replace('{{URL}}', kickstarter_url)
        text = text.replace('{{url}}', kickstarter_url)

        # {{name}}を置換
        if product_name:
            text = text.replace('{{name}}', product_name)
        else:
            text = text.replace('{{name}}', 'Manufacturer')

        return text
