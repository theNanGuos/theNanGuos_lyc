# WU-WEB-003 候选播放器与版本入口

**Goal：** 将装饰性音频竖条改为真实播放位置控件，使每个候选拥有独立音量，并从作品页进入现有结果页选择版本。

**Architecture：** 使用同一 HTMLAudioElement/Pinia 播放器作为时间事实源；`TrackProgress` 只可视化播放比例并支持 seek，不声称展示真实振幅。音量按 `audio_id` 保存。

**实际状态：** 见 [`STATUS.md`](../STATUS.md)。

## 1. WU 合同

| 项目 | 内容 |
|---|---|
| WU ID | `WU-WEB-003` |
| 所属阶段 / 里程碑 | P10 / M6 |
| 设计事实源 | [M6 交互与作品管理增强设计](../designs/2026-07-15-post-mvp-ux-library-design.md) |
| 前置依赖 | `WU-WEB-002`、`WU-SUNO-002` |
| 后续依赖 | `WU-QA-002` |

## 2. 范围

允许修改/替换 `frontend/src/components/Waveform.vue`，以及 `GlobalPlayer.vue`、`ResultPage.vue`、`WorksPage.vue`、player store、路由引用、样式和相关单元/E2E 测试。

必须实现：

- 新建语义明确的 `TrackProgress`，按 `currentTime / duration` 填充，支持点击、拖动和键盘 seek，并提供 slider 可访问属性；
- 结果页和全局播放器复用该控件，只有当前候选随音频事件更新；
- `volumeByAudioId: Record<string, number>`，候选首次默认 0.75，切换后恢复各自音量；结果页与全局播放器对同一候选保持一致；
- 作品行的标题、封面和“查看 N 个版本”进入已有 `/generations/{request_id}/result`；不新建页面；
- 作品页可保留首候选快捷播放，但取消固定首候选下载，具体版本在结果页播放和下载；版本数使用实际保留数，不回退为固定 2。

## 3. 非范围

- 不做音频振幅分析、缓存真实 waveform 或新增音频处理依赖；
- 不实现播放队列、倍速、跨进程播放位置、候选重排或新详情页；
- 不承担删除任务，删除归 `WU-API-002`。

## 4. 实施顺序

1. 先为比例计算、pointer/keyboard seek、当前候选更新、独立音量和版本路由补失败测试。
2. 建立 `TrackProgress` 的受控 props/events 和可访问语义，再替换全部 `Waveform` 引用。
3. 将时间事件接入 player store；处理 duration 未知、切歌、暂停、结束和媒体错误。
4. 增加按 `audio_id` 的音量映射，并验证两个候选互不联动。
5. 调整作品页版本入口和结果页候选数，补浏览器闭环。

## 5. 验证与完成标准

运行 player/UI 单元测试、类型检查、生产构建和“作品页 → 结果页 → 选择候选 → seek → 调音量 → 下载”的 Chromium E2E，并检查结果页与作品页 1440×1024 截图。

完成标准：竖条填充与实际播放位置同步且可 seek；两个候选的音量互不联动；所有保留版本可明确选择、播放和下载；不新增详情路由；旧装饰组件无残余引用；验证证据只写入 `STATUS.md`。

## 6. 风险与回滚

同一音频元素切换候选时可能产生迟到事件，store 必须用当前 `audio_id` 过滤。拖动与 `timeupdate` 竞争时以最终 pointer/keyboard 目标为准。出现问题时可回退视觉组件，但不得恢复误导性的固定进度或共享候选音量。
