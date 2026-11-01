package com.aicode.feature.git.data

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Git 提交页筛选条件的持久化。
 *
 * 按仓库路径分别记录：退出页面、关闭 App、重启手机后都保持，只有用户主动切换
 * 筛选条件（选「全部提交者」或换一个人）才会改动。用 SharedPreferences 而非
 * DataStore：这里只是两个同步读写的小字符串，没必要为它引入一条异步流。
 */
@Singleton
class GitFilterSettingsRepository @Inject constructor(
    @param:ApplicationContext context: Context
) {
    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    /** 该仓库上次选中的提交者；null 表示「全部提交者」。 */
    fun authorFilter(repoPath: String?): String? =
        repoPath?.let { prefs.getString(KEY_AUTHOR_PREFIX + it, null) }

    fun setAuthorFilter(repoPath: String?, author: String?) {
        if (repoPath == null) return
        prefs.edit().apply {
            if (author == null) remove(KEY_AUTHOR_PREFIX + repoPath)
            else putString(KEY_AUTHOR_PREFIX + repoPath, author)
        }.apply()
    }

    private companion object {
        const val PREFS_NAME = "git_filter_prefs"
        const val KEY_AUTHOR_PREFIX = "author:"
    }
}
