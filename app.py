from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# In-memory wiki data store
wiki_data = {
    "pages": {
        "メインページ": {
            "title": "メインページ",
            "content": """## エミュレーター開発者 Wiki へようこそ

このWikiはエミュレーター開発者のための包括的なリファレンスです。CPU エミュレーション、メモリ管理、グラフィックスレンダリング、そしてデバッグツールに関する情報を提供します。

## 主なカテゴリ

- **CPU アーキテクチャ** — x86、ARM、MIPS、RISC-V などの命令セットアーキテクチャ
- **メモリ管理** — MMU、ページテーブル、キャッシュシミュレーション
- **グラフィックス** — GPU エミュレーション、シェーダー変換、レンダリングパイプライン
- **オーディオ** — DSP エミュレーション、サウンドバッファ管理
- **入出力** — コントローラー、ストレージ、ネットワークエミュレーション
- **デバッグ** — トレーサー、プロファイラー、メモリビューア

## クイックスタート

エミュレーター開発を始めるには、まず [CPU基礎](/page/CPU基礎) を参照してください。""",
            "category": "一般",
            "last_modified": "2026-02-28",
            "author": "Admin"
        },
        "CPU基礎": {
            "title": "CPU基礎",
            "content": """## CPU エミュレーションの基礎

CPU エミュレーションはエミュレーター開発の核心です。ターゲットCPUの命令セットを正確に再現する必要があります。

## 命令サイクル

基本的な命令サイクルは以下の通りです：

1. **フェッチ (Fetch)** — プログラムカウンター (PC) が指すアドレスから命令を取得
2. **デコード (Decode)** — 命令をオペコードとオペランドに分解
3. **実行 (Execute)** — 命令に応じた処理を実行
4. **ライトバック (Write-back)** — 結果をレジスタやメモリに書き戻す

## レジスタ管理

```c
typedef struct {
    uint32_t r[16];   // 汎用レジスタ
    uint32_t pc;      // プログラムカウンター
    uint32_t sp;      // スタックポインター
    uint32_t flags;   // フラグレジスタ
} CPU_State;
```

## 命令デコード

効率的なデコードにはルックアップテーブルを使用します：

```c
typedef void (*InstrHandler)(CPU_State*, uint32_t);
InstrHandler dispatch_table[256];

void cpu_execute(CPU_State* cpu) {
    uint8_t opcode = fetch_byte(cpu);
    dispatch_table[opcode](cpu, opcode);
}
```

## パフォーマンス最適化

- **JIT コンパイル** — ゲストコードをホストコードに動的変換
- **ブロックキャッシュ** — 翻訳済みブロックをキャッシュして再利用
- **スーパーブロック** — 分岐をまたいだ最適化

## 関連記事

- [メモリ管理](/page/メモリ管理)
- [JITコンパイル](/page/JITコンパイル)
- [デバッグツール](/page/デバッグツール)""",
            "category": "CPU",
            "last_modified": "2026-02-28",
            "author": "Developer"
        },
        "メモリ管理": {
            "title": "メモリ管理",
            "content": """## メモリ管理ユニット (MMU)

エミュレーターにおけるメモリ管理は、仮想アドレスから物理アドレスへの変換を担います。

## アドレス空間レイアウト

典型的な32ビットシステムのメモリマップ：

| アドレス範囲 | 用途 |
|---|---|
| 0x00000000 - 0x7FFFFFFF | ユーザー空間 |
| 0x80000000 - 0xBFFFFFFF | カーネル空間 |
| 0xC0000000 - 0xFFFFFFFF | I/O マップ |

## ページテーブル実装

```c
#define PAGE_SIZE 4096
#define PAGE_BITS 12
#define PAGE_MASK (PAGE_SIZE - 1)

typedef struct {
    uint32_t phys_addr;
    uint8_t  flags;      // R/W/X/V bits
} PageEntry;

PageEntry page_table[1 << 20]; // 4GB / 4KB pages

uint32_t translate_addr(uint32_t virt) {
    uint32_t page_num = virt >> PAGE_BITS;
    uint32_t offset   = virt & PAGE_MASK;
    
    if (!(page_table[page_num].flags & FLAG_VALID))
        page_fault(virt);
    
    return page_table[page_num].phys_addr | offset;
}
```

## キャッシュシミュレーション

L1/L2キャッシュのエミュレーションは精度に影響します。

```c
typedef struct CacheLine {
    uint32_t tag;
    uint8_t  data[64];   // 64バイトキャッシュライン
    bool     valid;
    bool     dirty;
} CacheLine;
```

## ヒント

メモリアクセスのエミュレーションはボトルネックになりやすいです。ホストのページシステムを活用したソフトMMUが効果的です。""",
            "category": "メモリ",
            "last_modified": "2026-02-27",
            "author": "Developer"
        },
        "JITコンパイル": {
            "title": "JITコンパイル",
            "content": """## Just-In-Time コンパイル

JIT コンパイルは、インタープリタの柔軟性とネイティブ実行の速度を組み合わせます。

## 基本アーキテクチャ

```
ゲストコード → フロントエンド → IR → 最適化 → バックエンド → ホストコード
```

## 中間表現 (IR)

SSA (Static Single Assignment) 形式が一般的です：

```
# ゲスト: ADD R0, R1, R2
%1 = load_reg R1
%2 = load_reg R2
%3 = add %1, %2
store_reg R0, %3
```

## コードキャッシュ管理

```c
typedef struct {
    uint32_t guest_pc;
    void*    host_code;
    size_t   code_size;
} TranslatedBlock;

#define CACHE_SIZE (64 * 1024 * 1024)  // 64MB

typedef struct {
    uint8_t          code_buffer[CACHE_SIZE];
    size_t           code_ptr;
    TranslatedBlock* blocks[65536];
} CodeCache;
```

## 最適化手法

- **定数畳み込み** — コンパイル時に定数式を計算
- **デッドコード除去** — 使われない演算を削除
- **レジスタ割り当て** — ホストレジスタへの効率的なマッピング
- **チェイニング** — ブロック間のジャンプを直接接続

## プラットフォーム対応

各アーキテクチャ向けのコードジェネレーター：
- **x86_64** — `REX.W` プレフィックス、AVX 命令
- **AArch64** — Thumb2互換、NEON SIMD
- **RISC-V** — 圧縮命令セット対応""",
            "category": "CPU",
            "last_modified": "2026-02-26",
            "author": "Developer"
        },
        "グラフィックスエミュレーション": {
            "title": "グラフィックスエミュレーション",
            "content": """## GPU エミュレーション概要

グラフィックスエミュレーションは、ゲストのGPUコマンドをホストの描画APIに変換します。

## レンダリングパイプライン

```
コマンドバッファ → パーサー → 状態トラッカー → シェーダー変換 → ホストAPI呼び出し
```

## シェーダー変換

ゲストシェーダーをSPIR-Vや GLSLに変換：

```glsl
// 変換後のフラグメントシェーダー
#version 450

layout(location = 0) in vec4 v_color;
layout(location = 0) out vec4 out_color;

void main() {
    out_color = v_color;
}
```

## フレームバッファ管理

```c
typedef struct {
    uint32_t width, height;
    uint32_t format;        // RGBA8, RGB565, etc.
    void*    data;
    size_t   stride;
} Framebuffer;
```

## Vulkan バックエンド

Vulkanを使用した高性能レンダリング実装のポイント：
- **コマンドバッファ** — マルチスレッド対応
- **メモリヒープ** — VRAM/RAM の効率的な管理
- **パイプラインキャッシュ** — シェーダーコンパイルの高速化""",
            "category": "グラフィックス",
            "last_modified": "2026-02-25",
            "author": "Developer"
        },
        "デバッグツール": {
            "title": "デバッグツール",
            "content": """## エミュレーターデバッグツール

効果的なデバッグツールはエミュレーター開発に不可欠です。

## GDB スタブ

GDB リモートデバッグプロトコルの実装：

```c
// RSP (Remote Serial Protocol) パケット形式
// $<data>#<checksum>

void gdb_handle_packet(const char* packet) {
    switch (packet[0]) {
        case 'g': send_registers(); break;
        case 'G': set_registers(packet+1); break;
        case 'm': read_memory(packet+1); break;
        case 'M': write_memory(packet+1); break;
        case 'c': continue_execution(); break;
        case 's': single_step(); break;
    }
}
```

## メモリビューア

```python
def hexdump(data: bytes, offset: int = 0) -> str:
    result = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(
            chr(b) if 32 <= b < 127 else '.' for b in chunk
        )
        result.append(f'{offset+i:08x}  {hex_part:<48}  |{ascii_part}|')
    return '\\n'.join(result)
```

## プロファイラー

```c
typedef struct {
    uint64_t hit_count;
    uint64_t total_cycles;
    uint32_t pc;
} ProfileEntry;

void profiler_record(uint32_t pc, uint64_t cycles) {
    ProfileEntry* entry = &profile_table[pc & PROFILE_MASK];
    entry->hit_count++;
    entry->total_cycles += cycles;
    entry->pc = pc;
}
```

## ブレークポイント管理

- **ソフトウェアブレークポイント** — 命令をトラップ命令で置換
- **ハードウェアブレークポイント** — アドレス比較による停止
- **ウォッチポイント** — メモリアクセスの監視""",
            "category": "デバッグ",
            "last_modified": "2026-02-24",
            "author": "Developer"
        },
    },
    "categories": ["一般", "CPU", "メモリ", "グラフィックス", "オーディオ", "デバッグ", "I/O"]
}

def get_page_list():
    return list(wiki_data["pages"].keys())

def get_categories():
    return wiki_data["categories"]

def parse_markdown(text):
    """Simple markdown to HTML converter"""
    import re
    lines = text.split('\n')
    html = []
    in_code = False
    in_table = False
    
    for line in lines:
        # Code blocks
        if line.startswith('```'):
            if in_code:
                html.append('</code></pre>')
                in_code = False
            else:
                lang = line[3:].strip()
                html.append(f'<pre><code class="language-{lang}">')
                in_code = True
            continue
        
        if in_code:
            html.append(line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
            continue
        
        # Table rows
        if line.startswith('|') and line.endswith('|'):
            if not in_table:
                html.append('<table><tbody>')
                in_table = True
            cells = [c.strip() for c in line.strip('|').split('|')]
            row = ''.join(f'<td>{c}</td>' for c in cells)
            html.append(f'<tr>{row}</tr>')
            continue
        elif in_table and line.startswith('|---'):
            continue
        else:
            if in_table:
                html.append('</tbody></table>')
                in_table = False
        
        # Headings
        if line.startswith('## '):
            html.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            html.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('### '):
            html.append(f'<h3>{line[4:]}</h3>')
        elif line.strip() == '':
            html.append('<br>')
        else:
            # Inline formatting
            processed = line
            # Bold
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
            # Italic
            processed = re.sub(r'\*(.+?)\*', r'<em>\1</em>', processed)
            # Inline code
            processed = re.sub(r'`(.+?)`', r'<code>\1</code>', processed)
            # Links
            processed = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', processed)
            # List items
            if processed.lstrip().startswith('- '):
                processed = f'<li>{processed.lstrip()[2:]}</li>'
            elif re.match(r'^\d+\. ', processed):
                processed = f'<li>{re.sub(r"^\d+\. ", "", processed)}</li>'
            html.append(f'<p>{processed}</p>')
    
    if in_code:
        html.append('</code></pre>')
    if in_table:
        html.append('</tbody></table>')
    
    return '\n'.join(html)

@app.route('/')
def index():
    pages = get_page_list()
    categories = get_categories()
    return render_template('index.html', pages=pages, categories=categories, current_page=None)

@app.route('/page/<path:title>')
def view_page(title):
    pages = get_page_list()
    categories = get_categories()
    page = wiki_data["pages"].get(title)
    if not page:
        return render_template('404.html', pages=pages, categories=categories, title=title), 404
    
    content_html = parse_markdown(page["content"])
    
    # Get related pages (same category)
    related = [p for p, data in wiki_data["pages"].items() 
               if p != title and data.get("category") == page.get("category")]
    
    return render_template('page.html', 
                         page=page, 
                         content_html=content_html,
                         pages=pages, 
                         categories=categories,
                         related=related,
                         current_page=title)

@app.route('/edit/<path:title>', methods=['GET', 'POST'])
def edit_page(title):
    pages = get_page_list()
    categories = get_categories()
    
    if request.method == 'POST':
        content = request.form.get('content', '')
        category = request.form.get('category', '一般')
        
        if title not in wiki_data["pages"]:
            wiki_data["pages"][title] = {"title": title, "author": "User"}
        
        wiki_data["pages"][title]["content"] = content
        wiki_data["pages"][title]["category"] = category
        wiki_data["pages"][title]["last_modified"] = datetime.now().strftime("%Y-%m-%d")
        
        return redirect(url_for('view_page', title=title))
    
    page = wiki_data["pages"].get(title, {"title": title, "content": "", "category": "一般"})
    return render_template('edit.html', page=page, pages=pages, categories=categories, title=title)

@app.route('/new', methods=['GET', 'POST'])
def new_page():
    pages = get_page_list()
    categories = get_categories()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category = request.form.get('category', '一般')
        
        if title:
            wiki_data["pages"][title] = {
                "title": title,
                "content": content,
                "category": category,
                "last_modified": datetime.now().strftime("%Y-%m-%d"),
                "author": "User"
            }
            return redirect(url_for('view_page', title=title))
    
    return render_template('edit.html', page=None, pages=pages, categories=categories, title='')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    pages = get_page_list()
    categories = get_categories()
    results = []
    
    if query:
        for title, page in wiki_data["pages"].items():
            if (query.lower() in title.lower() or 
                query.lower() in page["content"].lower()):
                snippet = page["content"][:200] + "..."
                results.append({"title": title, "snippet": snippet, "category": page.get("category", "")})
    
    return render_template('search.html', 
                         query=query, 
                         results=results, 
                         pages=pages, 
                         categories=categories)

@app.route('/category/<cat>')
def category(cat):
    pages_list = get_page_list()
    categories = get_categories()
    cat_pages = [(t, p) for t, p in wiki_data["pages"].items() if p.get("category") == cat]
    return render_template('category.html', 
                         cat=cat, 
                         cat_pages=cat_pages,
                         pages=pages_list, 
                         categories=categories)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    results = [t for t in wiki_data["pages"] if query in t.lower()]
    return jsonify(results[:10])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
