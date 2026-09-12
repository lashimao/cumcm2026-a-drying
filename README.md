# 打印打印｜CUMCM 2026 A 开放建模实验

**把方法做成能运行、能质疑、能改进的公开作品。**

作者：[打印打印（@lashimao）](https://github.com/lashimao)

**[直接下载 PDF](https://raw.githubusercontent.com/lashimao/cumcm2026-a-drying/0cc69c7268ceb1167671aba1dd5a11ef0607d797/paper/%E8%AE%BA%E6%96%87%E9%98%85%E8%AF%BB%E7%89%88.pdf) · [直接下载 Word](https://raw.githubusercontent.com/lashimao/cumcm2026-a-drying/0cc69c7268ceb1167671aba1dd5a11ef0607d797/paper/%E8%AE%BA%E6%96%87%E9%98%85%E8%AF%BB%E7%89%88.docx) · [下载全部材料](https://codeload.github.com/lashimao/cumcm2026-a-drying/zip/0cc69c7268ceb1167671aba1dd5a11ef0607d797)**

下载入口固定到 2026-09-12 水印版本。PDF 和 Word 均为 24 页公开阅读版，带有“打印打印”浅灰斜向水印。Word 保留可编辑文字、公式和表格。

## 为什么公开

我想尝试一种具体的“解构”：把看起来需要身份背书的能力，拆成模型、代码、数据和验证，交给任何愿意检查的人。

这次公开 A 题的参考实现，也留下一道讨论题：当 AI 已经能参与模型、代码和论文的生产，比赛应当怎样评价人的理解、判断与贡献？

欢迎复现、挑错和改进。让作品接受检验，让围绕它的评价和定价接受讨论。

开放模型、程序、计算结果和可检查的假设。AI 深度参与了模型推导、程序实现和文稿制作；本仓库是研究参考实现，不是官方标准答案，不承诺获奖或真实工艺预测精度。

## 直接阅读与下载

| 材料 | 内容 |
|---|---|
| [论文阅读版 PDF](paper/论文阅读版.pdf) / [Word](paper/论文阅读版.docx) | 摘要、正文、参考文献，共 24 页，回答四问 |
| [问题一](results/result1.xlsx) | 前 1800 秒，每秒、每 0.1 厘米的温度与含水率 |
| [问题二](results/result2.xlsx) | 整个固定半径烘干过程的逐秒温度与含水率 |
| [问题三](results/result3.xlsx) / [问题四](results/result4.xlsx) | 全过程逐分钟结果，并追加严格整秒终点 |
| [结果与检验数据](results/summary.json) | 指定表格、网格收敛、解析特例、环境和参数情景 |
| [AI 工具使用详情](AI工具使用详情.pdf) | 原始生成过程、AI 参与和人工核验状态 |
| [发布版本说明](PUBLIC_RELEASE.md) | 公开副本的代码来源、改动和验证范围 |

可点击页首链接直接下载，也可通过 GitHub 的 **Code → Download ZIP** 下载整个仓库。无需购买或加入私域。

## 关键结果与成立条件

| 模型 | 全域含水率严格低于 0.15 kg/kg 的整秒终点 |
|---|---:|
| 问题三：固定半径 | 206958 秒，约 57.4883 小时 |
| 问题四：实测收缩半径及题四物性 | 183926 秒，约 51.0906 小时 |

环境只观测前 4 小时，之后基准方案保持末 1 小时均值。上述时间以这个延拓和题给经验物性为条件。问题四同时改变物性与几何，不能把两题全部时间差归因于收缩；交叉对照见论文与 `summary.json`。

含水率是干基质量比；收缩模型用材料坐标和一致的环带权重。采用径向有限体积、解析稀疏雅可比和 BDF 积分，最终径向区间数为 1280。模型不含端面三维效应、完整汽化潜热或吸附等温线，尚无药材内部测量数据作实验验证。结果显示四位小数，不代表物理精度达到四位小数。

## 本地复现

需要 Python 3.12 和官方 A 题原始附件。请自行从[竞赛官方网站](https://www.mcm.edu.cn/)取得题目及附件，在本地按以下结构放置；本仓库不重新分发官方原件：

```text
data/附件/附件1.xlsx
data/附件/附件2.xlsx
data/附件/附件3/result1.xlsx
data/附件/附件3/result2.xlsx
data/附件/附件3/result3.xlsx
data/附件/附件3/result4.xlsx
```

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python minimal_run.py --input-dir data/附件 --out verification-slice
.venv/bin/python reproduce.py --input-dir data/附件 --out reproduced
```

Windows 使用 `.venv/Scripts/python.exe`。完整复现会运行多个网格、收敛检验及边界和参数情景，耗时取决于电脑。输出写到 `reproduced/`，不会覆盖仓库内的已发布结果。

中文图默认使用 macOS 的 PingFang SC；其他系统可在 `make_figures.py` 中将该名称替换为已安装的中文字体，例如 Noto Sans CJK SC。字体选择不改变数值计算。

源码入口：`drying_model.py` 为方程与求解器；`experiments.py` 为完整数值实验；`export_results.py` 导出规定采样的 Excel；`make_figures.py` 作图；`reproduce.py` 串联整个过程。数值程序无需账号、密钥或联网。

## 数据阅读

`result2.xlsx` 两个数值工作表各含 206959 个数据行，文件较大，打开可能需要时间。其 OOXML 省略了稠密连续单元格的可选坐标属性，保留全部数值、顺序和样式。`result4.xlsx` 的域外空白表示该位置已无药材，并非零含水率；另有实际表面列和半径。显示为 `0.1500` 不用于判断严格不等式，未舍入终点值在说明表中。

## AI、使用范围与许可

本项目使用了 AI 生成与独立 AI 代理检查；代理检查不是参赛队员人工核验。公开许可不等于比赛允许使用。参赛者请遵守[2026 参赛规则](https://www.mcm.edu.cn/html_cn/node/9d8e511fe7a1447b35f53a82c908e2e0.html)及[AI 工具使用规定](https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html)，其中包含赛中交流、发布和人工审查要求。

本仓库自主编写的代码及有权许可的原创材料按 [MIT License](LICENSE) 发布。官方题目与原始附件、外部文献和安装时取得的第三方库不属于本仓库许可范围。原工作流使用的 `math-modeling` Skill 见[上游项目](https://github.com/XiaoMaColtAI/math-modeling-skill)；未找到其三项辅助脚本的明确再分发许可，因此本公开版使用重新编写的本地支持模块，不打包上游 Skill。
