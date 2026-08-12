# Bookshelf 最小示例

这是一个已经完成首次 ingest 的小型阅读库，用来观察 auto-wiki 的最终形态；不要把示例知识混入自己的正式库。

## 运行

```bash
cp -R examples/bookshelf /tmp/my-bookshelf
cd /tmp/my-bookshelf
python ~/.claude/skills/auto-wiki/references/store.py init wiki/books
python ~/.claude/skills/auto-wiki/references/precheck.py page wiki/books --strict
python ~/.claude/skills/auto-wiki/references/position_encoding.py wiki/books
python ~/.claude/skills/auto-wiki/references/schema.py --report wiki/books
```

浏览器打开 `wiki/books/_report.html`；使用 Obsidian 时选择 **Open folder as vault**，打开 `/tmp/my-bookshelf`。

自己的库不需要复制本示例。在空目录启动 Claude Code 后说 `/auto-wiki init`。
