package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.ui.Messages
import dev.sentinelseed.jetbrains.util.Seeds

/**
 * Action to insert the standard Sentinel alignment seed
 */
class InsertSeedAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return

        val seed = Seeds.STANDARD
        val tokenCount = Seeds.estimateTokenCount(seed)

        WriteCommandAction.runWriteCommandAction(project) {
            editor.document.insertString(editor.caretModel.offset, seed)
        }

        Messages.showInfoMessage(
            project,
            "Sentinel standard seed inserted (~$tokenCount tokens)",
            "Sentinel"
        )
    }

    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }
}
