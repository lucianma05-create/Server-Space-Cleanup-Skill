# 服务器冗余空间清理 Skill

面向多人共用服务器的 Codex Skill：通过多轮对话盘点个人目录中的大文件、模型权重、数据集、checkpoint、缓存与虚拟环境，给出可审查的清理建议，并且只在用户逐项确认后执行可能破坏数据的操作。

## 特性

- 默认只读盘点，先报告空间占用、类别和大文件，再给出建议。
- 每次会话先确认公共目录，默认模型目录为 `/publicdata/model`，数据集目录为 `/publicdata/data`。
- 对基础模型和可复用数据集进行版本、清单、大小及 SHA-256 校验；不以同名文件作为重复依据。
- 公共目录中不存在的内容采用“复制 → 校验 → 再确认是否删除个人副本”的流程。
- 公共目录为多人可写：Skill 不会自动删除、覆盖、重命名或移动其中的内容。
- checkpoint、微调权重、未知大文件仅作为待审查项，不会自动删除。

## 使用

将本目录放入 Codex 的 skills 目录后，在对话中直接描述需求，例如：

> 请盘点我的个人服务器空间，并给出安全的多轮清理建议。

Skill 会先询问本次个人目录范围，并确认或替换公共模型、数据集路径。每一批删除、迁移或环境移除操作均需要用户明确指定项目编号或路径后再次确认。

## 辅助脚本

两个脚本均为只读：

```bash
# 盘点目录，并默认列出大于等于 1 GiB 的文件
python scripts/inventory.py /data/$USER

# 调整大文件阈值与显示数量
python scripts/inventory.py /data/$USER --min-size-gib 5 --limit 100

# 为单个文件或目录生成 SHA-256 清单
python scripts/fingerprint.py /path/to/model-or-dataset
```

目录级哈希会读取全部文件，面对大型模型或数据集可能耗时较长；应仅在需要确认重复副本时使用。

## 安全边界

- 不检查或操作其他用户的个人目录。
- 不清理可能被活跃任务使用的文件。
- 旧文件不是可删除文件的充分依据。
- 任何证据不足的重复项都标为“未知”或“冲突”，由用户决定如何处理。
- 不使用未经审查的通配符进行删除。

详细工作流见 [SKILL.md](SKILL.md)，本服务器的公共存储规则见 [references/storage-policy.md](references/storage-policy.md)。


## V2：删除后保留原路径

对于已确认与公共模型或数据集完全一致、但项目代码仍使用个人路径的内容，V2 可将原路径切换为指向公共目录的绝对软链接，避免清理后出现“找不到文件”。

先只读验证：

```bash
python scripts/link_to_public.py \
  /data/$USER/models/example \
  /publicdata/model/example \
  --verify
```

确认输出无误且没有活跃任务使用该路径后，才执行切换：

```bash
python scripts/link_to_public.py \
  /data/$USER/models/example \
  /publicdata/model/example \
  --verify --apply
```

脚本会将个人副本改名为同级备份、在原位置创建绝对软链接并验证链接；**不会删除备份**。请先验证原有代码能正常运行，再在对话中明确确认删除脚本输出的那一个备份路径，以实际释放空间。若公共路径不是 `/publicdata` 下，请通过 `--public-root` 显式传入本次已确认的公共根目录。
