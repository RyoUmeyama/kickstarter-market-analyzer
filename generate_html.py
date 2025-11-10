#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to Beautiful HTML Generator
MarkdownファイルをGitHub Pages用の美しいHTMLに変換
"""

import markdown
import os
import sys

def convert_md_to_html(md_file, output_file=None):
    """MarkdownをBootstrap付きの美しいHTMLに変換"""

    # Markdownファイルを読み込み
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # MarkdownをHTMLに変換（拡張機能を有効化）
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br',
        ]
    )

    # ファイル名からタイトルを生成
    title = os.path.basename(md_file).replace('.md', '').replace('_', ' ').title()

    # Bootstrap + カスタムCSSでラップ
    full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap" rel="stylesheet">

    <!-- Syntax Highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github.min.css">

    <style>
        body {{
            font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.8;
            color: #333;
            background: #f8f9fa;
        }}

        .container {{
            max-width: 900px;
            margin: 40px auto;
            background: white;
            padding: 40px 50px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 2.2rem;
            font-weight: 700;
        }}

        h2 {{
            color: #34495e;
            border-left: 5px solid #3498db;
            padding-left: 15px;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.7rem;
            font-weight: 600;
        }}

        h3 {{
            color: #555;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.4rem;
            font-weight: 500;
        }}

        h4 {{
            color: #666;
            margin-top: 25px;
            margin-bottom: 12px;
            font-size: 1.2rem;
        }}

        p {{
            margin-bottom: 16px;
            font-size: 1rem;
        }}

        ul, ol {{
            margin-bottom: 20px;
            padding-left: 30px;
        }}

        li {{
            margin-bottom: 8px;
        }}

        table {{
            margin: 25px 0;
            border-collapse: collapse;
            width: 100%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        table thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        table thead th {{
            padding: 15px 12px;
            font-weight: 600;
            text-align: left;
            border: none;
        }}

        table tbody tr {{
            border-bottom: 1px solid #e0e0e0;
            transition: background 0.2s;
        }}

        table tbody tr:hover {{
            background: #f8f9fa;
        }}

        table tbody td {{
            padding: 12px;
        }}

        code {{
            background: #f4f4f4;
            padding: 3px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}

        pre {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}

        pre code {{
            background: transparent;
            padding: 0;
            color: inherit;
        }}

        blockquote {{
            border-left: 4px solid #f39c12;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
            background: #fffbf0;
            padding: 15px 20px;
            border-radius: 4px;
        }}

        strong {{
            color: #2c3e50;
            font-weight: 600;
        }}

        a {{
            color: #3498db;
            text-decoration: none;
            transition: color 0.2s;
        }}

        a:hover {{
            color: #2980b9;
            text-decoration: underline;
        }}

        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 40px 0;
        }}

        .badge {{
            font-size: 0.75em;
            margin-left: 5px;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px 25px;
                margin: 20px auto;
            }}
            h1 {{
                font-size: 1.8rem;
            }}
            h2 {{
                font-size: 1.4rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Syntax Highlighting -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
</body>
</html>
"""

    # 出力ファイル名を決定
    if output_file is None:
        output_file = md_file.replace('.md', '.html')

    # HTMLファイルを保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f'✓ Generated: {output_file}')
    return output_file

def main():
    """メイン処理"""
    import glob

    # consultingディレクトリの全Markdownファイルを変換
    consulting_dir = 'consulting'
    md_files = glob.glob(f'{consulting_dir}/*.md')

    print('Converting Markdown files to Beautiful HTML...\n')

    for md_file in md_files:
        # READMEは除外（インデックスページとして別途作成）
        if 'README' not in md_file:
            html_file = md_file.replace('.md', '.html')
            convert_md_to_html(md_file, html_file)

    # インデックスページを作成
    create_index_page(consulting_dir)

    print('\n✅ Conversion completed!')
    print(f'\nHTML files are saved in: {consulting_dir}/')
    print('\nTo view locally:')
    print(f'  open {consulting_dir}/index.html')
    print('\nTo host on GitHub Pages:')
    print('  1. Commit and push to GitHub')
    print('  2. Enable GitHub Pages in repository settings')
    print('  3. Select "main" branch and "/consulting" folder')

def create_index_page(directory):
    """インデックスページ（トップページ）を作成"""
    import glob

    html_files = glob.glob(f'{directory}/*.html')
    html_files = [f for f in html_files if 'index' not in f]

    # ファイルリストを生成
    file_links = []
    for html_file in sorted(html_files):
        basename = os.path.basename(html_file)
        title = basename.replace('.html', '').replace('_', ' ').title()
        file_links.append(f'<li><a href="{basename}" class="list-group-item list-group-item-action">{title}</a></li>')

    index_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kickstarter Market Analyzer - コンサルティング資料</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap" rel="stylesheet">

    <style>
        body {{
            font-family: 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            max-width: 700px;
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        .subtitle {{
            color: #7f8c8d;
            margin-bottom: 40px;
        }}
        .list-group-item {{
            border: none;
            border-left: 4px solid transparent;
            margin-bottom: 10px;
            border-radius: 8px;
            transition: all 0.3s;
        }}
        .list-group-item:hover {{
            border-left-color: #667eea;
            background: #f8f9fa;
            transform: translateX(5px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Kickstarter Market Analyzer</h1>
        <p class="subtitle">コンサルティング資料</p>

        <h4 class="mb-3">資料一覧</h4>
        <ul class="list-group">
            {''.join(file_links)}
        </ul>

        <div class="mt-5 text-center">
            <small class="text-muted">最終更新: 2025年11月10日</small>
        </div>
    </div>
</body>
</html>
"""

    index_path = f'{directory}/index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)

    print(f'✓ Generated: {index_path}')

if __name__ == '__main__':
    main()
