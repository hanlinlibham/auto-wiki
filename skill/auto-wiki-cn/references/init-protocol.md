# Init 协议：从零建立第一个知识库

> 目标：不要求用户理解“本体、节点、受控关系”等术语。通过最多三轮问答，把用户真实工作流变成可执行骨架，在当前目录建立一个可 ingest、可校验、可查询、可用 Obsidian 打开的最小知识库。

## 边界

- `init` 只负责首次建库或给现有库增加一个新领域，不导入整批历史资料。
- 写入前必须展示建库提案并获得一次确认。
- 不创建远程仓库、不推送 Git、不安装 Obsidian；这些动作另行征得用户同意。
- 已有 `wiki/_index.md` 时不得覆盖。改为说明现有领域，并询问是“增加领域”还是退出 init。
- 用户没提供材料时只完成空库，不编造示例知识。想体验示例时，引导使用 `examples/bookshelf/`。
- 不以“目录建出来了”作为成功。首次 ingest 后至少用一个用户真实问题验收；没有材料时把问题登记为待验收。

## 访谈：最多三轮，一次只问自然语言问题

### 第一轮：用途

问：

> 你拿到一份新材料后通常怎么处理、最后要产出什么？再举三个以后会反复问这个知识库的问题。

从回答中推导：

- Vault 显示名；
- 第一个领域的英文 slug；
- 中文 Hub 名；
- 中心对象；
- 4–6 个节点类型；
- 5–12 个路由关键词；
- 是否适用 `reading-notes` 种子。
- 3–10 个回归问题；初期不追求数百题，真实使用暴露问题后再追加。

不要让用户自己设计 schema。阅读、课程、论文、人物思想等积累默认推荐 `reading-notes`；专业领域没有合适种子就用 `none`。

### 第二轮：第一份材料

问：

> 你现在有一份想放进去的材料吗？可以给文件、链接或直接粘贴一段文字；另外，哪些内容会经常变化、多久值得更新一次？

只记录材料位置和更新节奏，不提前 ingest。区分：

- 稳定知识：定义、框架、长期机制；
- 动态知识：公告、估值、短期论点、证伪条件等，需要定期 source；
- 裸数据：高频行情或海量明细，不重复编译，交给外部数据工具。

### 第三轮：查看方式

问：

> 你准备主要用 Obsidian 浏览，还是先用普通文件夹和浏览器报告？材料有没有“不能联网、不能出本机或必须脱敏”的限制？

Obsidian 只是查看器，两个选项产生相同的 Markdown + SQLite 知识库。

## 建库提案

展示一个不超过十行的提案：

```text
位置：<绝对路径>
库名：<显示名>
首个领域：<slug>（<Hub 中文名>）
中心对象：<中文名称>
范围：<一句话>
节点类型：<4–6 项>
关系：<3–8 项>
路由词：<5–12 项>
冷启动种子：reading-notes | 无
查看器：Obsidian | 浏览器报告
第一份材料：<路径/链接/已粘贴/暂不导入>
真实工作流：<输入 → 判断 → 产出>
动态更新：<对象与节奏/无>
数据边界：<联网、出机、脱敏要求>
首轮验收问题：<3–10 个>
```

问“按这个创建吗？”。用户修改时只重列变化项；确认前不写文件。

## 执行

以下命令里的引擎目录取当前 Skill 根目录，不假设项目内有副本。

1. 确认目标目录存在并可写。没有 Git 仓库时运行 `git init`。
2. 创建 `Inbox/raw/` 和 `wiki/`。
3. 若不存在 `wiki/_config.yaml`，写入：

   ```yaml
   title_proper: <显示名>
   ops_dir: wiki/_ops
   ```

4. 在 `wiki/_ops/onboarding.md` 写入确认过的实例运行约束：

   ```markdown
   # 知识库运行约束

   ## 用途与真实工作流
   <输入 → 判断 → 产出>

   ## 回归问题
   - [ ] <问题；主要验收维度：事实准确性/来源完整性/推理可解释性>

   ## 动态更新
   <需要定期刷新的对象、节奏与可信来源；没有则写“无”>

   ## 数据与合规边界
   <联网、出机、脱敏限制>
   ```

   从 3–10 个真实问题起步。后续只有真实失败才追加问题，不为凑数量生成题库。
5. 调用现有脚手架：

   ```bash
   python <skill>/references/new_domain.py <slug> \
     --direction "<方向>" \
     --central "<中心对象>" \
     --hub "<Hub 中文名>" \
     --desc "<范围>" \
     --types "<逗号分隔的类型>" \
     --keywords "<逗号分隔的路由词>" \
     --seed "<reading-notes|none>"
   ```

6. 读取种子（若有），把生成的 `_ontology.md` 占位表填实：
   - 每种类型必须有一句“什么算、什么不算”的判据和一个例子；
   - 写入本域受控关系词表，逐条声明 `from → to`；
   - 删除 `<填判据>`、`<填例子>` 和所有脚手架占位提示；
   - 不改写六档时间模型和退役协议。
7. 用户选择 Obsidian 时：
   - 写入图谱配置：`python references/new_domain.py --graph`（等价于把 `assets/obsidian/graph.json`
     复制到 Vault 根目录 `.obsidian/graph.json`）。该配置的过滤已排除 hub 与 `_index` 子索引，
     否则索引页会成为链接全库的超级中心节点，把真实结构压成毛球；
   - ⚠️ **Obsidian 会回写这个文件**：用户在 Graph View 里改过过滤/缩放/颜色，关闭面板时
     Obsidian 就用运行态快照覆盖它（实测会清空 `search` 与 `colorGroups`）。
     发现过滤或配色失效，重跑 `--graph` 即可，这是幂等操作；
   - 告诉用户在 Obsidian 选择 **Open folder as vault**，打开的是 Vault 根目录，不是单个领域目录；
   - 不要求安装插件。
8. 用户提供了第一份材料时，立即执行标准 ingest；没有材料则保留空库。
9. 运行确定性验收：

   ```bash
   python <skill>/references/precheck.py page wiki/<slug> --strict
   python <skill>/references/schema.py wiki/<slug>
   python <skill>/references/position_encoding.py wiki/<slug>
   python <skill>/references/schema.py --report wiki/<slug>
   python <skill>/references/precheck.py contract .
   ```

   空库出现 `No pages found.` 是正常结果；有首次 ingest 时必须全部通过。
10. 有首次 ingest 时，从 `wiki/_ops/onboarding.md` 选择一个回归问题执行 query：
    - 回答必须引用 Wiki 页面与来源；
    - 记录“通过 / 失败及缺口”；
    - 失败先修路由、协议或知识缺口，不靠润色答案掩盖；
    - 不因为一个答案失败就换模型，先确认工作流和知识供给是否正确。

## 完成回执

只报告用户下一步真正需要的内容：

```text
知识库已建立：<绝对路径>
- 领域：wiki/<slug>/
- 原料箱：Inbox/raw/
- 图谱报告：wiki/<slug>/_report.html
- Obsidian：Open folder as vault → <绝对路径>（如选择）
- 第一份材料：已 ingest / 尚未提供
- 首轮真实问题：通过 / 待验收 / 失败（缺口：……）

以后可以直接说：
1. “把这篇材料 ingest 进去”
2. “基于 wiki 回答……”
3. “检查 wiki 健康度”
```

若验收失败，修复本次新建文件后重新验收；不得删除或覆盖用户已有内容来换取通过。
