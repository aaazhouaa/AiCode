package com.aicode.feature.agent.presentation.component

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aicode.R
import com.aicode.core.theme.Radius
import com.aicode.core.theme.Spacing
import com.aicode.core.theme.semanticColors
import com.aicode.core.ui.ExpandableChevronIcon
import com.aicode.feature.settings.domain.model.DashboardTask

/**
 * 位于聊天输入框上方的后台任务面板。
 *
 * 纯原生渲染：任务列表、数量、实时时长都来自 App 的 [DashboardTask] 实时流，
 * 不依赖面板脚本、不查余额、不输出 Token。有运行中任务才显示。
 */
@Composable
fun ProviderDashboardBar(
    /** 面板标题，通常为供应商名。 */
    title: String,
    /** 实时任务列表（与标题行数量同源，保证数量与列表一致）。 */
    tasks: List<DashboardTask>,
    maxExpandedBodyHeight: Dp,
    modifier: Modifier = Modifier,
    forceCollapse: Boolean = false,
    onExpandedChange: (Boolean) -> Unit = {}
) {
    var isExpanded by rememberSaveable { mutableStateOf(false) }

    // 弹窗/键盘叠加时同帧收起。
    val effectiveExpanded = isExpanded && !forceCollapse
    LaunchedEffect(effectiveExpanded) { onExpandedChange(effectiveExpanded) }

    val cardBgColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.98f)
    val borderColor = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.8f)
    val runningTaskCount = tasks.size

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.xs)
            .clip(RoundedCornerShape(Radius.lg))
            .border(1.dp, borderColor, RoundedCornerShape(Radius.lg)),
        shape = RoundedCornerShape(Radius.lg),
        color = cardBgColor
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.md, vertical = 10.dp)
        ) {
            // ── 标题行（点击展开/折叠） ──
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !effectiveExpanded },
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall.copy(fontSize = 15.sp),
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(end = Spacing.md)
                )

                Spacer(Modifier.weight(1f))

                Text(
                    text = stringResource(R.string.dashboard_running_task_count, runningTaskCount),
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.semanticColors.warning,
                    maxLines = 1
                )

                Spacer(Modifier.width(Spacing.sm))

                ExpandableChevronIcon(
                    expanded = effectiveExpanded,
                    contentDescription = if (effectiveExpanded) {
                        stringResource(R.string.common_collapse)
                    } else {
                        stringResource(R.string.common_expand)
                    },
                    size = 18.dp,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // ── 展开区：任务列表 ──
            AnimatedVisibility(
                visible = effectiveExpanded,
                enter = fadeIn(tween(180)) + expandVertically(tween(220)),
                exit = fadeOut(tween(140)) + shrinkVertically(tween(180))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = maxExpandedBodyHeight)
                        .verticalScroll(rememberScrollState())
                        .padding(top = Spacing.sm),
                    verticalArrangement = Arrangement.spacedBy(Spacing.xs)
                ) {
                    tasks.forEach { task ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = task.title,
                                    style = MaterialTheme.typography.bodySmall,
                                    fontWeight = FontWeight.Medium,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                            }
                            Spacer(Modifier.width(Spacing.sm))
                            Text(
                                text = formatElapsed(task.elapsedSec),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.semanticColors.subtleText
                            )
                        }
                    }
                }
            }
        }
    }
}

/** 秒数 → 中文时长（3秒 / 5分12秒 / 1时03分）。 */
private fun formatElapsed(seconds: Long): String {
    val total = seconds.coerceAtLeast(0)
    return when {
        total < 60 -> "${total}秒"
        total < 3600 -> "${total / 60}分${total % 60}秒"
        else -> "${total / 3600}时${(total % 3600) / 60}分"
    }
}
